"""Unit tests for the G.O.A.T. questionnaire + scoring (pure Python, no HA).

The GOAT (Fallout 3, Vault 101) determines the 3 Tag! skills of the FNV profile:
every answer scores 1 point per skill label it carries (question 6 answer 2 scores
two skills), question 10 scores nothing (all answers are "The Overseer."). The top
3 skills become the Tag! skills, ties broken alphabetically (per the wiki); the
single top skill determines the vault "job".
"""

import sys
from pathlib import Path

import pytest

# Make the integration's modules importable as top-level modules WITHOUT HA
# (importing the package would run __init__.py, which needs homeassistant).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "custom_components" / "gamified_gtd"))

import gamification as g  # noqa: E402
import goat_data as gd  # noqa: E402


def test_questionnaire_shape():
    """10 questions, numbered 1..10, each with 4 answers and a slide id."""
    assert len(gd.QUESTIONS) == 10
    for i, q in enumerate(gd.QUESTIONS, start=1):
        assert q.n == i
        assert q.slide == f"slide_{i}"
        assert len(q.answers) == 4
        assert q.text


def test_question_10_scores_nothing():
    """The joke question (all answers 'The Overseer.') must not score any skill."""
    for a in gd.QUESTIONS[9].answers:
        assert gd.LABEL_TO_FNV[a.skills[0]] is None


def test_question_6_answer_2_scores_two_skills():
    """'Trade a Vault hoodlum for his cherry bomb' = Explosives AND Barter."""
    skills = gd.QUESTIONS[5].answers[1].skills
    assert set(skills) == {"Explosives", "Barter"}


def test_all_first_answers():
    """Answering option 1 everywhere: Small Guns twice (Q5, Q7) -> top skill guns,
    tags = guns + the two alphabetically first 1-point skills."""
    result = gd.goat_result([0] * 10)
    assert result["counts"]["Small Guns"] == 2
    assert result["job"]["skill"] == "Small Guns"
    assert result["job"]["name"] == "Tattoo artist"
    # guns (2 points) + alphabetical tie-break among the 1-point labels:
    # Barter, Explosives, ... -> tags are FNV skill ids, de-duplicated.
    assert result["tags"] == ["guns", "barter", "explosives"]
    for tag in result["tags"]:
        assert tag in g.SKILLS


def test_big_and_small_guns_dedupe_to_one_tag():
    """Big Guns (Q4 answer 2) and Small Guns (Q5 answer 1) both map to FNV 'guns' —
    the tags must contain 'guns' only once."""
    # Q4=catcher(Big Guns), Q5=pistol(Small Guns), rest answer 4 (Q1 sneak, Q2 science,
    # Q3 nothing, Q6 repair, Q7 energy weapons, Q8 medicine, Q9 lockpick, Q10 none)
    result = gd.goat_result([3, 3, 3, 1, 0, 3, 3, 3, 3, 0])
    assert result["tags"].count("guns") == 1
    assert len(result["tags"]) == 3


def test_tie_break_is_alphabetical():
    """All skills at 1 point -> tags are the first 3 labels alphabetically."""
    # one distinct skill per question, all 1 point: Q1 science, Q2 melee, Q3 speech,
    # Q4 explosives, Q5 guns(small), Q6 lockpick, Q7 medicine, Q8 barter, Q9 repair
    result = gd.goat_result([0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    labels = sorted(result["counts"], key=lambda l: (-result["counts"][l], l))
    expected = []
    for label in labels:
        fnv = gd.LABEL_TO_FNV[label]
        if fnv not in expected:
            expected.append(fnv)
        if len(expected) == 3:
            break
    assert result["tags"] == expected


def test_wrong_answer_count_raises():
    with pytest.raises(ValueError):
        gd.goat_result([0, 1, 2])


def test_answer_index_out_of_range_raises():
    with pytest.raises(ValueError):
        gd.goat_result([0] * 9 + [4])


def test_every_job_has_name_and_comment():
    for label, job in gd.JOBS.items():
        assert job["name"] and job["comment"]
