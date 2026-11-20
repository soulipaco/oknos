"""Content packs: schema, loading and validation (docs/SPEC.md §4).

A pack is a folder with a pack.json manifest and items/*.json files, each a JSON
array of items. Invalid items are skipped and reported, never fatal.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from greek_coach import chapters as chapters_mod
from greek_coach import db, paths

log = logging.getLogger("greek_coach.packs")

OPEN_LICENCES = {"CC-BY-SA-4.0", "CC-BY-4.0", "CC0-1.0", "MIT"}
SUPPORTED_TYPES = {"vocab", "form", "mcq", "true_false", "match", "gap_bank", "categorise", "table_fill",
                   "write", "speak"}
# Types the spec defines that later phases build. Items of these types are skipped quietly.
LATER_TYPES: set[str] = set()
GAP_RE = re.compile(r"\{(\w+)\}")

Skill = Literal["vocab", "grammar", "history", "listening", "reading", "writing", "speaking"]
Level = Literal["A1", "A2", "B1"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Text(Strict):
    """A piece of text with optional translations."""

    el: str | None = None
    en: str | None = None
    tr: str | None = None


class Example(Strict):
    el: str
    en: str | None = None
    tr: str | None = None


class Stimulus(Strict):
    text: str | None = None
    audio: str | None = None
    tts: str | None = None
    plays: int | None = None
    # Play only this part of the audio file (seconds), so one recording of a whole exam paper
    # can serve its separate parts.
    start: float | None = Field(default=None, ge=0)
    end: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _range(self) -> "Stimulus":
        if self.start is not None and self.end is not None and self.end <= self.start:
            raise ValueError("stimulus.end must be after stimulus.start")
        if (self.start is not None or self.end is not None) and not self.audio:
            raise ValueError("stimulus.start/end need an audio file")
        return self


class BaseItem(Strict):
    id: str = Field(min_length=1)
    skill: Skill
    level: Level
    exam_task: str | None = None
    topics: list[str] = []
    rubric: Text | None = None
    # The question or situation in the learner's language (tr/en), always shown above the Greek.
    # For a task whose point is "what do you say here?"; the Greek still carries everything else.
    ask: Text | None = None
    stimulus: Stimulus | None = None
    explain: Text | None = None
    source: dict[str, Any] | None = None
    status: Literal["ok", "needs_review"] = "ok"


class VocabItem(BaseItem):
    type: Literal["vocab"]
    el: str = Field(min_length=1)
    lemma: str | None = None
    pos: str | None = None
    gender: Literal["m", "f", "n"] | None = None
    en: str | None = None
    tr: str | None = None
    example: Example | None = None
    # What the browser voice reads instead of `el`: a letter card says the letter's name and an
    # example word ("σίγμα, σούπα"), because a voice reading "Σ σ ς" names three letters.
    say: str | None = None

    @model_validator(mode="after")
    def _needs_a_meaning(self) -> "VocabItem":
        if not (self.en or self.tr):
            raise ValueError("a vocab item needs at least an English (en) or Turkish (tr) meaning")
        return self


class McqItem(BaseItem):
    type: Literal["mcq"]
    prompt: Text
    options: list[str] = Field(min_length=2, max_length=6)
    answer: int

    @model_validator(mode="after")
    def _answer_in_range(self) -> "McqItem":
        if not 0 <= self.answer < len(self.options):
            raise ValueError(f"answer {self.answer} is not one of the option positions 0..{len(self.options) - 1}")
        if len(set(self.options)) != len(self.options):
            raise ValueError("two options have the same text")
        return self


class Statement(Strict):
    el: str
    en: str | None = None
    tr: str | None = None
    answer: bool


class TrueFalseItem(BaseItem):
    type: Literal["true_false"]
    statements: list[Statement] = Field(min_length=1)


class Cue(Strict):
    lemma: str | None = None
    person: Literal["1sg", "2sg", "3sg", "1pl", "2pl", "3pl"] | None = None
    tense: str | None = None
    case: str | None = None
    number: Literal["sg", "pl"] | None = None


class FormItem(BaseItem):
    """Produce one word form in context, typed or chosen (SPEC §4.4)."""

    type: Literal["form"]
    text: str = Field(min_length=1)
    cue: Cue | None = None
    answer: dict[str, list[str]]
    options: dict[str, list[str]] | None = None
    grammar: list[str] = []
    translation: Text | None = None

    @model_validator(mode="after")
    def _gaps_match(self) -> "FormItem":
        gaps = GAP_RE.findall(self.text)
        if not gaps:
            raise ValueError("the text needs at least one gap such as {1}")
        if sorted(gaps) != sorted(self.answer):
            raise ValueError(f"the gaps in the text {sorted(gaps)} do not match the answer keys {sorted(self.answer)}")
        if any(not forms for forms in self.answer.values()):
            raise ValueError("every gap needs at least one accepted form")
        for gap, opts in (self.options or {}).items():
            if gap not in self.answer:
                raise ValueError(f"options are given for gap {gap}, which is not in the text")
            if not set(self.answer[gap]) & set(opts):
                raise ValueError(f"none of the options for gap {gap} is an accepted answer")
            if len(set(opts)) != len(opts):
                raise ValueError(f"two options for gap {gap} have the same text")
        return self


class MatchItem(BaseItem):
    type: Literal["match"]
    prompt: Text | None = None
    left: list[str] = Field(min_length=2)
    right: list[str] = Field(min_length=2)
    answer: list[int]

    @model_validator(mode="after")
    def _answer_shape(self) -> "MatchItem":
        if len(self.answer) != len(self.left):
            raise ValueError(f"answer needs one right-hand position for each of the {len(self.left)} left items")
        if any(not 0 <= a < len(self.right) for a in self.answer):
            raise ValueError(f"every answer must be a right-hand position 0..{len(self.right) - 1}")
        if len(set(self.answer)) != len(self.answer):
            raise ValueError("two left items point to the same right item")
        if len(set(self.right)) != len(self.right) or len(set(self.left)) != len(self.left):
            raise ValueError("two entries on the same side have the same text")
        return self


class GapBankItem(BaseItem):
    type: Literal["gap_bank"]
    text: str = Field(min_length=1)
    bank: list[str] = Field(min_length=2)
    answer: dict[str, str]
    translation: Text | None = None

    @model_validator(mode="after")
    def _gaps_match(self) -> "GapBankItem":
        gaps = GAP_RE.findall(self.text)
        if not gaps or sorted(gaps) != sorted(self.answer):
            raise ValueError(f"the gaps in the text {sorted(gaps)} do not match the answer keys {sorted(self.answer)}")
        if len(set(self.bank)) != len(self.bank):
            raise ValueError("the word bank has the same word twice")
        missing = [w for w in self.answer.values() if w not in self.bank]
        if missing:
            raise ValueError(f"these answers are not in the word bank: {missing}")
        if len(set(self.answer.values())) != len(self.answer):
            raise ValueError("two gaps have the same answer; each bank word may be used once")
        return self


class CategoriseItem(BaseItem):
    type: Literal["categorise"]
    prompt: Text | None = None
    categories: list[str] = Field(min_length=2)
    items: list[str] = Field(min_length=2)
    answer: list[int]

    @model_validator(mode="after")
    def _answer_shape(self) -> "CategoriseItem":
        if len(self.answer) != len(self.items):
            raise ValueError(f"answer needs one category position for each of the {len(self.items)} items")
        if any(not 0 <= a < len(self.categories) for a in self.answer):
            raise ValueError(f"every answer must be a category position 0..{len(self.categories) - 1}")
        return self


class TableFillItem(BaseItem):
    """Complete the cells of a table from a text or recording (SPEC §4.4). Note-taking is a
    one-column table. Each cell lists its accepted answers; a null cell is given (shown filled)."""

    type: Literal["table_fill"]
    prompt: Text | None = None
    columns: list[str] = Field(min_length=1)
    rows: list[str] = Field(min_length=1)
    answer: list[list[list[str] | str | None]]
    given: list[list[str | None]] | None = None   # text shown in cells that are not asked

    @model_validator(mode="after")
    def _shape(self) -> "TableFillItem":
        if len(self.answer) != len(self.rows):
            raise ValueError(f"answer needs one row for each of the {len(self.rows)} rows")
        for i, row in enumerate(self.answer):
            if len(row) != len(self.columns):
                raise ValueError(f"answer row {i + 1} needs one cell for each of the {len(self.columns)} columns")
            for cell in row:
                if isinstance(cell, list) and (not cell or any(not str(c).strip() for c in cell)):
                    raise ValueError(f"answer row {i + 1}: a cell needs at least one non-empty accepted answer")
                if isinstance(cell, str) and not cell.strip():
                    raise ValueError(f"answer row {i + 1}: an empty cell answer; use null for a given cell")
        if not self.cells():
            raise ValueError("the table asks for nothing: every cell is null")
        if self.given is not None:
            if len(self.given) != len(self.rows) or any(len(r) != len(self.columns) for r in self.given):
                raise ValueError("given must have the same shape as the table")
        return self

    def cells(self) -> list[tuple[int, int, list[str]]]:
        """The asked cells in reading order: (row, column, accepted answers)."""
        out = []
        for i, row in enumerate(self.answer):
            for j, cell in enumerate(row):
                if cell is None:
                    continue
                out.append((i, j, [cell] if isinstance(cell, str) else list(cell)))
        return out


class WriteItem(BaseItem):
    """A writing prompt in exam format. The app saves the text; the coach marks it (SPEC §4.4)."""

    type: Literal["write"]
    prompt: Text
    words: list[int] = Field(min_length=2, max_length=2)
    must_include: list[str | Text] = []

    @model_validator(mode="after")
    def _shape(self) -> "WriteItem":
        if not self.prompt.el:
            raise ValueError("a writing prompt needs the Greek task text in prompt.el")
        lo, hi = self.words
        if not 0 < lo <= hi:
            raise ValueError("words must be [minimum, maximum] with 0 < minimum <= maximum")
        return self


class SpeakItem(BaseItem):
    """A speaking card: record, play back, compare with the model answer. Never scored."""

    type: Literal["speak"]
    prompt: Text
    seconds: int = Field(default=60, ge=10, le=600)
    model: Text | None = None
    useful: list[str] = []

    @model_validator(mode="after")
    def _shape(self) -> "SpeakItem":
        if not self.prompt.el:
            raise ValueError("a speaking card needs the Greek task text in prompt.el")
        return self


ITEM_CLASSES = (VocabItem, FormItem, McqItem, TrueFalseItem, MatchItem, GapBankItem, CategoriseItem,
                TableFillItem, WriteItem, SpeakItem)
# Exam-format tasks the app checks itself (table_fill is typed, but checked like form).
SELECTION_TASKS = (McqItem, TrueFalseItem, MatchItem, GapBankItem, CategoriseItem, TableFillItem)
OPEN_TASKS = (WriteItem, SpeakItem)
TASK_TYPES = SELECTION_TASKS + OPEN_TASKS
Item = Annotated[
    Union[VocabItem, FormItem, McqItem, TrueFalseItem, MatchItem, GapBankItem, CategoriseItem, TableFillItem,
          WriteItem, SpeakItem],
    Field(discriminator="type"),
]
_item_adapter: TypeAdapter[Item] = TypeAdapter(Item)


class Manifest(Strict):
    id: str = Field(min_length=1)
    title: Text
    version: int
    levels: list[Level]
    visibility: Literal["open", "private", "generated"]
    licence: str
    source: str
    exam_blueprints: list[str] = []
    for_ui_lang: list[Literal["en", "tr"]] | None = None


class Unit(Strict):
    """One lesson of a course outline (a private pack's units.json)."""

    id: str
    order: int
    title: str
    theme: str | None = None
    pages: list[int | None] | None = None
    is_review: bool = False
    review_range: list[str] = []
    functions: list[str] = []
    grammar: list[str] = []
    vocabulary: list[str] = []


_units_adapter = TypeAdapter(list[Unit])


class GlossWord(Strict):
    """A word the lookup explains without it being a practice item (same shape as function_words.json)."""

    el: str = Field(min_length=1)
    forms: list[str] = []
    pos: str | None = None
    en: str | None = None
    tr: str | None = None

    @model_validator(mode="after")
    def _needs_a_meaning(self) -> "GlossWord":
        if not (self.en or self.tr):
            raise ValueError(f"the glossary word '{self.el}' needs an English (en) or Turkish (tr) meaning")
        return self


class Glossary(Strict):
    """A pack's glossary.json: what tapping a word finds when no item has it (phase 5d).

    forms: an inflected form -> its lemma(s), which the lookup then explains ("form of ...").
    words: meanings for words that are not practice items.
    names: a name -> "person" or "place", or the base name it is a form of (Νάξο -> Νάξος).
    leave: words left unexplained on purpose, with the reason (validate lists them).
    """

    source: str | None = None
    licence: str | None = None
    note: str | None = None
    forms: dict[str, str | list[str]] = {}
    words: list[GlossWord] = []
    names: dict[str, str] = {}
    leave: dict[str, str] = {}


@dataclass
class Pack:
    manifest: Manifest
    path: Path
    items: dict[str, Item] = field(default_factory=dict)
    units: list[Unit] = field(default_factory=list)
    chapters: dict[str, "chapters_mod.Chapter"] = field(default_factory=dict)  # stage id -> chapter
    glossary: Glossary | None = None
    item_files: dict[str, str] = field(default_factory=dict)  # item id -> the items file it came from

    @property
    def id(self) -> str:
        return self.manifest.id


@dataclass
class Catalog:
    packs: list[Pack] = field(default_factory=list)
    items: dict[str, tuple[Pack, Item]] = field(default_factory=dict)  # item_key -> (pack, item)
    problems: list[str] = field(default_factory=list)
    skipped_later_types: int = 0
    # (curriculum id, stage id) -> (pack, chapter); a later content root (the coach's) replaces an earlier one
    chapters: dict[tuple[str, str], tuple[Pack, "chapters_mod.Chapter"]] = field(default_factory=dict)

    def chapter(self, curriculum: str, stage: str) -> "chapters_mod.Chapter | None":
        entry = self.chapters.get((curriculum, stage))
        return entry[1] if entry else None


def _nfc(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_nfc(v) for v in value]
    if isinstance(value, dict):
        return {k: _nfc(v) for k, v in value.items()}
    return value


def _describe(error: ValidationError) -> str:
    parts = []
    for e in error.errors():
        where = ".".join(str(x) for x in e["loc"] if not str(x).startswith(tuple(c.__name__ for c in ITEM_CLASSES)) and str(x) not in {c.__name__ for c in ITEM_CLASSES})
        msg = e["msg"].removeprefix("Value error, ")
        parts.append(f"{where}: {msg}" if where else msg)
    return "; ".join(parts)


def _read_json(path: Path) -> Any:
    # utf-8-sig tolerates a BOM, which some Windows editors add.
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_pack(pack_dir: Path, expected_visibility: str | None = None) -> tuple[Pack | None, list[str], int]:
    """Load one pack folder. Returns (pack or None, problems, count of later-phase items skipped)."""
    problems: list[str] = []
    later = 0
    name = pack_dir.name
    manifest_file = pack_dir / "pack.json"
    try:
        manifest = Manifest.model_validate(_nfc(_read_json(manifest_file)))
    except FileNotFoundError:
        return None, [f"{name}: there is no pack.json"], 0
    except json.JSONDecodeError as e:
        return None, [f"{name}/pack.json is not valid JSON (line {e.lineno}): {e.msg}"], 0
    except ValidationError as e:
        return None, [f"{name}/pack.json: {_describe(e)}"], 0

    if expected_visibility and manifest.visibility != expected_visibility:
        problems.append(
            f"{name}: pack.json says visibility '{manifest.visibility}' but the pack is in the "
            f"'{expected_visibility}' folder; the pack was not loaded"
        )
        return None, problems, 0
    if manifest.visibility == "open" and manifest.licence not in OPEN_LICENCES:
        problems.append(f"{name}: open packs need an open licence, not '{manifest.licence}'; the pack was not loaded")
        return None, problems, 0

    pack = Pack(manifest=manifest, path=pack_dir)
    units_file = pack_dir / "units.json"
    if units_file.is_file():
        try:
            pack.units = _units_adapter.validate_python(_nfc(_read_json(units_file)))
        except (json.JSONDecodeError, ValidationError) as e:
            problems.append(f"{name}/units.json could not be read ({e.__class__.__name__}); the course outline was skipped")
    item_files = sorted((pack_dir / "items").glob("*.json"))
    chapter_files = chapters_mod.chapter_files(pack_dir)
    if not item_files and not chapter_files:
        problems.append(f"{name}: there are no item files in items/")
    for item_file in item_files:
        rel = f"{name}/items/{item_file.name}"
        try:
            raw = _read_json(item_file)
        except json.JSONDecodeError as e:
            problems.append(f"{rel} is not valid JSON (line {e.lineno}): {e.msg}; the whole file was skipped")
            continue
        if not isinstance(raw, list):
            problems.append(f"{rel} must contain a JSON array of items; the whole file was skipped")
            continue
        for n, entry in enumerate(raw, start=1):
            label = f"{rel} item {n}" + (f" ('{entry.get('id')}')" if isinstance(entry, dict) and entry.get("id") else "")
            if not isinstance(entry, dict):
                problems.append(f"{label}: is not an object; skipped")
                continue
            kind = entry.get("type")
            if kind in LATER_TYPES:
                later += 1
                continue
            if kind not in SUPPORTED_TYPES:
                problems.append(f"{label}: unknown type '{kind}'; skipped")
                continue
            try:
                item = _item_adapter.validate_python(_nfc(entry))
            except ValidationError as e:
                problems.append(f"{label}: {_describe(e)}; skipped")
                continue
            if item.id in pack.items:
                problems.append(f"{label}: the id '{item.id}' is used twice in this pack; the second one was skipped")
                continue
            pack.items[item.id] = item
            pack.item_files[item.id] = item_file.name
    glossary_file = pack_dir / "glossary.json"
    if glossary_file.is_file():
        try:
            pack.glossary = Glossary.model_validate(_nfc(_read_json(glossary_file)))
        except json.JSONDecodeError as e:
            problems.append(f"{name}/glossary.json is not valid JSON (line {e.lineno}): {e.msg}; the glossary was skipped")
        except ValidationError as e:
            problems.append(f"{name}/glossary.json: {_describe(e)}; the glossary was skipped")
    for chapter_file in chapter_files:
        rel = f"{name}/lessons/{chapter_file.name}"
        try:
            chapter = chapters_mod.parse(_nfc(_read_json(chapter_file)))
        except json.JSONDecodeError as e:
            problems.append(f"{rel} is not valid JSON (line {e.lineno}): {e.msg}; the chapter was skipped")
            continue
        except ValidationError as e:
            problems.append(f"{rel}: {chapters_mod.describe(e)}; the chapter was skipped")
            continue
        if chapter.stage != chapter_file.stem:
            problems.append(f"{rel}: the file name must be the stage id ('{chapter.stage}.json'); the chapter was skipped")
            continue
        pack.chapters[chapter.stage] = chapter
    return pack, problems, later


def chapter_ref_problems(catalog: "Catalog") -> list[str]:
    """Words and check items a chapter names that no loaded pack has. They are left out when the
    chapter is shown; `validate` reports them as problems."""
    out = []
    for (cur, stage), (pack, ch) in catalog.chapters.items():
        for key in ch.word_keys():
            entry = catalog.items.get(key)
            if entry is None:
                out.append(f"{pack.id}/lessons/{stage}.json: the word '{key}' is not a loaded item")
            elif entry[1].type != "vocab":
                out.append(f"{pack.id}/lessons/{stage}.json: '{key}' in a words block is a {entry[1].type} item, not a vocab item")
            elif entry[1].status != "ok":
                out.append(f"{pack.id}/lessons/{stage}.json: the word '{key}' is marked needs_review and is never shown")
        for key in ch.check_keys():
            entry = catalog.items.get(key)
            if entry is None:
                out.append(f"{pack.id}/lessons/{stage}.json: the check item '{key}' is not a loaded item")
            elif entry[1].type in ("write", "speak"):
                out.append(f"{pack.id}/lessons/{stage}.json: '{key}' is a {entry[1].type} item; checks must be checkable by the app")
    return out


def load_all() -> Catalog:
    catalog = Catalog()
    seen_ids: set[str] = set()
    for visibility, root in paths.content_roots():
        if not root.is_dir():
            continue
        for pack_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            pack, problems, later = load_pack(pack_dir, visibility)
            catalog.problems.extend(problems)
            catalog.skipped_later_types += later
            if pack is None:
                continue
            if pack.id in seen_ids:
                catalog.problems.append(f"{pack_dir}: the pack id '{pack.id}' is already used by another pack; skipped")
                continue
            seen_ids.add(pack.id)
            catalog.packs.append(pack)
            for item_id, item in pack.items.items():
                catalog.items[f"{pack.id}/{item_id}"] = (pack, item)
            for chapter in pack.chapters.values():
                catalog.chapters[(chapter.curriculum, chapter.stage)] = (pack, chapter)
    catalog.problems.extend(chapter_ref_problems(catalog))
    for problem in catalog.problems:
        log.warning("content: %s", problem)
    return catalog


def content_hash(item: Item) -> str:
    data = json.dumps(item.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def sync_items(conn: sqlite3.Connection, catalog: Catalog) -> None:
    """Record every loaded item in the items table; mark vanished ones retired."""
    ts = db.now()
    with conn:
        for key, (pack, item) in catalog.items.items():
            conn.execute(
                """
                INSERT INTO items(item_key, pack_id, type, skill, exam_task, level, content_hash, first_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_key) DO UPDATE SET
                    type=excluded.type, skill=excluded.skill, exam_task=excluded.exam_task,
                    level=excluded.level, content_hash=excluded.content_hash, retired_at=NULL
                """,
                (key, pack.id, item.type, item.skill, item.exam_task, item.level, content_hash(item), ts),
            )
        known = set(catalog.items)
        for row in conn.execute("SELECT item_key FROM items WHERE retired_at IS NULL").fetchall():
            if row["item_key"] not in known:
                conn.execute("UPDATE items SET retired_at=? WHERE item_key=?", (ts, row["item_key"]))


def servable(catalog: Catalog, ui_lang: str) -> list[tuple[str, Pack, Item]]:
    out = []
    for key, (pack, item) in catalog.items.items():
        if item.status != "ok":
            continue
        langs = pack.manifest.for_ui_lang
        if langs and ui_lang not in langs:
            continue
        out.append((key, pack, item))
    return out


def json_schemas() -> dict[str, dict]:
    """JSON Schemas for agents writing content (schemas/, SPEC §11)."""
    return {
        "pack": Manifest.model_json_schema(),
        "item": TypeAdapter(Item).json_schema(),
        "items-file": TypeAdapter(list[Item]).json_schema(),
        "units": _units_adapter.json_schema(),
        "chapter": chapters_mod.json_schema(),
        "glossary": Glossary.model_json_schema(),
    }
