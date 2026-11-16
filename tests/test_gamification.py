"""Unit tests for the pure FNV gamification logic (no Home Assistant needed).

Run with: python -m pytest tests/ -q
"""

import sys
from pathlib import Path

# Make custom_components/gamified_gtd importable without HA installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "custom_components" / "gamified_gtd"))

import gamification as g  # noqa: E402

ALL5 = {s: 5 for s in g.SPECIAL_STATS}
SKILLS15 = {s: 15 for s in g.SKILLS}


# ---------------------------------------------------------------------------
# XP curve (GECK engine formula)
# ---------------------------------------------------------------------------


def test_xp_curve_vanilla_totals():
    assert g.cumulative_xp_for_level(1) == 0
    assert g.cumulative_xp_for_level(2) == 200
    assert g.cumulative_xp_for_level(3) == 550
    assert g.cumulative_xp_for_level(4) == 1050
    assert g.cumulative_xp_for_level(50) == 186200


def test_xp_for_level_incremental():
    assert g.xp_for_level(2) == 200
    assert g.xp_for_level(3) == 350


def test_level_from_xp():
    assert g.level_from_xp(0) == 1
    assert g.level_from_xp(199) == 1
    assert g.level_from_xp(200) == 2
    assert g.level_from_xp(549) == 2
    assert g.level_from_xp(550) == 3
    assert g.level_from_xp(186200) == 50
    assert g.level_from_xp(10**9, cap=50) == 50
    assert g.level_from_xp(10**9, cap=30) == 30


# ---------------------------------------------------------------------------
# Skills / skill points / HP
# ---------------------------------------------------------------------------


def test_skill_points_odd_int_alternates():
    p, carry = g.skill_points_for_level_up(9, False)
    assert (p, carry) == (14, True)
    p, carry = g.skill_points_for_level_up(9, True)
    assert (p, carry) == (15, False)
    p, carry = g.skill_points_for_level_up(10, False)
    assert (p, carry) == (15, False)


def test_skill_formula_fnv_example():
    # Wiki example: END 5, LCK 5 -> Unarmed 15
    assert g.skill_value("unarmed", ALL5, 0, False) == 15
    assert g.skill_value("unarmed", ALL5, 0, True) == 30  # Tag!
    assert g.skill_value("guns", ALL5, 10, False) == min(100, 2 + 2 * 5 + 3 + 10)


def test_hp_formula():
    assert g.hit_points(5, 1) == 200
    assert g.hit_points(5, 1, 30) == 230  # Life Giver


# ---------------------------------------------------------------------------
# Task XP / caps / karma
# ---------------------------------------------------------------------------


def test_task_xp_factors():
    assert g.task_xp(3, 45, 4, 0, False) == 27  # 10 * 1.5 * 1.5 * 1.2
    assert g.task_xp(5, 2, 1, 0, False) == 2  # 2-minute rule: 10 * 0.5 * 0.5 * 0.8
    x = g.task_xp(3, 45, 4, 100, True)  # on-time +25%, karma +100 -> +10%
    assert x == round(10 * 1.5 * 1.5 * 1.2 * 1.25 * 1.1)
    assert g.task_xp(1, 120, 5, -100, False) >= 1  # always at least 1 XP


def test_caps_from_xp():
    assert g.caps_from_xp(27) == 2
    assert g.caps_from_xp(9) == 0


def test_karma_titles_and_clamp():
    assert g.karma_title(100) == "Saint"
    assert g.karma_title(0) == "Neutral"
    assert g.karma_title(-100) == "Fiend"
    assert g.clamp_karma(150) == 100
    assert g.clamp_karma(-150) == -100


# ---------------------------------------------------------------------------
# Perks: the full 88-perk data set and requirement model
# ---------------------------------------------------------------------------


def test_perk_dataset_is_complete_88():
    assert len(g.PERKS) == 88
    assert len(g.PERKS_BY_ID) == 88
    assert len({p.id for p in g.PERKS}) == 88
    levels = sorted({p.min_level for p in g.PERKS})
    assert levels == [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28]


def test_perk_ranks():
    assert g.PERKS_BY_ID["intense_training"].max_ranks == 10
    assert g.PERKS_BY_ID["swift_learner"].max_ranks == 3
    assert g.PERKS_BY_ID["demolition_expert"].max_ranks == 3
    assert g.PERKS_BY_ID["toughness"].max_ranks == 2


def test_available_perks_at_level_2():
    avail = {p.id for p in g.available_perks(2, ALL5, SKILLS15, [])}
    # gender perks + no-requirement perks + Swift Learner (INT 4) are available
    assert {
        "confirmed_bachelor",
        "chez_la_femme",
        "lady_killer",
        "black_widow",
        "intense_training",
        "swift_learner",
    } <= avail
    assert "friend_of_the_night" not in avail  # needs PER 6
    assert "hunter" not in avail  # needs Survival 30


def test_perk_requirements_any_of():
    run_n_gun = g.PERKS_BY_ID["run_n_gun"]
    assert g.perk_requirements_met(run_n_gun, 4, ALL5, {**SKILLS15, "guns": 45}, [])
    assert not g.perk_requirements_met(run_n_gun, 4, ALL5, SKILLS15, [])
    lead_belly = g.PERKS_BY_ID["lead_belly"]  # Survival 40 OR Endurance 5
    assert g.perk_requirements_met(lead_belly, 6, ALL5, SKILLS15, [])


def test_perk_requirements_special_max_and_perk_prereq():
    wh = g.PERKS_BY_ID["weapon_handling"]  # Strength below 10
    assert g.perk_requirements_met(wh, 16, ALL5, SKILLS15, [])
    assert not g.perk_requirements_met(wh, 16, {**ALL5, "strength": 10}, SKILLS15, [])
    gs = g.PERKS_BY_ID["ghastly_scavenger"]  # requires Cannibal
    assert not g.perk_requirements_met(gs, 12, ALL5, SKILLS15, [])
    assert g.perk_requirements_met(gs, 12, ALL5, SKILLS15, ["cannibal"])


def test_perk_requirements_level_and_ranks():
    assert not g.perk_requirements_met(g.PERKS_BY_ID["educated"], 2, ALL5, SKILLS15, [])
    assert not g.perk_requirements_met(
        g.PERKS_BY_ID["swift_learner"], 2, ALL5, SKILLS15, ["swift_learner"] * 3
    )


def test_perk_effect_aggregations():
    assert g.xp_multiplier([]) == 1.0
    assert g.xp_multiplier(["swift_learner"]) == 1.10
    assert abs(g.xp_multiplier(["swift_learner"] * 3) - 1.1**3) < 1e-9
    assert g.caps_multiplier(["fortune_finder"]) == 1.25
    assert g.skill_points_bonus_per_level(["educated", "comprehension"]) == 3
    assert g.hp_bonus(["life_giver"]) == 30
