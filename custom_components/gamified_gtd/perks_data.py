"""All 88 regular Fallout: New Vegas perks with their requirements — pure data, no HA imports.

Requirements are 1:1 from the game (level, SPECIAL, skill, perk prerequisites).
`requires_any` holds alternative conditions, each a dict like {"skill": "guns", "value": 45}
or {"special": "agility", "value": 5}. `requires_special_max` means "SPECIAL below value"
(e.g. Weapon Handling: Strength below 10).

`effect` maps the perk to integration mechanics where it translates:
  - xp_multiplier / caps_multiplier: multiplicative per rank (list entries stack)
  - skill_points_per_level: extra skill points on every level-up
  - special_plus: +1 to a chosen SPECIAL stat (Intense Training)
  - hp_bonus: flat HP bonus (Life Giver)
  - instant_level: immediately gain one level (Here and Now)
  - tag_skill: tag one additional skill (+15) (Tag!)
  - flavor: no direct mechanical translation (combat/dialogue perks) — still selectable 1:1
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class Perk:
    id: str
    name: str
    description: str
    min_level: int = 2
    max_ranks: int = 1
    requires_special: dict[str, int] = field(default_factory=dict)
    requires_skill: dict[str, int] = field(default_factory=dict)
    requires_any: tuple[dict, ...] = ()
    requires_special_max: dict[str, int] = field(default_factory=dict)
    requires_perk: str | None = None
    effect: dict = field(default_factory=dict)


def _flavor(description: str) -> dict:
    return {"flavor": description}


PERKS: list[Perk] = [
    # ---------------- Level 2 ----------------
    Perk("confirmed_bachelor", "Confirmed Bachelor",
         "+10% damage against male opponents; unique dialogue options with the same sex. (Male characters only in FNV.)",
         effect=_flavor("+10% damage vs. same sex")),
    Perk("chez_la_femme", "Cherchez la Femme",
         "+10% damage against female opponents; unique dialogue options with the opposite sex. (Female characters only in FNV.)",
         effect=_flavor("+10% damage vs. opposite sex")),
    Perk("lady_killer", "Lady Killer",
         "+10% damage against female opponents. (Male characters only in FNV.)",
         effect=_flavor("+10% damage vs. women")),
    Perk("black_widow", "Black Widow",
         "+10% damage against male opponents. (Female characters only in FNV.)",
         effect=_flavor("+10% damage vs. men")),
    Perk("friend_of_the_night", "Friend of the Night",
         "Eyes adapt quickly to low-light conditions.",
         requires_skill={"sneak": 30}, requires_special={"perception": 6},
         effect=_flavor("Better night vision")),
    Perk("heave_ho", "Heave Ho!",
         "Thrown weapons fly farther and faster.",
         requires_skill={"explosives": 30}, requires_special={"strength": 5},
         effect=_flavor("Thrown weapons fly farther")),
    Perk("hunter", "Hunter",
         "75% more critical damage against animals.",
         requires_skill={"survival": 30}, effect=_flavor("+75% crit dmg vs. animals")),
    Perk("intense_training", "Intense Training",
         "+1 to any SPECIAL attribute of your choice.",
         max_ranks=10, effect={"special_plus": 1}),
    Perk("rapid_reload", "Rapid Reload",
         "Weapon reloads 25% faster.",
         requires_skill={"guns": 30}, requires_special={"agility": 5},
         effect=_flavor("25% faster reloads")),
    Perk("retention", "Retention",
         "Skill magazine bonuses last three times as long.",
         requires_special={"intelligence": 5}, effect=_flavor("Magazines last 3x longer")),
    Perk("swift_learner", "Swift Learner",
         "+10% XP from all sources per rank.",
         max_ranks=3, requires_special={"intelligence": 4}, effect={"xp_multiplier": 1.10}),
    # ---------------- Level 4 ----------------
    Perk("cannibal", "Cannibal",
         "Eat corpses in sneak mode to regain HP; loses Karma each time.",
         effect=_flavor("Eat corpses, -Karma")),
    Perk("comprehension", "Comprehension",
         "Double magazine bonus and +1 skill point per skill book.",
         requires_special={"intelligence": 4}, effect={"skill_points_per_level": 1}),
    Perk("educated", "Educated",
         "+2 skill points on every level-up.",
         requires_special={"intelligence": 4}, effect={"skill_points_per_level": 2}),
    Perk("entomologist", "Entomologist",
         "+50% damage against mutated insects.",
         requires_skill={"survival": 45}, requires_special={"intelligence": 4},
         effect=_flavor("+50% dmg vs. insects")),
    Perk("rad_child", "Rad Child",
         "Regenerate more health the higher your radiation stage.",
         requires_skill={"survival": 70}, effect=_flavor("Radiation heals you")),
    Perk("run_n_gun", "Run 'n Gun",
         "Reduced accuracy penalty when running with one-handed guns/energy weapons.",
         requires_any=({"skill": "guns", "value": 45}, {"skill": "energy_weapons", "value": 45}),
         effect=_flavor("Move and shoot accurately")),
    Perk("travel_light", "Travel Light",
         "Run 10% faster in light armor or no armor.",
         requires_skill={"survival": 45}, effect=_flavor("+10% run speed, light armor")),
    # ---------------- Level 6 ----------------
    Perk("bloody_mess", "Bloody Mess",
         "Enemies often explode; +5% damage with all weapons.",
         effect=_flavor("+5% damage, gore")),
    Perk("demolition_expert", "Demolition Expert",
         "+20% damage with explosive weapons per rank.",
         max_ranks=3, requires_skill={"explosives": 50}, effect=_flavor("+20% explosive dmg/rank")),
    Perk("ferocious_loyalty", "Ferocious Loyalty",
         "Companions gain much greater damage resistance below 50% of your HP.",
         requires_special={"charisma": 6}, effect=_flavor("Companions tankier")),
    Perk("fortune_finder", "Fortune Finder",
         "Find considerably more bottle caps in containers.",
         requires_special={"luck": 5}, effect={"caps_multiplier": 1.25}),
    Perk("gunslinger", "Gunslinger",
         "Significantly increased V.A.T.S. accuracy with pistols.",
         effect=_flavor("Pistol accuracy in V.A.T.S.")),
    Perk("hand_loader", "Hand Loader",
         "Recover more ammo when using Guns; all hand-load recipes unlocked.",
         requires_skill={"repair": 70}, effect=_flavor("Ammo recovery, recipes")),
    Perk("lead_belly", "Lead Belly",
         "-50% radiation from food and drinks.",
         requires_any=({"skill": "survival", "value": 40}, {"special": "endurance", "value": 5}),
         effect=_flavor("-50% rad from consumables")),
    Perk("shotgun_surgeon", "Shotgun Surgeon",
         "Shotguns ignore an additional 10 points of target Damage Threshold.",
         requires_skill={"guns": 45}, effect=_flavor("Shotguns ignore 10 DT")),
    Perk("the_professional", "The Professional",
         "Sneak attack criticals with pistols/SMGs do +20% damage.",
         requires_skill={"sneak": 70}, effect=_flavor("+20% sneak crit dmg, pistols")),
    Perk("toughness", "Toughness",
         "+3 Damage Threshold per rank.",
         max_ranks=2, requires_special={"endurance": 5}, effect=_flavor("+3 DT/rank")),
    Perk("vigilant_recycler", "Vigilant Recycler",
         "Recover more drained ammo with Energy Weapons; better recycling recipes.",
         requires_skill={"science": 70}, effect=_flavor("Ammo recycling")),
    # ---------------- Level 8 ----------------
    Perk("commando", "Commando",
         "Significantly increased V.A.T.S. accuracy with rifles.",
         effect=_flavor("Rifle accuracy in V.A.T.S.")),
    Perk("cowboy", "Cowboy",
         "+25% damage with revolvers, lever-action firearms, dynamite, knives, hatchets.",
         requires_skill={"guns": 45, "melee_weapons": 45}, effect=_flavor("+25% cowboy weapons dmg")),
    Perk("living_anatomy", "Living Anatomy",
         "See HP/DT of targets; +5% damage vs. humans and non-feral ghouls.",
         requires_skill={"medicine": 70}, effect=_flavor("See HP/DT, +5% dmg vs. humans")),
    Perk("pack_rat", "Pack Rat",
         "Items weighing 2 or less weigh half as much.",
         requires_skill={"barter": 70}, requires_special={"intelligence": 5},
         effect=_flavor("Light items weigh half")),
    Perk("quick_draw", "Quick Draw",
         "Equip and holster weapons 50% faster.",
         requires_special={"agility": 5}, effect=_flavor("50% faster draw/holster")),
    Perk("rad_resistance", "Rad Resistance",
         "+25% radiation resistance.",
         requires_skill={"survival": 40}, requires_special={"endurance": 5},
         effect=_flavor("+25% rad resistance")),
    Perk("scrounger", "Scrounger",
         "Find considerably more ammunition in containers.",
         requires_special={"luck": 5}, effect=_flavor("More ammo found")),
    Perk("stonewall", "Stonewall",
         "+5 DT against melee/unarmed; cannot be knocked down.",
         requires_special={"strength": 6, "endurance": 6}, effect=_flavor("+5 DT vs. melee, no knockdown")),
    Perk("strong_back", "Strong Back",
         "Carry 50 more pounds.",
         requires_special={"strength": 5, "endurance": 5}, effect=_flavor("+50 carry weight")),
    Perk("super_slam", "Super Slam",
         "Melee/unarmed attacks can knock down targets.",
         requires_skill={"melee_weapons": 45}, requires_special={"strength": 6},
         effect=_flavor("Melee knockdown chance")),
    Perk("terrifying_presence", "Terrifying Presence",
         "Sometimes terrify groups of opponents in conversations.",
         requires_skill={"speech": 70}, effect=_flavor("Terrify enemies in dialogue")),
    # ---------------- Level 10 ----------------
    Perk("animal_friend", "Animal Friend",
         "Rank 1: animals won't attack. Rank 2: they aid you in combat.",
         max_ranks=2, requires_skill={"survival": 45}, requires_special={"charisma": 6},
         effect=_flavor("Animals friendly")),
    Perk("finesse", "Finesse",
         "Critical hit chance equivalent to +5 Luck.",
         effect=_flavor("+5% crit chance")),
    Perk("here_and_now", "Here and Now",
         "Immediately gain one additional level.",
         effect={"instant_level": True}),
    Perk("math_wrath", "Math Wrath",
         "All V.A.T.S. action point costs reduced by 10%.",
         requires_skill={"science": 70}, effect=_flavor("-10% V.A.T.S. AP costs")),
    Perk("miss_fortune", "Miss Fortune",
         "In V.A.T.S., Miss Fortune occasionally knocks over enemies.",
         requires_special={"luck": 6}, effect=_flavor("Luck-based V.A.T.S. help")),
    Perk("mister_sandman", "Mister Sandman",
         "Silently kill sleeping humans/ghouls in sneak mode; bonus XP.",
         requires_skill={"sneak": 60}, effect=_flavor("Sleep-kills, bonus XP")),
    Perk("mysterious_stranger", "Mysterious Stranger",
         "The Mysterious Stranger occasionally appears in V.A.T.S. to kill an enemy.",
         requires_special={"luck": 6}, effect=_flavor("Stranger kills in V.A.T.S.")),
    Perk("nerd_rage", "Nerd Rage!",
         "Strength raised to 10 and +15 DT when HP drops to 20% or below.",
         requires_skill={"science": 50}, requires_special={"intelligence": 5},
         effect=_flavor("STR 10, +15 DT at low HP")),
    Perk("night_person", "Night Person",
         "+2 Intelligence and Perception at night (max 10).",
         effect=_flavor("+2 INT/PER at night")),
    Perk("plasma_spaz", "Plasma Spaz",
         "-10% AP cost for all plasma weapons.",
         requires_skill={"energy_weapons": 70}, effect=_flavor("-10% AP, plasma weapons")),
    # ---------------- Level 12 ----------------
    Perk("fast_metabolism", "Fast Metabolism",
         "+20% health bonus when using Stimpaks.",
         effect=_flavor("+20% Stimpak healing")),
    Perk("ghastly_scavenger", "Ghastly Scavenger",
         "Eat Super Mutant/Feral Ghoul corpses in sneak mode; loses Karma.",
         requires_perk="cannibal", effect=_flavor("Eat mutants/ghouls, -Karma")),
    Perk("hit_the_deck", "Hit the Deck",
         "+50% DT against all explosions.",
         requires_skill={"explosives": 70}, effect=_flavor("+50% DT vs. explosions")),
    Perk("life_giver", "Life Giver",
         "+30 hit points.",
         requires_special={"endurance": 6}, effect={"hp_bonus": 30}),
    Perk("long_haul", "Long Haul",
         "Over-encumbered no longer prevents fast travel.",
         requires_skill={"barter": 70}, requires_special={"endurance": 6},
         effect=_flavor("Fast travel while over-encumbered")),
    Perk("piercing_strike", "Piercing Strike",
         "Unarmed/melee attacks negate 15 points of target DT.",
         requires_skill={"unarmed": 70}, effect=_flavor("Melee ignores 15 DT")),
    Perk("pyromaniac", "Pyromaniac",
         "+50% damage with fire-based weapons.",
         requires_skill={"explosives": 60}, effect=_flavor("+50% fire weapon dmg")),
    Perk("robotics_expert", "Robotics Expert",
         "+25% damage to robots; sneaking up on a robot shuts it down permanently.",
         requires_skill={"science": 50}, effect=_flavor("+25% dmg vs. robots, shutdown")),
    Perk("silent_running", "Silent Running",
         "Running no longer factors into a successful sneak attempt.",
         requires_skill={"sneak": 50}, requires_special={"agility": 6},
         effect=_flavor("Silent while running")),
    Perk("sniper", "Sniper",
         "Significantly increased chance to hit the head in V.A.T.S.",
         requires_special={"perception": 6, "agility": 6}, effect=_flavor("Headshot chance in V.A.T.S.")),
    Perk("splash_damage", "Splash Damage",
         "+25% area of effect for all explosives.",
         requires_skill={"explosives": 70}, effect=_flavor("+25% explosive AoE")),
    Perk("unstoppable_force", "Unstoppable Force",
         "Large additional damage through enemy blocks with melee/unarmed.",
         requires_skill={"melee_weapons": 90}, requires_special={"strength": 7},
         effect=_flavor("Melee damage through blocks")),
    # ---------------- Level 14 ----------------
    Perk("adamantium_skeleton", "Adamantium Skeleton",
         "Limbs receive only 50% damage.",
         effect=_flavor("-50% limb damage")),
    Perk("center_of_mass", "Center of Mass",
         "+15% damage in V.A.T.S. when targeting the torso.",
         requires_skill={"guns": 70}, effect=_flavor("+15% torso dmg in V.A.T.S.")),
    Perk("chemist", "Chemist",
         "Chems last twice as long.",
         requires_skill={"medicine": 60}, effect=_flavor("Chems last 2x")),
    Perk("jury_rigging", "Jury Rigging",
         "Repair any item with a roughly similar item.",
         requires_skill={"repair": 90}, effect=_flavor("Repair with any similar item")),
    Perk("light_step", "Light Step",
         "Never set off mines or floor-based traps.",
         requires_special={"perception": 6, "agility": 6}, effect=_flavor("No mines/traps")),
    Perk("purifier", "Purifier",
         "+50% unarmed/melee damage vs. mutated abominations.",
         effect=_flavor("+50% melee dmg vs. abominations")),
    # ---------------- Level 16 ----------------
    Perk("action_boy", "Action Boy",
         "+15 action points in V.A.T.S. per rank. (Action Girl variant for female characters.)",
         max_ranks=2, requires_special={"agility": 6}, effect=_flavor("+15 AP/rank")),
    Perk("better_criticals", "Better Criticals",
         "+50% damage on all critical hits.",
         requires_special={"perception": 6, "luck": 6}, effect=_flavor("+50% crit damage")),
    Perk("chem_resistant", "Chem Resistant",
         "50% less chance to become addicted to chems.",
         requires_skill={"medicine": 60}, effect=_flavor("-50% addiction chance")),
    Perk("meltdown", "Meltdown",
         "Enemies killed by energy weapons explode for the damage dealt.",
         requires_skill={"energy_weapons": 90}, effect=_flavor("Energy kills explode")),
    Perk("tag", "Tag!",
         "Tag one additional skill: +15 points.",
         effect={"tag_skill": True}),
    Perk("weapon_handling", "Weapon Handling",
         "Weapon strength requirements are 2 points lower.",
         requires_special_max={"strength": 10}, effect=_flavor("-2 weapon STR requirement")),
    # ---------------- Level 18 ----------------
    Perk("computer_whiz", "Computer Whiz",
         "Get a second attempt after being locked out of a computer.",
         requires_skill={"science": 70}, requires_special={"intelligence": 7},
         effect=_flavor("Retry locked terminals")),
    Perk("concentrated_fire", "Concentrated Fire",
         "V.A.T.S. accuracy on a body part increases with each subsequent hit.",
         requires_skill={"energy_weapons": 60, "guns": 60},
         effect=_flavor("Stacking V.A.T.S. accuracy")),
    Perk("infiltrator", "Infiltrator",
         "Get a second attempt after breaking a lock.",
         requires_skill={"lockpick": 70}, requires_special={"perception": 7},
         effect=_flavor("Retry broken locks")),
    Perk("paralyzing_palm", "Paralyzing Palm",
         "Chance to paralyze an opponent with an unarmed V.A.T.S. strike.",
         requires_skill={"unarmed": 70}, effect=_flavor("Unarmed paralyze strike")),
    # ---------------- Level 20 ----------------
    Perk("explorer", "Explorer",
         "All locations revealed on the map.",
         effect=_flavor("Reveal all locations")),
    Perk("grim_reapers_sprint", "Grim Reaper's Sprint",
         "Killing in V.A.T.S. restores 20 AP on exit.",
         effect=_flavor("+20 AP after V.A.T.S. kill")),
    Perk("ninja", "Ninja",
         "+15% crit chance with melee/unarmed; sneak crits +25% damage.",
         requires_skill={"melee_weapons": 80, "sneak": 80},
         effect=_flavor("+15% melee crit, +25% sneak crit")),
    Perk("solar_powered", "Solar Powered",
         "+2 Strength and slow health regeneration in direct sunlight.",
         requires_special={"endurance": 7}, effect=_flavor("+2 STR, regen in sunlight")),
    # ---------------- Level 22 ----------------
    Perk("laser_commander", "Laser Commander",
         "+15% damage and +10% crit chance with all laser weapons.",
         requires_skill={"energy_weapons": 90}, effect=_flavor("+15% dmg, +10% crit, lasers")),
    Perk("nuka_chemist", "Nuka Chemist",
         "Unlock special Nuka-Cola recipes at workbenches.",
         requires_skill={"science": 90}, effect=_flavor("Special Nuka-Cola recipes")),
    Perk("spray_n_pray", "Spray 'n Pray",
         "Much less damage to companions from your attacks.",
         effect=_flavor("-75% companion friendly fire")),
    # ---------------- Level 24 ----------------
    Perk("slayer", "Slayer",
         "+30% attack speed with melee weapons and unarmed.",
         requires_skill={"unarmed": 90}, requires_special={"agility": 7},
         effect=_flavor("+30% melee attack speed")),
    # ---------------- Level 26 ----------------
    Perk("nerves_of_steel", "Nerves of Steel",
         "+20% action point regeneration rate.",
         requires_special={"agility": 7}, effect=_flavor("+20% AP regen")),
    # ---------------- Level 28 ----------------
    Perk("rad_absorption", "Rad Absorption",
         "Radiation level slowly decreases on its own.",
         requires_special={"endurance": 7}, effect=_flavor("Radiation fades over time")),
]



# Minimum level requirement per perk (FNV: perks unlock at even levels 2-28)
_LEVEL_BY_ID = {
    # level 2
    "confirmed_bachelor": 2, "chez_la_femme": 2, "lady_killer": 2, "black_widow": 2,
    "friend_of_the_night": 2, "heave_ho": 2, "hunter": 2, "intense_training": 2,
    "rapid_reload": 2, "retention": 2, "swift_learner": 2,
    # level 4
    "cannibal": 4, "comprehension": 4, "educated": 4, "entomologist": 4,
    "rad_child": 4, "run_n_gun": 4, "travel_light": 4,
    # level 6
    "bloody_mess": 6, "demolition_expert": 6, "ferocious_loyalty": 6, "fortune_finder": 6,
    "gunslinger": 6, "hand_loader": 6, "lead_belly": 6, "shotgun_surgeon": 6,
    "the_professional": 6, "toughness": 6, "vigilant_recycler": 6,
    # level 8
    "commando": 8, "cowboy": 8, "living_anatomy": 8, "pack_rat": 8, "quick_draw": 8,
    "rad_resistance": 8, "scrounger": 8, "stonewall": 8, "strong_back": 8, "super_slam": 8,
    "terrifying_presence": 8,
    # level 10
    "animal_friend": 10, "finesse": 10, "here_and_now": 10, "math_wrath": 10,
    "miss_fortune": 10, "mister_sandman": 10, "mysterious_stranger": 10, "nerd_rage": 10,
    "night_person": 10, "plasma_spaz": 10,
    # level 12
    "fast_metabolism": 12, "ghastly_scavenger": 12, "hit_the_deck": 12, "life_giver": 12,
    "long_haul": 12, "piercing_strike": 12, "pyromaniac": 12, "robotics_expert": 12,
    "silent_running": 12, "sniper": 12, "splash_damage": 12, "unstoppable_force": 12,
    # level 14
    "adamantium_skeleton": 14, "center_of_mass": 14, "chemist": 14, "jury_rigging": 14,
    "light_step": 14, "purifier": 14,
    # level 16
    "action_boy": 16, "better_criticals": 16, "chem_resistant": 16, "meltdown": 16,
    "tag": 16, "weapon_handling": 16,
    # level 18
    "computer_whiz": 18, "concentrated_fire": 18, "infiltrator": 18, "paralyzing_palm": 18,
    # level 20
    "explorer": 20, "grim_reapers_sprint": 20, "ninja": 20, "solar_powered": 20,
    # level 22
    "laser_commander": 22, "nuka_chemist": 22, "spray_n_pray": 22,
    # level 24
    "slayer": 24,
    # level 26
    "nerves_of_steel": 26,
    # level 28
    "rad_absorption": 28,
}

PERKS = [replace(perk, min_level=_LEVEL_BY_ID[perk.id]) for perk in PERKS]
PERKS_BY_ID = {perk.id: perk for perk in PERKS}
