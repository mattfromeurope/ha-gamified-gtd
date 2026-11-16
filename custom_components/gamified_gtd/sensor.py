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
    """Set up profile sensors and the quest log."""
    manager: GTDManager = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
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
    async_add_entities(entities)


class GTDProfileSensor(SensorEntity):
    """Base class for per-person sensors."""

    _attr_should_poll = False

    def __init__(self, manager: GTDManager, person: str, name: str, suffix: str) -> None:
        self._manager = manager
        self._person = person
        self._attr_name = f"{name} {suffix}"
        self._attr_unique_id = f"{manager.entry_id}_{person}_{suffix.lower().replace(' ', '_')}"

    @callback
    def _handle_update(self, event) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_DATA_UPDATED, self._handle_update)
        )

    @property
    def profile(self) -> dict[str, Any]:
        return self._manager.data["profiles"][self._person]


class LevelSensor(GTDProfileSensor):
    def __init__(self, manager, person, name):
        super().__init__(manager, person, name, "Level")

    @property
    def native_value(self) -> int:
        return self.profile["level"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cap = self._manager.level_cap
        level = self.profile["level"]
        return {
            "xp": self.profile["xp"],
            "xp_to_next": g.cumulative_xp_for_level(level + 1, cap) - self.profile["xp"]
            if level < cap
            else 0,
            "skill_points_available": self.profile["skill_points_available"],
            "perk_choice_pending": self.profile["perk_choice_pending"],
            "days_since_review": self._days_since_review(),
        }

    def _days_since_review(self) -> int | None:
        last = self.profile.get("last_review_completed")
        if not last:
            return None
        from homeassistant.util import dt as dt_util

        from datetime import datetime

        return (dt_util.now() - datetime.fromisoformat(last)).days


class HPSensor(GTDProfileSensor):
    def __init__(self, manager, person, name):
        super().__init__(manager, person, name, "HP")

    @property
    def native_value(self) -> int:
        return self._manager.profile_hp(self.profile)


class KarmaSensor(GTDProfileSensor):
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
    def __init__(self, manager, person, name):
        super().__init__(manager, person, name, "SPECIAL")

    @property
    def native_value(self) -> None:
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return dict(self.profile["special"])


class SkillsSensor(GTDProfileSensor):
    def __init__(self, manager, person, name):
        super().__init__(manager, person, name, "Skills")

    @property
    def native_value(self) -> None:
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._manager.effective_skills(self.profile)


class PerksSensor(GTDProfileSensor):
    def __init__(self, manager, person, name):
        super().__init__(manager, person, name, "Perks")

    @property
    def native_value(self) -> int:
        return len(self.profile["perks"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"perks": list(self.profile["perks"])}


class QuestLogSensor(SensorEntity):
    """Quest log: active and completed projects with x/y progress."""

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
