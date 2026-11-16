"""Core manager: storage and business logic for Gamified GTD."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import gamification as g
from .const import (
    CONF_CONTEXTS,
    CONF_DEFAULT_ENERGY,
    CONF_DEFAULT_PROFILE,
    CONF_DEFAULT_TIME_ESTIMATE,
    CONF_DEFAULT_XP_BASE,
    CONF_LEVEL_CAP,
    CONF_PERSONS,
    CONF_REWARDS,
    DEFAULT_CONTEXTS,
    DEFAULT_ENERGY,
    DEFAULT_LEVEL_CAP,
    DEFAULT_REWARDS,
    DEFAULT_TIME_ESTIMATE,
    DEFAULT_XP_BASE,
    DOMAIN,
    EVENT_DATA_UPDATED,
    EVENT_LEVEL_UP,
    EVENT_PERK_AVAILABLE,
    EVENT_PERK_CHOSEN,
    EVENT_QUEST_COMPLETED,
    EVENT_REVIEW_COMPLETED,
    EVENT_REWARD_REDEEMED,
    EVENT_TASK_COMPLETED,
    LIST_INBOX,
    LIST_NEXT_ACTIONS,
    OVERDUE_KARMA_DAYS,
    PROJECT_ACTIVE,
    PROJECT_DONE,
    REVIEW_CHECKLIST,
    REVIEW_INTERVAL_DAYS,
    STORAGE_KEY,
    STORAGE_VERSION,
    TASK_DONE,
    TASK_OPEN,
)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now_iso() -> str:
    return dt_util.now().isoformat()


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


class GTDManager:
    """Holds all data and implements the services' logic."""

    def __init__(self, hass: HomeAssistant, entry_id: str, options: dict[str, Any]) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._options = options
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, Any] = {}

    @property
    def options(self) -> dict[str, Any]:
        return self._options

    @property
    def level_cap(self) -> int:
        return int(self._options.get(CONF_LEVEL_CAP, DEFAULT_LEVEL_CAP))

    @property
    def default_time_estimate(self) -> float:
        return float(self._options.get(CONF_DEFAULT_TIME_ESTIMATE, DEFAULT_TIME_ESTIMATE))

    @property
    def default_energy(self) -> int:
        return int(self._options.get(CONF_DEFAULT_ENERGY, DEFAULT_ENERGY))

    @property
    def xp_base(self) -> int:
        return int(self._options.get(CONF_DEFAULT_XP_BASE, DEFAULT_XP_BASE))

    @property
    def rewards(self) -> list[dict[str, Any]]:
        rewards = self._options.get(CONF_REWARDS)
        if rewards is None:
            return [dict(r) for r in self.data.get("rewards", DEFAULT_REWARDS)]
        return list(rewards)

    async def async_load(self) -> None:
        stored = await self._store.async_load()
        if stored is None:
            self.data = self._initial_data()
        else:
            self.data = stored
        self._ensure_profiles()
        await self._save()

    def _initial_data(self) -> dict[str, Any]:
        return {
            "profiles": {},
            "tasks": {},
            "projects": {},
            "reviews": {},
            "rewards": [dict(r) for r in DEFAULT_REWARDS],
        }

    def _ensure_profiles(self) -> None:
        option_profiles = self._options.get("_profiles", {})
        for person in self._options.get(CONF_PERSONS, []):
            if person not in self.data["profiles"]:
                self.data["profiles"][person] = self._new_profile(person)
            setup = option_profiles.get(person)
            if setup:
                profile = self.data["profiles"][person]
                if setup.get("special"):
                    profile["special"] = {
                        stat: int(setup["special"].get(stat, 5)) for stat in g.SPECIAL_STATS
                    }
                if setup.get("tagged_skills"):
                    profile["tagged_skills"] = list(setup["tagged_skills"])

    def _new_profile(self, person: str) -> dict[str, Any]:
        name = person.split(".", 1)[-1]
        return {
            "person": person,
            "name": name,
            "special": {stat: 5 for stat in g.SPECIAL_STATS},
            "skills_allocated": {skill: 0 for skill in g.SKILLS},
            "tagged_skills": [],
            "skill_points_available": 0,
            "carry_half_point": False,
            "xp": 0,
            "level": 1,
            "karma": 0,
            "caps": 0,
            "perks": [],
            "perk_choice_pending": False,
            "review_streak": 0,
            "last_review_completed": None,
            "created_at": _now_iso(),
        }

    async def _save(self) -> None:
        await self._store.async_save(self.data)
        self.hass.bus.async_fire(EVENT_DATA_UPDATED, {"entry_id": self.entry_id})

    # ------------------------------------------------------------------
    # Profiles
    # ------------------------------------------------------------------

    def get_profile(self, person: str | None) -> dict[str, Any]:
        profiles = self.data["profiles"]
        if person and person in profiles:
            return profiles[person]
        if person:
            raise ValueError(f"Unknown person: {person}")
        default = self._options.get(CONF_DEFAULT_PROFILE)
        if default in profiles:
            return profiles[default]
        if profiles:
            return next(iter(profiles.values()))
        raise ValueError("No profiles configured")

    def profile_hp(self, profile: dict[str, Any]) -> int:
        return g.hit_points(
            profile["special"]["endurance"],
            profile["level"],
            g.hp_bonus(profile["perks"]),
        )

    def effective_skills(self, profile: dict[str, Any]) -> dict[str, int]:
        special = profile["special"]
        tagged = set(profile.get("tagged_skills", []))
        return {
            skill: g.skill_value(
                skill,
                special,
                profile["skills_allocated"].get(skill, 0),
                skill in tagged,
            )
            for skill in g.SKILLS
        }

    def _profile_from_call(self, call: ServiceCall) -> dict[str, Any]:
        return self.get_profile(call.data.get("person"))

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def _new_task(self, title: str, call_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": _new_id(),
            "title": title,
            "notes": call_data.get("notes", ""),
            "list": call_data.get("list", LIST_INBOX),
            "status": TASK_OPEN,
            "context": call_data.get("context"),
            "project_id": call_data.get("project_id"),
            "priority": int(call_data.get("priority", 3)),
            "due": call_data.get("due"),
            "time_estimate": float(
                call_data.get("time_estimate", self.default_time_estimate)
            ),
            "energy": int(call_data.get("energy", self.default_energy)),
            "assigned_to": call_data.get("assigned_to"),
            "tags": list(call_data.get("tags", [])),
            "created_at": _now_iso(),
            "completed_at": None,
        }

    def get_task(self, task_id: str) -> dict[str, Any]:
        task = self.data["tasks"].get(task_id)
        if task is None:
            raise ValueError(f"Unknown task: {task_id}")
        return task

    async def add_to_inbox(self, call: ServiceCall) -> dict[str, Any]:
        task = self._new_task(
            call.data["title"], {**call.data, "list": call.data.get("list", LIST_INBOX)}
        )
        self.data["tasks"][task["id"]] = task
        await self._save()
        return {"task_id": task["id"]}

    async def clarify(self, call: ServiceCall) -> dict[str, Any]:
        task = self.get_task(call.data["task_id"])
        decision = call.data["decision"]
        if decision == "done":
            return await self.complete_task(call)
        target_lists = {
            "next_action": LIST_NEXT_ACTIONS,
            "waiting_for": "waiting_for",
            "someday": "someday_maybe",
        }
        if decision in target_lists:
            task["list"] = target_lists[decision]
        elif decision == "project":
            if call.data.get("project_id"):
                project_id = call.data["project_id"]
            else:
                project_id = self._create_project(
                    call.data.get("project_name", task["title"]),
                    call.data.get("desired_outcome", ""),
                    None,
                )
            task["list"] = LIST_NEXT_ACTIONS
            task["project_id"] = project_id
        else:
            raise ValueError(f"Unknown clarify decision: {decision}")
        if call.data.get("context"):
            task["context"] = call.data["context"]
        if call.data.get("assigned_to"):
            task["assigned_to"] = call.data["assigned_to"]
        await self._save()
        return {"task_id": task["id"], "list": task["list"]}

    async def update_task(self, call: ServiceCall) -> dict[str, Any]:
        task = self.get_task(call.data["task_id"])
        for key in (
            "title",
            "notes",
            "list",
            "context",
            "project_id",
            "due",
            "assigned_to",
            "tags",
        ):
            if key in call.data:
                task[key] = call.data[key]
        if "priority" in call.data:
            task["priority"] = int(call.data["priority"])
        if "time_estimate" in call.data:
            task["time_estimate"] = float(call.data["time_estimate"])
        if "energy" in call.data:
            task["energy"] = int(call.data["energy"])
        await self._save()
        return {"task_id": task["id"]}

    async def skip_task(self, call: ServiceCall) -> dict[str, Any]:
        task = self.get_task(call.data["task_id"])
        task["list"] = "waiting_for"
        await self._save()
        return {"task_id": task["id"]}

    async def remove_task(self, call: ServiceCall) -> None:
        task_id = call.data["task_id"]
        task = self.get_task(task_id)
        if task.get("project_id"):
            project = self.data["projects"].get(task["project_id"])
            if project and task_id in project["task_ids"]:
                project["task_ids"].remove(task_id)
        del self.data["tasks"][task_id]
        await self._save()

    async def complete_task(self, call: ServiceCall) -> dict[str, Any]:
        task = self.get_task(call.data["task_id"])
        if task["status"] == TASK_DONE:
            return {"task_id": task["id"], "already_done": True}
        task["status"] = TASK_DONE
        task["completed_at"] = _now_iso()

        profile = self.get_profile(task.get("assigned_to") or call.data.get("person"))
        today = dt_util.now().date()
        due = _parse_date(task.get("due"))
        overdue = due is not None and due < today
        on_time = due is not None and due >= today
        days_overdue = (today - due).days if overdue else 0

        xp = g.task_xp(
            priority=task.get("priority", 3),
            time_estimate=task.get("time_estimate", self.default_time_estimate),
            energy=task.get("energy", self.default_energy),
            karma=profile["karma"],
            on_time=on_time,
            xp_base=self.xp_base,
            xp_multiplier=g.xp_multiplier(profile["perks"]),
        )
        caps = 0
        if not overdue:
            caps = round(g.caps_from_xp(xp) * g.caps_multiplier(profile["perks"]))

        if due is not None:
            if on_time:
                profile["karma"] = g.clamp_karma(profile["karma"] + 1)
            elif days_overdue > OVERDUE_KARMA_DAYS:
                profile["karma"] = g.clamp_karma(profile["karma"] - 1)

        task["xp_awarded"] = xp
        level_ups = await self._award_xp(profile, xp)
        profile["caps"] += caps
        await self._save()

        result = {
            "task_id": task["id"],
            "xp": xp,
            "caps": caps,
            "level_ups": level_ups,
            "person": profile["person"],
        }
        self.hass.bus.async_fire(
            EVENT_TASK_COMPLETED,
            {**result, "title": task["title"], "project_id": task.get("project_id")},
        )
        if task.get("project_id"):
            await self._maybe_complete_project(task["project_id"])
        return result

    # ------------------------------------------------------------------
    # XP / levels / perks / skills
    # ------------------------------------------------------------------

    async def _award_xp(self, profile: dict[str, Any], xp: int) -> list[int]:
        profile["xp"] += xp
        level_ups: list[int] = []
        cap = self.level_cap
        while profile["level"] < cap and profile["xp"] >= g.cumulative_xp_for_level(
            profile["level"] + 1, cap
        ):
            profile["level"] += 1
            level_ups.append(profile["level"])
            points, profile["carry_half_point"] = g.skill_points_for_level_up(
                profile["special"]["intelligence"], profile["carry_half_point"]
            )
            profile["skill_points_available"] += points + g.skill_points_bonus_per_level(
                profile["perks"]
            )
            if profile["level"] % 2 == 0:
                profile["perk_choice_pending"] = True
            self.hass.bus.async_fire(
                EVENT_LEVEL_UP,
                {
                    "person": profile["person"],
                    "level": profile["level"],
                    "skill_points": profile["skill_points_available"],
                },
            )
            if profile["perk_choice_pending"]:
                self.hass.bus.async_fire(
                    EVENT_PERK_AVAILABLE, {"person": profile["person"], "level": profile["level"]}
                )
        return level_ups

    async def allocate_skill_points(self, call: ServiceCall) -> dict[str, Any]:
        profile = self._profile_from_call(call)
        skill = call.data["skill"]
        points = int(call.data["points"])
        if skill not in g.SKILLS:
            raise ValueError(f"Unknown skill: {skill}")
        if points < 0 or points > profile["skill_points_available"]:
            raise ValueError("Not enough skill points available")
        profile["skills_allocated"][skill] = profile["skills_allocated"].get(skill, 0) + points
        profile["skill_points_available"] -= points
        await self._save()
        return {
            "person": profile["person"],
            "skill": skill,
            "skill_value": self.effective_skills(profile)[skill],
            "skill_points_available": profile["skill_points_available"],
        }

    async def choose_perk(self, call: ServiceCall) -> dict[str, Any]:
        profile = self._profile_from_call(call)
        perk_id = call.data["perk"]
        perk = g.PERKS_BY_ID.get(perk_id)
        if perk is None:
            raise ValueError(f"Unknown perk: {perk_id}")
        if not profile.get("perk_choice_pending"):
            raise ValueError("No perk choice pending (perks are available every 2 levels)")
        skills = self.effective_skills(profile)
        if not g.perk_requirements_met(
            perk, profile["level"], profile["special"], skills, profile["perks"].count(perk_id)
        ):
            raise ValueError(f"Requirements for perk '{perk.name}' not met")
        profile["perks"].append(perk_id)
        profile["perk_choice_pending"] = False
        if perk.effect.get("special_plus"):
            stat = call.data.get("special_stat", "strength")
            if stat not in g.SPECIAL_STATS:
                raise ValueError(f"Unknown SPECIAL stat: {stat}")
            profile["special"][stat] = min(10, profile["special"][stat] + 1)
        if perk.effect.get("tag_skill"):
            skill = call.data.get("skill")
            if skill not in g.SKILLS:
                raise ValueError(f"Tag! needs a valid skill, got: {skill}")
            if skill not in profile["tagged_skills"]:
                profile["tagged_skills"].append(skill)
        if perk.effect.get("instant_level"):
            needed = g.cumulative_xp_for_level(profile["level"] + 1, self.level_cap) - profile["xp"]
            if needed > 0:
                await self._award_xp(profile, needed)
        await self._save()
        self.hass.bus.async_fire(
            EVENT_PERK_CHOSEN, {"person": profile["person"], "perk": perk_id}
        )
        return {"person": profile["person"], "perk": perk_id, "perks": profile["perks"]}

    # ------------------------------------------------------------------
    # Projects / quests
    # ------------------------------------------------------------------

    def _create_project(
        self, name: str, desired_outcome: str, due: str | None
    ) -> str:
        project = {
            "id": _new_id(),
            "name": name,
            "desired_outcome": desired_outcome,
            "task_ids": [],
            "status": PROJECT_ACTIVE,
            "due": due,
            "created_at": _now_iso(),
            "completed_at": None,
        }
        self.data["projects"][project["id"]] = project
        return project["id"]

    async def create_project(self, call: ServiceCall) -> dict[str, Any]:
        project_id = self._create_project(
            call.data["name"], call.data.get("desired_outcome", ""), call.data.get("due")
        )
        await self._save()
        return {"project_id": project_id}

    async def add_to_project(self, call: ServiceCall) -> dict[str, Any]:
        task = self.get_task(call.data["task_id"])
        project = self.data["projects"].get(call.data["project_id"])
        if project is None:
            raise ValueError(f"Unknown project: {call.data['project_id']}")
        if project["status"] != PROJECT_ACTIVE:
            project["status"] = PROJECT_ACTIVE
            project["completed_at"] = None
        if task["id"] not in project["task_ids"]:
            project["task_ids"].append(task["id"])
        task["project_id"] = project["id"]
        task["list"] = LIST_NEXT_ACTIONS
        await self._save()
        return {"project_id": project["id"], "task_id": task["id"]}

    def quest_progress(self, project: dict[str, Any]) -> tuple[int, int]:
        steps = [self.data["tasks"].get(tid) for tid in project["task_ids"]]
        steps = [t for t in steps if t]
        done = sum(1 for t in steps if t["status"] == TASK_DONE)
        return done, len(steps)

    async def _maybe_complete_project(self, project_id: str) -> None:
        project = self.data["projects"].get(project_id)
        if project is None or project["status"] != PROJECT_ACTIVE:
            return
        steps = [self.data["tasks"].get(tid) for tid in project["task_ids"]]
        open_steps = [t for t in steps if t and t["status"] != TASK_DONE]
        if steps and not open_steps:
            await self._complete_project(project, automatic=True)

    async def complete_project(self, call: ServiceCall) -> dict[str, Any]:
        project = self.data["projects"].get(call.data["project_id"])
        if project is None:
            raise ValueError(f"Unknown project: {call.data['project_id']}")
        return await self._complete_project(project, automatic=False)

    async def _complete_project(
        self, project: dict[str, Any], automatic: bool
    ) -> dict[str, Any]:
        project["status"] = PROJECT_DONE
        project["completed_at"] = _now_iso()
        done, total = self.quest_progress(project)
        step_xp = 0
        for tid in project["task_ids"]:
            task = self.data["tasks"].get(tid)
            if task and task["status"] == TASK_DONE:
                step_xp += task.get("xp_awarded", 0)
        quest_xp = step_xp + g.QUEST_STEP_BONUS_XP * max(total, 1)
        due = _parse_date(project.get("due"))
        if due is not None and due >= dt_util.now().date():
            quest_xp = round(quest_xp * (1 + g.QUEST_ON_TIME_BONUS))
        profile = self.get_profile(None)
        level_ups = await self._award_xp(profile, quest_xp)
        caps = round(g.caps_from_xp(quest_xp) * g.caps_multiplier(profile["perks"]))
        profile["caps"] += caps
        await self._save()
        self.hass.bus.async_fire(
            EVENT_QUEST_COMPLETED,
            {
                "project_id": project["id"],
                "name": project["name"],
                "xp": quest_xp,
                "caps": caps,
                "steps": f"{done}/{total}",
                "automatic": automatic,
                "person": profile["person"],
            },
        )
        return {
            "project_id": project["id"],
            "xp": quest_xp,
            "caps": caps,
            "level_ups": level_ups,
        }

    # ------------------------------------------------------------------
    # Weekly review
    # ------------------------------------------------------------------

    def review_checklist_state(self) -> dict[str, bool]:
        tasks = list(self.data["tasks"].values())
        inbox_open = any(t["list"] == LIST_INBOX and t["status"] == TASK_OPEN for t in tasks)
        week_ago = (dt_util.now() - timedelta(days=REVIEW_INTERVAL_DAYS)).isoformat()
        stale_actions = any(
            t["list"] == LIST_NEXT_ACTIONS
            and t["status"] == TASK_OPEN
            and t["created_at"] < week_ago
            for t in tasks
        )
        return {
            "inbox_empty": not inbox_open,
            "next_actions_current": not stale_actions,
            "projects_reviewed": True,
            "waiting_for_followed_up": True,
            "calendar_checked": True,
            "someday_reviewed": True,
        }

    def review_due(self, profile: dict[str, Any]) -> bool:
        last = profile.get("last_review_completed")
        if last is None:
            return True
        last_dt = datetime.fromisoformat(last)
        return dt_util.now() - last_dt >= timedelta(days=REVIEW_INTERVAL_DAYS)

    async def start_review(self, call: ServiceCall) -> dict[str, Any]:
        profile = self._profile_from_call(call)
        review = {
            "id": _new_id(),
            "person": profile["person"],
            "started_at": _now_iso(),
            "completed_at": None,
            "checklist": self.review_checklist_state(),
        }
        self.data["reviews"][review["id"]] = review
        await self._save()
        return {"review_id": review["id"], "checklist": review["checklist"]}

    async def complete_review(self, call: ServiceCall) -> dict[str, Any]:
        profile = self._profile_from_call(call)
        open_reviews = [
            r
            for r in self.data["reviews"].values()
            if r["person"] == profile["person"] and r["completed_at"] is None
        ]
        review = open_reviews[-1] if open_reviews else None
        if review is None:
            raise ValueError("No open review — call start_review first")
        review["completed_at"] = _now_iso()
        review["checklist"] = self.review_checklist_state()
        last = profile.get("last_review_completed")
        if last is None:
            weeks_overdue = 0
        else:
            weeks_overdue = max(
                0,
                ((dt_util.now() - datetime.fromisoformat(last)).days - REVIEW_INTERVAL_DAYS)
                // REVIEW_INTERVAL_DAYS,
            )
        if weeks_overdue:
            profile["karma"] = g.clamp_karma(
                profile["karma"] + weeks_overdue * g.REVIEW_OVERDUE_KARMA_PER_WEEK
            )
            profile["review_streak"] = 0
        else:
            profile["review_streak"] = profile.get("review_streak", 0) + 1
        xp = g.REVIEW_BASE_XP * max(profile["review_streak"], 1)
        xp = round(xp * (1 + (profile["karma"] / 100) * g.KARMA_XP_MODIFIER))
        level_ups = await self._award_xp(profile, xp)
        caps = round(g.caps_from_xp(xp) * g.caps_multiplier(profile["perks"]))
        profile["caps"] += caps
        profile["last_review_completed"] = review["completed_at"]
        await self._save()
        self.hass.bus.async_fire(
            EVENT_REVIEW_COMPLETED,
            {
                "person": profile["person"],
                "review_id": review["id"],
                "xp": xp,
                "caps": caps,
                "streak": profile["review_streak"],
                "checklist": review["checklist"],
            },
        )
        return {"review_id": review["id"], "xp": xp, "caps": caps, "level_ups": level_ups}

    # ------------------------------------------------------------------
    # Rewards
    # ------------------------------------------------------------------

    async def redeem_reward(self, call: ServiceCall) -> dict[str, Any]:
        profile = self._profile_from_call(call)
        reward_id = call.data["reward"]
        reward = next((r for r in self.rewards if r["id"] == reward_id), None)
        if reward is None:
            raise ValueError(f"Unknown reward: {reward_id}")
        if profile["caps"] < reward["cost"]:
            raise ValueError(
                f"Not enough caps: {profile['caps']} < {reward['cost']}"
            )
        profile["caps"] -= reward["cost"]
        await self._save()
        self.hass.bus.async_fire(
            EVENT_REWARD_REDEEMED,
            {
                "person": profile["person"],
                "reward": reward["id"],
                "name": reward["name"],
                "cost": reward["cost"],
                "caps_left": profile["caps"],
            },
        )
        return {"reward": reward["id"], "caps_left": profile["caps"]}

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def get_state(self, call: ServiceCall) -> dict[str, Any]:
        profile = self._profile_from_call(call)
        cap = self.level_cap
        quests = []
        for project in self.data["projects"].values():
            done, total = self.quest_progress(project)
            quests.append(
                {
                    "id": project["id"],
                    "name": project["name"],
                    "status": project["status"],
                    "progress": f"{done}/{total}",
                    "due": project.get("due"),
                }
            )
        return {
            "person": profile["person"],
            "level": profile["level"],
            "xp": profile["xp"],
            "xp_to_next": g.cumulative_xp_for_level(profile["level"] + 1, cap) - profile["xp"]
            if profile["level"] < cap
            else 0,
            "skill_points_available": profile["skill_points_available"],
            "perk_choice_pending": profile["perk_choice_pending"],
            "karma": profile["karma"],
            "karma_title": g.karma_title(profile["karma"]),
            "caps": profile["caps"],
            "hp": self.profile_hp(profile),
            "special": dict(profile["special"]),
            "skills": self.effective_skills(profile),
            "perks": [
                {"id": pid, "name": g.PERKS_BY_ID[pid].name, "description": g.PERKS_BY_ID[pid].description}
                for pid in profile["perks"]
                if pid in g.PERKS_BY_ID
            ],
            "review_streak": profile.get("review_streak", 0),
            "review_due": self.review_due(profile),
            "quests": quests,
        }
