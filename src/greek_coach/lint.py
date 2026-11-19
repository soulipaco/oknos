"""Checks on the Greek inside a pack, for `greek-coach validate` (docs/COACHING.md).

A learner cannot tell when generated Greek is wrong, so the mechanical errors a writer (human or
model) makes are caught here:

problems (must be fixed):
  - Latin letters inside a Greek word (homoglyphs: Latin "o" or "a" in "καλo")
  - polytonic characters (the app is monotonic)
  - text that is not NFC
  - "σ" at the end of a word, or "ς" inside one

notes (look again, may be fine):
  - a word of two or more syllables with no accent (capitals, as in notices, are exempt)
  - for generated packs: Greek words found in no loaded pack and not in the dictionary index,
    which are either misspellings or words above the learner's level
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from greek_coach import greek

_POLYTONIC = re.compile(r"[ἀ-῿]")
_GREEK = r"Ͱ-Ͽἀ-῿"
_MIXED = re.compile(rf"\b(?=[\w]*[{_GREEK}])(?=[\w]*[A-Za-z])[\w]+\b")
_SIGMA_END = re.compile(rf"[{_GREEK}]σ(?![{_GREEK}\w])")
_FINAL_INSIDE = re.compile(rf"ς(?=[{_GREEK}])")
# Fields that are identifiers or tags, never shown as Greek text.
_SKIP_KEYS = {"id", "type", "skill", "level", "exam_task", "topics", "grammar", "status", "source",
              "audio", "pos", "gender", "person", "tense", "case", "number"}


def _strings(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _strings(v, f"{path}[{i}]")
    elif isinstance(value, dict):
        for k, v in value.items():
            if k in _SKIP_KEYS:
                continue
            yield from _strings(v, f"{path}.{k}" if path else str(k))


FRAGMENT_POS = {"letter", "digraph", "syllable"}  # reading cards: parts of words, not words


def check_text(text: str, fragment: bool = False) -> tuple[list[str], list[str]]:
    """(problems, notes) for one string. A fragment (a letter pair such as τσ) may end in σ."""
    problems: list[str] = []
    notes: list[str] = []
    if not greek.has_greek(text):
        return problems, notes
    if unicodedata.normalize("NFC", text) != text:
        problems.append("is not NFC-normalised")
    if _POLYTONIC.search(text):
        problems.append(f"has polytonic characters ({''.join(sorted(set(_POLYTONIC.findall(text))))}); use monotonic")
    mixed = [w for w in _MIXED.findall(text) if not w.isascii()]
    if mixed:
        problems.append(f"mixes Latin and Greek letters in {', '.join(sorted(set(mixed))[:5])} (look-alike letters)")
    if _SIGMA_END.search(text) and not fragment:
        bad = [w for w in greek.words(text) if w.endswith("σ") and len(w) > 1]
        problems.append(f"ends a word with σ instead of ς: {', '.join(sorted(set(bad))[:5])}")
    if _FINAL_INSIDE.search(text):
        bad = [w for w in greek.words(text) if "ς" in w[:-1]]
        problems.append(f"has ς inside a word: {', '.join(sorted(set(bad))[:5])}")
    unaccented = [w for w in greek.words(text)
                  if greek.syllables(w) >= 2 and not greek.is_accented(w) and not w.isupper()
                  and greek.nfc(w).lower() not in _UNACCENTED_OK]
    if unaccented:
        notes.append(f"no accent on {', '.join(sorted(set(unaccented))[:5])}")
    return problems, notes


# Two-syllable words that are written without an accent in monotonic spelling.
_UNACCENTED_OK = {"μου", "σου", "του", "της", "μας", "σας", "τους", "τις", "των", "στο", "στη", "στην", "στον",
                  "στα", "στις", "στους", "στου", "στης", "για", "μια", "δυο", "και", "θα", "να", "τα", "τον", "την"}


_TURKISH = re.compile(r"[ığşİŞĞ]|\b(ve|bir|bu|için|değil|ile|ama|çok)\b")
_ENGLISH = re.compile(r"\b(the|and|you|is|are|of|to|with|this|not)\b", re.I)


def language_swaps(value: Any, path: str = "") -> Iterable[str]:
    """Paths where `tr` holds English and `en` holds Turkish: a generator script that swapped them."""
    if isinstance(value, dict):
        t, e = value.get("tr"), value.get("en")
        if isinstance(t, str) and isinstance(e, str) and _ENGLISH.search(t) and not _TURKISH.search(t) and _TURKISH.search(e):
            yield path or "(top)"
        for k, v in value.items():
            yield from language_swaps(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from language_swaps(v, f"{path}[{i}]")


def lint_items(raw_items: list[Any], label: str) -> tuple[list[str], list[str]]:
    """Lint the raw JSON items of one file (before NFC normalisation, so non-NFC text is caught)."""
    problems: list[str] = []
    notes: list[str] = []
    for n, entry in enumerate(raw_items, start=1):
        if not isinstance(entry, dict):
            continue
        name = f"{label} item {n}" + (f" ('{entry.get('id')}')" if entry.get("id") else "")
        fragment_card = entry.get("pos") in FRAGMENT_POS
        problems += [f"{name} {path}: the tr text looks English and the en text Turkish (swapped?)"
                     for path in language_swaps(entry)]
        for path, text in _strings(entry):
            p, nt = check_text(text, fragment=fragment_card and path == "el")
            problems += [f"{name} {path}: {x}" for x in p]
            notes += [f"{name} {path}: {x}" for x in nt]
    return problems, notes


def lint_pack(pack_dir: Path) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    notes: list[str] = []
    for item_file in sorted((pack_dir / "items").glob("*.json")):
        try:
            raw = json.loads(item_file.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            continue  # the loader already reports this
        if isinstance(raw, list):
            p, n = lint_items(raw, f"{pack_dir.name}/items/{item_file.name}")
            problems += p
            notes += n
    return problems, notes


# ---------- words nobody else uses ----------

def known_words(catalog, exclude_pack: str | None = None) -> set[str]:
    """Folded Greek words from every loaded pack except one, plus the dictionary index if cached."""
    out: set[str] = set()
    for pack in catalog.packs:
        if pack.id == exclude_pack:
            continue
        for item in pack.items.values():
            for _, text in _strings(item.model_dump(mode="json")):
                out.update(greek.fold(w) for w in greek.words(text))
    try:
        from greek_coach.importer import enrich

        if enrich.INDEX.is_file():
            index = json.loads(enrich.INDEX.read_text(encoding="utf-8"))
            out.update(greek.fold(w) for w in index.get("nouns", {}))
            for lemma, forms in index.get("verbs", {}).items():
                out.add(greek.fold(lemma))
                out.update(greek.fold(f[0]) for f in forms)
            out.update(greek.fold(k.split("|", 1)[0]) for k in index.get("glosses", {}))
    except (OSError, ValueError):
        pass
    return out


def unfamiliar_words(pack, known: set[str]) -> list[str]:
    """Greek words in a pack that no other content uses. Inflected forms of known words are
    accepted when their first letters match a known word (a rough stem test)."""
    stems = {w[:5] for w in known if len(w) >= 6}
    seen: dict[str, str] = {}
    for item in pack.items.values():
        for _, text in _strings(item.model_dump(mode="json")):
            for w in greek.words(text):
                f = greek.fold(w)
                if f in known or len(f) < 3 or w.isupper():
                    continue
                if len(f) >= 6 and f[:5] in stems:
                    continue
                seen.setdefault(f, w)
    return sorted(seen.values())


# ---------- exam-task tags (coverage, SPEC §1.5) ----------

TASK_ITEM_TYPES = {"mcq", "true_false", "match", "gap_bank", "categorise", "table_fill", "write", "speak"}
LEVEL_RANK = {"A1": 0, "A2": 1, "B1": 2}


def lint_tags(pack) -> tuple[list[str], list[str]]:
    """An exam_task must name a blueprint task that this item's type and skill can train.

    Problems: an unknown task id, a type the task does not use, a skill that is not the
    task's unit. Notes: an item below the exam's level (it is practice, not evidence for
    readiness), and, in coach packs, task-type items with no exam_task at all.
    """
    from greek_coach import exams

    tasks = exams.all_task_ids()
    problems: list[str] = []
    notes: list[str] = []
    untagged = []
    for item_id, item in pack.items.items():
        tag = item.exam_task
        if not tag:
            if item.type in TASK_ITEM_TYPES and item.skill not in ("vocab", "grammar"):
                untagged.append(item_id)
            continue
        entry = tasks.get(tag)
        if entry is None:
            known = ", ".join(sorted(t for t in tasks if t.split(".")[:2] == tag.split(".")[:2])) or "see exams/*.json"
            problems.append(f"{item_id}: exam_task '{tag}' is not a task in any blueprint (this unit has: {known})")
            continue
        bp, unit, task = entry
        if item.type not in task.types:
            problems.append(f"{item_id}: exam_task '{tag}' is trained by {task.types}, not by a '{item.type}' item")
        if item.skill != unit.skill:
            problems.append(f"{item_id}: exam_task '{tag}' is a {unit.skill} task, but the item's skill is '{item.skill}'")
        if LEVEL_RANK.get(item.level, 0) < LEVEL_RANK[bp.level]:
            notes.append(f"{item_id}: level {item.level} is below {bp.short}; it trains {tag} but does not count as readiness evidence")
    if untagged and pack.manifest.visibility == "generated":
        notes.append("task items without exam_task (they count only as general practice): " + ", ".join(untagged[:15]))
    return problems, notes


# ---------- chapters (phase 5c) ----------

# Words a chapter may use without teaching them first: articles, pronouns, the commonest
# particles and prepositions. Everything else should be a word of this or an earlier stage.
FUNCTION_WORDS = {greek.fold(w) for w in (
    "ο", "η", "το", "οι", "τα", "τον", "την", "τη", "του", "της", "των", "τους", "τις", "ένας", "μια", "μία", "ένα",
    "και", "ή", "αλλά", "να", "θα", "δεν", "μη", "μην", "με", "σε", "στο", "στη", "στην", "στον", "στα", "στις",
    "στους", "από", "για", "μου", "σου", "μας", "σας", "εγώ", "εσύ", "αυτός", "αυτή", "αυτό", "εμείς", "εσείς",
    "αυτοί", "αυτές", "αυτά", "ναι", "όχι", "τι", "πού", "πώς", "που", "πως", "κι")}
CHAPTER_SKIP_KEYS = {"type", "kind", "exam_task", "items", "id", "curriculum", "stage", "level"}


def _chapter_greek(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    """The Greek-bearing strings of a raw chapter: el fields, table cells, speakers, and the [[..]]
    spans inside the explanations (the explanation text itself is Turkish or English)."""
    from greek_coach.chapters import INLINE_GREEK

    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _chapter_greek(v, f"{path}[{i}]")
    elif isinstance(value, dict):
        for k, v in value.items():
            if k in ("tr", "en") and isinstance(v, str):
                for span in INLINE_GREEK.findall(v):
                    yield f"{path}.{k}[[..]]", span
                continue
            if k in CHAPTER_SKIP_KEYS:
                continue
            yield from _chapter_greek(v, f"{path}.{k}" if path else str(k))


def lint_chapter_files(pack_dir: Path) -> tuple[list[str], list[str]]:
    """The Greek lint (problems and notes) over a pack's lessons/*.json, before NFC normalisation."""
    from greek_coach.chapters import chapter_files

    problems: list[str] = []
    notes: list[str] = []
    for f in chapter_files(pack_dir):
        try:
            raw = json.loads(f.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            continue  # the loader already reports this
        label = f"{pack_dir.name}/lessons/{f.name}"
        problems += [f"{label} {path}: the tr text looks English and the en text Turkish (swapped?)"
                     for path in language_swaps(raw)]
        for path, text in _chapter_greek(raw):
            # a letter pair alone in a table cell (τσ, μπ) is a fragment, not a word ending in σ
            p, nt = check_text(text, fragment=len(text.strip()) <= 3 and " " not in text.strip())
            problems += [f"{label} {path}: {x}" for x in p]
            notes += [f"{label} {path}: {x}" for x in nt]
    return problems, notes


def _is_name(word: str) -> bool:
    """A capitalised word that is not all capitals is usually a name (Νίκος, Αθήνα) or starts a sentence."""
    return word[:1].isupper() and not word.isupper()


def chapter_checks(pack, catalog) -> tuple[list[str], list[str]]:
    """Problems: the chapter's curriculum or stage does not exist, or it names items nobody has.
    Notes: reading time outside the level's range, and Greek words in its dialogues and examples
    that neither this nor an earlier stage teaches (nor the chapter's own words or [[glosses]])."""
    from greek_coach import curriculum as curriculum_mod
    from greek_coach.chapters import MINUTES
    from greek_coach.packs import VocabItem, chapter_ref_problems

    problems: list[str] = []
    notes: list[str] = []
    if not pack.chapters:
        return problems, notes
    curricula = curriculum_mod.available(catalog)
    problems += [p for p in chapter_ref_problems(catalog) if p.startswith(f"{pack.id}/")]
    for stage_id, ch in pack.chapters.items():
        label = f"{pack.id}/lessons/{stage_id}.json"
        cur = curricula.get(ch.curriculum)
        if cur is None:
            problems.append(f"{label}: the curriculum '{ch.curriculum}' does not exist (known: {', '.join(sorted(curricula))})")
            continue
        if stage_id not in [s.id for s in cur.stages]:
            problems.append(f"{label}: the curriculum '{cur.id}' has no stage '{stage_id}'")
            continue
        from greek_coach import exams
        from greek_coach.chapters import Tip

        task_ids = exams.all_task_ids()
        for _, _, b in ch.blocks():
            if isinstance(b, Tip) and b.exam_task and b.exam_task not in task_ids:
                problems.append(f"{label}: the tip's exam_task '{b.exam_task}' is not a task in any blueprint")
        lo, hi = MINUTES[ch.level]
        for lang in ("tr", "en"):
            est = ch.estimated_minutes(lang)
            if not lo <= est <= hi:
                notes.append(f"{label}: reading time in {lang} is about {est:.0f} min; {ch.level} chapters take {lo}-{hi}")
        if abs(ch.estimated_minutes("tr") - ch.minutes) > 4:
            notes.append(f"{label}: 'minutes' says {ch.minutes}, the text reads in about {ch.estimated_minutes('tr'):.0f}")
        # what may be used: words placed at this or an earlier stage, and the glosses of those chapters
        idx = cur.index(stage_id)
        placed = curriculum_mod.assignment(cur, catalog)
        allowed: set[str] = set(FUNCTION_WORDS)
        for k, i in placed.items():
            if i is not None and i <= idx:
                item = catalog.items[k][1]
                if isinstance(item, VocabItem):
                    allowed.update(greek.fold(w) for w in greek.words(item.el + " " + (item.lemma or "")))
        for s in cur.stages[: idx + 1]:
            other = catalog.chapter(cur.id, s.id)
            if other is not None:
                # glossed spans, the forms a table teaches, and the speakers' names count as taught
                taught = other.inline_greek() + other.table_cells() + other.speakers()
                for span in taught:
                    allowed.update(greek.fold(w) for w in greek.words(span))
        stems = {w[:4] for w in allowed if len(w) >= 5}
        untaught: list[str] = []
        for line in ch.greek_lines():
            for sentence in re.split(r"[.!;?…»«]+", line["el"]):
                for n, w in enumerate(greek.words(sentence)):
                    f = greek.fold(w)
                    # a capital inside a sentence is a name; at its start it is just a capital
                    if f in allowed or len(f) < 3 or w.isupper() or (n > 0 and _is_name(w)):
                        continue
                    if len(f) >= 5 and f[:4] in stems:
                        continue
                    if w not in untaught:
                        untaught.append(w)
        if untaught:
            notes.append(f"{label}: Greek words no stage up to this one teaches (add them to a words block, gloss "
                         f"them with [[..]], or check the level): {', '.join(untaught[:30])}")
    return problems, notes
