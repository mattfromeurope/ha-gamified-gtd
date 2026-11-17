"""Checks for the custom card assets served from www/ (pure Python, no HA needed).

Background: the card module must NOT use a static `import ... from "lit"`. HA's
index.html only exposes "lit" through an import map on recent frontend versions
(>= 2025.12); on older versions that static import fails the whole module with
"Failed to resolve module specifier \"lit\"" and no custom element is ever
defined, so every card shows "Custom element not found". The cards module loads
lit via dynamic import("lit") with a fallback to the vendored gamified-gtd-lit.js
bundle next to it — these tests pin that contract.
"""

import re
from pathlib import Path

WWW = Path(__file__).resolve().parent.parent / "custom_components" / "gamified_gtd" / "www"
CARDS = WWW / "gamified-gtd-cards.js"
LIT = WWW / "gamified-gtd-lit.js"

CARD_TAGS = [
    "gamified-gtd-stats",
    "gamified-gtd-quests",
    "gamified-gtd-tasks",
    "gamified-gtd-review",
    "gamified-gtd-rewards",
]


def test_cards_module_has_no_static_lit_import():
    """A static bare "lit" import would kill the whole module on older HA versions."""
    src = CARDS.read_text(encoding="utf-8")
    assert not re.search(r'^import\s.*from\s["\']lit["\']', src, re.MULTILINE), (
        "cards module must load lit dynamically, not via a static bare import"
    )


def test_cards_module_loads_lit_dynamically_with_vendored_fallback():
    src = CARDS.read_text(encoding="utf-8")
    assert 'await import("lit")' in src
    assert 'await import("./gamified-gtd-lit.js")' in src


def test_all_five_cards_are_registered():
    src = CARDS.read_text(encoding="utf-8")
    for tag in CARD_TAGS:
        assert f'defineCard("{tag}"' in src, f"card {tag} is not registered"
    # defineCard must guard against double registration (module can load twice)
    assert "customElements.get(tag)" in src


def test_vendored_lit_bundle_exists_and_exports_lit_api():
    assert LIT.exists(), "vendored lit bundle gamified-gtd-lit.js is missing"
    lit = LIT.read_text(encoding="utf-8")
    assert len(lit) > 10_000, "vendored lit bundle looks empty/truncated"
    # ESM export names survive minification and are what the cards module imports.
    for name in ("LitElement", "html", "css"):
        assert re.search(rf"as {name}\b", lit), f"lit bundle does not export {name}"
