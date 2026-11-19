"""Tap-a-word lookup: any Greek word on screen -> its meaning, if a pack has it.

Matches, best first: the exact word, the word without accents, a verb form that a form item
lists, then the same stem with a different ending (καφέ -> καφές, φαρμακείου -> φαρμακείο).
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from greek_coach import greek
from greek_coach.checking import meaning
from greek_coach.packs import Catalog, FormItem, VocabItem

# Endings stripped to find a shared stem, longest first.
_ENDINGS = sorted(
    ["ος", "ης", "ας", "ες", "ου", "ων", "ους", "ο", "α", "η", "ι", "ω", "ε", "εσ", "οι", "ια", "ιου", "ιων",
     "ει", "εις", "ουμε", "ετε", "ουν", "ω", "ασ", "ησ", "οσ", "ουσ", "ια", "εια", "ειο", "ειου", "ειων",
     "ματα", "μα", "ματος", "ατε", "αμε", "ανε", "αν", "α", "ομαι", "εται", "ονται", "ησα", "ησε", "ησαν"],
    key=len, reverse=True,
)


def _stems(word: str) -> set[str]:
    base = greek.fold(word)
    out = set()
    for end in _ENDINGS:
        e = greek.fold(end)
        if base.endswith(e) and len(base) - len(e) >= 3:
            out.add(base[: -len(e)])
    if len(base) >= 4:
        out.add(base)
    return out


@dataclass
class Entry:
    item_key: str
    el: str
    en: str | None
    tr: str | None
    pos: str | None
    say: str | None = None


class Index:
    def __init__(self, catalog: Catalog):
        self.exact: dict[str, list[Entry]] = defaultdict(list)
        self.folded: dict[str, list[Entry]] = defaultdict(list)
        self.stem: dict[str, list[Entry]] = defaultdict(list)
        self.inside: dict[str, list[Entry]] = defaultdict(list)  # a word -> the phrases that contain it
        lemma_entry: dict[str, Entry] = {}
        self.function: dict[str, Entry] = {}
        for key, (pack, item) in catalog.items.items():
            if not isinstance(item, VocabItem) or item.status != "ok":
                continue
            entry = Entry(key, item.el, item.en, item.tr, item.pos, item.say)
            forms = {item.el, greek.strip_article(item.el)} | ({item.lemma} if item.lemma else set())
            for form in forms:
                self.exact[greek.norm_answer(form)].append(entry)
                self.folded[greek.fold(form)].append(entry)
                lemma_entry.setdefault(greek.fold(form), entry)
            if " " not in greek.strip_article(item.el):
                for st in _stems(greek.strip_article(item.el)):
                    self.stem[st].append(entry)
            elif item.pos in ("phrase", None):
                # "με λένε …": tapping λένε in a dialogue finds the phrase it belongs to
                for w in greek.words(item.el):
                    if len(w) >= 3:
                        self.inside[greek.fold(w)].append(entry)
        # Verb forms from the verb track point at their lemma's vocab entry, when we have one.
        for key, (pack, item) in catalog.items.items():
            if isinstance(item, FormItem) and item.cue and item.cue.lemma:
                target = lemma_entry.get(greek.fold(item.cue.lemma))
                if target is None:
                    continue
                for forms in item.answer.values():
                    for form in forms:
                        for w in greek.words(form):
                            if w != "θα":
                                self.folded.setdefault(greek.fold(w), []).append(target)
        # Articles, pronouns, prepositions and particles: in no pack, but on every line.
        for row in _function_words():
            entry = Entry(f"function/{row['el']}", row["el"], row["en"], row["tr"], row.get("pos"))
            for form in [row["el"], *row.get("forms", [])]:
                self.function.setdefault(greek.fold(form), entry)

    def find(self, word: str) -> tuple[list[Entry], str]:
        word = greek.to_monotonic(word.strip(" .,;:!?«»\"'()·"))
        for table, how, k in ((self.exact, "exact", greek.norm_answer(word)), (self.folded, "accents", greek.fold(word))):
            if table.get(k):
                return _dedupe(table[k]), how
        if greek.fold(word) in self.function:
            return [self.function[greek.fold(word)]], "exact"
        hits: list[Entry] = []
        for st in sorted(_stems(word), key=len, reverse=True):
            hits += self.stem.get(st, [])
            if hits:
                break
        if hits:
            return _dedupe(hits), "stem"
        inside = self.inside.get(greek.fold(word), [])
        return _dedupe(inside), "phrase" if inside else "none"


def _dedupe(entries: list[Entry]) -> list[Entry]:
    seen, out = set(), []
    for e in entries:
        if e.item_key not in seen:
            seen.add(e.item_key)
            out.append(e)
    return out[:3]


def as_json(entries: list[Entry], how: str, lang: str) -> dict:
    return {
        "match": how,
        "entries": [{"item_key": e.item_key, "el": e.el, "pos": e.pos, "say": e.say,
                     "meaning": (e.tr if lang == "tr" and e.tr else None) or e.en or e.tr or "",
                     "meaning_lang": lang if getattr(e, lang, None) else ("en" if e.en else "tr")} for e in entries],
    }


FUNCTION_WORDS_FILE = Path(__file__).with_name("function_words.json")


def _function_words() -> list[dict]:
    try:
        return json.loads(FUNCTION_WORDS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def meaning_of(item: VocabItem, lang: str) -> str:
    return meaning(item, lang)
