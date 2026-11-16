"""Reminders and notifications: due-date reminders, location-based held reminders,
repeat-while-overdue and the daily summary — modeled after Better ToDo.

Per-task reminders fire at due time or X minutes before (tasks without a due time use
09:00). A reminder can be tied to a zone with mode "inside" (deliver on arrival) or
"outside" (deliver on leaving); while the condition is not met the reminder is held and
delivered the moment it matches. Held reminders are dropped when the task is completed
or its due changes. Persons without location tracking count as matching.
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Any, Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_point_in_time, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    CONF_HA_NOTIFICATION,
    CONF_NOTIFY_SERVICES,
    CONF_SUMMARY_ENABLED,
    CONF_SUMMARY_TIME,
    CONF_UNASSIGNED_TO_ALL,
    DEFAULT_DUE_TIME,
    DEFAULT_SUMMARY_TIME,
    DOMAIN,
    EVENT_DATA_UPDATED,
    EVENT_REMINDER_SENT,
    EVENT_SUMMARY_SENT,
    SUMMARY_HORIZON_DAYS,
    TASK_OPEN,
)

_LOGGER = logging.getLogger(__name__)


def _parse_due(task: dict[str, Any]) -> datetime | None:
    """Combine the task's due date with its due time (default 09:00 when only a date
    is set) and return a timezone-aware local datetime; None when no due date."""
    due = task.get("due")
    if not due:
        return None
    due_time_str = task.get("due_time") or DEFAULT_DUE_TIME
    hh, mm = (int(x) for x in due_time_str.split(":")[:2])
    naive = datetime.fromisoformat(due).replace(hour=hh, minute=mm)
    return dt_util.as_local(naive)


class NotificationScheduler:
    """Schedules and delivers reminders + the daily summary for all open tasks."""

    def __init__(self, hass: HomeAssistant, manager) -> None:
        self.hass = hass
        self.manager = manager
        self._unsub: list[Callable] = []  # event subscriptions (data updates, person state changes)
        self._timers: list[Callable] = []  # cancel callbacks of armed point-in-time timers
        # Held location-based reminders: [{task_id, person, offset, loc}] waiting for
        # the person to enter/leave the zone. In-memory only (rebuilt on restart).
        self._held: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    async def async_start(self) -> None:
        """Subscribe to data updates + person state changes and schedule everything.

        `initial=True` on the first run gives catch-up behavior after downtime:
        only the latest missed reminder per task is delivered, not all of them.
        """
        self._unsub.append(
            self.hass.bus.async_listen(EVENT_DATA_UPDATED, self._on_data_updated)
        )
        for person in self.manager.data["profiles"]:
            self._unsub.append(
                async_track_state_change_event(
                    self.hass, [person], self._on_person_state_changed
                )
            )
        self._reschedule(initial=True)

    async def async_stop(self) -> None:
        """Cancel all timers and subscriptions (on unload)."""
        for cancel in self._timers:
            cancel()
        for unsub in self._unsub:
            unsub()
        self._timers.clear()
        self._unsub.clear()
        self._held.clear()

    def _on_data_updated(self, event) -> None:
        """Any task change -> rebuild the whole schedule (simple and always correct)."""
        self._reschedule(initial=False)

    def _on_person_state_changed(self, event) -> None:
        """A person changed zone -> re-check held location reminders."""
        self._deliver_held()

    # ------------------------------------------------------------------
    # scheduling
    # ------------------------------------------------------------------

    def _reschedule(self, initial: bool) -> None:
        """Rebuild all timers from the current open tasks + the daily summary timer."""
        for cancel in self._timers:
            cancel()
        self._timers.clear()
        self._held.clear()
        now = dt_util.now()
        for task in list(self.manager.data["tasks"].values()):
            if task["status"] != TASK_OPEN:
                continue
            due = _parse_due(task)
            reminders = task.get("reminders") or []
            if due and reminders:
                times = [due - timedelta(minutes=int(r)) for r in reminders]
                if initial:
                    past = [t for t in times if t <= now]
                    if past:
                        self._fire_reminder(task["id"], max(past), initial=True)
                    future = [t for t in times if t > now]
                else:
                    future = times
                for when in future:
                    self._arm(when, lambda t=task["id"], w=when: self._fire_reminder(t, w, initial=False))
            repeat = task.get("overdue_repeat")
            if due and repeat:
                self._arm(due + timedelta(minutes=int(repeat)), lambda t=task["id"]: self._fire_overdue(t))
        self._schedule_summary()

    def _arm(self, when: datetime, action: Callable) -> None:
        """Arm a one-shot action: fire immediately if the time already passed
        (catch-up), otherwise via async_track_point_in_time."""
        now = dt_util.now()
        if when <= now:
            action()
            return
        self._timers.append(
            async_track_point_in_time(self.hass, lambda _now: action(), when)
        )

    # ------------------------------------------------------------------
    # reminders
    # ------------------------------------------------------------------

    def _recipients(self, task: dict[str, Any]) -> list[str]:
        """Who gets a reminder: the assigned person, or — for unassigned tasks when
        'unassigned_to_all' is enabled — every person with a notify service."""
        assigned = task.get("assigned_to")
        if assigned:
            return [assigned]
        if self.manager.options.get(CONF_UNASSIGNED_TO_ALL):
            return [
                p
                for p, svc in self._notify_map().items()
                if svc
            ]
        return []

    def _notify_map(self) -> dict[str, str]:
        """person entity id -> notify service (from the options flow)."""
        return dict(self.manager.options.get(CONF_NOTIFY_SERVICES) or {})

    def _person_zone(self, person: str) -> str | None:
        """Current zone of a person (the person entity's state is the zone name)."""
        state = self.hass.states.get(person)
        return state.state if state else None

    def _location_ok(self, loc: dict[str, Any], person: str) -> bool:
        """Location condition check: mode 'inside' -> person must be in the zone,
        'outside' -> must not be. Persons without location tracking (no state)
        count as matching so a reminder is never swallowed (Better ToDo behavior)."""
        zone = self._person_zone(person)
        if zone is None:
            return True  # no location tracking -> never swallow the reminder
        if loc.get("mode") == "inside":
            return zone == loc.get("zone")
        return zone != loc.get("zone")

    def _fire_reminder(self, task_id: str, when: datetime, initial: bool) -> None:
        """A reminder time arrived: resolve recipients; if a location condition is set
        and not met, hold the reminder for that person, else send immediately."""
        task = self.manager.data["tasks"].get(task_id)
        if not task or task["status"] != TASK_OPEN:
            return
        offset = round((_parse_due(task) - when).total_seconds() / 60) if _parse_due(task) else 0
        loc = task.get("location")
        for person in self._recipients(task):
            if loc and not self._location_ok(loc, person):
                self._held.append(
                    {"task_id": task_id, "person": person, "offset": offset, "loc": loc}
                )
                continue
            self._send_reminder(task, person, offset)

    def _fire_overdue(self, task_id: str) -> None:
        """Repeat-while-overdue tick: send if still overdue, then re-arm for the next
        interval (counted from now, so downtime never stacks missed nudges)."""
        task = self.manager.data["tasks"].get(task_id)
        if not task or task["status"] != TASK_OPEN:
            return
        due = _parse_due(task)
        repeat = int(task.get("overdue_repeat") or 0)
        if due and repeat and dt_util.now() >= due:
            for person in self._recipients(task):
                loc = task.get("location")
                if loc and not self._location_ok(loc, person):
                    self._held.append(
                        {"task_id": task_id, "person": person, "offset": -1, "loc": loc}
                    )
                    continue
                self._send_reminder(task, person, -1)
            self._arm(due + timedelta(minutes=repeat) + (dt_util.now() - due), lambda: self._fire_overdue(task_id))

    def _deliver_held(self) -> None:
        """Re-check held reminders after a zone change. Held reminders are dropped when
        the task was completed or its location condition changed in the meantime."""
        still_held = []
        for held in self._held:
            task = self.manager.data["tasks"].get(held["task_id"])
            if not task or task["status"] != TASK_OPEN or task.get("location") != held["loc"]:
                continue  # dropped: completed or due/location changed
            if self._location_ok(held["loc"], held["person"]):
                self._send_reminder(task, held["person"], held["offset"])
            else:
                still_held.append(held)
        self._held = still_held

    def _send_reminder(self, task: dict[str, Any], person: str, offset: int) -> None:
        """Deliver one reminder: push via the person's notify service (if configured)
        and always fire reminder_sent (offset -1 = overdue repeat)."""
        service = self._notify_map().get(person)
        due = _parse_due(task)
        if offset >= 0:
            when_txt = f"due {due.strftime('%Y-%m-%d %H:%M')}, reminder {offset} min before" if offset else f"due {due.strftime('%Y-%m-%d %H:%M')}"
        else:
            when_txt = "overdue"
        message = f"[{DOMAIN}] {task['title']} ({when_txt})"
        if service:
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "notify", service.split(".", 1)[1] if "." in service else service,
                    {"title": "Gamified GTD", "message": message},
                    blocking=True,
                )
            )
        self.hass.bus.async_fire(
            EVENT_REMINDER_SENT,
            {
                "task_id": task["id"],
                "title": task["title"],
                "person": person,
                "offset_minutes": offset,
                "delivered": bool(service),
            },
        )

    # ------------------------------------------------------------------
    # daily summary
    # ------------------------------------------------------------------

    def _schedule_summary(self) -> None:
        """Arm the next daily summary at the configured time (today or tomorrow)."""
        if not self.manager.options.get(CONF_SUMMARY_ENABLED):
            return
        time_str = self.manager.options.get(CONF_SUMMARY_TIME, DEFAULT_SUMMARY_TIME)
        hh, mm = (int(x) for x in time_str.split(":")[:2])
        now = dt_util.now()
        when = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if when <= now:
            when += timedelta(days=1)
        self._timers.append(
            async_track_point_in_time(
                self.hass, lambda _now: self._fire_summary(), when
            )
        )

    def _fire_summary(self) -> None:
        """Daily summary tick: send, then always re-arm for the next day."""
        try:
            self._send_daily_summary()
        finally:
            self._schedule_summary()

    def _send_daily_summary(self) -> None:
        """Per person: one push listing their open tasks — overdue/today always, plus
        tasks due within the 7-day horizon. No message when the list is empty.
        Optionally also posts to the HA notification center (dismissed when empty)."""
        today = dt_util.now().date()
        horizon = today + timedelta(days=SUMMARY_HORIZON_DAYS)
        tasks = [t for t in self.manager.data["tasks"].values() if t["status"] == TASK_OPEN]
        for person in self.manager.data["profiles"]:
            mine = [
                t
                for t in tasks
                if t.get("assigned_to") == person
                or (not t.get("assigned_to") and self.manager.options.get(CONF_UNASSIGNED_TO_ALL))
            ]
            lines = []
            for t in sorted(mine, key=lambda x: (x.get("due") or "9999", x.get("priority", 3))):
                due = t.get("due")
                if not due:
                    continue
                due_date = datetime.fromisoformat(due).date()
                if due_date <= today:
                    overdue_days = (today - due_date).days
                    tag = f"OVERDUE {overdue_days}d" if overdue_days > 0 else "TODAY"
                    lines.append(f"[{tag}] {t['title']}")
                elif due_date <= horizon:
                    lines.append(f"[{due_date.isoformat()}] {t['title']}")
            if not lines:
                continue  # never spam an empty list
            message = "Open tasks:\n" + "\n".join(lines)
            service = self._notify_map().get(person)
            if service:
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        "notify", service.split(".", 1)[1] if "." in service else service,
                        {"title": "Gamified GTD — daily summary", "message": message},
                        blocking=True,
                    )
                )
            self.hass.bus.async_fire(
                EVENT_SUMMARY_SENT, {"person": person, "tasks": len(lines)}
            )
        if self.manager.options.get(CONF_HA_NOTIFICATION):
            all_open = [t for t in tasks if t.get("due")]
            if all_open:
                body = "\n".join(
                    f"• {t['title']} ({t.get('due')})" for t in sorted(all_open, key=lambda x: x.get("due") or "")
                )
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        "persistent_notification", "create",
                        {"title": "Gamified GTD — open tasks", "message": body, "notification_id": f"{DOMAIN}_summary"},
                        blocking=True,
                    )
                )
            else:
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        "persistent_notification", "dismiss",
                        {"notification_id": f"{DOMAIN}_summary"},
                        blocking=True,
                    )
                )
