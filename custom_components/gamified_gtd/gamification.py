"""Pure FNV (Fallout: New Vegas) gamification logic — no Home Assistant imports.

Kept HA-free on purpose so the whole ruleset can be unit-tested standalone
(see the checks run during development: XP curve, skill formula, perks, ...).

All formulas are taken 1:1 from Fallout: New Vegas (see DESIGN.md):
- GECK XP curve: cumulative XP(n) = (n-1) * ((n-2)/2 * iXPBase + iXPBumpBase)
- Skills: 2 + 2*governing SPECIAL + ceil(Luck/2) + allocated (+15 per Tag!)
- Skill points per level-up: 10 + 0.5 * INT (odd INT alternates via carry)
- Perk every 2 levels (from level 2), level cap 30 (base game) / 50 (all DLCs)
- HP derived stat: 95 + 20*END + 5*level

The 88 regular perks with their exact requirements live in perks_data.py.
"""

from __future__ import annotations

import math

try:  # package import (inside Home Assistant)
    from .perks_data import PERKS, PERKS_BY_ID, Perk
except ImportError:  # standalone testing from this directory
    from perks_data import PERKS, PERKS_BY_ID, Perk

# ---------------------------------------------------------------------------
# S.P.E.C.I.A.L. — the 7 primary attributes, each 1-10.
# Set once per profile at setup; afterwards only +1 via perks (Intense Training).
# Tasks never raise SPECIAL directly — they only grant XP.
# ---------------------------------------------------------------------------
SPECIAL_STATS = [
    "strength",
    "perception",
    "endurance",
    "charisma",
    "intelligence",
    "agility",
    "luck",
]

# The 13 FNV skills and the SPECIAL attribute each one is governed by.
# (STR->Melee, PER->Energy Weapons/Explosives/Lockpick, END->Survival/Unarmed,
#  CHA->Barter/Speech, INT->Medicine/Repair/Science, AGI->Guns/Sneak;
#  LCK adds ceil(Luck/2) to every skill.)
SKILL_GOVERNING_SPECIAL = {
    "barter": "charisma",
    "energy_weapons": "perception",
    "explosives": "perception",
    "guns": "agility",
    "lockpick": "perception",
    "medicine": "intelligence",
    "melee_weapons": "strength",
    "repair": "intelligence",
    "science": "intelligence",
    "sneak": "agility",
    "speech": "charisma",
    "survival": "endurance",
    "unarmed": "endurance",
}

SKILLS = list(SKILL_GOVERNING_SPECIAL)

SKILL_MAX = 100  # hard skill cap in FNV
TAG_BONUS = 15  # Tag! bonus per tagged skill
NUM_TAG_SKILLS = 3  # 3 Tag! skills at character creation

DEFAULT_LEVEL_CAP = 50  # with all four DLCs
BASE_GAME_LEVEL_CAP = 30  # without DLCs

# Karma range is scaled to -100..+100 (FNV uses a wider range); the value acts as a
# global XP modifier of +/-10%.
KARMA_MIN = -100
KARMA_MAX = 100
KARMA_XP_MODIFIER = 0.10  # karma +100 => +10% XP, karma -100 => -10% XP

CAPS_PER_XP = 10  # 1 cap per 10 XP (only for tasks that are not overdue)

# ---------------------------------------------------------------------------
# Task XP factors (mechanism fixed in DESIGN.md; exact numbers tunable later)
# ---------------------------------------------------------------------------
XP_BASE = 10
# Priority 1 = highest … 5 = lowest.
PRIORITY_FACTORS = {1: 3.0, 2: 2.0, 3: 1.5, 4: 1.0, 5: 0.5}
ON_TIME_XP_BONUS = 0.25  # +25% when completed before the due date
QUEST_STEP_BONUS_XP = 25  # quest bonus per step: 25 XP * number of steps
QUEST_ON_TIME_BONUS = 0.25  # +25% quest XP when finished before the quest deadline
REVIEW_BASE_XP = 100  # weekly review bonus base (times streak)

# Karma rules (OVERDUE_KARMA_DAYS, REVIEW_OVERDUE_KARMA_PER_WEEK) live in const.py.

# GECK game settings for the XP curve (vanilla values).
XP_BASE_SETTING = 150  # iXPBase
XP_BUMP_BASE_SETTING = 200  # iXPBumpBase


def cumulative_xp_for_level(level: int, cap: int = DEFAULT_LEVEL_CAP) -> int:
    """GECK/FNV engine formula: total XP needed to reach `level` (cumulative).

    XP(n) = (n - 1) * ((n - 2) / 2 * iXPBase + iXPBumpBase), iXPBase=150, iXPBumpBase=200.
    Vanilla totals: level 2 = 200, level 3 = 550, level 4 = 1050, level 50 = 186,200.
    """
    if level <= 1:
        return 0  # level 1 needs no XP
    level = min(level, cap)  # never compute beyond the cap
    return round((level - 1) * ((level - 2) / 2 * XP_BASE_SETTING + XP_BUMP_BASE_SETTING))


def xp_for_level(level: int, cap: int = DEFAULT_LEVEL_CAP) -> int:
    """XP needed to go from level-1 to level (incremental = cumulative difference)."""
    return cumulative_xp_for_level(level, cap) - cumulative_xp_for_level(level - 1, cap)


def level_from_xp(xp: int, cap: int = DEFAULT_LEVEL_CAP) -> int:
    """Current level for a total XP amount (walks the cumulative thresholds)."""
    level = 1
    while level < cap and xp >= cumulative_xp_for_level(level + 1, cap):
        level += 1
    return level


def skill_points_for_level_up(intelligence: int, carry_half: bool) -> tuple[int, bool]:
    """FNV: 10 + 0.5*INT skill points per level-up.

    Odd INT yields a half point; FNV stores it and grants it on alternating
    (even) level-ups — modeled via the `carry_half` flag that toggles each call.
    Returns (points, new_carry_flag).
    """
    points = 10 + intelligence // 2
    if intelligence % 2 == 1 and carry_half:
        points += 1  # the carried half point lands on this (even) level-up
    return points, (intelligence % 2 == 1 and not carry_half)


def skill_value(
    skill: str,
    special: dict[str, int],
    allocated: int,
    tagged: bool,
) -> int:
    """FNV skill formula: 2 + 2*governing SPECIAL + ceil(Luck/2) + allocated (+15 if Tag!).

    Example from the wiki: END 5, LCK 5 -> Unarmed = 2 + 2*5 + ceil(5/2) = 15.
    Capped at SKILL_MAX (100).
    """
    governing = SKILL_GOVERNING_SPECIAL[skill]
    base = 2 + 2 * special.get(governing, 0) + math.ceil(special.get("luck", 0) / 2)
    if tagged:
        base += TAG_BONUS
    return min(SKILL_MAX, base + allocated)


def hit_points(endurance: int, level: int, perk_bonus: int = 0) -> int:
    """FNV derived stat: HP = 95 + 20*END + 5*level, plus flat perk bonuses (Life Giver)."""
    return 95 + 20 * endurance + 5 * level + perk_bonus


def time_factor(minutes: float) -> float:
    """XP multiplier from the estimated time: 2-minute rule up to long tasks."""
    if minutes <= 2:
        return 0.5  # 2-minute rule: quick tasks are worth less
    if minutes <= 15:
        return 1.0
    if minutes <= 60:
        return 1.5
    return 2.0  # > 60 min


def energy_factor(energy: int) -> float:
    """XP multiplier from the required energy level (1 = low … 5 = high)."""
    return {1: 0.8, 2: 0.9, 3: 1.0, 4: 1.2, 5: 1.5}.get(energy, 1.0)


def task_xp(
    priority: int,
    time_estimate: float,
    energy: int,
    karma: int,
    on_time: bool,
    xp_base: int = XP_BASE,
    xp_multiplier: float = 1.0,
) -> int:
    """XP for one completed action — ALWAYS granted, even when overdue.

    XP = base * priority factor * time factor * energy factor,
    +25% when completed on time, scaled by the karma modifier (+/-10%),
    then by perk multipliers (e.g. Swift Learner). Minimum 1 XP.
    """
    xp = (
        xp_base
        * PRIORITY_FACTORS.get(priority, 1.0)
        * time_factor(time_estimate)
        * energy_factor(energy)
    )
    if on_time:
        xp *= 1 + ON_TIME_XP_BONUS
    # Karma modifier: karma -100..+100 maps to -10%..+10% XP.
    xp *= 1 + (karma / 100) * KARMA_XP_MODIFIER
    xp *= xp_multiplier
    return max(1, round(xp))


def caps_from_xp(xp: int) -> int:
    """Caps granted for an XP amount: 1 cap per 10 XP (floor)."""
    return xp // CAPS_PER_XP


def karma_title(karma: int) -> str:
    """Karma titles inspired by FNV (level/karma-dependent in the game; here scaled
    to the -100..+100 range): Saint … Fiend."""
    if karma >= 80:
        return "Saint"
    if karma >= 50:
        return "Revered"
    if karma >= 20:
        return "Good"
    if karma > -20:
        return "Neutral"
    if karma > -50:
        return "Bad"
    if karma > -80:
        return "Vilified"
    return "Fiend"


def clamp_karma(karma: int) -> int:
    """Clamp karma to the -100..+100 range."""
    return max(KARMA_MIN, min(KARMA_MAX, karma))


def _any_condition_met(
    condition: dict, special: dict[str, int], skills: dict[str, int]
) -> bool:
    """Evaluate one any-of condition: either a skill threshold or a SPECIAL threshold."""
    if "skill" in condition:
        return skills.get(condition["skill"], 0) >= condition["value"]
    if "special" in condition:
        return special.get(condition["special"], 0) >= condition["value"]
    return False


def perk_requirements_met(
    perk: Perk,
    level: int,
    special: dict[str, int],
    skills: dict[str, int],
    owned: list[str],
) -> bool:
    """Check FNV perk requirements 1:1.

    - minimum level
    - rank limit (max_ranks, e.g. 10x Intense Training)
    - SPECIAL minimums (requires_special) and maximums (requires_special_max,
      e.g. Weapon Handling needs Strength below 10)
    - skill minimums (requires_skill)
    - perk prerequisite (requires_perk, e.g. Ghastly Scavenger needs Cannibal)
    - any-of alternatives (requires_any, e.g. Run 'n Gun: Guns 45 OR Energy Weapons 45)
    """
    if level < perk.min_level:
        return False
    if owned.count(perk.id) >= perk.max_ranks:
        return False
    for stat, minimum in perk.requires_special.items():
        if special.get(stat, 0) < minimum:
            return False
    for stat, maximum in perk.requires_special_max.items():
        if special.get(stat, 0) >= maximum:
            return False
    for skill, minimum in perk.requires_skill.items():
        if skills.get(skill, 0) < minimum:
            return False
    if perk.requires_perk and perk.requires_perk not in owned:
        return False
    if perk.requires_any and not any(
        _any_condition_met(cond, special, skills) for cond in perk.requires_any
    ):
        return False
    return True


def available_perks(
    level: int,
    special: dict[str, int],
    skills: dict[str, int],
    owned: list[str],
) -> list[Perk]:
    """All perks the profile may choose right now (requirements met)."""
    return [
        perk
        for perk in PERKS
        if perk_requirements_met(perk, level, special, skills, owned)
    ]


# ---------------------------------------------------------------------------
# Perk effect aggregations — owned is a list of perk ids, so multi-rank perks
# (e.g. 3x Swift Learner) appear multiple times and stack multiplicatively.
# ---------------------------------------------------------------------------


def xp_multiplier(owned: list[str]) -> float:
    """Combined XP multiplier from all owned perks (multiplicative per rank)."""
    multiplier = 1.0
    for perk_id in owned:
        perk = PERKS_BY_ID.get(perk_id)
        if perk and "xp_multiplier" in perk.effect:
            multiplier *= float(perk.effect["xp_multiplier"])
    return multiplier


def caps_multiplier(owned: list[str]) -> float:
    """Combined caps multiplier from all owned perks (e.g. Fortune Finder)."""
    multiplier = 1.0
    for perk_id in owned:
        perk = PERKS_BY_ID.get(perk_id)
        if perk and "caps_multiplier" in perk.effect:
            multiplier *= float(perk.effect["caps_multiplier"])
    return multiplier


def skill_points_bonus_per_level(owned: list[str]) -> int:
    """Extra skill points per level-up from perks (Educated +2, Comprehension +1)."""
    bonus = 0
    for perk_id in owned:
        perk = PERKS_BY_ID.get(perk_id)
        if perk and "skill_points_per_level" in perk.effect:
            bonus += int(perk.effect["skill_points_per_level"])
    return bonus


def hp_bonus(owned: list[str]) -> int:
    """Flat HP bonus from perks (Life Giver +30)."""
    bonus = 0
    for perk_id in owned:
        perk = PERKS_BY_ID.get(perk_id)
        if perk and "hp_bonus" in perk.effect:
            bonus += int(perk.effect["hp_bonus"])
    return bonus
