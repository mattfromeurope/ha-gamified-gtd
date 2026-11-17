"""Tests for the GTD todo entity state attributes (needs `homeassistant` installed).

Regression test for "list cards show no tasks": HA does NOT put `todo_items` into a
todo entity's state attributes (the frontend uses websocket for that) — the custom
tasks card reads `state.attributes.todo_items`, so the integration must expose the
items explicitly in extra_state_attributes, together with the per-task metadata
under `tasks`.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytest.importorskip("homeassistant")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.gamified_gtd.todo import GTDTodoListEntity  # noqa: E402


def _manager():
    mgr = MagicMock()
    mgr.entry_id = "e1"
    mgr.data = {
        "tasks": {
            "t1": {
                "id": "t1",
                "title": "Buy milk",
                "list": "inbox",
                "status": "open",
                "due": "2026-11-20",
                "notes": "2%",
                "priority": 2,
                "time_estimate": 30.0,
                "energy": 1,
                "assigned_to": "person.matthias_wichert",
                "context": "@errands",
                "project_id": "p1",
                "tags": ["shopping"],
                "due_time": "18:00",
                "reminders": [60, 1440],
                "location": {"zone": "zone.home", "mode": "inside"},
                "overdue_repeat": 60,
            },
            # a task of ANOTHER list must not leak into this entity's attributes
            "t2": {"id": "t2", "title": "Other", "list": "next_actions", "status": "open"},
        }
    }
    return mgr


def test_extra_state_attributes_expose_todo_items():
    """The card reads attributes.todo_items — it must be a list of plain dicts."""
    ent = GTDTodoListEntity(_manager(), "inbox", "GTD Inbox")
    attrs = ent.extra_state_attributes
    assert "todo_items" in attrs, "todo_items missing — list cards would show no tasks"
    items = attrs["todo_items"]
    assert len(items) == 1  # only the inbox task, not t2
    item = items[0]
    assert item["uid"] == "t1"
    assert item["summary"] == "Buy milk"
    assert item["status"] == "needs_action"  # StrEnum serializes to its value
    assert item["due"] == "2026-11-20"
    assert item["description"] == "2%"


def test_completed_task_status_serializes():
    mgr = _manager()
    mgr.data["tasks"]["t1"]["status"] = "done"
    ent = GTDTodoListEntity(mgr, "inbox", "GTD Inbox")
    assert ent.extra_state_attributes["todo_items"][0]["status"] == "completed"


def test_tasks_metadata_keyed_by_uid_with_all_form_fields():
    """The edit form prefills from attributes.tasks[uid] — all fields must be there."""
    ent = GTDTodoListEntity(_manager(), "inbox", "GTD Inbox")
    meta = ent.extra_state_attributes["tasks"]["t1"]
    for key in (
        "assigned_to", "context", "project_id", "priority", "time_estimate",
        "energy", "tags", "status", "due_time", "reminders", "location", "overdue_repeat",
    ):
        assert key in meta, f"metadata field {key} missing — edit form would be empty"
    assert meta["location"] == {"zone": "zone.home", "mode": "inside"}
    assert meta["reminders"] == [60, 1440]
    assert "t2" not in ent.extra_state_attributes["tasks"]
