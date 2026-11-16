"""LLM / voice assistant tools for conversation agents (Assist "Control Home Assistant").

Registered via homeassistant.helpers.llm — the agent then gets tools like
list_tasks, add_task, complete_task, get_state, choose_perk, … All of them only
call the existing manager services logic, so behavior is identical to the
services/cards.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import llm

from .const import DOMAIN, TASK_DONE, TASK_OPEN

LIST_OPTIONS = ["inbox", "next_actions", "waiting_for", "someday_maybe"]


def _call(data: dict[str, Any]):
    """Wrap a plain dict as a ServiceCall-like object (the manager only uses .data)."""
    return SimpleNamespace(data=data)


class GamifiedGTDAPI(llm.API):
    """Tool set exposed to LLM conversation agents.

    Registered once in async_setup via llm.async_register_api; HA shows it in the
    agent's 'Control Home Assistant' tool list. Every tool delegates to the manager,
    so behavior is identical to services and cards.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            "Gamified GTD",
            "https://github.com/mattfromeurope/ha-gamified-gtd",
            DOMAIN,
        )

    def _manager(self):
        """The (first) manager instance — tools operate on the first config entry."""
        managers = self.hass.data[DOMAIN].get("managers", [])
        if not managers:
            raise ValueError("Gamified GTD is not set up")
        return managers[0]

    async def async_get_tools(self, context: llm.Context) -> list[llm.Tool]:
        """Declare all tools with their parameter schemas (voluptuous -> JSON schema)."""
        return [
            llm.Tool(
                name="list_tasks",
                description=(
                    "List GTD tasks. Filters: person (default: first profile), list, "
                    "assigned_to, tags, due (today/overdue/week), status (open/done/all), sort. "
                    "Each task includes a ready-to-read 'speech' line."
                ),
                parameters=vol.Schema(
                    {
                        vol.Optional("person"): cv.string,
                        vol.Optional("list"): vol.In(LIST_OPTIONS),
                        vol.Optional("assigned_to"): cv.string,
                        vol.Optional("tags"): vol.Any(cv.string, [cv.string]),
                        vol.Optional("due"): vol.In(["today", "overdue", "week"]),
                        vol.Optional("status"): vol.In(["open", "done", "all"]),
                        vol.Optional("sort"): vol.In(["stored", "priority", "due"]),
                    }
                ),
            ),
            llm.Tool(
                name="add_task",
                description="Add a task (to the inbox by default). Returns the task id.",
                parameters=vol.Schema(
                    {
                        vol.Required("title"): cv.string,
                        vol.Optional("list"): vol.In(LIST_OPTIONS),
                        vol.Optional("notes"): cv.string,
                        vol.Optional("due"): cv.string,
                        vol.Optional("due_time"): cv.string,
                        vol.Optional("priority"): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
                        vol.Optional("assigned_to"): cv.string,
                        vol.Optional("tags"): vol.Any(cv.string, [cv.string]),
                        vol.Optional("context"): cv.string,
                        vol.Optional("time_estimate"): vol.Coerce(float),
                        vol.Optional("energy"): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
                        vol.Optional("project_id"): cv.string,
                        vol.Optional("reminders"): vol.Any([vol.Coerce(int)], cv.string),
                    }
                ),
            ),
            llm.Tool(
                name="complete_task",
                description="Mark a task done (grants XP/caps/karma, may level up). By task_id or exact title (+list).",
                parameters=vol.Schema(
                    {
                        vol.Optional("task_id"): cv.string,
                        vol.Optional("title"): cv.string,
                        vol.Optional("list"): vol.In(LIST_OPTIONS),
                        vol.Optional("person"): cv.string,
                    }
                ),
            ),
            llm.Tool(
                name="clarify_task",
                description="Process an inbox task: decision = next_action/project/waiting_for/someday/done.",
                parameters=vol.Schema(
                    {
                        vol.Required("task_id"): cv.string,
                        vol.Required("decision"): vol.In(
                            ["next_action", "project", "waiting_for", "someday", "done"]
                        ),
                        vol.Optional("context"): cv.string,
                        vol.Optional("project_id"): cv.string,
                        vol.Optional("project_name"): cv.string,
                        vol.Optional("desired_outcome"): cv.string,
                        vol.Optional("person"): cv.string,
                    }
                ),
            ),
            llm.Tool(
                name="get_state",
                description="Full FNV profile of a person: level, xp, karma, caps, SPECIAL, skills, perks, quests.",
                parameters=vol.Schema({vol.Optional("person"): cv.string}),
            ),
            llm.Tool(
                name="allocate_skill_points",
                description="Distribute skill points from a level-up to a skill.",
                parameters=vol.Schema(
                    {
                        vol.Optional("person"): cv.string,
                        vol.Required("skill"): cv.string,
                        vol.Required("points"): vol.Coerce(int),
                    }
                ),
            ),
            llm.Tool(
                name="choose_perk",
                description="Choose a perk (available every 2 levels; requirements are enforced).",
                parameters=vol.Schema(
                    {
                        vol.Optional("person"): cv.string,
                        vol.Required("perk"): cv.string,
                        vol.Optional("special_stat"): cv.string,
                        vol.Optional("skill"): cv.string,
                    }
                ),
            ),
            llm.Tool(
                name="create_project",
                description="Create a project (quest).",
                parameters=vol.Schema(
                    {
                        vol.Required("name"): cv.string,
                        vol.Optional("desired_outcome"): cv.string,
                        vol.Optional("due"): cv.string,
                    }
                ),
            ),
            llm.Tool(
                name="complete_project",
                description="Complete a quest (pays automatic quest XP/caps).",
                parameters=vol.Schema({vol.Required("project_id"): cv.string}),
            ),
            llm.Tool(
                name="review",
                description="Start or complete the weekly review (auto-checked checklist, bonus XP).",
                parameters=vol.Schema(
                    {
                        vol.Optional("person"): cv.string,
                        vol.Required("action"): vol.In(["start", "complete"]),
                    }
                ),
            ),
            llm.Tool(
                name="redeem_reward",
                description="Spend caps on a reward from the shop.",
                parameters=vol.Schema(
                    {
                        vol.Optional("person"): cv.string,
                        vol.Required("reward"): cv.string,
                    }
                ),
            ),
        ]

    async def async_call_tool(self, tool: llm.Tool, args: dict[str, Any], context: llm.Context):
        """Dispatch a tool call to the matching _tool_<name> method."""
        manager = self._manager()
        handler = getattr(self, f"_tool_{tool.name}", None)
        if handler is None:
            raise ValueError(f"Unknown tool: {tool.name}")
        return await handler(manager, args)

    # ------------------------------------------------------------------
    # tool implementations
    # ------------------------------------------------------------------

    async def _tool_list_tasks(self, manager, args: dict[str, Any]) -> dict[str, Any]:
        """list_tasks: filter tasks (list/assigned/tags/due/status), sort, and return
        them with a ready-to-read 'speech' line for voice assistants."""
        from datetime import date, timedelta

        tasks = list(manager.data["tasks"].values())
        if args.get("list"):
            tasks = [t for t in tasks if t["list"] == args["list"]]
        if args.get("assigned_to"):
            tasks = [t for t in tasks if t.get("assigned_to") == args["assigned_to"]]
        if args.get("tags"):
            tags = {args["tags"]} if isinstance(args["tags"], str) else set(args["tags"])
            tasks = [t for t in tasks if tags & set(t.get("tags", []))]
        status = args.get("status", "open")
        if status == "open":
            tasks = [t for t in tasks if t["status"] == TASK_OPEN]
        elif status == "done":
            tasks = [t for t in tasks if t["status"] == TASK_DONE]
        due_filter = args.get("due")
        today = date.today()
        if due_filter == "today":
            tasks = [
                t
                for t in tasks
                if t.get("due") and date.fromisoformat(t["due"]) <= today
            ]
        elif due_filter == "overdue":
            tasks = [
                t
                for t in tasks
                if t.get("due") and date.fromisoformat(t["due"]) < today
            ]
        elif due_filter == "week":
            tasks = [
                t
                for t in tasks
                if t.get("due") and date.fromisoformat(t["due"]) <= today + timedelta(days=7)
            ]
        sort = args.get("sort", "stored")
        if sort == "priority":
            tasks.sort(key=lambda t: (t.get("priority", 3), t.get("due") or "9999", t["title"]))
        elif sort == "due":
            tasks.sort(key=lambda t: (t.get("due") or "9999", t.get("priority", 3), t["title"]))
        out = []
        for t in tasks:
            due_txt = t.get("due") or "no due date"
            speech = f"{t['title']} — {t['list'].replace('_', ' ')}, priority {t.get('priority', 3)}, {due_txt}"
            out.append(
                {
                    "task_id": t["id"],
                    "title": t["title"],
                    "list": t["list"],
                    "status": t["status"],
                    "due": t.get("due"),
                    "priority": t.get("priority"),
                    "context": t.get("context"),
                    "assigned_to": t.get("assigned_to"),
                    "tags": t.get("tags", []),
                    "project_id": t.get("project_id"),
                    "speech": speech,
                }
            )
        return {"count": len(out), "tasks": out}

    async def _tool_add_task(self, manager, args: dict[str, Any]) -> dict[str, Any]:
        """add_task: create a task (inbox by default) with all optional fields."""
        return await manager.add_to_inbox(_call(args))

    async def _tool_complete_task(self, manager, args: dict[str, Any]) -> dict[str, Any]:
        """complete_task: by task_id, or by exact open-task title (+optional list)."""
        task_id = args.get("task_id")
        if not task_id:
            title = args.get("title")
            if not title:
                raise ValueError("Provide task_id or title")
            matches = [
                t
                for t in manager.data["tasks"].values()
                if t["title"] == title
                and (not args.get("list") or t["list"] == args["list"])
                and t["status"] == TASK_OPEN
            ]
            if not matches:
                raise ValueError(f"No open task titled '{title}'")
            task_id = matches[0]["id"]
        return await manager.complete_task(_call({"task_id": task_id, "person": args.get("person")}))

    async def _tool_clarify_task(self, manager, args: dict[str, Any]) -> dict[str, Any]:
        """clarify_task: process an inbox task (next_action/project/waiting_for/...)."""
        return await manager.clarify(_call(args))

    async def _tool_get_state(self, manager, args: dict[str, Any]) -> dict[str, Any]:
        """get_state: full FNV profile (level/xp/karma/caps/SPECIAL/skills/perks/quests)."""
        return manager.get_state(_call({"person": args.get("person")}))

    async def _tool_allocate_skill_points(self, manager, args: dict[str, Any]) -> dict[str, Any]:
        """allocate_skill_points: spend level-up skill points on a skill."""
        return await manager.allocate_skill_points(_call(args))

    async def _tool_choose_perk(self, manager, args: dict[str, Any]) -> dict[str, Any]:
        """choose_perk: pick a perk when a choice is pending (requirements enforced)."""
        return await manager.choose_perk(_call(args))

    async def _tool_create_project(self, manager, args: dict[str, Any]) -> dict[str, Any]:
        """create_project: start a quest (name / desired outcome / deadline)."""
        return await manager.create_project(_call(args))

    async def _tool_complete_project(self, manager, args: dict[str, Any]) -> dict[str, Any]:
        """complete_project: finish a quest (automatic quest XP/caps payout)."""
        return await manager.complete_project(_call(args))

    async def _tool_review(self, manager, args: dict[str, Any]) -> dict[str, Any]:
        """review: action=start -> start_review, action=complete -> complete_review."""
        if args["action"] == "start":
            return await manager.start_review(_call({"person": args.get("person")}))
        return await manager.complete_review(_call({"person": args.get("person")}))

    async def _tool_redeem_reward(self, manager, args: dict[str, Any]) -> dict[str, Any]:
        """redeem_reward: spend caps on a shop reward."""
        return await manager.redeem_reward(_call(args))
