"""Gamified GTD — a gamified attempt on GTD (Fallout: New Vegas style) for Home Assistant."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .manager import GTDManager
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["todo", "sensor"]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Register the static path and the custom card module (auto-loaded in the frontend)."""
    www_dir = os.path.join(os.path.dirname(__file__), "www")
    hass.http.async_register_static_path(f"/{DOMAIN}_static", www_dir)
    with open(os.path.join(os.path.dirname(__file__), "manifest.json"), encoding="utf-8") as f:
        version = json.load(f).get("version", "0.0.0")
    try:
        from homeassistant.components.frontend import add_extra_js_url

        add_extra_js_url(hass, f"/{DOMAIN}_static/gamified-gtd-cards.js?v={version}")
    except Exception as err:  # noqa: BLE001 - card is optional, backend must still work
        _LOGGER.warning("Could not register custom cards JS: %s", err)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gamified GTD from a config entry."""
    manager = GTDManager(hass, entry.entry_id, dict(entry.options or entry.data))
    await manager.async_load()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager
    hass.data[DOMAIN]["managers"] = [
        m for m in hass.data[DOMAIN].values() if isinstance(m, GTDManager)
    ]

    await async_setup_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.data[DOMAIN]["managers"] = [
            m for m in hass.data[DOMAIN].values() if isinstance(m, GTDManager)
        ]
        if not hass.data[DOMAIN]["managers"]:
            await async_unload_services(hass)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload on options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def get_manager(hass: HomeAssistant) -> GTDManager:
    """Return the (first) manager — services operate on the first entry for now."""
    managers: list[GTDManager] = hass.data[DOMAIN].get("managers", [])
    if not managers:
        raise ValueError("Gamified GTD is not set up")
    return managers[0]


def person_label(hass: HomeAssistant, person: str) -> str:
    """Friendly name for a person entity id."""
    state = hass.states.get(person)
    if state is not None:
        return str(state.attributes.get("friendly_name", person))
    return person.split(".", 1)[-1]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries."""
    return True
