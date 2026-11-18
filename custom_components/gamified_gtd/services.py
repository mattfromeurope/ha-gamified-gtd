"""Service registrations for Gamified GTD.

All 17 services of the `gamified_gtd` domain are registered once (guarded by
`hass.services.has_service`) and delegate to the manager of the first config entry.
Each registration carries a voluptuous schema so the HA UI shows proper form fields;
the human-readable descriptions live in services.yaml.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv

from . import gamification as g
from .const import (
    DOMAIN,
    SERVICE_ADD_REWARD,
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
    SERVICE_MOVE_TASK,
    SERVICE_REDEEM_REWARD,
    SERVICE_REMOVE_PROJECT,
    SERVICE_REMOVE_REWARD,
    SERVICE_REMOVE_TASK,
    SERVICE_RESET_PROFILE,
    SERVICE_SKIP_TASK,
    SERVICE_START_REVIEW,
    SERVICE_SUBMIT_GOAT,
    SERVICE_UPDATE_PROJECT,
    SERVICE_UPDATE_REWARD,
    SERVICE_UPDATE_TASK,
    TODO_LISTS,
)
from .goat_data import QUESTIONS
from .manager import get_manager

# Shared field block: every task-addressing service takes a task_id.
TASK_FIELDS = {
    vol.Required("task_id"): cv.string,
}

# add_to_inbox: quick capture with all optional task fields (incl. reminders /
# location / overdue_repeat for the notification scheduler and the target list).
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
        vol.Optional("list"): vol.In(list(TODO_LISTS)),
        vol.Optional("waiting_for"): cv.string,
        vol.Optional("defer_until"): cv.string,
        vol.Optional("due_time"): cv.string,
        vol.Optional("reminders"): vol.Any([vol.Coerce(int)], cv.string),
        vol.Optional("location"): vol.Schema(
            {vol.Required("zone"): cv.string, vol.Required("mode"): vol.In(["inside", "outside"])}
        ),
        vol.Optional("overdue_repeat"): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)

# clarify: decision = next_action / project / waiting_for / someday / done.
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
        vol.Optional("waiting_for"): cv.string,  # whom we wait for (decision=waiting_for)
        vol.Optional("assigned_to"): cv.string,
        vol.Optional("person"): cv.string,
    }
)

# update_task: any subset of task fields.
UPDATE_TASK_SCHEMA = vol.Schema(
    {
        **TASK_FIELDS,
        vol.Optional("title"): cv.string,
        vol.Optional("notes"): cv.string,
        vol.Optional("list"): vol.In(list(TODO_LISTS)),
        vol.Optional("context"): cv.string,
        vol.Optional("project_id"): cv.string,
        vol.Optional("waiting_for"): cv.string,
        vol.Optional("defer_until"): cv.string,
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

# create_project: a quest with name / desired outcome / optional deadline.
CREATE_PROJECT_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Optional("desired_outcome"): cv.string,
        vol.Optional("due"): cv.string,
    }
)

# add_to_project: attach a task to a quest.
ADD_TO_PROJECT_SCHEMA = vol.Schema(
    {
        **TASK_FIELDS,
        vol.Required("project_id"): cv.string,
    }
)

# allocate_skill_points: person + skill + points (FNV level-up points).
ALLOCATE_SKILL_POINTS_SCHEMA = vol.Schema(
    {
        vol.Optional("person"): cv.string,
        vol.Required("skill"): vol.In(g.SKILLS),
        vol.Required("points"): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)

# choose_perk: perk id + optional special_stat (Intense Training) / skill (Tag!).
CHOOSE_PERK_SCHEMA = vol.Schema(
    {
        vol.Optional("person"): cv.string,
        vol.Required("perk"): vol.In(list(g.PERKS_BY_ID)),
        vol.Optional("special_stat"): vol.In(g.SPECIAL_STATS),
        vol.Optional("skill"): vol.In(g.SKILLS),
    }
)

# redeem_reward: spend caps on a shop reward.
REDEEM_REWARD_SCHEMA = vol.Schema(
    {
        vol.Optional("person"): cv.string,
        vol.Required("reward"): cv.string,
    }
)

# Reward shop management: add / update / remove custom rewards (thin frontend for the
# rewards card; also usable from automations and LLM tools).
ADD_REWARD_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Optional("description", default=""): cv.string,
        vol.Optional("cost", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)
UPDATE_REWARD_SCHEMA = vol.Schema(
    {
        vol.Required("reward"): cv.string,  # reward id
        vol.Optional("name"): cv.string,
        vol.Optional("description"): cv.string,
        vol.Optional("cost"): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)
REMOVE_REWARD_SCHEMA = vol.Schema({vol.Required("reward"): cv.string})

# move_task: move a task to another GTD list (keeps project assignment + metadata).
MOVE_TASK_SCHEMA = vol.Schema(
    {
        **TASK_FIELDS,
        vol.Required("list"): vol.In(list(TODO_LISTS)),
    }
)

# submit_goat: G.O.A.T. answers — one 0-based answer index per question (10 questions).
# Accepted as a list of ints OR as a comma separated string ("0,2,1,...") — the
# manager normalizes both (the service UI only offers a text field).
SUBMIT_GOAT_SCHEMA = vol.Schema(
    {
        vol.Optional("person"): cv.string,
        vol.Required("answers"): vol.Any(
            vol.All(
                [vol.All(vol.Coerce(int), vol.Range(min=0, max=3))],
                vol.Length(min=len(QUESTIONS), max=len(QUESTIONS)),
            ),
            cv.string,
        ),
    }
)

# person-only services (start/complete review, get_state).
# update_project / remove_project: manage a quest (rename, outcome, deadline / delete).
UPDATE_PROJECT_SCHEMA = vol.Schema(
    {
        vol.Required("project_id"): cv.string,
        vol.Optional("name"): cv.string,
        vol.Optional("desired_outcome"): cv.string,
        vol.Optional("due"): cv.string,
    }
)
REMOVE_PROJECT_SCHEMA = vol.Schema({vol.Required("project_id"): cv.string})

PERSON_ONLY_SCHEMA = vol.Schema({vol.Optional("person"): cv.string})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register all gamified_gtd services (once — guarded so multiple entries don't
    double-register). Each handler resolves the manager and forwards the call."""
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

    async def handle_update_project(call: ServiceCall) -> None:
        await get_manager(hass).update_project(call)

    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE_PROJECT, handle_update_project, schema=UPDATE_PROJECT_SCHEMA
    )

    async def handle_remove_project(call: ServiceCall) -> None:
        await get_manager(hass).remove_project(call)

    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_PROJECT, handle_remove_project, schema=REMOVE_PROJECT_SCHEMA
    )

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

    async def handle_add_reward(call: ServiceCall) -> dict:
        return await get_manager(hass).add_reward(call)

    # OPTIONAL (not ONLY): the rewards card calls via hass.callService without
    # return_response — with ONLY that errors ("requires return_response=True").
    # OPTIONAL accepts both plain calls and response-requesting calls.
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_REWARD,
        handle_add_reward,
        schema=ADD_REWARD_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def handle_update_reward(call: ServiceCall) -> dict:
        return await get_manager(hass).update_reward(call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_REWARD,
        handle_update_reward,
        schema=UPDATE_REWARD_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def handle_remove_reward(call: ServiceCall) -> dict:
        return await get_manager(hass).remove_reward(call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_REWARD,
        handle_remove_reward,
        schema=REMOVE_REWARD_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def handle_get_state(call: ServiceCall) -> dict:
        return get_manager(hass).get_state(call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_STATE,
        handle_get_state,
        schema=PERSON_ONLY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    async def handle_move(call: ServiceCall) -> None:
        await get_manager(hass).move_task(call)

    hass.services.async_register(DOMAIN, SERVICE_MOVE_TASK, handle_move, schema=MOVE_TASK_SCHEMA)

    async def handle_goat(call: ServiceCall) -> dict:
        return await get_manager(hass).submit_goat(call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SUBMIT_GOAT,
        handle_goat,
        schema=SUBMIT_GOAT_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    async def handle_reset(call: ServiceCall) -> dict:
        return await get_manager(hass).reset_profile(call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_PROFILE,
        handle_reset,
        schema=PERSON_ONLY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Remove all gamified_gtd services (when the last config entry is unloaded)."""
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
        SERVICE_UPDATE_PROJECT,
        SERVICE_REMOVE_PROJECT,
        SERVICE_ALLOCATE_SKILL_POINTS,
        SERVICE_CHOOSE_PERK,
        SERVICE_START_REVIEW,
        SERVICE_COMPLETE_REVIEW,
        SERVICE_REDEEM_REWARD,
        SERVICE_ADD_REWARD,
        SERVICE_UPDATE_REWARD,
        SERVICE_REMOVE_REWARD,
        SERVICE_GET_STATE,
        SERVICE_MOVE_TASK,
        SERVICE_SUBMIT_GOAT,
        SERVICE_RESET_PROFILE,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
