"""Chapters: the lesson a learner reads before practising a stage (docs/SPEC.md §4.8, phase 5c).

A chapter belongs to one stage of one curriculum and lives in a pack at
`lessons/<stage id>.json`. It is made of sections in a fixed order (the coursebook's own lesson
flow: warm-up, text, comprehension, grammar, words, tips, try it), and each section of typed
blocks. Blocks rather than free Markdown, so the Greek can be linted, words linked to vocab items,
and a smaller model can fill the format in reliably.

The chapter also places items: the vocab items of its `words` blocks and the items of its `check`
blocks belong to its stage (curriculum.placed), after an explicit `stage:` tag.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

SECTION_ORDER = ("intro", "warmup", "text", "comprehension", "grammar", "words", "tips", "try")
REQUIRED_SECTIONS = ("intro", "text", "grammar", "words", "try")
WORDS_PER_MINUTE = 110      # explanation text in the learner's language
GREEK_WORDS_PER_MINUTE = 45  # slow reading of Greek at A1-A2, with the translation
MINUTES = {"A1": (6, 16), "A2": (8, 18), "B1": (10, 22)}  # the range validate accepts; LESSONS §4 gives the target
INLINE_GREEK = re.compile(r"\[\[([^\]]+)\]\]")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Bi(Strict):
    """Explanation text in both interface languages (both required)."""

    tr: str = Field(min_length=1)
    en: str = Field(min_length=1)


class Prose(Strict):
    """A paragraph. Inline: **bold**, *italic*, [[Greek]] (tappable, read aloud)."""

    type: Literal["prose"]
    tr: str = Field(min_length=1)
    en: str = Field(min_length=1)


class Line(Strict):
    who: str = Field(min_length=1)
    el: str = Field(min_length=1)
    tr: str = Field(min_length=1)
    en: str = Field(min_length=1)


class Dialogue(Strict):
    type: Literal["dialogue"]
    setting: Bi | None = None
    # A scene of the dialogue (docs/brand/CHARACTERS.md): a file in the pack's pictures/ folder.
    picture: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._-]+\.(webp|png|svg)$")
    picture_alt: Bi | None = None
    lines: list[Line] = Field(min_length=2)


class Table(Strict):
    """A grammar paradigm or a word table. A cell is Greek text (a string), or an explanation in
    both languages ({tr, en}): the reader shows the one in the UI language."""

    type: Literal["table"]
    caption: Bi | None = None
    head: list[str | Bi] = Field(min_length=1)
    rows: list[list[str | Bi]] = Field(min_length=1)
    note: Bi | None = None

    @model_validator(mode="after")
    def _shape(self) -> "Table":
        for i, row in enumerate(self.rows):
            if len(row) != len(self.head):
                raise ValueError(f"table row {i + 1} has {len(row)} cells; the header has {len(self.head)}")
        return self


class Example(Strict):
    el: str = Field(min_length=1)
    tr: str = Field(min_length=1)
    en: str = Field(min_length=1)
    note: Bi | None = None


class Examples(Strict):
    type: Literal["examples"]
    items: list[Example] = Field(min_length=1)


class Words(Strict):
    """Vocab items, by key (<pack>/<id>). They belong to this chapter's stage."""

    type: Literal["words"]
    items: list[str] = Field(min_length=1)


class Tip(Strict):
    """tr_bridge: what Turkish shares; mistake: a typical error; exam: how it appears in the exam."""

    type: Literal["tip"]
    kind: Literal["tr_bridge", "mistake", "exam"]
    tr: str = Field(min_length=1)
    en: str = Field(min_length=1)
    exam_task: str | None = None


class Check(Strict):
    """1-5 items (<pack>/<id>) answered inside the chapter. They do not count as exam evidence."""

    type: Literal["check"]
    items: list[str] = Field(min_length=1, max_length=5)


Block = Annotated[Union[Prose, Dialogue, Table, Examples, Words, Tip, Check], Field(discriminator="type")]


class Section(Strict):
    kind: Literal["intro", "warmup", "text", "comprehension", "grammar", "words", "tips", "try"]
    title: Bi | None = None
    blocks: list[Block] = Field(min_length=1)


class Chapter(Strict):
    id: str = Field(min_length=1)
    curriculum: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    level: Literal["A1", "A2", "B1"]
    title: Bi
    minutes: int = Field(ge=3, le=30)
    version: int = 1
    sections: list[Section] = Field(min_length=1)

    @model_validator(mode="after")
    def _order(self) -> "Chapter":
        kinds = [s.kind for s in self.sections]
        ranks = [SECTION_ORDER.index(k) for k in kinds]
        if ranks != sorted(ranks):
            raise ValueError(f"sections must follow the order {', '.join(SECTION_ORDER)}; found {', '.join(kinds)}")
        missing = [k for k in REQUIRED_SECTIONS if k not in kinds]
        if missing:
            raise ValueError(f"missing section(s): {', '.join(missing)}")
        for s in self.sections:
            if s.kind == "words" and not any(isinstance(b, Words) for b in s.blocks):
                raise ValueError("the words section needs a words block")
            if s.kind == "try" and not any(isinstance(b, Check) for b in s.blocks):
                raise ValueError("the try section needs a check block")
        return self

    # ---------- what the chapter refers to ----------

    def blocks(self):
        for i, s in enumerate(self.sections):
            for b in s.blocks:
                yield i, s, b

    def word_keys(self) -> list[str]:
        return _unique(k for _, _, b in self.blocks() if isinstance(b, Words) for k in b.items)

    def check_keys(self) -> list[str]:
        return _unique(k for _, _, b in self.blocks() if isinstance(b, Check) for k in b.items)

    def greek_lines(self) -> list[dict]:
        """Greek sentences with their translations: dialogue lines and examples, in order."""
        out = []
        for _, _, b in self.blocks():
            if isinstance(b, Dialogue):
                out += [{"el": ln.el, "tr": ln.tr, "en": ln.en, "who": ln.who} for ln in b.lines]
            elif isinstance(b, Examples):
                out += [{"el": e.el, "tr": e.tr, "en": e.en} for e in b.items]
        return out

    def inline_greek(self) -> list[str]:
        """The [[Greek]] spans of the explanations (glossed in place)."""
        out = []
        for _, _, b in self.blocks():
            if isinstance(b, (Prose, Tip)):
                out += INLINE_GREEK.findall(b.tr) + INLINE_GREEK.findall(b.en)
        return out

    def table_cells(self) -> list[str]:
        return [c for _, _, b in self.blocks() if isinstance(b, Table) for row in [b.head, *b.rows] for c in row
                if isinstance(c, str)]

    def speakers(self) -> list[str]:
        return [ln.who for _, _, b in self.blocks() if isinstance(b, Dialogue) for ln in b.lines]

    def estimated_minutes(self, lang: str = "tr") -> float:
        """Reading time from word counts: explanations in one language plus the Greek."""
        expl = greek = 0
        for _, s, b in self.blocks():
            if isinstance(b, (Prose, Tip)):
                expl += len(getattr(b, lang).split())
            elif isinstance(b, Dialogue):
                greek += sum(len(ln.el.split()) for ln in b.lines)
            elif isinstance(b, Examples):
                greek += sum(len(e.el.split()) for e in b.items)
            elif isinstance(b, Table):
                greek += sum(len(c.split()) for row in b.rows for c in row if isinstance(c, str))
                expl += sum(len(getattr(c, lang).split()) for row in b.rows for c in row if isinstance(c, Bi))
            elif isinstance(b, Check):
                greek += 25 * len(b.items)  # about half a minute per question
        return expl / WORDS_PER_MINUTE + greek / GREEK_WORDS_PER_MINUTE


def _unique(values) -> list[str]:
    seen: list[str] = []
    for v in values:
        if v not in seen:
            seen.append(v)
    return seen


_adapter = TypeAdapter(Chapter)


def parse(data) -> Chapter:
    return _adapter.validate_python(data)


def describe(error: ValidationError) -> str:
    parts = []
    for e in error.errors():
        where = ".".join(str(x) for x in e["loc"] if not str(x)[:1].isupper())
        msg = e["msg"].removeprefix("Value error, ")
        parts.append(f"{where}: {msg}" if where else msg)
    return "; ".join(parts[:6]) + (f" (and {len(parts) - 6} more)" if len(parts) > 6 else "")


def chapter_files(pack_dir: Path) -> list[Path]:
    """lessons/*.json, except the outline (lessons/outline.json is the writer's plan, not a chapter)."""
    folder = pack_dir / "lessons"
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob("*.json") if not p.stem.startswith("outline"))


def json_schema() -> dict:
    return _adapter.json_schema()


def read_raw(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))
