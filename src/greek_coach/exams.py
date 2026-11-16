"""Exam blueprints: tracked facts about a public exam (docs/SPEC.md §1, §4.5).

A blueprint is `exams/<id>.json`: units with points and minutes, the tasks in each unit
with the item types that train them, the official pass rule, exam technique, source links
and the pages the `watch` skill checks. Adding an exam needs no code change.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from greek_coach import paths

log = logging.getLogger("greek_coach.exams")

EXAMS_DIR = paths.REPO_ROOT / "exams"
NOT_BLUEPRINTS = {"watch-sources.json"}
LEVELS = ("A1", "A2", "B1")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Text(Strict):
    el: str | None = None
    en: str
    tr: str | None = None


class Lines(Strict):
    en: list[str]
    tr: list[str] = []


class TaskSpec(Strict):
    id: str
    title: Text
    types: list[str] = Field(min_length=1)       # item types that train this task (SPEC §1.5)
    questions: int | None = None                 # scored questions in the real paper
    points: float = Field(gt=0)
    points_verified: bool = True                 # false where the official split is not published
    words: list[int] | None = None               # writing: [min, max]


class UnitSpec(Strict):
    id: str
    skill: Literal["history", "listening", "reading", "writing", "speaking"]
    title: Text
    points: float = Field(gt=0)
    minutes: int = Field(gt=0)
    marked_by: Literal["app", "coach"]
    tasks: list[TaskSpec] = Field(min_length=1)
    technique: Lines
    note: Text | None = None

    @model_validator(mode="after")
    def _points_add_up(self) -> "UnitSpec":
        total = round(sum(t.points for t in self.tasks), 4)
        if abs(total - self.points) > 1e-6:
            raise ValueError(f"unit {self.id}: task points add up to {total}, not {self.points}")
        return self


class PassRule(Strict):
    min_total: float | None = None      # the whole exam must reach this many points
    unit_min_share: float = Field(gt=0, le=1)  # a unit "passes" at this share of its points
    units_needed: int = Field(ge=1)     # how many units must pass
    text: Text


class Source(Strict):
    url: str
    what: str
    checked: str


class WatchSpec(Strict):
    what: str
    what_tr: str | None = None
    urls: list[str] = Field(min_length=1)
    look_for: str


class Match(Strict):
    grammar: list[str] = []      # prefixes of form items' grammar tags
    topics: list[str] = []
    exam_tasks: list[str] = []


class Beyond(Strict):
    """Something the higher level adds over the lower one (B1 over A2), for coverage and the plan."""

    id: str
    area: Literal["grammar", "linking", "vocabulary", "text", "task_type", "spelling"]
    title: Text
    match: Match = Match()


class Blueprint(Strict):
    id: str
    title: Text
    short: str                              # "B1", "A2+"
    level: Literal["A1", "A2", "B1"]
    task_prefix: str                        # exam_task ids start with "<task_prefix>."
    checked_at: str
    total_points: float
    hours_estimate: list[int] = Field(min_length=2, max_length=2)  # ΚΕΓ teaching hours, cumulative
    pass_rule: PassRule
    units: list[UnitSpec] = Field(min_length=1)
    sessions_note: Text | None = None
    sources: list[Source] = []
    watch: WatchSpec
    beyond_a2: list[Beyond] = []

    @model_validator(mode="after")
    def _consistent(self) -> "Blueprint":
        total = round(sum(u.points for u in self.units), 4)
        if abs(total - self.total_points) > 1e-6:
            raise ValueError(f"units add up to {total} points, not total_points {self.total_points}")
        if self.pass_rule.units_needed > len(self.units):
            raise ValueError("pass_rule.units_needed is more than the number of units")
        seen = set()
        for u in self.units:
            for t in u.tasks:
                if not t.id.startswith(f"{self.task_prefix}.{u.id}."):
                    raise ValueError(f"task id {t.id} must start with '{self.task_prefix}.{u.id}.'")
                if t.id in seen:
                    raise ValueError(f"task id {t.id} is used twice")
                seen.add(t.id)
        return self

    # ---------- lookups ----------

    def unit(self, unit_id: str) -> UnitSpec | None:
        return next((u for u in self.units if u.id == unit_id), None)

    def task(self, task_id: str) -> tuple[UnitSpec, TaskSpec] | None:
        for u in self.units:
            for t in u.tasks:
                if t.id == task_id:
                    return u, t
        return None

    def task_ids(self) -> set[str]:
        return {t.id for u in self.units for t in u.tasks}

    def pass_line(self, unit: UnitSpec) -> float:
        return round(unit.points * self.pass_rule.unit_min_share, 4)


def passes(bp: Blueprint, unit_points: dict[str, float]) -> bool:
    """Apply the exam's real pass rule to points per unit (every unit must be given)."""
    rule = bp.pass_rule
    passed = sum(1 for u in bp.units if unit_points[u.id] >= bp.pass_line(u) - 1e-9)
    if passed < rule.units_needed:
        return False
    if rule.min_total is not None and sum(unit_points[u.id] for u in bp.units) < rule.min_total - 1e-9:
        return False
    return True


_adapter = TypeAdapter(Blueprint)


def blueprint_files(folder: Path | None = None) -> list[Path]:
    folder = folder or EXAMS_DIR
    return sorted(p for p in folder.glob("*.json") if p.name not in NOT_BLUEPRINTS)


def load_file(path: Path) -> Blueprint:
    return _adapter.validate_python(json.loads(path.read_text(encoding="utf-8-sig")))


@lru_cache(maxsize=4)
def _load_cached(folder: str, stamp: tuple) -> dict[str, Blueprint]:
    out: dict[str, Blueprint] = {}
    for path in blueprint_files(Path(folder)):
        try:
            bp = load_file(path)
        except (json.JSONDecodeError, ValidationError) as e:
            log.warning("blueprint %s skipped: %s", path.name, e)
            continue
        out[bp.id] = bp
    return out


def load_blueprints(folder: Path | None = None) -> dict[str, Blueprint]:
    """Every valid blueprint by id (a broken file is logged and skipped)."""
    folder = folder or EXAMS_DIR
    stamp = tuple((p.name, p.stat().st_mtime_ns) for p in blueprint_files(folder))
    return _load_cached(str(folder), stamp)


def all_task_ids() -> dict[str, tuple[Blueprint, UnitSpec, TaskSpec]]:
    out = {}
    for bp in load_blueprints().values():
        for u in bp.units:
            for t in u.tasks:
                out[t.id] = (bp, u, t)
    return out


def blueprint_for_task(task_id: str | None) -> Blueprint | None:
    if not task_id:
        return None
    entry = all_task_ids().get(task_id)
    return entry[0] if entry else None


def json_schema() -> dict:
    return _adapter.json_schema()
