"""The mapping file that tells the importer where things are in someone's material.

A mapping describes the *shape* of the source (file names relative to the source folder,
field names, level names). It never contains the material itself, so a mapping can be
tracked in git even when the material is private. See docs/IMPORTING.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from pydantic import BaseModel, ConfigDict, Field

from greek_coach.packs import Level, Text


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PackInfo(Strict):
    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: Text
    levels: List[Level] = ["A1", "A2"]
    licence: str = "private, commercial source"
    source: str = "Imported from the learner's own material"


class VocabularySource(Strict):
    file: str
    # Dotted paths to the lists of entries inside the file ("" = the file is the list).
    lists: List[str] = [""]
    # Our field -> dotted path in an entry. Required: greek, and en or tr.
    fields: dict[str, str]
    # Source level names -> A1/A2/B1. Unknown or missing levels use default_level.
    levels: dict[str, Level] = {}
    default_level: Level = "A1"
    # Source part-of-speech codes -> our names (noun, verb, adj, adv, phrase, ...).
    pos: dict[str, str] = {}


class PagesSource(Strict):
    """Running text of the book, used to link words to the units they appear in."""

    file: str  # .json list or .jsonl
    list: str = ""
    fields: dict[str, str]  # unit, text, page (optional)


class UnitsSource(Strict):
    file: str
    list: str = ""
    fields: dict[str, str]  # id, order, title, theme, page_start, page_end, is_review, review_range, functions, grammar, vocabulary


class RawSource(Strict):
    """Exercises or other material kept as source prompts in raw/, never served."""

    name: str = Field(pattern=r"^[a-z0-9_-]+$")
    file: str
    list: str = ""
    fields: dict[str, str]  # id, text, unit, page, doc, marker, type, skill, kind, flags
    # Rules for the kind field: first match wins. {"field": "...", "equals": value, "kind": "..."}
    kind_rules: List[dict[str, Any]] = []
    default_kind: str = "exercise"
    min_greek_letters: int = 25
    min_greek_share: float = 0.5


class AudioSource(Strict):
    dir: str
    # A JSON object {file name: transcript} or a list of {file, text} objects.
    transcripts: str | None = None
    transcript_fields: dict[str, str] = {"file": "file", "text": "text"}


class Mapping(Strict):
    pack: PackInfo
    vocabulary: VocabularySource | None = None
    pages: PagesSource | None = None
    units: UnitsSource | None = None
    raw: List[RawSource] = []
    audio: AudioSource | None = None


def load(path: Path) -> Mapping:
    return Mapping.model_validate(json.loads(path.read_text(encoding="utf-8-sig")))


def get(entry: Any, dotted: str | None, default: Any = None) -> Any:
    """Read a dotted path such as 'source.page' from a nested dict."""
    if not dotted:
        return entry if dotted == "" else default
    value = entry
    for part in dotted.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return default
    return value
