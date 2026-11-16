"""Gamified GTD — a gamified attempt on GTD (Fallout: New Vegas style) for Home Assistant.

This module wires everything together:
- ``async_setup`` registers the custom card JS and the LLM tool set once per HA start.
- ``async_setup_entry`` creates the manager (storage + business logic), forwards the
  ``todo``/``sensor`` platforms, registers the services and starts the notification
  scheduler for the entry.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .manager import GTDManager, get_manager  # noqa: F401  (re-exported)
from .notify import NotificationScheduler
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

# Entity platforms forwarded per config entry.
PLATFORMS = ["todo", "sensor"]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up once per Home Assistant start (not per config entry).

    Registers the static path for the card JS / user icons, adds the card module to
    the frontend's extra JS URLs, and registers the LLM tool set for conversation
    agents. Everything frontend/LLM related is best-effort: the backend works even
    if that registration fails.
    """
    await _async_register_frontend_assets(hass)
    try:
        from homeassistant.helpers import llm

        from .llm_api import GamifiedGTDAPI

        # Makes the "Gamified GTD" tool set selectable in Assist's Control-Home-Assistant.
        llm.async_register_api(hass, GamifiedGTDAPI(hass))
    except Exception as err:  # noqa: BLE001 - LLM tools are optional on older cores
        _LOGGER.warning("Could not register LLM tools: %s", err)
    return True


async def _async_register_frontend_assets(hass: HomeAssistant) -> None:
    """Serve www/ and register the card module with the frontend (idempotent).

    Two things are needed before the custom cards can load:
    1. a static path, so that /gamified_gtd_static/gamified-gtd-cards.js returns 200
       (cards JS + vendored lit fallback + the user icon drop-in folder);
    2. the card module added to the frontend's "extra module url" set
       (frontend.DATA_EXTRA_MODULE_URL) — HA's index.html dynamically imports every
       URL in that set on page load. ?v=<manifest version> busts the browser cache
       (the static path sends long-lived cache headers) after updates.

    Called from BOTH async_setup and async_setup_entry: the domain-level async_setup
    only runs when the first config entry is set up, and calling it in both places
    guarantees the URL is present before the next page load regardless of setup
    order differences between HA versions. A failure here must never break the
    backend, so everything is best-effort and only logs a warning.
    """
    data = hass.data.setdefault(DOMAIN, {})
    if data.get("_frontend_assets_registered"):
        return  # already done in this HA process — register only once
    data["_frontend_assets_registered"] = True
    www_dir = os.path.join(os.path.dirname(__file__), "www")
    try:
        # Serve www/ under /gamified_gtd_static (cards JS + optional user icons).
        # NOTE: the singular hass.http.async_register_static_path was removed in newer
        # HA versions (breaks in 2025.7) — use the plural async API with a fallback.
        if hasattr(hass.http, "async_register_static_paths"):
            from homeassistant.components.http import StaticPathConfig

            await hass.http.async_register_static_paths(
                [StaticPathConfig(f"/{DOMAIN}_static", www_dir)]
            )
        else:  # older HA versions
            hass.http.async_register_static_path(f"/{DOMAIN}_static", www_dir)
    except Exception as err:  # noqa: BLE001 - cards are optional, backend must still work
        _LOGGER.warning("Could not register static path for card assets: %s", err)
    with open(os.path.join(os.path.dirname(__file__), "manifest.json"), encoding="utf-8") as f:
        version = json.load(f).get("version", "0.0.0")
    try:
        from homeassistant.components.frontend import add_extra_js_url

        # ?v=<version> forces a reload of the card JS after updates.
        add_extra_js_url(hass, f"/{DOMAIN}_static/gamified-gtd-cards.js?v={version}")
    except Exception as err:  # noqa: BLE001 - card is optional, backend must still work
        _LOGGER.warning("Could not register custom cards JS: %s", err)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gamified GTD from a config entry.

    Creates the manager (loads the store, ensures profiles), registers services once,
    forwards platforms, and starts the reminder/summary scheduler.
    """
    # Make sure the card assets are registered even if the domain-level
    # async_setup ran in an unexpected order (helper is idempotent).
    await _async_register_frontend_assets(hass)

    # Options override data; the manager keeps a merged view.
    manager = GTDManager(hass, entry.entry_id, dict(entry.options or entry.data))
    await manager.async_load()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager
    # Keep a flat list of managers — services use the first one for now.
    hass.data[DOMAIN]["managers"] = [
        m for m in hass.data[DOMAIN].values() if isinstance(m, GTDManager)
    ]

    await async_setup_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reminder/summary scheduler for this entry's data.
    scheduler = NotificationScheduler(hass, manager)
    await scheduler.async_start()
    hass.data[DOMAIN][f"{entry.entry_id}_scheduler"] = scheduler

    # Reload the whole entry when options change.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry: stop the scheduler, unload platforms, drop the manager.

    Services are only removed when the last entry is gone.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        scheduler = hass.data[DOMAIN].pop(f"{entry.entry_id}_scheduler", None)
        if scheduler is not None:
            await scheduler.async_stop()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.data[DOMAIN]["managers"] = [
            m for m in hass.data[DOMAIN].values() if isinstance(m, GTDManager)
        ]
        if not hass.data[DOMAIN]["managers"]:
            await async_unload_services(hass)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when the user changes options in the config flow."""
    await hass.config_entries.async_reload(entry.entry_id)


def person_label(hass: HomeAssistant, person: str) -> str:
    """Friendly name for a person entity id (falls back to the entity id suffix)."""
    state = hass.states.get(person)
    if state is not None:
        return str(state.attributes.get("friendly_name", person))
    return person.split(".", 1)[-1]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries (storage version is handled by the manager)."""
    return True
