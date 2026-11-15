"""Answer checking for the phase-3 exercise types (SPEC §4.6)."""

import pytest
from pydantic import ValidationError

from greek_coach.checking import CheckError, check, check_typed
from greek_coach.packs import CategoriseItem, FormItem, GapBankItem, MatchItem, VocabItem, _item_adapter

PIGA = FormItem(id="f", type="form", skill="grammar", level="A2",
                text="Χθες {1} στη λαϊκή.", cue={"lemma": "πηγαίνω", "person": "1sg", "tense": "aorist"},
                answer={"1": ["πήγα"]})
FARMAKEIO = VocabItem(id="v", type="vocab", skill="vocab", level="A1", el="το φαρμακείο", lemma="φαρμακείο", en="pharmacy")


@pytest.mark.parametrize("typed,ok,note", [
    ("πήγα", True, None),
    ("  Πήγα ", True, None),
    ("πηγα", True, "πήγα"),      # accent missing: right, with a note
    ("πηγά", True, "πήγα"),      # accent on the wrong vowel: right, with a note
    ("πήγες", False, None),
    ("", False, None),
])
def test_form_typed_is_accent_tolerant(typed, ok, note):
    r = check(PIGA, {}, {"answers": {"1": typed}})
    assert r.correct is ok
    assert r.accent_note == note


def test_typed_vocab_article_is_optional_and_sigma_folds():
    card = {"direction": "meaning_el_typed"}
    assert check(FARMAKEIO, card, {"text": "φαρμακείο"}).correct
    assert check(FARMAKEIO, card, {"text": "το φαρμακείο"}).correct
    r = check(FARMAKEIO, card, {"text": "φαρμακειο"})
    assert r.correct and r.accent_note == "το φαρμακείο"
    assert check_typed("καφεσ", ["καφές"]).ok


def test_match_scores_per_pair():
    item = MatchItem(id="m", type="match", skill="reading", level="A1",
                     left=["α", "β", "γ"], right=["1", "2", "3", "4"], answer=[1, 0, 2])
    r = check(item, {}, {"answers": [1, 0, 3]})
    assert r.parts == [True, True, False] and not r.correct and r.score == pytest.approx(2 / 3, abs=1e-3)
    with pytest.raises(CheckError):
        check(item, {}, {"answers": [1, 0]})
    with pytest.raises(CheckError):
        check(item, {}, {"answers": [1, 0, 9]})


def test_gap_bank_and_categorise():
    gb = GapBankItem(id="g", type="gap_bank", skill="reading", level="A1",
                     text="Είναι {1} και {2}.", bank=["ανοιχτό", "κλειστό", "μακριά"], answer={"1": "ανοιχτό", "2": "κλειστό"})
    assert check(gb, {}, {"answers": {"1": "ανοιχτό", "2": "κλειστό"}}).correct
    assert check(gb, {}, {"answers": {"1": "κλειστό", "2": "κλειστό"}}).parts == [False, True]
    cat = CategoriseItem(id="c", type="categorise", skill="history", level="A2",
                         categories=["Α", "Β"], items=["x", "y", "z"], answer=[0, 1, 1])
    assert check(cat, {}, {"answers": [0, 1, 1]}).correct
    assert check(cat, {}, {"answers": [1, 1, 1]}).score == pytest.approx(2 / 3, abs=1e-3)


@pytest.mark.parametrize("bad", [
    {"type": "form", "text": "no gap", "answer": {"1": ["x"]}},
    {"type": "form", "text": "{1}", "answer": {"1": ["πήγα"]}, "options": {"1": ["πήγες", "πάει"]}},
    {"type": "gap_bank", "text": "{1}", "bank": ["α", "β"], "answer": {"1": "γ"}},
    {"type": "match", "left": ["a", "b"], "right": ["1", "2"], "answer": [0, 0]},
    {"type": "categorise", "categories": ["A", "B"], "items": ["x", "y"], "answer": [0, 5]},
])
def test_invalid_items_are_rejected(bad):
    with pytest.raises(ValidationError):
        _item_adapter.validate_python({"id": "x", "skill": "reading", "level": "A1", **bad})
