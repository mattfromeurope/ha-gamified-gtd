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
    "gamified-gtd-stats",    # Pip-Boy top bar: HP | LEVEL+XP | CAPS + karma
    "gamified-gtd-special",  # the 7 S.P.E.C.I.A.L. attributes
    "gamified-gtd-skills",   # the 13 skills with TAG! badges
    "gamified-gtd-perks",    # owned perks only
    "gamified-gtd-levelup",  # skill points + perk choice (interactive)
    "gamified-gtd-goat",     # G.O.A.T. test -> Tag! skills
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


def test_all_cards_are_registered():
    src = CARDS.read_text(encoding="utf-8")
    for tag in CARD_TAGS:
        assert f'defineCard("{tag}"' in src, f"card {tag} is not registered"
    # defineCard must guard against double registration (module can load twice)
    assert "customElements.get(tag)" in src


def test_cards_read_todo_items_attribute():
    """HA does not expose todo items in state attributes — the tasks card must read
    the integration-provided `todo_items` attribute (todo.py adds it explicitly)."""
    src = CARDS.read_text(encoding="utf-8")
    assert "attributes.todo_items" in src
    # and the move-between-lists + project assignment UI must exist
    assert '"move_task"' in src
    assert "td-project" in src


def test_cards_are_theme_aware_not_pipboy_green():
    """The cards must follow the selected HA theme (theme variables), not the old
    hardcoded Pip-Boy green — so they blend in with the built-in cards."""
    src = CARDS.read_text(encoding="utf-8")
    assert "4aff4a" not in src, "hardcoded Pip-Boy green still present"
    assert "--pip:" not in src
    assert "sepia(1)" not in src, "green icon filter still present"
    assert "text-transform: uppercase" not in src
    for var in ("var(--primary-text-color)", "var(--divider-color)", "var(--primary-color)"):
        assert var in src, f"theme variable {var} missing"


def test_special_card_uses_pipboy_split_layout():
    """SPECIAL card: attribute list left, selected attribute's icon + scrollable
    description right (Pip-Boy STATS layout)."""
    src = CARDS.read_text(encoding="utf-8")
    assert 'defineCard("gamified-gtd-special"' in src
    for marker in ('class="split"', 'class="alist"', 'class="arow', 'class="detail"',
                   "detail-icon", "detail-desc", "@mouseenter"):
        assert marker in src, f"split-layout marker {marker} missing"
    # every SPECIAL attribute carries a description for the detail pane
    for stat in ("strength", "perception", "endurance", "charisma", "intelligence", "agility", "luck"):
        assert f'id: "{stat}"' in src and "desc:" in src


def test_icon_helper_png_then_svg_then_placeholder_then_text():
    """Icon lookup order: user drop-in .png -> shipped <id>.svg -> shipped
    placeholder.svg -> text glyph."""
    src = CARDS.read_text(encoding="utf-8")
    assert '.png`' in src and '.svg`' in src and 'placeholder.svg' in src
    assert 'e.target.src = svg' in src
    assert 'e.target.src = generic' in src


def test_skills_and_perks_cards_use_pipboy_split_layout():
    """Skills and Perks cards use the same split layout as SPECIAL (list left,
    icon + scrollable description right)."""
    src = CARDS.read_text(encoding="utf-8")
    for tag in ("gamified-gtd-skills", "gamified-gtd-perks"):
        assert f'defineCard("{tag}"' in src
    # both cards render the shared split structure
    assert src.count('class="split"') >= 3  # special + skills + perks
    assert src.count('class="alist"') >= 3
    assert src.count("detail-desc") >= 3
    # every skill has a description for the detail pane
    for skill in ("barter", "guns", "sneak", "unarmed"):
        assert f'id: "{skill}"' in src
    assert src.count("desc:") >= 20  # 7 SPECIAL + 13 skills


def test_skill_and_perk_placeholder_svgs_shipped():
    """Vault-Boy-style placeholder SVGs for all 13 skills + generic perk placeholder."""
    skill_dir = WWW / "gamified_gtd_icons" / "skill"
    skills = ("barter", "energy_weapons", "explosives", "guns", "lockpick", "medicine",
              "melee_weapons", "repair", "science", "sneak", "speech", "survival", "unarmed")
    for skill in skills:
        f = skill_dir / f"{skill}.svg"
        assert f.exists(), f"missing skill placeholder {f}"
        assert "<svg" in f.read_text(encoding="utf-8")
    assert (WWW / "gamified_gtd_icons" / "perk" / "placeholder.svg").exists()


def test_special_placeholder_svgs_shipped():
    """Original Vault-Boy-style placeholder SVGs for all 7 SPECIAL attributes
    (user .png drop-ins still take precedence)."""
    icons = WWW / "gamified_gtd_icons" / "special"
    for stat in ("strength", "perception", "endurance", "charisma", "intelligence", "agility", "luck"):
        f = icons / f"{stat}.svg"
        assert f.exists(), f"missing placeholder {f}"
        assert "<svg" in f.read_text(encoding="utf-8")


def test_vendored_lit_bundle_exists_and_exports_lit_api():
    assert LIT.exists(), "vendored lit bundle gamified-gtd-lit.js is missing"
    lit = LIT.read_text(encoding="utf-8")
    assert len(lit) > 10_000, "vendored lit bundle looks empty/truncated"
    # ESM export names survive minification and are what the cards module imports.
    for name in ("LitElement", "html", "css"):
        assert re.search(rf"as {name}\b", lit), f"lit bundle does not export {name}"
