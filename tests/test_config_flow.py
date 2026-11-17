"""Options flow: S.P.E.C.I.A.L. step is followed directly by the G.O.A.T. step while
character creation is pending (no G.O.A.T. result, no Tag! skills yet) — and by the
manual Tag! picker once a character exists. Also covers the `_options` initialization
(plain OptionsFlow does not provide it in HA — it must come from config_entry.options).
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytest.importorskip("homeassistant")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import voluptuous_serialize  # noqa: E402
from homeassistant.helpers import config_validation as cv  # noqa: E402

from custom_components.gamified_gtd.config_flow import GamifiedGDTOptionsFlow  # noqa: E402
from custom_components.gamified_gtd.goat_data import QUESTIONS  # noqa: E402

SPECIAL_STATS = (
    "strength", "perception", "endurance", "charisma",
    "intelligence", "agility", "luck",
)


def _valid_special_input() -> dict:
    """A valid FNV allocation: all attributes at 5 plus 5 free points = 40 total."""
    values = {s: "5" for s in SPECIAL_STATS}
    values["strength"] = "10"
    return values


def _flow(profiles: dict | None = None, person: str = "person.x") -> GamifiedGDTOptionsFlow:
    flow = GamifiedGDTOptionsFlow()
    flow._options = {"_profiles": profiles or {}}
    flow._person = person
    return flow


def test_goat_step_shows_one_question_with_radio_answers():
    """One question per form: the question markdown (incl. slide image when the drop-in
    file exists) goes into the {question} placeholder — async_show_form has no
    description kwarg, descriptions come from strings.json. The single 'answer' field
    uses SelectSelectorMode.LIST, which the frontend renders as radio buttons."""
    flow = _flow()
    flow._special = {s: 5 for s in SPECIAL_STATS}
    result = asyncio.run(flow.async_step_goat(None))
    assert result["type"] == "form" and result["step_id"] == "goat"
    assert not result.get("last_step")
    assert len(result["data_schema"].schema) == 1  # only the current question
    question_md = result["description_placeholders"]["question"]
    assert "Question 1 of 10" in question_md and QUESTIONS[0].text in question_md
    # no slide drop-ins in the repo -> no broken image markdown
    assert "![G.O.A.T. slide" not in question_md
    # serialized schema: select selector in LIST mode (radio buttons) with 4 options
    (field,) = voluptuous_serialize.convert(
        result["data_schema"], custom_serializer=cv.custom_serializer
    )
    assert field["name"] == "answer"
    sel = field["selector"]["select"]
    assert sel["mode"] == "list" and len(sel["options"]) == 4


def test_goat_step_walks_all_10_questions_then_stores_result():
    """Each submit stores one answer and shows the next question; after the 10th the
    flow finishes and SPECIAL + G.O.A.T. result + Tag! skills are stored on the profile."""
    flow = _flow()
    flow._special = {s: 5 for s in SPECIAL_STATS}

    async def run():
        r = await flow.async_step_goat(None)  # first question form
        for i in range(len(QUESTIONS)):
            assert r["type"] == "form" and r["step_id"] == "goat"
            # last question shows "Submit" instead of "Next"
            assert r["last_step"] == (i == len(QUESTIONS) - 1)
            assert f"Question {i + 1} of 10" in r["description_placeholders"]["question"]
            _serialize(r)
            r = await flow.async_step_goat({"answer": "0"})
        return r

    result = asyncio.run(run())
    assert result["type"] == "create_entry"
    setup = result["data"]["_profiles"]["person.x"]
    assert setup["special"] == flow._special
    assert setup["tagged_skills"] == setup["goat"]["tags"] == ["guns", "barter", "explosives"]
    assert setup["goat"]["job"]["name"] == "Tattoo artist"
    assert setup["goat"]["answers"] == [0] * 10
    assert "completed_at" in setup["goat"]


def test_special_step_routes_to_goat_while_character_creation_pending():
    flow = _flow(profiles={})
    result = asyncio.run(flow.async_step_special(_valid_special_input()))
    assert result["step_id"] == "goat"


def test_special_step_rejects_wrong_total_and_reshows_form():
    """All attributes at 5 = 35 points, not 40 -> base error, form re-shown."""
    flow = _flow(profiles={})
    result = asyncio.run(flow.async_step_special({s: "5" for s in SPECIAL_STATS}))
    assert result["type"] == "form" and result["step_id"] == "special"
    assert "40" in result["errors"]["base"]


def test_special_step_routes_to_tags_when_character_exists():
    flow = _flow(profiles={"person.x": {"tagged_skills": ["guns"]}})
    result = asyncio.run(flow.async_step_special(_valid_special_input()))
    assert result["step_id"] == "tags"


def _serialize(result) -> None:
    """Every form schema must survive voluptuous_serialize.convert — HA calls this when
    sending the form to the frontend; a custom function inside vol.All raises ValueError
    and the UI shows 'Unknown error occurred' on the step that was just submitted."""
    assert result["type"] == "form"
    voluptuous_serialize.convert(result["data_schema"], custom_serializer=cv.custom_serializer)


def test_all_step_schemas_serialize_for_frontend():
    """Regression: vol.All(vol.Schema(...), _validate_special) broke serialization ->
    'Unknown error occurred' after OK on the person step (special form never shown)."""
    flow = _flow()
    flow.hass = MagicMock()
    flow.hass.states.async_all.return_value = [MagicMock(entity_id="person.x")]
    entry = MagicMock()
    entry.data = {"persons": ["person.x"]}
    entry.options = {}
    flow._config_entry = entry
    flow.handler = "e1"
    flow.flow_id = "f1"
    flow.context = {}

    async def run():
        r = await flow.async_step_init(None)
        _serialize(r)
        r = await flow.async_step_init(
            {
                "persons": ["person.x"], "level_cap": "30",
                "default_time_estimate": 15, "default_energy": 3, "default_xp_base": 10,
            }
        )
        _serialize(r)  # notify
        r = await flow.async_step_notify({})
        _serialize(r)  # person
        r = await flow.async_step_person({"person": "person.x"})
        _serialize(r)  # special
        r = await flow.async_step_special(_valid_special_input())
        _serialize(r)  # goat, question 1 (character creation pending)
        for _ in range(len(QUESTIONS) - 1):
            r = await flow.async_step_goat({"answer": "0"})
            _serialize(r)  # goat, next question
        # invalid SPECIAL (35 != 40) re-shows the form with a base error
        r = await flow.async_step_special({s: "5" for s in SPECIAL_STATS})
        assert r["type"] == "form" and r["step_id"] == "special" and r["errors"]["base"]
        _serialize(r)

    asyncio.run(run())


def test_options_flow_options_initialized_from_entry():
    """Plain OptionsFlow has no _options attribute in HA — async_step_init must
    initialize it from config_entry.options, not crash with AttributeError on submit."""
    flow = GamifiedGDTOptionsFlow()
    assert not hasattr(flow, "_options")
    flow.hass = MagicMock()
    flow.hass.states.async_all.return_value = []
    entry = MagicMock()
    entry.data = {}
    entry.options = {"persons": ["person.x"], "_profiles": {}}
    flow._config_entry = entry  # config_entry property returns this without hass
    result = asyncio.run(flow.async_step_init(None))
    assert result["type"] == "form" and result["step_id"] == "init"
    assert flow._options == {"persons": ["person.x"], "_profiles": {}}
    result = asyncio.run(
        flow.async_step_init(
            {
                "persons": ["person.x"],
                "level_cap": "30",
                "default_time_estimate": 15,
                "default_energy": 3,
                "default_xp_base": 10,
            }
        )
    )
    assert result["step_id"] == "notify"  # submit no longer crashes, flow continues
    assert flow._options["persons"] == ["person.x"]
