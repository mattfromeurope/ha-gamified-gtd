"""Regression tests for async_setup with different HA http APIs.

Issue #3 follow-up: `hass.http.async_register_static_path` (singular) was removed
in newer HA versions -> AttributeError during setup ("refuses to load").
The setup must work with both the old singular and the new plural API.

Requires `homeassistant` installed (runs in the import-smoke CI job).
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytest.importorskip("homeassistant")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.gamified_gtd import async_setup  # noqa: E402


class _NewHTTP:
    """HA >= 2025.x style: only the plural async API exists."""

    def __init__(self):
        self.calls = []

    async def async_register_static_paths(self, configs):
        self.calls.append(configs)


class _OldHTTP:
    """Old HA style: only the singular sync API exists."""

    def __init__(self):
        self.calls = []

    def async_register_static_path(self, url_path, path):
        self.calls.append((url_path, path))


def _hass(http):
    hass = MagicMock()
    hass.http = http
    return hass


def test_setup_with_new_plural_api():
    from homeassistant.components.http import StaticPathConfig

    http = _NewHTTP()
    assert asyncio.run(async_setup(_hass(http), {})) is True
    assert len(http.calls) == 1
    config = http.calls[0][0]
    assert isinstance(config, StaticPathConfig)
    assert config.url_path == "/gamified_gtd_static"
    assert config.path.endswith(os.path.join("gamified_gtd", "www"))


def test_setup_with_old_singular_api():
    http = _OldHTTP()
    assert asyncio.run(async_setup(_hass(http), {})) is True
    assert len(http.calls) == 1
    assert http.calls[0][0] == "/gamified_gtd_static"
