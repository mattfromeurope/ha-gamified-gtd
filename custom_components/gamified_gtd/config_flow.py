"""Config flow for Gamified GTD.

Initial flow (`async_step_user`): pick persons + global options (level cap, defaults,
contexts); one entry per person selection (unique id = sorted person list).

Options flow steps: init (globals) -> notify (notify service per person, daily summary,
HA notification, unassigned-to-all) -> person (pick one) -> special (7 SPECIAL values)
-> goat (10 G.O.A.T. questions, one per form with radio-button answers, while
character creation is pending) or tags (3 Tag! skills, when it is already done).
Per-person setup is stored under "_profiles" and applied by the manager on load.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from . import gamification as g
from .goat_data import QUESTIONS, goat_result
from .const import (
    CONF_CONTEXTS,
    SPECIAL_BASE,
    SPECIAL_FREE_POINTS,
    SPECIAL_MAX,
    SPECIAL_MIN,
    SPECIAL_TOTAL_POINTS,
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
    """All person.* entities as select options (sorted)."""
    return [
        selector.SelectOptionDict(value=state.entity_id, label=state.entity_id)
        for state in sorted(hass.states.async_all("person"), key=lambda s: s.entity_id)
    ]


def _validate_special(value: dict[str, Any]) -> dict[str, Any]:
    """FNV character-creation rule for the SPECIAL allocator: every attribute is
    1-10, starts at 5, and exactly 5 additional points are distributed freely —
    values may be raised AND lowered, but the total must always be 40."""
    total = sum(int(value.get(stat, SPECIAL_BASE)) for stat in g.SPECIAL_STATS)
    if total != SPECIAL_TOTAL_POINTS:
        raise vol.Invalid(
            f"SPECIAL must total exactly {SPECIAL_TOTAL_POINTS} points "
            f"(each of the 7 attributes starts at {SPECIAL_BASE} and you distribute "
            f"{SPECIAL_FREE_POINTS} more points freely, {SPECIAL_MIN}-{SPECIAL_MAX} each) — "
            f"got {total}"
        )
    return value


def _special_schema() -> vol.Schema:
    """Plain serializable schema for the 7 SPECIAL allocator fields (no custom function
    inside vol.All — that breaks voluptuous_serialize.convert, see async_step_special)."""
    return vol.Schema(
        {
            vol.Required(stat, default=SPECIAL_BASE): vol.All(
                vol.Coerce(int), vol.Range(min=SPECIAL_MIN, max=SPECIAL_MAX)
            )
            for stat in g.SPECIAL_STATS
        }
    )


def _base_schema(hass, defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Schema for the global options (persons, level cap, default time/energy, XP base,
    default contexts) — used by the initial flow and the options 'init' step."""
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
            # NOTE: SelectOptionDict values must be strings (int values raise
            # voluptuous errors -> frontend 400). The manager coerces to int.
            vol.Required(
                CONF_LEVEL_CAP, default=str(defaults.get(CONF_LEVEL_CAP, DEFAULT_LEVEL_CAP))
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value="30", label="30 (base game)"),
                        selector.SelectOptionDict(value="50", label="50 (all DLCs)"),
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
    """Handle the initial config flow (persons + global options)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Single step: select persons and set globals; creates the entry."""
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
    """Options flow: global settings (init), notifications (notify), then per-person
    SPECIAL allocation (special) and Tag! skills (tags) — FNV character creation."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: global options (persons, level cap, defaults, contexts)."""
        # Plain OptionsFlow does NOT provide self._options in HA (only
        # OptionsFlowWithConfigEntry sets it), so initialize it from the entry here.
        if not hasattr(self, "_options"):
            self._options = dict(self.config_entry.options)
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
        """Step 2: notifications — one notify-service field per person plus daily
        summary toggle/time, HA notification center, unassigned-to-all."""
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
        """Step 3: pick the person whose SPECIAL/Tag! setup to edit."""
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
        """Step 4: allocate the 7 SPECIAL attributes like FNV character creation —
        each starts at 5, 5 points are freely distributed (raise or lower, 1-10),
        so the total must be exactly 40 (enforced by _validate_special)."""
        if user_input is not None:
            # Validate the 40-point rule here in the step and NOT via vol.All(...,
            # _validate_special) in the data_schema: voluptuous_serialize.convert
            # (used to send the form to the frontend) cannot serialize a plain
            # function inside vol.All and raises -> "Unknown error occurred".
            try:
                _validate_special(user_input)
            except vol.Invalid as err:
                return self.async_show_form(
                    step_id="special", data_schema=_special_schema(), errors={"base": str(err)}
                )
            self._special = {
                stat: int(user_input.get(stat, SPECIAL_BASE)) for stat in g.SPECIAL_STATS
            }
            # While character creation is pending (no G.O.A.T. result and no Tag!
            # skills yet), the G.O.A.T. follows directly after S.P.E.C.I.A.L.; for an
            # already-created character the manual Tag! picker is shown instead.
            setup = self._options.get("_profiles", {}).get(self._person, {})
            if not setup.get("goat") and not setup.get("tagged_skills"):
                return await self.async_step_goat()
            return await self.async_step_tags()
        return self.async_show_form(step_id="special", data_schema=_special_schema())

    async def async_step_goat(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """G.O.A.T. step (Fallout 3 Vault 101 test), shown directly after the
        S.P.E.C.I.A.L. step while character creation is pending. ONE question per form:
        the question text (+ slide image when the user dropped it in) goes into the
        markdown description, the 4 answers are radio buttons (SelectSelectorMode.LIST
        renders a ha-radio-group) directly below it — so every answer is clearly tied
        to its question. After the 10th answer, _goat_finish scores the answers and
        stores SPECIAL + G.O.A.T. result + Tag! skills on the person's profile — no
        dashboard card needed."""
        if not hasattr(self, "_goat_idx"):
            self._goat_idx = 0  # 0-based index of the question currently shown
            self._goat_answers = []
        if user_input is not None:
            # store the answer of the question that was just shown, then advance
            self._goat_answers.append(int(user_input["answer"]))
            self._goat_idx += 1
            if self._goat_idx >= len(QUESTIONS):
                return await self._goat_finish()
        q = QUESTIONS[self._goat_idx]
        # Slide images are user drop-ins (original FNV art is copyrighted):
        # www/gamified_gtd_icons/goat/slide_<n>.png, served under /<DOMAIN>_static/...
        # Embed the image only when the file exists -> no broken images. Select option
        # values must be strings (int values raise voluptuous errors -> frontend 400).
        goat_dir = os.path.join(
            os.path.dirname(__file__), "www", "gamified_gtd_icons", "goat"
        )
        img = ""
        if os.path.exists(os.path.join(goat_dir, f"{q.slide}.png")):
            img = f"\n\n![G.O.A.T. slide {q.n}](/{DOMAIN}_static/gamified_gtd_icons/goat/{q.slide}.png)"
        question_md = f"**Question {q.n} of {len(QUESTIONS)}.** {q.text}{img}"
        schema = vol.Schema(
            {
                vol.Required("answer", default="0"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=str(i), label=a.text)
                            for i, a in enumerate(q.answers)
                        ],
                        mode=selector.SelectSelectorMode.LIST,  # -> radio buttons
                    )
                )
            }
        )
        # async_show_form has no `description` kwarg — the step description comes from
        # strings.json; the dynamic question markdown is injected via the {question}
        # placeholder (rendered as markdown by the frontend).
        return self.async_show_form(
            step_id="goat",
            data_schema=schema,
            description_placeholders={"question": question_md},
            last_step=self._goat_idx == len(QUESTIONS) - 1,
        )

    async def _goat_finish(self) -> ConfigFlowResult:
        """Score the collected G.O.A.T. answers (one 0-based answer index per question)
        via goat_data.goat_result and finish the options flow, storing SPECIAL + the
        G.O.A.T. result + the derived Tag! skills on the chosen person's profile."""
        result = goat_result(self._goat_answers)
        profiles = dict(self._options.get("_profiles", {}))
        profiles[self._person] = {
            "special": self._special,
            "goat": {
                "answers": self._goat_answers,
                "counts": result["counts"],
                "tags": result["tags"],
                "job": result["job"],
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            "tagged_skills": result["tags"],
        }
        self._options["_profiles"] = profiles
        self._options[CONF_DEFAULT_PROFILE] = self._options.get(
            CONF_DEFAULT_PROFILE, self._person
        )
        return self.async_create_entry(title="", data=self._options)

    async def async_step_tags(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 5 (alternative): choose the 3 Tag! skills (+15 each) manually; finishes
        the options flow. Only shown when character creation is already done — while it
        is pending, the G.O.A.T. step follows S.P.E.C.I.A.L. instead."""
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
