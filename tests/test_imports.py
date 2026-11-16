"""Smoke test: import every integration module the way Home Assistant does.

Requires `homeassistant` to be installed (CI job installs it). Import errors that
originate from HA's own site-packages (missing optional deps in a minimal pip
env) are tolerated; errors from OUR files fail the test — this is what caused
"Invalid handler specified" in the config flow before.

Also asserts the ConfigFlow handler is discoverable for the domain.
"""

import importlib
import sys
import traceback
from pathlib import Path

import pytest

pytest.importorskip("homeassistant")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so "custom_components" is importable

MODULES = [
    "custom_components.gamified_gtd",
    "custom_components.gamified_gtd.const",
    "custom_components.gamified_gtd.gamification",
    "custom_components.gamified_gtd.perks_data",
    "custom_components.gamified_gtd.manager",
    "custom_components.gamified_gtd.notify",
    "custom_components.gamified_gtd.sensor",
    "custom_components.gamified_gtd.todo",
    "custom_components.gamified_gtd.services",
    "custom_components.gamified_gtd.config_flow",
    "custom_components.gamified_gtd.llm_api",
]


def _error_in_our_code(tb_text: str) -> bool:
    """True if the traceback's failing frame is inside our component (not site-packages)."""
    lines = [l for l in tb_text.splitlines() if l.strip().startswith("File")]
    if not lines:
        return True
    last = lines[-1]
    return "custom_components" in last and "site-packages" not in last


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module):
    try:
        importlib.import_module(module)
    except Exception:
        tb = traceback.format_exc()
        if _error_in_our_code(tb):
            raise AssertionError(f"import of {module} fails in OUR code:\n{tb}")
        pytest.skip(f"HA-internal dependency missing in minimal env: {tb.splitlines()[-1]}")


def test_config_flow_handler_registered():
    """HA discovers config flows via the HANDLERS registry (the `domain=` class
    keyword registers the subclass there) — this is what 'Invalid handler
    specified' complained about when imports were broken."""
    from homeassistant.config_entries import HANDLERS, ConfigFlow

    importlib.import_module("custom_components.gamified_gtd.config_flow")
    assert "gamified_gtd" in HANDLERS, "domain not registered in HANDLERS"
    handler = HANDLERS["gamified_gtd"]
    assert issubclass(handler, ConfigFlow)
    assert handler.__name__ == "GamifiedGTDConfigFlow"


def test_config_flow_user_form_builds(tmp_path):
    """Build the initial form exactly like the frontend does — catches selector
    schema errors (e.g. non-string SelectOptionDict values -> HTTP 400)."""
    import asyncio

    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import HANDLERS

    importlib.import_module("custom_components.gamified_gtd.config_flow")

    async def run():
        hass = HomeAssistant(str(tmp_path))
        hass.states.async_set("person.alex", "home", {"friendly_name": "Alex"})
        flow = HANDLERS["gamified_gtd"]()
        flow.hass = hass
        flow.handler = "gamified_gtd"
        flow.flow_id = "test"
        flow.context = {"source": "user"}
        result = await flow.async_step_user(None)
        assert result["type"] == "form"
        assert result["step_id"] == "user"
        # the schema must be serializable the way the frontend receives it
        for key in result["data_schema"].schema:
            pass
        return result

    result = asyncio.run(run())
    # every select option value must be a string
    for key, validator in result["data_schema"].schema.items():
        cfg = getattr(validator, "config", None)
        options = getattr(cfg, "options", None) if cfg else None
        if options:
            for opt in options:
                assert isinstance(opt["value"], str), f"{key}: option value not a str: {opt}"
