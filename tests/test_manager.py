"""Manager-level regression tests for the service logic (needs `homeassistant`).

Covers the bugs/services added around the Pip-Boy cards + GOAT:
- choose_perk passed an int instead of the owned-perk list to
  perk_requirements_met -> "'int' object has no attribute 'count'" on EVERY call
- move_task moves a task between GTD lists
- update_task keeps project <-> task links in sync (quest x/y progress)
- submit_goat scores the answers and sets the Tag! skills on the profile
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("homeassistant")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from homeassistant.core import Context, ServiceCall  # noqa: E402

from custom_components.gamified_gtd.const import DOMAIN  # noqa: E402
from custom_components.gamified_gtd.manager import GTDManager  # noqa: E402


def _manager() -> GTDManager:
    """A manager with mocked hass + storage, one profile for person.x."""
    mgr = GTDManager(MagicMock(), "e1", {})
    mgr.data = mgr._initial_data()
    mgr.data["profiles"]["person.x"] = mgr._new_profile("person.x")
    mgr._save = AsyncMock()  # don't touch real storage
    # the character-creation hint posts a persistent notification via the service bus
    mgr.hass.services.async_call = AsyncMock()
    return mgr


def _profile(mgr) -> dict:
    return mgr.data["profiles"]["person.x"]


def _call(service: str, data: dict) -> ServiceCall:
    """ServiceCall(hass, domain, service, data) — hass first since HA 2024.x."""
    return ServiceCall(MagicMock(), DOMAIN, service, data)


def test_choose_perk_regression_owned_list_not_count():
    """Regression: choose_perk must pass profile['perks'] (a list) to
    perk_requirements_met, not profile['perks'].count(...) (an int)."""
    mgr = _manager()
    profile = _profile(mgr)
    profile["level"] = 4  # 'educated' is a level-4 perk
    profile["perk_choice_pending"] = True
    profile["special"]["intelligence"] = 10  # satisfy 'educated' (INT >= 4)
    call = _call("choose_perk", {"person": "person.x", "perk": "educated"})
    result = asyncio.run(mgr.choose_perk(call))
    assert result["perk"] == "educated"
    assert "educated" in profile["perks"]
    assert profile["perk_choice_pending"] is False


def test_choose_perk_rejects_unmet_requirements():
    mgr = _manager()
    profile = _profile(mgr)
    profile["level"] = 2
    profile["perk_choice_pending"] = True
    # 'educated' needs INT >= 6, profile has INT 5
    call = _call("choose_perk", {"person": "person.x", "perk": "educated"})
    with pytest.raises(ValueError, match="not met"):
        asyncio.run(mgr.choose_perk(call))
    assert profile["perks"] == []


def test_move_task_between_lists():
    mgr = _manager()
    mgr.data["tasks"]["t1"] = mgr._new_task("Buy milk", {"list": "inbox"})
    call = _call("move_task", {"task_id": "t1", "list": "next_actions"})
    result = asyncio.run(mgr.move_task(call))
    assert result["list"] == "next_actions"
    assert mgr.data["tasks"]["t1"]["list"] == "next_actions"
    with pytest.raises(ValueError):
        asyncio.run(mgr.move_task(_call("move_task", {"task_id": "t1", "list": "nope"})))


def test_update_task_project_link_stays_in_sync():
    """Assigning via update_task must add the task to project['task_ids'] (drives the
    quest x/y progress) and removing it must remove it again."""
    mgr = _manager()
    task = mgr._new_task("Step 1", {"list": "inbox"})  # note: _new_task assigns its own id
    mgr.data["tasks"][task["id"]] = task
    tid = task["id"]
    project_id = mgr._create_project("Quest", "outcome", None)
    asyncio.run(
        mgr.update_task(_call("update_task", {"task_id": tid, "project_id": project_id}))
    )
    assert task["project_id"] == project_id
    assert tid in mgr.data["projects"][project_id]["task_ids"]
    # detach again (empty string = none, as the card sends it)
    asyncio.run(
        mgr.update_task(_call("update_task", {"task_id": tid, "project_id": ""}))
    )
    assert task["project_id"] is None
    assert tid not in mgr.data["projects"][project_id]["task_ids"]


def test_reset_profile_resets_character_only():
    """reset_profile resets level/XP/SPECIAL/skills/perks/caps/GOAT — but NOT tasks,
    projects, karma or review state."""
    from custom_components.gamified_gtd import gamification as g

    mgr = _manager()
    profile = _profile(mgr)
    # simulate a developed character plus unrelated data that must survive
    profile.update({
        "level": 7, "xp": 5000, "caps": 123, "karma": 42, "review_streak": 3,
        "perks": ["educated"], "tagged_skills": ["guns"], "goat": {"tags": ["guns"]},
        "skills_allocated": {"guns": 10}, "skill_points_available": 4,
        "special": {stat: 8 for stat in g.SPECIAL_STATS},
    })
    task = mgr._new_task("Keep me", {"list": "inbox"})
    mgr.data["tasks"][task["id"]] = task
    mgr.data["projects"]["p1"] = {
        "id": "p1", "name": "Quest", "desired_outcome": "", "task_ids": [task["id"]],
        "status": "active", "due": None, "created_at": "", "completed_at": None,
    }

    result = asyncio.run(mgr.reset_profile(_call("reset_profile", {"person": "person.x"})))

    assert result["reset"] is True
    assert result["character_creation_pending"] is True
    assert result["user"] is None  # no user context on the call -> generic hint
    # the pending hint fires IMMEDIATELY on reset (not only at the next HA start) and
    # links into the integration settings (SPECIAL first, G.O.A.T. right after)
    mgr.hass.services.async_call.assert_awaited()
    args = mgr.hass.services.async_call.await_args.args
    assert args[0] == "persistent_notification" and args[1] == "create"
    assert f"/config/integrations/integration/{DOMAIN}" in args[2]["message"]
    assert profile["goat_prompted"] is True  # notification was sent (flag consumed)
    assert profile["level"] == 1 and profile["xp"] == 0 and profile["caps"] == 0
    assert profile["perks"] == [] and profile["tagged_skills"] == [] and profile["goat"] is None
    assert profile["skill_points_available"] == 0
    assert all(v == 5 for v in profile["special"].values())  # back to FNV base 5
    assert profile["skills_allocated"]["guns"] == 0
    # untouched: karma, review, tasks, projects
    assert profile["karma"] == 42 and profile["review_streak"] == 3
    assert task["id"] in mgr.data["tasks"]
    assert "p1" in mgr.data["projects"]
    assert mgr.data["projects"]["p1"]["task_ids"] == [task["id"]]


def test_reset_profile_notifies_triggering_user():
    """reset_profile resolves the HA user from the service-call context and addresses
    the persistent notification to them (persistent notifications are global in HA,
    so the text personalizes the message)."""
    from types import SimpleNamespace

    mgr = _manager()
    mgr.hass.auth.async_get_user = AsyncMock(
        return_value=SimpleNamespace(name="Matt")
    )
    mgr.hass.states.async_all = MagicMock(
        return_value=[
            SimpleNamespace(entity_id="person.x", attributes={"user_id": "u1"}),
            SimpleNamespace(entity_id="person.other", attributes={"user_id": "u2"}),
        ]
    )
    call = ServiceCall(
        MagicMock(), DOMAIN, "reset_profile", {"person": "person.x"},
        context=Context(user_id="u1"),
    )
    result = asyncio.run(mgr.reset_profile(call))
    assert result["user"] == "Matt"
    args = mgr.hass.services.async_call.await_args.args
    assert "reset by Matt" in args[2]["message"]


def test_triggering_user_without_context_returns_none():
    mgr = _manager()
    user, person = asyncio.run(mgr._triggering_user(_call("reset_profile", {})))
    assert user is None and person is None


def test_character_creation_pending_flag():
    mgr = _manager()
    profile = _profile(mgr)
    assert mgr.profile_pending_character_creation(profile) is True
    profile["tagged_skills"] = ["guns"]  # manual tags count as done
    assert mgr.profile_pending_character_creation(profile) is False
    profile["tagged_skills"] = []
    profile["goat"] = {"tags": ["guns"]}  # GOAT result counts as done
    assert mgr.profile_pending_character_creation(profile) is False


def test_submit_goat_sets_tag_skills():
    mgr = _manager()
    call = _call("submit_goat", {"person": "person.x", "answers": [0] * 10})
    result = asyncio.run(mgr.submit_goat(call))
    # all-first-answers: Small Guns x2 -> guns; tie-break alphabetical -> barter, explosives
    assert result["tags"] == ["guns", "barter", "explosives"]
    assert _profile(mgr)["tagged_skills"] == ["guns", "barter", "explosives"]
    assert _profile(mgr)["goat"]["job"]["name"] == "Tattoo artist"
    # answers as comma separated string (service UI text field) work too
    call2 = _call("submit_goat", {"person": "person.x", "answers": "0,0,0,0,0,0,0,0,0,0"})
    result2 = asyncio.run(mgr.submit_goat(call2))
    assert result2["tags"] == result["tags"]
