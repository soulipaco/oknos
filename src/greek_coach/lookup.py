"""Tap-a-word lookup: any Greek word on screen -> its meaning.

Matches, best first (SPEC §4.8):
1. the exact word, or a verb form that a form item lists;
2. the word without accents;
3. a function word, an instruction word, or a word of a pack's glossary;
4. a name: a known person or place, or a speaker of a chapter (and its forms: Νίνας -> Νίνα);
5. an inflected form a glossary maps to its lemma (ακούστε -> ακούω), shown as "form of";
6. the same stem with a different ending (καφέ -> καφές, φαρμακείου -> φαρμακείο);
7. a phrase the word belongs to (λένε -> με λένε …).
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, replace
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

FUNCTION_WORDS_FILE = Path(__file__).with_name("function_words.json")
RUBRIC_WORDS_FILE = Path(__file__).with_name("rubric_words.json")
NAMES_FILE = Path(__file__).with_name("names.json")
NAME_KINDS = ("person", "place")
NAME_MEANINGS = {"person": ("a name (of a person)", "özel isim (kişi adı)"),
                 "place": ("a place name", "yer adı")}


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
    form_of: str | None = None  # the tapped word is a form of this lemma


class Index:
    def __init__(self, catalog: Catalog):
        self.exact: dict[str, list[Entry]] = defaultdict(list)
        self.folded: dict[str, list[Entry]] = defaultdict(list)
        self.stem: dict[str, list[Entry]] = defaultdict(list)
        self.inside: dict[str, list[Entry]] = defaultdict(list)  # a word -> the phrases that contain it
        self.function: dict[str, Entry] = {}                     # function, instruction and glossary words
        self.forms: dict[str, list[str]] = defaultdict(list)     # folded form -> its lemmas
        self.names: dict[str, str] = {}                          # folded name -> "person" | "place"
        self.name_base: dict[str, str] = {}                      # folded name -> the base name as written
        lemma_entry: dict[str, Entry] = {}
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
                lemma = greek.strip_article(target.el)
                for forms in item.answer.values():
                    for form in forms:
                        for w in greek.words(form):
                            if w != "θα":
                                labelled = target if greek.fold(w) == greek.fold(lemma) else replace(target, form_of=lemma)
                                self.folded.setdefault(greek.fold(w), []).append(labelled)
        # Articles, pronouns, prepositions and particles, and the words of the instructions: in no
        # pack, but on every screen. Then the packs' glossaries.
        for kind, path in (("function", FUNCTION_WORDS_FILE), ("rubric", RUBRIC_WORDS_FILE)):
            for row in _rows(path):
                # an article's or pronoun's variants (τη, την) are listed in its meaning, not "forms of" it
                self._add_word(Entry(f"{kind}/{row['el']}", row["el"], row.get("en"), row.get("tr"), row.get("pos")),
                               [row["el"], *row.get("forms", [])], label_forms=kind != "function")
        self._add_names(_names(), override=False)
        for pack in catalog.packs:
            g = pack.glossary
            if g is None:
                continue
            for w in g.words:
                self._add_word(Entry(f"glossary/{pack.id}/{w.el}", w.el, w.en, w.tr, w.pos), [w.el, *w.forms])
            for form, lemmas in g.forms.items():
                for lemma in [lemmas] if isinstance(lemmas, str) else lemmas:
                    if lemma not in self.forms[greek.fold(form)]:
                        self.forms[greek.fold(form)].append(lemma)
            self._add_names(g.names, override=True)
        # The speakers of the chapters' dialogues are names, unless a word explains them (Υπάλληλος).
        speakers = {who for _, ch in catalog.chapters.values() for who in ch.speakers()}
        for who in sorted(speakers):
            for part in greek.words(who):
                if (_is_capitalised(part) and len(part) > 2 and greek.fold(part) not in self.names
                        and not self._direct(part)[0]):
                    self._add_names({part: "person"}, override=False)
        # Forms of a name share its stem (Νίνας -> Νίνα, Κώστα -> Κώστας).
        self.name_stem: dict[str, str] = {}
        for folded, base in self.name_base.items():
            for st in _stems(base):
                self.name_stem.setdefault(st, folded)

    def _add_word(self, entry: Entry, forms: list[str], label_forms: bool = True) -> None:
        base = greek.fold(greek.strip_article(entry.el))
        for form in forms:
            for f in {form, greek.strip_article(form)}:  # η βαλίτσα is found as βαλίτσα too
                key = greek.fold(f)
                if key not in self.function:
                    # a listed form (ακούστε of ακούω) says what it is a form of
                    labelled = label_forms and key != base
                    self.function[key] = replace(entry, form_of=greek.strip_article(entry.el)) if labelled else entry

    def _add_names(self, names: dict[str, str], override: bool) -> None:
        # a value is "person" / "place", or the base name the key is a form of (Νάξο -> Νάξος)
        for name, value in names.items():
            if value in NAME_KINDS:
                base, kind = name, value
            else:
                base = value
                kind = names.get(value) if names.get(value) in NAME_KINDS else self.names.get(greek.fold(value), "person")
            key = greek.fold(name)
            if override or key not in self.names:
                self.names[key] = kind
                self.name_base[key] = base

    def _direct(self, word: str) -> tuple[list[Entry], str]:
        """Steps 1-3: the word itself is known."""
        for table, how, k in ((self.exact, "exact", greek.norm_answer(word)), (self.folded, "accents", greek.fold(word))):
            if table.get(k):
                return _dedupe(table[k]), how
        entry = self.function.get(greek.fold(word))
        if entry is not None:
            return [entry], "form" if entry.form_of else "exact"
        return [], "none"

    def known(self, word: str) -> bool:
        """The word itself has a meaning (an item, a function, instruction or glossary word)."""
        return bool(self._direct(word)[0])

    def _name(self, word: str, by_stem: bool) -> Entry | None:
        if not _is_capitalised(word):
            return None
        key = greek.fold(word)
        if key not in self.names:
            if not by_stem:
                return None
            key = next((self.name_stem[st] for st in sorted(_stems(word), key=len, reverse=True)
                        if st in self.name_stem), None)
            if key is None:
                return None
        kind, base = self.names[key], self.name_base[key]
        en, tr = NAME_MEANINGS[kind]
        return Entry(f"name/{base}", base, en, tr, "name")

    def find(self, word: str) -> tuple[list[Entry], str]:
        word = greek.to_monotonic(word.strip(" .,;:!?«»\"'()·"))
        entries, how = self._direct(word)
        if entries:
            return entries, how
        name = self._name(word, by_stem=False)
        if name:
            return [name], "name"
        hits = [replace(e, form_of=e.form_of or lemma) for lemma in self.forms.get(greek.fold(word), [])
                for e in self._direct(lemma)[0]]
        if hits:
            return _dedupe(hits), "form"
        name = self._name(word, by_stem=True)
        if name:
            return [name], "name"
        for st in sorted(_stems(word), key=len, reverse=True):
            hits += self.stem.get(st, [])
            if hits:
                break
        if hits:
            return _dedupe(hits), "stem"
        inside = self.inside.get(greek.fold(word), [])
        return _dedupe(inside), "phrase" if inside else "none"


def _is_capitalised(word: str) -> bool:
    return word[:1].isupper()


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
        "entries": [{"item_key": e.item_key, "el": e.el, "pos": e.pos, "say": e.say, "form_of": e.form_of,
                     "meaning": (e.tr if lang == "tr" and e.tr else None) or e.en or e.tr or "",
                     "meaning_lang": lang if getattr(e, lang, None) else ("en" if e.en else "tr")} for e in entries],
    }


def _rows(path: Path) -> list[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _names() -> dict[str, str]:
    """names.json: {"person": [...], "place": [...]}; a row is a name, or [name, its forms...]."""
    try:
        data = json.loads(NAMES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[str, str] = {}
    for kind in NAME_KINDS:
        for row in data.get(kind, []):
            name, *forms = [row] if isinstance(row, str) else row
            out[name] = kind
            out.update({f: name for f in forms})
    return out


def meaning_of(item: VocabItem, lang: str) -> str:
    return meaning(item, lang)
