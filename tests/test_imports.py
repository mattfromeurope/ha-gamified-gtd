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
