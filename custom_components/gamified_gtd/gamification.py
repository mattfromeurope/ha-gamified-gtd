"""Pure FNV (Fallout: New Vegas) gamification logic — no Home Assistant imports.

All formulas are taken 1:1 from Fallout: New Vegas (see DESIGN.md).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

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


def hit_points(endurance: int, level: int) -> int:
    """FNV derived stat: HP = 95 + 20*END + 5*level."""
    return 95 + 20 * endurance + 5 * level


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
    """FNV-style karma titles, scaled to the -100..+100 range."""
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


@dataclass(frozen=True)
class Perk:
    """One FNV perk. `effect` maps to integration mechanics.

    effect types:
      - xp_multiplier: multiplies all XP gains (e.g. Swift Learner)
      - skill_points_per_level: extra skill points on every level-up (e.g. Educated)
      - special_plus: +1 to a SPECIAL stat (e.g. Intense Training)
    """

    id: str
    name: str
    description: str
    min_level: int = 2
    requires_special: dict[str, int] = field(default_factory=dict)
    requires_skill: dict[str, int] = field(default_factory=dict)
    effect: dict[str, object] = field(default_factory=dict)
    max_ranks: int = 1


PERKS: list[Perk] = [
    Perk(
        id="swift_learner",
        name="Swift Learner",
        description="+10% XP from all sources.",
        min_level=2,
        effect={"xp_multiplier": 1.10},
    ),
    Perk(
        id="educated",
        name="Educated",
        description="+2 skill points per level-up.",
        min_level=4,
        requires_special={"intelligence": 6},
        effect={"skill_points_per_level": 2},
    ),
    Perk(
        id="intense_training",
        name="Intense Training",
        description="+1 to any SPECIAL attribute. Can be taken up to 10 times.",
        min_level=2,
        effect={"special_plus": 1},
        max_ranks=10,
    ),
    Perk(
        id="comprehension",
        name="Comprehension",
        description="Skill books and magazines grant +10% more skill points.",
        min_level=4,
        requires_skill={"science": 20},
        effect={"skill_points_per_level": 1},
    ),
    Perk(
        id="good_natured",
        name="Good Natured",
        description="+10 to Barter and Speech.",
        min_level=2,
        requires_special={"charisma": 5},
        effect={"skill_plus": {"barter": 10, "speech": 10}},
    ),
    Perk(
        id="caps_collector",
        name="Caps Collector",
        description="+25% Caps from all sources.",
        min_level=6,
        requires_special={"luck": 6},
        effect={"caps_multiplier": 1.25},
    ),
]

PERKS_BY_ID = {perk.id: perk for perk in PERKS}


def perk_requirements_met(
    perk: Perk,
    level: int,
    special: dict[str, int],
    skills: dict[str, int],
    taken_ranks: int,
) -> bool:
    """Check FNV perk requirements (level, SPECIAL, skill) and rank limit."""
    if level < perk.min_level:
        return False
    if taken_ranks >= perk.max_ranks:
        return False
    for stat, minimum in perk.requires_special.items():
        if special.get(stat, 0) < minimum:
            return False
    for skill, minimum in perk.requires_skill.items():
        if skills.get(skill, 0) < minimum:
            return False
    return True


def available_perks(
    level: int,
    special: dict[str, int],
    skills: dict[str, int],
    owned: list[str],
) -> list[Perk]:
    """Perks the profile may choose right now."""
    counts: dict[str, int] = {}
    for perk_id in owned:
        counts[perk_id] = counts.get(perk_id, 0) + 1
    return [
        perk
        for perk in PERKS
        if perk_requirements_met(perk, level, special, skills, counts.get(perk.id, 0))
    ]


def xp_multiplier(owned: list[str]) -> float:
    multiplier = 1.0
    for perk_id in owned:
        effect = PERKS_BY_ID.get(perk_id)
        if effect and "xp_multiplier" in effect.effect:
            multiplier *= float(effect.effect["xp_multiplier"])
    return multiplier


def caps_multiplier(owned: list[str]) -> float:
    multiplier = 1.0
    for perk_id in owned:
        effect = PERKS_BY_ID.get(perk_id)
        if effect and "caps_multiplier" in effect.effect:
            multiplier *= float(effect.effect["caps_multiplier"])
    return multiplier


def skill_points_bonus_per_level(owned: list[str]) -> int:
    bonus = 0
    for perk_id in owned:
        effect = PERKS_BY_ID.get(perk_id)
        if effect and "skill_points_per_level" in effect.effect:
            bonus += int(effect.effect["skill_points_per_level"])
    return bonus
