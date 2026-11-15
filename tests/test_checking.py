import pytest

from greek_coach.checking import CheckError, check
from greek_coach.packs import McqItem, TrueFalseItem, VocabItem

KAFES = VocabItem(id="v", type="vocab", skill="vocab", level="A1", el="ο καφές", en="coffee", tr="kahve")


@pytest.mark.parametrize("lang,choice,ok", [
    ("tr", "kahve", True),
    ("tr", "çay", False),
    ("en", "coffee", True),
    ("en", "kahve", False),
])
def test_vocab_greek_to_meaning(lang, choice, ok):
    r = check(KAFES, {"direction": "el_meaning", "lang": lang}, {"choice": choice})
    assert r.correct is ok
    assert r.score == (1.0 if ok else 0.0)
    assert r.answer == ("kahve" if lang == "tr" else "coffee")


def test_vocab_meaning_to_greek_normalises_unicode():
    # "έ" written as ε + combining acute (NFD) must still count.
    decomposed = "ο καφές"
    r = check(KAFES, {"direction": "meaning_el", "lang": "tr"}, {"choice": decomposed})
    assert r.correct
    assert r.answer == "ο καφές"


def test_vocab_missing_tr_falls_back_to_en():
    item = VocabItem(id="v", type="vocab", skill="vocab", level="A1", el="το ταξί", en="taxi")
    assert check(item, {"direction": "el_meaning", "lang": "tr"}, {"choice": "taxi"}).correct


def test_vocab_rejects_unknown_direction():
    with pytest.raises(CheckError):
        check(KAFES, {"direction": "sideways"}, {"choice": "kahve"})


def test_mcq():
    item = McqItem(id="q", type="mcq", skill="vocab", level="A1", prompt={"el": "Πού;"},
                   options=["Α.", "Β.", "Γ."], answer=1)
    assert check(item, {}, {"choice": 1}).correct
    assert not check(item, {}, {"choice": 0}).correct
    with pytest.raises(CheckError):
        check(item, {}, {"choice": 7})
    with pytest.raises(CheckError):
        check(item, {}, {"choice": True})


def test_true_false_scores_each_statement():
    item = TrueFalseItem(id="r", type="true_false", skill="reading", level="A1", statements=[
        {"el": "Ένα.", "answer": False}, {"el": "Δύο.", "answer": True}, {"el": "Τρία.", "answer": True},
    ])
    r = check(item, {}, {"answers": [False, True, False]})
    assert r.parts == [True, True, False]
    assert r.score == pytest.approx(2 / 3, abs=1e-3)
    assert r.correct is False
    full = check(item, {}, {"answers": [False, True, True]})
    assert full.correct and full.score == 1.0
    with pytest.raises(CheckError):
        check(item, {}, {"answers": [True]})
