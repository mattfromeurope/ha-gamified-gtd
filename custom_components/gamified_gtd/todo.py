"""Todo list entities mirroring the GTD lists (shared, assigned via attribute)."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.todo import TodoItem, TodoItemStatus, TodoListEntity, TodoListEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, EVENT_DATA_UPDATED, TODO_LISTS, TASK_DONE, TASK_OPEN
from .manager import GTDManager


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the four shared GTD todo lists (todo.gtd_inbox, ... — one entity per
    GTD list, shared across persons like Better ToDo; assignment via attribute)."""
    manager: GTDManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GTDTodoListEntity(manager, list_key, name) for list_key, name in TODO_LISTS.items()
    )


class GTDTodoListEntity(TodoListEntity):
    """One todo entity per GTD list; writes through to the manager's storage.

    The todo entities are the Companion-App/calendar-compatible mirror: HA's built-in
    todo card works on them, and completing an item routes through
    complete_task so XP/Caps/Karma are awarded even without the custom card.
    Rich task fields (assigned_to, context, priority, ...) are exposed as entity
    attributes under 'tasks' keyed by task id.
    """

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(self, manager: GTDManager, list_key: str, name: str) -> None:
        self._manager = manager
        self._list_key = list_key
        self._attr_name = name
        self._attr_unique_id = f"{manager.entry_id}_{list_key}"

    # Updates are event-driven (EVENT_DATA_UPDATED), not polled. NOTE: bus.async_listen
    # passes the event as an argument (async_run_hass_job calls target(*args)), so the
    # listener MUST accept it — a zero-arg listener raises TypeError on every event and
    # never runs (entities then only refresh via the 30s poll = visible UI lag).
    _attr_should_poll = False

    @callback
    def _handle_coordinator_update(self, event=None) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_DATA_UPDATED, self._handle_coordinator_update)
        )

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Build HA TodoItems from the manager's tasks of this list."""
        items = []
        for task in self._manager.data["tasks"].values():
            if task["list"] != self._list_key:
                continue
            items.append(
                TodoItem(
                    uid=task["id"],
                    summary=task["title"],
                    status=TodoItemStatus.COMPLETED
                    if task["status"] == TASK_DONE
                    else TodoItemStatus.NEEDS_ACTION,
                    due=date.fromisoformat(task["due"]) if task.get("due") else None,
                    description=task.get("notes") or None,
                )
            )
        return items

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """State attributes for the custom tasks card.

        IMPORTANT: HA does NOT put `todo_items` into the state attributes of a todo
        entity (the frontend gets items via websocket) — so we expose them explicitly
        here as plain dicts. Without this key the custom card sees no tasks at all
        ("list cards show nothing") even though the built-in todo card works.
        Also carries per-task metadata (assigned_to, context, project, ...) under
        'tasks' keyed by task id.
        """
        items = [
            {
                "uid": item.uid,
                "summary": item.summary,
                "status": str(item.status),  # StrEnum -> "needs_action" / "completed"
                "due": item.due.isoformat() if item.due else None,
                "description": item.description,
            }
            for item in (self.todo_items or [])
        ]
        tasks = {
            task["id"]: {
                "assigned_to": task.get("assigned_to"),
                "context": task.get("context"),
                "project_id": task.get("project_id"),
                "priority": task.get("priority"),
                "time_estimate": task.get("time_estimate"),
                "energy": task.get("energy"),
                "tags": task.get("tags", []),
                "status": task["status"],
                "xp_awarded": task.get("xp_awarded"),  # for the quest card's reward estimate
                # notification fields so the edit form can prefill them
                "due_time": task.get("due_time"),
                "reminders": task.get("reminders", []),
                "location": task.get("location"),
                "overdue_repeat": task.get("overdue_repeat"),
            }
            for task in self._manager.data["tasks"].values()
            if task["list"] == self._list_key
        }
        return {"todo_items": items, "tasks": tasks}

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """HA todo 'add item' -> creates the task via the manager (in this list).
        NOTE: ServiceCall's first argument is hass (since HA 2024.x) — the old
        ServiceCall(domain, service, data) signature silently produced an empty
        data dict and every write-through raised KeyError."""
        await self._manager.add_to_inbox(
            ServiceCall(
                self.hass,
                DOMAIN,
                "add_to_inbox",
                {
                    "title": item.summary,
                    "notes": item.description or "",
                    "list": self._list_key,
                    "due": item.due.isoformat() if item.due else None,
                },
            )
        )

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """HA todo 'update item': completing routes through complete_task (gamification!),
        reopening sets the task back to open."""
        if item.status == TodoItemStatus.COMPLETED:
            await self._manager.complete_task(
                ServiceCall(self.hass, DOMAIN, "complete_task", {"task_id": item.uid})
            )
        else:
            task = self._manager.get_task(item.uid)
            task["status"] = TASK_OPEN
            task["completed_at"] = None
            await self._manager._save()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """HA todo 'remove items' -> delete via the manager."""
        for uid in uids:
            if uid in self._manager.data["tasks"]:
                await self._manager.remove_task(
                    ServiceCall(self.hass, DOMAIN, "remove_task", {"task_id": uid})
                )
