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
    # A real dict: the frontend-asset registration stores an idempotence flag
    # in hass.data[DOMAIN], and add_extra_js_url needs the frontend UrlManager
    # entries in hass.data — a MagicMock would silently swallow both.
    hass.data = {}
    return hass


def _hass_with_frontend(http):
    """hass mock that looks like a running HA frontend integration."""
    from homeassistant.components.frontend import (
        DATA_EXTRA_JS_URL_ES5,
        DATA_EXTRA_MODULE_URL,
        UrlManager,
    )

    hass = _hass(http)
    hass.data[DATA_EXTRA_MODULE_URL] = UrlManager(lambda *args: None, [])
    hass.data[DATA_EXTRA_JS_URL_ES5] = UrlManager(lambda *args: None, [])
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


def test_setup_registers_card_module_as_extra_frontend_url():
    """The card JS must land in frontend.DATA_EXTRA_MODULE_URL — HA's index.html
    dynamically imports every URL in that set on page load. Without it the cards
    show "Custom element not found"."""
    from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL

    http = _NewHTTP()
    hass = _hass_with_frontend(http)
    assert asyncio.run(async_setup(hass, {})) is True
    urls = hass.data[DATA_EXTRA_MODULE_URL].urls
    assert any(
        u.startswith("/gamified_gtd_static/gamified-gtd-cards.js?v=") for u in urls
    ), f"card module URL missing from extra module urls: {urls}"


def test_frontend_asset_registration_is_idempotent():
    """async_setup AND async_setup_entry both call the registration — it must not
    register the static path / extra URL twice (aiohttp would raise on duplicate
    resources)."""
    from custom_components.gamified_gtd import _async_register_frontend_assets

    http = _NewHTTP()
    hass = _hass_with_frontend(http)
    asyncio.run(_async_register_frontend_assets(hass))
    asyncio.run(_async_register_frontend_assets(hass))
    assert len(http.calls) == 1


def test_static_path_serves_cards_and_lit_bundle():
    """End-to-end: the static resource registered with hass.http must actually
    serve the card module and the vendored lit fallback with 200 + JS content type
    (loopback only)."""
    aiohttp = pytest.importorskip("aiohttp")
    from aiohttp import web

    from homeassistant.components.http.static import CachingStaticResource

    www = (
        Path(__file__).resolve().parent.parent
        / "custom_components"
        / "gamified_gtd"
        / "www"
    )

    async def main():
        app = web.Application()
        # Same call our async_setup performs via hass.http.async_register_static_paths.
        app.router.register_resource(CachingStaticResource("/gamified_gtd_static", str(www)))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(
                    f"http://127.0.0.1:{port}/gamified_gtd_static/gamified-gtd-cards.js?v=0.1.1"
                ) as resp:
                    body = await resp.text()
                    assert resp.status == 200
                    assert "javascript" in (resp.headers.get("Content-Type") or "")
                    assert "defineCard" in body
                async with sess.get(
                    f"http://127.0.0.1:{port}/gamified_gtd_static/gamified-gtd-lit.js"
                ) as resp:
                    lit = await resp.text()
                    assert resp.status == 200
                    assert "LitElement" in lit
        finally:
            await runner.cleanup()

    asyncio.run(main())
