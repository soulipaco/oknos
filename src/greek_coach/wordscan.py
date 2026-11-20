"""The Greek words a learner can tap, and the ones the lookup cannot explain (phase 5d).

The fields read here are the ones `web/app.js` renders with `greekText(..., tappable)`: rubrics,
stimulus texts and transcripts, prompts, statements, the form and gap texts (with the answer
filled in, as shown after checking), match and categorise entries, table rows and columns, the
speaking card's useful phrases and model, vocab words and their examples; in chapters, dialogue
lines, examples, table cells and the [[Greek]] spans of the explanations. Option buttons (mcq
options, form choices, the gap-bank) are plain text and not tappable.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable

from greek_coach import greek
from greek_coach.chapters import Bi, Chapter, Table
from greek_coach.packs import (GAP_RE, CategoriseItem, FormItem, GapBankItem, MatchItem, McqItem, SpeakItem,
                               TableFillItem, TrueFalseItem, VocabItem, WriteItem)


def item_texts(item) -> Iterable[str]:
    if item.rubric and item.rubric.el:
        yield item.rubric.el
    if item.stimulus:
        if item.stimulus.text:
            yield item.stimulus.text
        if item.stimulus.tts:
            yield item.stimulus.tts
    prompt = getattr(item, "prompt", None)
    if prompt is not None and getattr(prompt, "el", None):
        yield prompt.el
    if isinstance(item, VocabItem):
        yield item.el
        if item.example:
            yield item.example.el
    elif isinstance(item, FormItem):
        yield GAP_RE.sub(lambda m: item.answer[m.group(1)][0], item.text)
    elif isinstance(item, GapBankItem):
        yield GAP_RE.sub(" ", item.text)
    elif isinstance(item, TrueFalseItem):
        yield from (s.el for s in item.statements)
    elif isinstance(item, MatchItem):
        yield from item.left
        yield from item.right
    elif isinstance(item, CategoriseItem):
        yield from item.items
    elif isinstance(item, TableFillItem):
        yield from item.columns
        yield from item.rows
    elif isinstance(item, SpeakItem):
        yield from item.useful
        if item.model and item.model.el:
            yield item.model.el
    elif isinstance(item, (McqItem, WriteItem)):
        pass


def chapter_texts(chapter: Chapter) -> Iterable[str]:
    for line in chapter.greek_lines():
        yield line["el"]
    yield from chapter.inline_greek()
    for _, _, b in chapter.blocks():
        if isinstance(b, Table):  # the header row is not tappable
            yield from (c for row in b.rows for c in row if not isinstance(c, Bi))


def tappable(texts: Iterable[str]) -> list[str]:
    """Word tokens as the screen splits them; one-letter tokens are not tappable."""
    return [w for t in texts for w in greek.words(t) if len(w) > 1]


@dataclass
class Gaps:
    """Tappable words per place (an items file or a chapter) and those the lookup cannot explain."""

    words: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))   # place -> words
    missing: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    left: dict[str, str] = field(default_factory=dict)  # word -> reason it is left unexplained on purpose

    @property
    def total(self) -> int:
        return len(set().union(*self.words.values())) if self.words else 0

    @property
    def unexplained(self) -> set[str]:
        return set().union(*self.missing.values()) if self.missing else set()

    @property
    def without_reason(self) -> set[str]:
        return {w for w in self.unexplained if w not in self.left}

    @property
    def share(self) -> float:
        return len(self.unexplained) / self.total if self.total else 0.0


def places(pack) -> Iterable[tuple[str, list[str]]]:
    """(place, words) for each items file and each chapter of a pack."""
    by_file: dict[str, list[str]] = defaultdict(list)
    for item_id, item in pack.items.items():
        if item.status != "ok":
            continue
        by_file[f"{pack.id}/items/{pack.item_files.get(item_id, '?')}"] += tappable(item_texts(item))
    yield from sorted(by_file.items())
    for stage, ch in sorted(pack.chapters.items()):
        yield f"{pack.id}/lessons/{stage}.json", tappable(chapter_texts(ch))


def scan(packs, index) -> Gaps:
    """The gaps of these packs, explained by everything `index` knows."""
    gaps = Gaps()
    cache: dict[str, bool] = {}
    for pack in packs:
        if pack.glossary:
            gaps.left.update(pack.glossary.leave)
        for place, words in places(pack):
            for w in words:
                key = greek.to_monotonic(w)
                gaps.words[place].add(key)
                if key not in cache:
                    cache[key] = index.find(key)[1] != "none"
                if not cache[key]:
                    gaps.missing[place].add(key)
    return gaps


# ---------- filling the gaps from Wiktionary (greek-coach words) ----------

def where_used(pack) -> dict[str, str]:
    """word -> the first text of the pack it appears in (context for whoever explains it)."""
    out: dict[str, str] = {}
    texts = [t for item in pack.items.values() for t in item_texts(item)]
    texts += [t for ch in pack.chapters.values() for t in chapter_texts(ch)]
    for t in texts:
        for w in greek.words(t):
            out.setdefault(greek.to_monotonic(w), t[:160])
    return out


def known_lemmas(index, forms_index: dict, word: str) -> list[str]:
    """Wiktionary's lemmas for a form that the lookup itself explains (one more hop for a form of a form)."""
    from greek_coach.importer import enrich

    out: list[str] = []
    for lemma, _ in enrich.lemmas_of(forms_index, word):
        candidates = [lemma] + [l2 for l2, _ in enrich.lemmas_of(forms_index, lemma)]
        for c in candidates:
            if index.known(c) and c not in out:
                out.append(c)
                break
    return out


def fill_forms(pack, index, forms_index: dict, main_index: dict | None = None) -> tuple[dict[str, list[str]], list[dict]]:
    """(new forms for the pack's glossary, leftovers). A leftover has the word, Wiktionary's lemmas
    with an English gloss as a hint, and a text where it appears."""
    from greek_coach.importer import enrich

    gaps = scan([pack], index)
    used = where_used(pack)
    forms: dict[str, list[str]] = {}
    leftovers: list[dict] = []
    for w in sorted(gaps.without_reason, key=greek.fold):
        lemmas = known_lemmas(index, forms_index, w)
        if lemmas:
            forms[greek.nfc(w.lower())] = lemmas
            continue
        hints = []
        for lemma, pos in enrich.lemmas_of(forms_index, w)[:3]:
            gloss = (main_index or {}).get("glosses", {}).get(f"{lemma}|{pos}", "")
            hints.append({"lemma": lemma, "pos": pos, "gloss": gloss})
        if not hints and main_index:
            for pos in ("noun", "adj", "adv", "verb", "name", "prep", "conj", "intj", "num", "pron", "particle"):
                gloss = main_index.get("glosses", {}).get(f"{w}|{pos}") or main_index.get("glosses", {}).get(f"{w.lower()}|{pos}")
                if gloss:
                    hints.append({"lemma": w, "pos": pos, "gloss": gloss})
        leftovers.append({"word": w, "wiktionary": hints, "context": used.get(w, ""),
                          "places": sorted(p for p, ws in gaps.missing.items() if w in ws)})
    return forms, leftovers


def write_forms(pack_dir, forms: dict[str, list[str]]) -> int:
    """Merge forms into <pack>/glossary.json (made if missing). Returns how many were new."""
    import json

    path = pack_dir / "glossary.json"
    data = json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else {
        "source": "Inflected forms mapped to their lemma from the English Wiktionary (https://en.wiktionary.org, "
                  "via kaikki.org, CC BY-SA 4.0); meanings written for this pack.",
        "licence": "CC-BY-SA-4.0",
    }
    have = data.setdefault("forms", {})
    new = 0
    for form, lemmas in forms.items():
        if form not in have:
            new += 1
        have[form] = lemmas[0] if len(lemmas) == 1 else lemmas
    data["forms"] = dict(sorted(have.items(), key=lambda kv: greek.fold(kv[0])))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return new


VISIBILITY_ORDER = ("open", "private", "generated")


def visible_to(catalog, visibility: str):
    """The catalog as a pack of this visibility can rely on: an open pack only on open packs (a
    fresh clone has nothing else), a private pack on open and private ones, the coach's on all."""
    from greek_coach.packs import Catalog

    allowed = set(VISIBILITY_ORDER[: VISIBILITY_ORDER.index(visibility) + 1])
    out = Catalog()
    out.packs = [p for p in catalog.packs if p.manifest.visibility in allowed]
    ids = {p.id for p in out.packs}
    out.items = {k: v for k, v in catalog.items.items() if v[0].id in ids}
    out.chapters = {k: v for k, v in catalog.chapters.items() if v[0].id in ids}
    return out


def lint_pack(pack, catalog) -> tuple[list[str], list[str]]:
    """For validate: (problems, notes). Notes: per items file and chapter, the tappable words the
    lookup cannot explain; the words left unexplained on purpose, with their reasons. Problems: a
    glossary form whose lemma the lookup does not know (the form would still find nothing)."""
    from greek_coach import lookup

    if pack.id not in {p.id for p in catalog.packs}:  # a pack outside the content folders
        catalog.packs.append(pack)
        catalog.items.update({f"{pack.id}/{i}": (pack, it) for i, it in pack.items.items()})
        catalog.chapters.update({(c.curriculum, c.stage): (pack, c) for c in pack.chapters.values()})
    index = lookup.Index(visible_to(catalog, pack.manifest.visibility))
    problems: list[str] = []
    notes: list[str] = []
    if pack.glossary:
        for form, lemmas in pack.glossary.forms.items():
            for lemma in [lemmas] if isinstance(lemmas, str) else lemmas:
                if not index.known(lemma):
                    problems.append(f"{pack.id}/glossary.json: the form '{form}' points at '{lemma}', which nothing explains")
    gaps = scan([pack], index)
    for place, words in sorted(gaps.missing.items()):
        open_words = sorted(w for w in words if w not in gaps.left)
        if open_words:
            notes.append(f"{place}: {len(open_words)} tappable word(s) find no meaning: " + ", ".join(open_words[:40])
                         + (" …" if len(open_words) > 40 else "") + " (greek-coach words --write maps inflected forms)")
    left = sorted(gaps.unexplained & set(gaps.left))
    if left:
        notes.append("left unexplained on purpose: " + "; ".join(f"{w} ({gaps.left[w]})" for w in left))
    if gaps.total:
        notes.append(f"tap-a-word: {gaps.total - len(gaps.unexplained)} of {gaps.total} tappable words have a meaning "
                     f"({1 - gaps.share:.1%})")
    return problems, notes
