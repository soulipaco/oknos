"""Enrichment from the English Wiktionary's Greek entries, as extracted by kaikki.org (CC BY-SA).

The full dump (~211 MB) is downloaded once, with the learner's OK, into .cache/oknos/.
`build_index` streams it and keeps only what the app needs: the gender of every noun and the
conjugation of the verbs we ask for. The small index is what later runs read.
"""

from __future__ import annotations

import json
from pathlib import Path

from oknos import greek, paths

KAIKKI_URL = "https://kaikki.org/dictionary/Greek/kaikki.org-dictionary-Greek.jsonl"
CACHE_DIR = paths.CACHE_DIR
DUMP = CACHE_DIR / "kaikki.org-dictionary-Greek.jsonl"
INDEX = CACHE_DIR / "kaikki-el-index.json"
INDEX_VERSION = 3


def _genders(entry: dict) -> list[str]:
    out: list[str] = []
    for t in entry.get("head_templates", []):
        args = t.get("args", {})
        for key in ("1", "g", "g2", "g3") if t.get("name") == "el-noun" else ("g", "g2", "g3"):
            value = (args.get(key) or "").strip()
            if value and value[0] in "mfn" and value not in out:
                out.append(value)
    return out


def build_index(dump: Path = DUMP, out: Path = INDEX) -> dict:
    """Stream the dump once; keep noun genders, verb forms and short English glosses."""
    nouns: dict[str, list[str]] = {}
    verbs: dict[str, list[list]] = {}
    glosses: dict[str, str] = {}
    with dump.open(encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            word = greek.nfc(entry.get("word", ""))
            pos = entry.get("pos")
            if not word:
                continue
            if pos in ("noun", "name"):
                for g in _genders(entry):
                    nouns.setdefault(word, [])
                    if g not in nouns[word]:
                        nouns[word].append(g)
            elif pos == "verb":
                forms = [
                    [greek.nfc(fm["form"]), sorted(fm.get("tags", []))]
                    for fm in entry.get("forms", [])
                    if fm.get("source") == "conjugation" and fm.get("form") and greek.has_greek(fm["form"])
                ]
                if forms and word not in verbs:
                    verbs[word] = forms
            for sense in entry.get("senses", [])[:1]:
                gl = (sense.get("glosses") or [None])[0]
                if gl and f"{word}|{pos}" not in glosses:
                    glosses[f"{word}|{pos}"] = gl[:120]
    index = {"version": INDEX_VERSION, "source": KAIKKI_URL, "licence": "CC-BY-SA-4.0 (Wiktionary)",
             "nouns": nouns, "verbs": verbs, "glosses": glosses}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return index


def load_index() -> dict | None:
    """The index, built from the dump on first use. None if the dump was never downloaded."""
    if INDEX.is_file():
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        if index.get("version") == INDEX_VERSION:
            return index
    if DUMP.is_file():
        return build_index()
    return None


def noun_gender(index: dict, word: str) -> tuple[str | None, str | None]:
    """(gender for the item, article to show). Common-gender nouns get 'ο/η' and no single gender."""
    genders = index["nouns"].get(word) or index["nouns"].get(greek.nfc(word.lower()))
    if not genders:
        return None, None
    gloss = index["glosses"].get(f"{word}|noun", "")
    plural = any(g.endswith("-p") for g in genders) or "plural of" in gloss
    letters = []
    for g in genders:
        if g[0] not in letters:
            letters.append(g[0])
    if plural:
        return (letters[0] if len(letters) == 1 else None), "οι" if letters[0] in "mf" else "τα"
    if len(letters) == 1:
        return letters[0], greek.ARTICLE_FOR_GENDER[letters[0]]
    if set(letters) == {"m", "f"}:
        return None, "ο/η"
    return None, None


PERSONS = {"1sg": ("first-person", "singular"), "2sg": ("second-person", "singular"), "3sg": ("third-person", "singular"),
           "1pl": ("first-person", "plural"), "2pl": ("second-person", "plural"), "3pl": ("third-person", "plural")}


def verb_forms(index: dict, lemma: str, person: str, tense: str) -> set[str]:
    """Forms Wiktionary gives for a verb in present / aorist / future (active indicative).

    The future is θα + the dependent (perfective) form, which is how Wiktionary tabulates it.
    """
    table = index["verbs"].get(lemma)
    if not table and lemma.endswith("ώ"):  # αγαπώ is listed under αγαπάω, μιλώ under μιλάω
        table = index["verbs"].get(lemma[:-1] + "άω")
    if not table and lemma.endswith("άω"):
        table = index["verbs"].get(lemma[:-2] + "ώ")
    if not table:
        return set()
    deponent = lemma.endswith("μαι")
    p, n = PERSONS[person]
    want = {"present": {"present", "imperfective", "indicative"},
            "aorist": {"past", "perfective", "indicative"},
            "future": {"dependent", "perfective"},
            "imperfect": {"imperfect", "imperfective", "indicative"}}[tense]
    out = set()
    for form, tags in table:
        tags = set(tags)
        if form.startswith("-") or " " in form:
            continue
        if ("passive" in tags) != deponent:
            continue
        if not (p in tags and n in tags and want <= tags):
            continue
        if tense in ("present", "future") and tags & {"past", "imperfect"}:
            continue
        out.add(f"θα {form}" if tense == "future" else form)
    return out


FORMS_INDEX = CACHE_DIR / "kaikki-el-forms.json"
FORMS_INDEX_VERSION = 1
_SKIP_FORM_TAGS = {"romanization", "table-tags", "inflection-template", "class", "transliteration"}


def build_forms_index(dump: Path = DUMP, out: Path = FORMS_INDEX) -> dict:
    """Stream the dump once; map every inflected form (folded) to its lemmas and their part of speech.

    From two places: non-lemma entries that say what they are a form of (απαντήσεις: form of
    απάντηση), and the declension and conjugation tables of the lemmas themselves.
    """
    lemma_of: dict[str, list[list[str]]] = {}

    def add(form: str, lemma: str, pos: str) -> None:
        key = greek.fold(form)
        if greek.fold(lemma) == key:
            return
        rows = lemma_of.setdefault(key, [])
        if [lemma, pos] not in rows:
            rows.append([lemma, pos])

    with dump.open(encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            word = greek.nfc(entry.get("word", ""))
            pos = entry.get("pos") or ""
            if not word or not greek.has_greek(word):
                continue
            for sense in entry.get("senses", []):
                for ref in sense.get("form_of", []) + sense.get("alt_of", []):
                    lemma = greek.nfc(ref.get("word") or "")
                    if lemma and greek.has_greek(lemma) and " " not in lemma:
                        add(word, lemma, pos)
            for fm in entry.get("forms", []):
                form = greek.nfc(fm.get("form") or "")
                if (not form or " " in form or "-" in form or not greek.has_greek(form)
                        or set(fm.get("tags", [])) & _SKIP_FORM_TAGS):
                    continue
                add(form, word, pos)
    index = {"version": FORMS_INDEX_VERSION, "source": KAIKKI_URL, "licence": "CC-BY-SA-4.0 (Wiktionary)",
             "lemma_of": lemma_of}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return index


def load_forms_index() -> dict | None:
    """The form -> lemma index, built from the dump on first use. None if the dump was never downloaded."""
    if FORMS_INDEX.is_file():
        index = json.loads(FORMS_INDEX.read_text(encoding="utf-8"))
        if index.get("version") == FORMS_INDEX_VERSION:
            return index
    if DUMP.is_file():
        return build_forms_index()
    return None


def lemmas_of(forms_index: dict, word: str) -> list[tuple[str, str]]:
    """(lemma, part of speech) pairs Wiktionary gives for a form; a lemma that is the word itself is left out."""
    return [(lemma, pos) for lemma, pos in forms_index["lemma_of"].get(greek.fold(word), [])
            if greek.fold(lemma) != greek.fold(word)]
