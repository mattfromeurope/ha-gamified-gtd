"""Sensors: per-person FNV profile sensors plus the quest log."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import gamification as g
from .const import CONF_PERSONS, DOMAIN, EVENT_DATA_UPDATED
from .manager import GTDManager


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the seven per-person profile sensors, the quest log and the rewards shop."""
    manager: GTDManager = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    # One set of sensors per configured person (sensor.<name>_level, ..._hp, ...).
    for person in manager.data["profiles"]:
        name = manager.data["profiles"][person]["name"]
        entities.extend(
            [
                LevelSensor(manager, person, name),
                HPSensor(manager, person, name),
                KarmaSensor(manager, person, name),
                CapsSensor(manager, person, name),
                SpecialSensor(manager, person, name),
                SkillsSensor(manager, person, name),
                PerksSensor(manager, person, name),
            ]
        )
    entities.append(QuestLogSensor(manager))
    entities.append(RewardsSensor(manager))
    async_add_entities(entities)


class GTDProfileSensor(SensorEntity):
    """Base class for per-person sensors.

    No polling: every sensor subscribes to EVENT_DATA_UPDATED and rewrites its state
    whenever the manager saves.
    """

    _attr_should_poll = False

    def __init__(self, manager: GTDManager, person: str, name: str, suffix: str) -> None:
        self._manager = manager
        self._person = person
        self._attr_name = f"{name} {suffix}"
        self._attr_unique_id = f"{manager.entry_id}_{person}_{suffix.lower().replace(' ', '_')}"

    @callback
    def _handle_update(self, event) -> None:
        """Refresh on any data update."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Subscribe to data updates for the lifetime of the entity."""
        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_DATA_UPDATED, self._handle_update)
        )

    @property
    def profile(self) -> dict[str, Any]:
        """The current profile dict of this sensor's person."""
        return self._manager.data["profiles"][self._person]


class LevelSensor(GTDProfileSensor):
    """Level sensor: state = level; attributes carry XP progress, skill points,
    pending perk choice, currently available perks, review state and checklist."""

    def __init__(self, manager, person, name):
        super().__init__(manager, person, name, "Level")

    @property
    def native_value(self) -> int:
        return self.profile["level"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """XP bar values (xp_in_level / xp_level_span for the card progress bar),
        available perks with name+description (for the choose-perk dialog),
        review due state, auto-checked checklist and streak."""
        cap = self._manager.level_cap
        level = self.profile["level"]
        skills = self._manager.effective_skills(self.profile)
        available = g.available_perks(
            level, self.profile["special"], skills, self.profile["perks"]
        )
        cum_level = g.cumulative_xp_for_level(level, cap)
        cum_next = g.cumulative_xp_for_level(level + 1, cap) if level < cap else cum_level
        return {
            "xp": self.profile["xp"],
            "xp_to_next": cum_next - self.profile["xp"] if level < cap else 0,
            "xp_in_level": self.profile["xp"] - cum_level,
            "xp_level_span": max(cum_next - cum_level, 1),
            "skill_points_available": self.profile["skill_points_available"],
            "perk_choice_pending": self.profile["perk_choice_pending"],
            "available_perks": [
                {"id": p.id, "name": p.name, "description": p.description}
                for p in available
            ],
            "days_since_review": self._days_since_review(),
            "review_checklist": self._manager.review_checklist_state(),
            "review_streak": self.profile.get("review_streak", 0),
        }

    def _days_since_review(self) -> int | None:
        last = self.profile.get("last_review_completed")
        if not last:
            return None
        from homeassistant.util import dt as dt_util

        from datetime import datetime

        return (dt_util.now() - datetime.fromisoformat(last)).days


class HPSensor(GTDProfileSensor):
    """HP derived stat (95 + 20*END + 5*level + perk bonuses) — Pip-Boy flavor."""

    def __init__(self, manager, person, name):
        super().__init__(manager, person, name, "HP")

    @property
    def native_value(self) -> int:
        return self._manager.profile_hp(self.profile)


class KarmaSensor(GTDProfileSensor):
    """Karma: state = FNV-style title, attribute 'karma' = the -100..+100 value."""

    def __init__(self, manager, person, name):
        super().__init__(manager, person, name, "Karma")

    @property
    def native_value(self) -> str:
        return g.karma_title(self.profile["karma"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"karma": self.profile["karma"]}


class CapsSensor(GTDProfileSensor):
    def __init__(self, manager, person, name):
        super().__init__(manager, person, name, "Caps")

    @property
    def native_value(self) -> int:
        return self.profile["caps"]


class SpecialSensor(GTDProfileSensor):
    """The 7 SPECIAL attributes as state attributes."""

    def __init__(self, manager, person, name):
        super().__init__(manager, person, name, "SPECIAL")

    @property
    def native_value(self) -> None:
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return dict(self.profile["special"])


class SkillsSensor(GTDProfileSensor):
    """The 13 FNV skills (computed via the formula) as state attributes."""

    def __init__(self, manager, person, name):
        super().__init__(manager, person, name, "Skills")

    @property
    def native_value(self) -> None:
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._manager.effective_skills(self.profile)


class PerksSensor(GTDProfileSensor):
    """Chosen perks: state = count, attributes = ids + display names."""

    def __init__(self, manager, person, name):
        super().__init__(manager, person, name, "Perks")

    @property
    def native_value(self) -> int:
        return len(self.profile["perks"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        perks = list(self.profile["perks"])
        return {
            "perks": perks,
            "perk_names": {pid: g.PERKS_BY_ID[pid].name for pid in perks if pid in g.PERKS_BY_ID},
        }


class RewardsSensor(SensorEntity):
    """The caps reward shop (sensor.gtd_rewards): state = number of rewards,
    attribute 'rewards' = the full list (id/name/description/cost) for the shop card."""

    _attr_should_poll = False
    _attr_name = "GTD Rewards"

    def __init__(self, manager: GTDManager) -> None:
        self._manager = manager
        self._attr_unique_id = f"{manager.entry_id}_rewards"

    @callback
    def _handle_update(self, event) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_DATA_UPDATED, self._handle_update)
        )

    @property
    def native_value(self) -> int:
        return len(self._manager.rewards)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"rewards": [dict(r) for r in self._manager.rewards]}


class QuestLogSensor(SensorEntity):
    """Quest log (sensor.gtd_quest_log): state = number of active quests,
    attribute 'quests' = {project_id: {name, desired_outcome, status, progress, due}}."""

    _attr_should_poll = False
    _attr_name = "GTD Quest Log"

    def __init__(self, manager: GTDManager) -> None:
        self._manager = manager
        self._attr_unique_id = f"{manager.entry_id}_quest_log"

    @callback
    def _handle_update(self, event) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_DATA_UPDATED, self._handle_update)
        )

    @property
    def native_value(self) -> int:
        return sum(
            1
            for p in self._manager.data["projects"].values()
            if p["status"] == "active"
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        quests = {}
        for project in self._manager.data["projects"].values():
            done, total = self._manager.quest_progress(project)
            quests[project["id"]] = {
                "name": project["name"],
                "desired_outcome": project.get("desired_outcome", ""),
                "status": project["status"],
                "progress": f"{done}/{total}",
                "due": project.get("due"),
            }
        return {"quests": quests}
