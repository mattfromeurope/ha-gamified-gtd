"""Pure FNV (Fallout: New Vegas) gamification logic — no Home Assistant imports.

All formulas are taken 1:1 from Fallout: New Vegas (see DESIGN.md).
The 88 regular perks live in perks_data.py.
"""

from __future__ import annotations

import math

try:  # package import (inside Home Assistant)
    from .perks_data import PERKS, PERKS_BY_ID, Perk
except ImportError:  # standalone testing from this directory
    from perks_data import PERKS, PERKS_BY_ID, Perk

SPECIAL_STATS = [
    "strength",
    "perception",
    "endurance",
    "charisma",
    "intelligence",
    "agility",
    "luck",
]

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

SKILL_MAX = 100
TAG_BONUS = 15
NUM_TAG_SKILLS = 3

DEFAULT_LEVEL_CAP = 50
BASE_GAME_LEVEL_CAP = 30

KARMA_MIN = -100
KARMA_MAX = 100
KARMA_XP_MODIFIER = 0.10  # karma of +100 => +10% XP, -100 => -10% XP

CAPS_PER_XP = 10

XP_BASE = 10
PRIORITY_FACTORS = {1: 3.0, 2: 2.0, 3: 1.5, 4: 1.0, 5: 0.5}
ON_TIME_XP_BONUS = 0.25
QUEST_STEP_BONUS_XP = 25
QUEST_ON_TIME_BONUS = 0.25
REVIEW_BASE_XP = 100

OVERDUE_KARMA_DAYS = 7
REVIEW_OVERDUE_KARMA_PER_WEEK = -1

XP_BASE_SETTING = 150  # GECK iXPBase
XP_BUMP_BASE_SETTING = 200  # GECK iXPBumpBase


def cumulative_xp_for_level(level: int, cap: int = DEFAULT_LEVEL_CAP) -> int:
    """GECK/FNV engine formula: total XP needed to reach `level`.

    XP(n) = (n - 1) * ((n - 2) / 2 * iXPBase + iXPBumpBase), iXPBase=150, iXPBumpBase=200.
    Vanilla totals: level 2 = 200, level 3 = 550, level 4 = 1050, level 50 = 186,200.
    """
    if level <= 1:
        return 0
    level = min(level, cap)
    return round((level - 1) * ((level - 2) / 2 * XP_BASE_SETTING + XP_BUMP_BASE_SETTING))


def xp_for_level(level: int, cap: int = DEFAULT_LEVEL_CAP) -> int:
    """XP needed to go from level-1 to level (incremental)."""
    return cumulative_xp_for_level(level, cap) - cumulative_xp_for_level(level - 1, cap)


def level_from_xp(xp: int, cap: int = DEFAULT_LEVEL_CAP) -> int:
    """Current level for a total XP amount."""
    level = 1
    while level < cap and xp >= cumulative_xp_for_level(level + 1, cap):
        level += 1
    return level


def skill_points_for_level_up(intelligence: int, carry_half: bool) -> tuple[int, bool]:
    """FNV: 10 + 0.5*INT skill points per level; odd INT alternates (half point carried)."""
    points = 10 + intelligence // 2
    if intelligence % 2 == 1 and carry_half:
        points += 1
    return points, (intelligence % 2 == 1 and not carry_half)


def skill_value(
    skill: str,
    special: dict[str, int],
    allocated: int,
    tagged: bool,
) -> int:
    """FNV skill formula: 2 + 2*governing SPECIAL + ceil(Luck/2) + allocated (+15 if Tag!)."""
    governing = SKILL_GOVERNING_SPECIAL[skill]
    base = 2 + 2 * special.get(governing, 0) + math.ceil(special.get("luck", 0) / 2)
    if tagged:
        base += TAG_BONUS
    return min(SKILL_MAX, base + allocated)


def hit_points(endurance: int, level: int, perk_bonus: int = 0) -> int:
    """FNV derived stat: HP = 95 + 20*END + 5*level (+ perk bonuses like Life Giver)."""
    return 95 + 20 * endurance + 5 * level + perk_bonus


def time_factor(minutes: float) -> float:
    if minutes <= 2:
        return 0.5  # 2-minute rule
    if minutes <= 15:
        return 1.0
    if minutes <= 60:
        return 1.5
    return 2.0


def energy_factor(energy: int) -> float:
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
    """XP for a completed action. Always granted, even when overdue."""
    xp = (
        xp_base
        * PRIORITY_FACTORS.get(priority, 1.0)
        * time_factor(time_estimate)
        * energy_factor(energy)
    )
    if on_time:
        xp *= 1 + ON_TIME_XP_BONUS
    xp *= 1 + (karma / 100) * KARMA_XP_MODIFIER
    xp *= xp_multiplier
    return max(1, round(xp))


def caps_from_xp(xp: int) -> int:
    return xp // CAPS_PER_XP


def karma_title(karma: int) -> str:
    """Karma titles inspired by FNV (level/karma-dependent there; scaled to -100..+100 here)."""
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
    return max(KARMA_MIN, min(KARMA_MAX, karma))


def _any_condition_met(
    condition: dict, special: dict[str, int], skills: dict[str, int]
) -> bool:
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
    """Check FNV perk requirements: level, rank limit, SPECIAL (min/max), skill, perk prereq, any-of."""
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
    """Perks the profile may choose right now."""
    return [
        perk
        for perk in PERKS
        if perk_requirements_met(perk, level, special, skills, owned)
    ]


def xp_multiplier(owned: list[str]) -> float:
    multiplier = 1.0
    for perk_id in owned:
        perk = PERKS_BY_ID.get(perk_id)
        if perk and "xp_multiplier" in perk.effect:
            multiplier *= float(perk.effect["xp_multiplier"])
    return multiplier


def caps_multiplier(owned: list[str]) -> float:
    multiplier = 1.0
    for perk_id in owned:
        perk = PERKS_BY_ID.get(perk_id)
        if perk and "caps_multiplier" in perk.effect:
            multiplier *= float(perk.effect["caps_multiplier"])
    return multiplier


def skill_points_bonus_per_level(owned: list[str]) -> int:
    bonus = 0
    for perk_id in owned:
        perk = PERKS_BY_ID.get(perk_id)
        if perk and "skill_points_per_level" in perk.effect:
            bonus += int(perk.effect["skill_points_per_level"])
    return bonus


def hp_bonus(owned: list[str]) -> int:
    bonus = 0
    for perk_id in owned:
        perk = PERKS_BY_ID.get(perk_id)
        if perk and "hp_bonus" in perk.effect:
            bonus += int(perk.effect["hp_bonus"])
    return bonus
