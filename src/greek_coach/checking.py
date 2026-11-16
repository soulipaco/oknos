"""Deterministic answer checking (docs/SPEC.md §4.6).

The server never trusts the browser's verdict: it re-derives the right answer
from the loaded item. Selection types score per sub-answer; typed answers are
accent-tolerant and report a missing or wrong accent instead of failing it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from greek_coach import greek
from greek_coach.packs import (
    CategoriseItem,
    FormItem,
    GapBankItem,
    Item,
    MatchItem,
    McqItem,
    SpeakItem,
    TableFillItem,
    TrueFalseItem,
    VocabItem,
    WriteItem,
)

# el_meaning: Greek shown, pick the meaning. meaning_el: meaning shown, pick the Greek.
# audio_meaning: Greek heard, pick the meaning. meaning_el_typed: meaning shown, type the Greek.
VOCAB_DIRECTIONS = ("el_meaning", "meaning_el", "audio_meaning", "meaning_el_typed")


class CheckError(ValueError):
    """The response does not fit the item (a bug in the client, not a wrong answer)."""


@dataclass
class Result:
    score: float | None  # None for write and speak, which the coach marks later
    correct: bool | None
    answer: Any  # what the right answer was, for feedback
    parts: list[bool] = field(default_factory=list)
    accent_note: str | None = None


def meaning(item: VocabItem, lang: str) -> str:
    """The item's meaning in the UI language, falling back tr -> en -> the other."""
    value = getattr(item, lang, None) if lang in ("en", "tr") else None
    return value or item.en or item.tr or ""


def _same(a: str, b: str) -> bool:
    return greek.nfc(a).strip() == greek.nfc(b).strip()


@dataclass
class Typed:
    ok: bool
    accent_note: str | None = None


def check_typed(given: str, accepted: list[str], article_optional: bool = True) -> Typed:
    """Compare a typed answer with the accepted forms (SPEC §4.6).

    Exact after normalising: right. Equal only when accents are ignored: right, with a note
    naming the correctly accented form. A leading article is optional.
    """
    if not isinstance(given, str) or not given.strip():
        return Typed(False)

    def variants(text: str) -> set[str]:
        out = {greek.norm_answer(text)}
        if article_optional:
            out.add(greek.norm_answer(greek.strip_article(text)))
        return out

    given_v = variants(given)
    for form in accepted:
        if given_v & variants(form):
            return Typed(True)
    given_f = {greek.strip_accents(v) for v in given_v}
    for form in accepted:
        if given_f & {greek.strip_accents(v) for v in variants(form)}:
            return Typed(True, accent_note=form)
    return Typed(False)


def gap_order(gaps) -> list[str]:
    """Gap names in reading order: numeric names numerically, then the rest."""
    return sorted(gaps, key=lambda g: (0, int(g), "") if str(g).isdigit() else (1, 0, str(g)))


def _index(value: Any, size: int, what: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < size:
        raise CheckError(f"{what} must be a position 0..{size - 1}")
    return value


def _per_part(parts: list[bool], answer: Any, note: str | None = None) -> Result:
    score = sum(parts) / len(parts) if parts else 0.0
    return Result(score=round(score, 4), correct=all(parts), answer=answer, parts=parts, accent_note=note)


def check(item: Item, card: dict[str, Any], response: dict[str, Any]) -> Result:
    if isinstance(item, VocabItem):
        direction = card.get("direction")
        if direction not in VOCAB_DIRECTIONS:
            raise CheckError(f"unknown vocab card direction {direction!r}")
        if direction == "meaning_el_typed":
            text = response.get("text")
            if not isinstance(text, str):
                raise CheckError("a typed vocab answer needs a 'text' string")
            accepted = [item.el] + ([item.lemma] if item.lemma else [])
            typed = check_typed(text, accepted)
            return Result(score=1.0 if typed.ok else 0.0, correct=typed.ok, answer=item.el,
                          accent_note=item.el if typed.accent_note else None)
        choice = response.get("choice")
        if not isinstance(choice, str):
            raise CheckError("a vocab answer needs a 'choice' string")
        right = item.el if direction == "meaning_el" else meaning(item, card.get("lang", "en"))
        ok = _same(choice, right)
        return Result(score=1.0 if ok else 0.0, correct=ok, answer=right)

    if isinstance(item, FormItem):
        answers = response.get("answers")
        if not isinstance(answers, dict) or set(answers) != set(item.answer):
            raise CheckError(f"a form answer needs an 'answers' object with the gaps {sorted(item.answer)}")
        parts, note = [], None
        for gap in gap_order(item.answer):
            typed = check_typed(answers[gap], item.answer[gap], article_optional=False)
            parts.append(typed.ok)
            note = note or typed.accent_note
        return _per_part(parts, {g: f[0] for g, f in item.answer.items()}, note)

    if isinstance(item, McqItem):
        choice = _index(response.get("choice"), len(item.options), "an mcq answer 'choice'")
        ok = choice == item.answer
        return Result(score=1.0 if ok else 0.0, correct=ok, answer=item.answer)

    if isinstance(item, TrueFalseItem):
        answers = response.get("answers")
        if not isinstance(answers, list) or len(answers) != len(item.statements):
            raise CheckError(f"a true_false answer needs {len(item.statements)} answers")
        parts = [a is s.answer for a, s in zip(answers, item.statements)]
        return _per_part(parts, [s.answer for s in item.statements])

    if isinstance(item, (MatchItem, CategoriseItem)):
        answers = response.get("answers")
        size = len(item.left) if isinstance(item, MatchItem) else len(item.items)
        targets = len(item.right) if isinstance(item, MatchItem) else len(item.categories)
        if not isinstance(answers, list) or len(answers) != size:
            raise CheckError(f"a {item.type} answer needs {size} answers")
        picked = [_index(a, targets, f"each {item.type} answer") for a in answers]
        return _per_part([p == a for p, a in zip(picked, item.answer)], item.answer)

    if isinstance(item, GapBankItem):
        answers = response.get("answers")
        if not isinstance(answers, dict) or set(answers) != set(item.answer):
            raise CheckError(f"a gap_bank answer needs an 'answers' object with the gaps {sorted(item.answer)}")
        parts = [isinstance(answers[g], str) and _same(answers[g], item.answer[g]) for g in gap_order(item.answer)]
        return _per_part(parts, item.answer)

    if isinstance(item, TableFillItem):
        cells = item.cells()
        answers = response.get("answers")
        if not isinstance(answers, list) or len(answers) != len(cells):
            raise CheckError(f"a table_fill answer needs 'answers', a list of {len(cells)} cell texts in reading order")
        parts, note = [], None
        for given, (_, _, accepted) in zip(answers, cells):
            typed = check_typed(given if isinstance(given, str) else "", accepted, article_optional=True)
            parts.append(typed.ok)
            note = note or typed.accent_note
        return _per_part(parts, [accepted[0] for _, _, accepted in cells], note)

    if isinstance(item, WriteItem):
        if response.get("skipped") is True:
            return Result(score=None, correct=None, answer=None)
        text = response.get("text")
        if not isinstance(text, str) or not text.strip():
            raise CheckError("a writing answer needs a non-empty 'text' string")
        if len(text) > 5000:
            raise CheckError("the text is too long (more than 5000 characters)")
        return Result(score=None, correct=None, answer=None)

    if isinstance(item, SpeakItem):
        if response.get("skipped") is True:
            return Result(score=None, correct=None, answer=None)
        recording = response.get("recording")
        if recording is not None and not isinstance(recording, str):
            raise CheckError("a speaking answer's 'recording' must be the name the upload returned")
        return Result(score=None, correct=None, answer=None)

    raise CheckError(f"items of type {item.type!r} cannot be checked yet")
