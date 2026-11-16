"""Service registrations for Gamified GTD."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv

from . import gamification as g
from .const import (
    DOMAIN,
    SERVICE_ADD_TO_INBOX,
    SERVICE_ADD_TO_PROJECT,
    SERVICE_ALLOCATE_SKILL_POINTS,
    SERVICE_CHOOSE_PERK,
    SERVICE_CLARIFY,
    SERVICE_COMPLETE_PROJECT,
    SERVICE_COMPLETE_REVIEW,
    SERVICE_COMPLETE_TASK,
    SERVICE_CREATE_PROJECT,
    SERVICE_GET_STATE,
    SERVICE_REDEEM_REWARD,
    SERVICE_REMOVE_TASK,
    SERVICE_SKIP_TASK,
    SERVICE_START_REVIEW,
    SERVICE_UPDATE_TASK,
)
from . import get_manager

TASK_FIELDS = {
    vol.Required("task_id"): cv.string,
}

ADD_TO_INBOX_SCHEMA = vol.Schema(
    {
        vol.Required("title"): cv.string,
        vol.Optional("notes"): cv.string,
        vol.Optional("priority", default=3): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
        vol.Optional("due"): cv.string,
        vol.Optional("time_estimate"): vol.All(vol.Coerce(float), vol.Range(min=0)),
        vol.Optional("energy"): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
        vol.Optional("assigned_to"): cv.string,
        vol.Optional("tags"): vol.Any(cv.string, [cv.string]),
        vol.Optional("context"): cv.string,
        vol.Optional("project_id"): cv.string,
        vol.Optional("list"): vol.In(["inbox", "next_actions", "waiting_for", "someday_maybe"]),
        vol.Optional("due_time"): cv.string,
        vol.Optional("reminders"): vol.Any([vol.Coerce(int)], cv.string),
        vol.Optional("location"): vol.Schema(
            {vol.Required("zone"): cv.string, vol.Required("mode"): vol.In(["inside", "outside"])}
        ),
        vol.Optional("overdue_repeat"): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)

CLARIFY_SCHEMA = vol.Schema(
    {
        **TASK_FIELDS,
        vol.Required("decision"): vol.In(
            ["next_action", "project", "waiting_for", "someday", "done"]
        ),
        vol.Optional("context"): cv.string,
        vol.Optional("project_id"): cv.string,
        vol.Optional("project_name"): cv.string,
        vol.Optional("desired_outcome"): cv.string,
        vol.Optional("assigned_to"): cv.string,
        vol.Optional("person"): cv.string,
    }
)

UPDATE_TASK_SCHEMA = vol.Schema(
    {
        **TASK_FIELDS,
        vol.Optional("title"): cv.string,
        vol.Optional("notes"): cv.string,
        vol.Optional("list"): vol.In(["inbox", "next_actions", "waiting_for", "someday_maybe"]),
        vol.Optional("context"): cv.string,
        vol.Optional("project_id"): cv.string,
        vol.Optional("priority"): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
        vol.Optional("due"): cv.string,
        vol.Optional("time_estimate"): vol.All(vol.Coerce(float), vol.Range(min=0)),
        vol.Optional("energy"): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
        vol.Optional("assigned_to"): cv.string,
        vol.Optional("tags"): vol.Any(cv.string, [cv.string]),
        vol.Optional("due_time"): cv.string,
        vol.Optional("reminders"): vol.Any([vol.Coerce(int)], cv.string),
        vol.Optional("location"): vol.Schema(
            {vol.Required("zone"): cv.string, vol.Required("mode"): vol.In(["inside", "outside"])}
        ),
        vol.Optional("overdue_repeat"): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)

CREATE_PROJECT_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Optional("desired_outcome"): cv.string,
        vol.Optional("due"): cv.string,
    }
)

ADD_TO_PROJECT_SCHEMA = vol.Schema(
    {
        **TASK_FIELDS,
        vol.Required("project_id"): cv.string,
    }
)

ALLOCATE_SKILL_POINTS_SCHEMA = vol.Schema(
    {
        vol.Optional("person"): cv.string,
        vol.Required("skill"): vol.In(g.SKILLS),
        vol.Required("points"): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)

CHOOSE_PERK_SCHEMA = vol.Schema(
    {
        vol.Optional("person"): cv.string,
        vol.Required("perk"): vol.In(list(g.PERKS_BY_ID)),
        vol.Optional("special_stat"): vol.In(g.SPECIAL_STATS),
        vol.Optional("skill"): vol.In(g.SKILLS),
    }
)

REDEEM_REWARD_SCHEMA = vol.Schema(
    {
        vol.Optional("person"): cv.string,
        vol.Required("reward"): cv.string,
    }
)

PERSON_ONLY_SCHEMA = vol.Schema({vol.Optional("person"): cv.string})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register all gamified_gtd services (once)."""
    if hass.services.has_service(DOMAIN, SERVICE_ADD_TO_INBOX):
        return

    async def handle(call: ServiceCall) -> None:
        await get_manager(hass).add_to_inbox(call)

    hass.services.async_register(DOMAIN, SERVICE_ADD_TO_INBOX, handle, schema=ADD_TO_INBOX_SCHEMA)

    async def handle_clarify(call: ServiceCall) -> None:
        await get_manager(hass).clarify(call)

    hass.services.async_register(DOMAIN, SERVICE_CLARIFY, handle_clarify, schema=CLARIFY_SCHEMA)

    async def handle_complete(call: ServiceCall) -> None:
        await get_manager(hass).complete_task(call)

    hass.services.async_register(DOMAIN, SERVICE_COMPLETE_TASK, handle_complete, schema=vol.Schema({**TASK_FIELDS, vol.Optional("person"): cv.string}))

    async def handle_update(call: ServiceCall) -> None:
        await get_manager(hass).update_task(call)

    hass.services.async_register(DOMAIN, SERVICE_UPDATE_TASK, handle_update, schema=UPDATE_TASK_SCHEMA)

    async def handle_skip(call: ServiceCall) -> None:
        await get_manager(hass).skip_task(call)

    hass.services.async_register(DOMAIN, SERVICE_SKIP_TASK, handle_skip, schema=vol.Schema(TASK_FIELDS))

    async def handle_remove(call: ServiceCall) -> None:
        await get_manager(hass).remove_task(call)

    hass.services.async_register(DOMAIN, SERVICE_REMOVE_TASK, handle_remove, schema=vol.Schema(TASK_FIELDS))

    async def handle_create_project(call: ServiceCall) -> None:
        await get_manager(hass).create_project(call)

    hass.services.async_register(DOMAIN, SERVICE_CREATE_PROJECT, handle_create_project, schema=CREATE_PROJECT_SCHEMA)

    async def handle_add_to_project(call: ServiceCall) -> None:
        await get_manager(hass).add_to_project(call)

    hass.services.async_register(DOMAIN, SERVICE_ADD_TO_PROJECT, handle_add_to_project, schema=ADD_TO_PROJECT_SCHEMA)

    async def handle_complete_project(call: ServiceCall) -> None:
        await get_manager(hass).complete_project(call)

    hass.services.async_register(DOMAIN, SERVICE_COMPLETE_PROJECT, handle_complete_project, schema=vol.Schema({vol.Required("project_id"): cv.string}))

    async def handle_allocate(call: ServiceCall) -> None:
        await get_manager(hass).allocate_skill_points(call)

    hass.services.async_register(
        DOMAIN, SERVICE_ALLOCATE_SKILL_POINTS, handle_allocate, schema=ALLOCATE_SKILL_POINTS_SCHEMA
    )

    async def handle_choose_perk(call: ServiceCall) -> None:
        await get_manager(hass).choose_perk(call)

    hass.services.async_register(DOMAIN, SERVICE_CHOOSE_PERK, handle_choose_perk, schema=CHOOSE_PERK_SCHEMA)

    async def handle_start_review(call: ServiceCall) -> None:
        await get_manager(hass).start_review(call)

    hass.services.async_register(DOMAIN, SERVICE_START_REVIEW, handle_start_review, schema=PERSON_ONLY_SCHEMA)

    async def handle_complete_review(call: ServiceCall) -> None:
        await get_manager(hass).complete_review(call)

    hass.services.async_register(DOMAIN, SERVICE_COMPLETE_REVIEW, handle_complete_review, schema=PERSON_ONLY_SCHEMA)

    async def handle_redeem(call: ServiceCall) -> None:
        await get_manager(hass).redeem_reward(call)

    hass.services.async_register(DOMAIN, SERVICE_REDEEM_REWARD, handle_redeem, schema=REDEEM_REWARD_SCHEMA)

    async def handle_get_state(call: ServiceCall) -> dict:
        return get_manager(hass).get_state(call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_STATE,
        handle_get_state,
        schema=PERSON_ONLY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Remove all gamified_gtd services."""
    for service in (
        SERVICE_ADD_TO_INBOX,
        SERVICE_CLARIFY,
        SERVICE_COMPLETE_TASK,
        SERVICE_UPDATE_TASK,
        SERVICE_SKIP_TASK,
        SERVICE_REMOVE_TASK,
        SERVICE_CREATE_PROJECT,
        SERVICE_ADD_TO_PROJECT,
        SERVICE_COMPLETE_PROJECT,
        SERVICE_ALLOCATE_SKILL_POINTS,
        SERVICE_CHOOSE_PERK,
        SERVICE_START_REVIEW,
        SERVICE_COMPLETE_REVIEW,
        SERVICE_REDEEM_REWARD,
        SERVICE_GET_STATE,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
