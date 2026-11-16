"""Config flow for Gamified GTD."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from . import gamification as g
from .const import (
    CONF_CONTEXTS,
    CONF_DEFAULT_ENERGY,
    CONF_DEFAULT_PROFILE,
    CONF_DEFAULT_TIME_ESTIMATE,
    CONF_DEFAULT_XP_BASE,
    CONF_HA_NOTIFICATION,
    CONF_LEVEL_CAP,
    CONF_NOTIFY_SERVICES,
    CONF_PERSONS,
    CONF_REWARDS,
    CONF_SUMMARY_ENABLED,
    CONF_SUMMARY_TIME,
    CONF_UNASSIGNED_TO_ALL,
    DEFAULT_CONTEXTS,
    DEFAULT_ENERGY,
    DEFAULT_LEVEL_CAP,
    DEFAULT_SUMMARY_TIME,
    DEFAULT_TIME_ESTIMATE,
    DEFAULT_XP_BASE,
    DOMAIN,
)


def _person_options(hass) -> list[selector.SelectOptionDict]:
    return [
        selector.SelectOptionDict(value=state.entity_id, label=state.entity_id)
        for state in sorted(hass.states.async_all("person"), key=lambda s: s.entity_id)
    ]


def _base_schema(hass, defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_PERSONS, default=defaults.get(CONF_PERSONS, [])
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_person_options(hass),
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_LEVEL_CAP, default=defaults.get(CONF_LEVEL_CAP, DEFAULT_LEVEL_CAP)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=30, label="30 (base game)"),
                        selector.SelectOptionDict(value=50, label="50 (all DLCs)"),
                    ]
                )
            ),
            vol.Required(
                CONF_DEFAULT_TIME_ESTIMATE,
                default=defaults.get(CONF_DEFAULT_TIME_ESTIMATE, DEFAULT_TIME_ESTIMATE),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
            vol.Required(
                CONF_DEFAULT_ENERGY, default=defaults.get(CONF_DEFAULT_ENERGY, DEFAULT_ENERGY)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
            vol.Required(
                CONF_DEFAULT_XP_BASE, default=defaults.get(CONF_DEFAULT_XP_BASE, DEFAULT_XP_BASE)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1000)),
            vol.Optional(
                CONF_CONTEXTS, default=defaults.get(CONF_CONTEXTS, DEFAULT_CONTEXTS)
            ): selector.TextSelector(
                selector.TextSelectorConfig(multiple=True)
            ),
        }
    )


class GamifiedGTDConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            persons = user_input[CONF_PERSONS]
            await self.async_set_unique_id("_".join(sorted(persons)))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Gamified GTD", data={**user_input, CONF_REWARDS: None}
            )
        return self.async_show_form(
            step_id="user", data_schema=_base_schema(self.hass)
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> "GamifiedGDTOptionsFlow":
        return GamifiedGDTOptionsFlow()


class GamifiedGDTOptionsFlow(OptionsFlow):
    """Options: global settings plus per-person SPECIAL / Tag! setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._options = {**self._options, **user_input}
            return await self.async_step_notify()
        merged = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=_base_schema(self.hass, merged)
        )

    async def async_step_notify(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            notify_map = {
                p: user_input.pop(p, "")
                for p in self._options.get(CONF_PERSONS, [])
                if p in user_input
            }
            self._options[CONF_NOTIFY_SERVICES] = notify_map
            self._options.update(user_input)
            return await self.async_step_person()
        merged = {**self.config_entry.data, **self.config_entry.options}
        persons = merged.get(CONF_PERSONS, [])
        notify_map = merged.get(CONF_NOTIFY_SERVICES, {})
        schema = {
            vol.Optional(
                CONF_SUMMARY_ENABLED,
                default=bool(merged.get(CONF_SUMMARY_ENABLED, False)),
            ): bool,
            vol.Optional(
                CONF_SUMMARY_TIME,
                default=merged.get(CONF_SUMMARY_TIME, DEFAULT_SUMMARY_TIME),
            ): selector.TimeSelector(),
            vol.Optional(
                CONF_HA_NOTIFICATION,
                default=bool(merged.get(CONF_HA_NOTIFICATION, False)),
            ): bool,
            vol.Optional(
                CONF_UNASSIGNED_TO_ALL,
                default=bool(merged.get(CONF_UNASSIGNED_TO_ALL, False)),
            ): bool,
        }
        for person in persons:
            schema[vol.Optional(person, default=notify_map.get(person, ""))] = cv.string
        return self.async_show_form(
            step_id="notify", data_schema=vol.Schema(schema)
        )

    async def async_step_person(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        persons = self._options.get(CONF_PERSONS, [])
        if user_input is not None:
            self._person = user_input["person"]
            return await self.async_step_special()
        return self.async_show_form(
            step_id="person",
            data_schema=vol.Schema(
                {
                    vol.Required("person"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=p, label=p) for p in persons
                            ]
                        )
                    )
                }
            ),
        )

    async def async_step_special(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._special = user_input
            return await self.async_step_tags()
        schema = vol.Schema(
            {
                vol.Required(stat, default=5): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=10)
                )
                for stat in g.SPECIAL_STATS
            }
        )
        return self.async_show_form(step_id="special", data_schema=schema)

    async def async_step_tags(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            profiles = dict(self._options.get("_profiles", {}))
            profiles[self._person] = {
                "special": self._special,
                "tagged_skills": user_input["tagged_skills"],
            }
            self._options["_profiles"] = profiles
            self._options[CONF_DEFAULT_PROFILE] = self._options.get(
                CONF_DEFAULT_PROFILE, self._person
            )
            return self.async_create_entry(title="", data=self._options)
        return self.async_show_form(
            step_id="tags",
            data_schema=vol.Schema(
                {
                    vol.Required("tagged_skills"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=s, label=s) for s in g.SKILLS
                            ],
                            multiple=True,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )
