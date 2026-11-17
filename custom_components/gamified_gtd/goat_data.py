"""G.O.A.T. — Generalized Occupational Aptitude Test (Fallout 3, Vault 101).

Pure data + scoring, no HA imports (unit-testable).

At integration start the user takes the G.O.A.T. (card `custom:gamified-gtd-goat`)
and the result determines the 3 Tag! skills of the FNV profile — instead of picking
them manually in the options flow. Question texts/answers are the Fallout 3 GOAT
questionnaire; slide images are NOT shipped (copyright) — the user drops them into
www/gamified_gtd_icons/goat/slide_<n>.png (see that folder's README).

Fallout 3 uses "Big Guns"/"Small Guns"; FNV merged them into "Guns" — see
LABEL_TO_FNV. Question 6 answer 2 is worth TWO skills ("Explosives and Barter").
Question 10 is the joke question ("The Overseer." for every answer) and scores nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Fallout 3 skill label -> FNV skill id (None = scores no skill).
LABEL_TO_FNV = {
    "Barter": "barter",
    "Big Guns": "guns",
    "Small Guns": "guns",
    "Energy Weapons": "energy_weapons",
    "Explosives": "explosives",
    "Lockpick": "lockpick",
    "Medicine": "medicine",
    "Melee Weapons": "melee_weapons",
    "Repair": "repair",
    "Science": "science",
    "Sneak": "sneak",
    "Speech": "speech",
    "Unarmed": "unarmed",
    "Nothing": None,
    "-/-": None,
}


@dataclass(frozen=True)
class GoatAnswer:
    """One answer option: text plus the Fallout 3 skill label(s) it scores."""

    text: str
    skills: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GoatQuestion:
    """One GOAT question: slide image id (drop-in goat/slide_<n>.png), text, answers."""

    n: int  # 1-based question number
    slide: str  # icon id, e.g. "slide_1"
    text: str
    answers: tuple[GoatAnswer, ...]


# The 10 GOAT questions (Vault 101). Answers map to Fallout 3 skill labels.
QUESTIONS: tuple[GoatQuestion, ...] = (
    GoatQuestion(
        n=1,
        slide="slide_1",
        text='You are approached by a frenzied Vault scientist, who yells, "I\'m going to put my quantum harmonizer in your photonic resonation chamber!" What\'s your response?',
        answers=(
            GoatAnswer('"But doctor, wouldn\'t that cause a parabolic destabilization of the fission singularity?"', ("Science",)),
            GoatAnswer('"Yeah? Up yours too, buddy!"', ("Speech",)),
            GoatAnswer("Say nothing, grab a nearby pipe and hit the scientist in the head to knock him out. For all you know, he was planning to blow up the vault.", ("Melee Weapons",)),
            GoatAnswer("Say nothing, but slip away before the scientist can continue his rant.", ("Sneak",)),
        ),
    ),
    GoatQuestion(
        n=2,
        slide="slide_2",
        text="While working as an intern in the Clinic, a patient with a strange infection on his foot stumbles through the door. The infection is spreading at an alarming rate, but the doctor has stepped out for a while. What do you do?",
        answers=(
            GoatAnswer("Amputate the foot before the infection spreads.", ("Melee Weapons",)),
            GoatAnswer("Scream for help.", ("Speech",)),
            GoatAnswer("Medicate the infected area to the best of your abilities.", ("Medicine",)),
            GoatAnswer("Restrain the patient, and merely observe as the infection spreads.", ("Science",)),
        ),
    ),
    GoatQuestion(
        n=3,
        slide="slide_3",
        text="You discover a young boy lost in the lower levels of the Vault. He's hungry and frightened, but also appears to be in possession of stolen property. What do you do?",
        answers=(
            GoatAnswer("Give the boy a hug and tell him everything will be okay.", ("Speech",)),
            GoatAnswer("Confiscate the property by force, and leave him there as punishment.", ("Unarmed",)),
            GoatAnswer("Pick the boy's pocket to take the stolen property for yourself, and leave the boy to his fate.", ("Sneak",)),
            GoatAnswer("Lead the boy to safety, then turn him over to the overseer.", ("Nothing",)),
        ),
    ),
    GoatQuestion(
        n=4,
        slide="slide_4",
        text="Congratulations! You made one of the Vault 101 baseball teams! Which position do you prefer?",
        answers=(
            GoatAnswer("Pitcher.", ("Explosives",)),
            GoatAnswer("Catcher.", ("Big Guns",)),
            GoatAnswer("Designated Hitter.", ("Melee Weapons",)),
            GoatAnswer("None, you wish the vault had a soccer team.", ("Unarmed",)),
        ),
    ),
    GoatQuestion(
        n=5,
        slide="slide_5",
        text="Your grandmother invites you to tea, but you're surprised when she gives you a pistol and orders you to kill another Vault resident. What do you do?",
        answers=(
            GoatAnswer("Obey your elder and kill the Vault resident with the pistol.", ("Small Guns",)),
            GoatAnswer("Offer your most prized possession for the resident's life.", ("Barter",)),
            GoatAnswer("Ask granny for a minigun instead. After all, you don't want to miss.", ("Big Guns",)),
            GoatAnswer("Throw your tea in granny's face.", ("Explosives",)),
        ),
    ),
    GoatQuestion(
        n=6,
        slide="slide_6",
        text="Old Mr. Abernathy has locked himself in his quarters again, and you've been ordered to get him out. How do you proceed?",
        answers=(
            GoatAnswer("Use a bobby pin to pick the lock on the door.", ("Lockpick",)),
            GoatAnswer("Trade a Vault hoodlum for his cherry bomb and blow open the lock.", ("Explosives", "Barter")),
            GoatAnswer("Go to the armory, retrieve a laser pistol, and blow the lock off.", ("Energy Weapons",)),
            GoatAnswer("Walk away, and let the old coot rot.", ("Repair",)),
        ),
    ),
    GoatQuestion(
        n=7,
        slide="slide_7",
        text="Oh, no! You've been exposed to radiation, and a mutated hand has grown out of your stomach! What's the best course of treatment?",
        answers=(
            GoatAnswer("A bullet to the brain.", ("Small Guns",)),
            GoatAnswer("Large doses of anti-mutagen agent.", ("Medicine",)),
            GoatAnswer("Prayer. Maybe God will spare you in exchange for a life of pious devotion.", ("Barter",)),
            GoatAnswer("Removal of the mutated tissue with a precision laser.", ("Energy Weapons",)),
        ),
    ),
    GoatQuestion(
        n=8,
        slide="slide_8",
        text="A fellow Vault 101 resident is in possession of a Grognak the Barbarian comic book, issue number 1. You want it. What's the best way to obtain it?",
        answers=(
            GoatAnswer("Trade the comic book for one of your own valuable possessions.", ("Barter",)),
            GoatAnswer("Steal the comic book at gunpoint.", ("Small Guns",)),
            GoatAnswer("Sneak into the resident's quarters, and steal the comic book from his desk.", ("Sneak",)),
            GoatAnswer("Slip some knock out drops into the resident's Nuka-Cola, and take the comic book when he's unconscious.", ("Medicine",)),
        ),
    ),
    GoatQuestion(
        n=9,
        slide="slide_9",
        text="You decide it would be fun to play a prank on your father. You enter his private restroom when no one is looking, and…",
        answers=(
            GoatAnswer("Loosen some bolts on some pipes. When the sink is turned on, the room will flood.", ("Repair",)),
            GoatAnswer("Put a firecracker in the toilet. That's sure to cause some chaos.", ("Explosives",)),
            GoatAnswer("Break into the locked medicine cabinet and replace his high blood pressure medication with sugar pills.", ("Medicine",)),
            GoatAnswer("Manipulate the power wattage on his razor, so he'll get an electric shock next time he shaves.", ("Lockpick",)),
        ),
    ),
    GoatQuestion(
        n=10,
        slide="slide_10",
        text="Who is indisputably the most important person in Vault 101: He who shelters us from the harshness of the atomic wasteland, and to whom we owe everything we have, including our lives?",
        answers=(
            GoatAnswer("The Overseer.", ("-/-",)),
            GoatAnswer("The Overseer.", ("-/-",)),
            GoatAnswer("The Overseer.", ("-/-",)),
            GoatAnswer("The Overseer.", ("-/-",)),
        ),
    ),
)

# Result table (Mr. Brotch's jobs), keyed by the Fallout 3 skill label.
# None = no skill scored at all (the unimplemented "Masseuse" outcome).
JOBS: dict[str | None, dict[str, str]] = {
    "Barter": {"name": "Vault chaplain", "comment": "They say the G.O.A.T. never lies. According to this, you're slated to be the next vault… Chaplain. God help us all."},
    "Big Guns": {"name": "Laundry cannon operator", "comment": "Well according to this, you're in line to be trained as a laundry cannon operator. First time for everything indeed."},
    "Small Guns": {"name": "Tattoo artist", "comment": "Huh. I wonder who will be brave enough to be your first customer as the vault's new Tattoo Artist? I promise it won't be me."},
    "Energy Weapons": {"name": "Pedicurist", "comment": "It's nice to know I can still be surprised. Pedicurist! I might have guessed Manicurist, or even Masseuse. But apparently you're a foot person."},
    "Explosives": {"name": "Waste management specialist", "comment": "It says here you're perfectly suited for a career as a Waste Management Specialist. A specialist, mind you, not just a dabbler. Congratulations!"},
    "Lockpick": {"name": "Vault loyalty inspector", "comment": "Huh. \"Vault Loyalty Inspector\"… I thought that had been phased out decades ago. Well, sounds like a job right up your alley, hmm?"},
    "Medicine": {"name": "Clinical test subject", "comment": "Interesting. \"Clinical Test Subject\"… sounds like something you should excel at. I guess you and your dad will be working together."},
    "Melee Weapons": {"name": "Fry cook", "comment": "Looks like the diner's going to get a new Fry Cook. I'll just say this once: hold the mustard, extra pickles. Ha ha ha."},
    "Repair": {"name": "Jukebox technician", "comment": "Thank goodness. We're finally getting a new Jukebox Technician. That thing hasn't worked right since old Joe Palmer passed."},
    "Science": {"name": "Pip-Boy programmer", "comment": "Well, well. Pip-Boy Programmer, eh? Stanley will finally have someone to talk shop with."},
    "Sneak": {"name": "Shift supervisor", "comment": "Apparently you're management material. You're going to be trained as a Shift Supervisor. Could I be talking to the next Overseer? Stranger things have happened."},
    "Speech": {"name": "Marriage counselor", "comment": "Wow. Wow. Says here you're going to be the vault's Marriage Counselor. Almost makes me want to get married, just to be able to avail myself of your services."},
    "Unarmed": {"name": "Little league coach", "comment": "Apparently you'll have a career in professional sports. You're the new vault Little League coach! Congratulations."},
    None: {"name": "Masseuse", "comment": "Looks like you'll be putting your… physical talents to good use as the vault's new Masseuse."},
}


def goat_result(answers: list[int], num_tags: int = 3) -> dict[str, Any]:
    """Score the GOAT: `answers` is one 0-based answer index per question.

    Returns {"counts": {fo3_label: points}, "tags": [fnv skill ids], "job": {...}}.
    - Every answer adds 1 point per skill label it carries (question 6 answer 2: two).
    - Question 10 scores nothing (all answers are "The Overseer." / "-/-").
    - Tag! skills = the `num_tags` highest-scoring skills; ties are broken
      alphabetically (per the wiki's note), then converted to FNV skill ids.
    - The "job" is the single highest-scoring skill (same tie-break).
    """
    if len(answers) != len(QUESTIONS):
        raise ValueError(f"Expected {len(QUESTIONS)} answers, got {len(answers)}")
    counts: dict[str, int] = {}
    for question, answer_idx in zip(QUESTIONS, answers):
        if not 0 <= answer_idx < len(question.answers):
            raise ValueError(f"Answer index {answer_idx} out of range for question {question.n}")
        for label in question.answers[answer_idx].skills:
            if LABEL_TO_FNV.get(label) is None:
                continue  # "Nothing" / "-/-" score no points
            counts[label] = counts.get(label, 0) + 1
    # Ranking: most points first, ties alphabetically by Fallout 3 label.
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    top_label = ranked[0][0] if ranked else None
    # Convert the top labels to FNV skill ids, de-duplicated (Big/Small Guns -> guns).
    tags: list[str] = []
    for label, _points in ranked:
        fnv = LABEL_TO_FNV[label]
        if fnv not in tags:
            tags.append(fnv)
        if len(tags) >= num_tags:
            break
    job = JOBS.get(top_label, JOBS[None])
    return {
        "counts": counts,
        "tags": tags,
        "job": {"skill": top_label, "name": job["name"], "comment": job["comment"]},
    }
