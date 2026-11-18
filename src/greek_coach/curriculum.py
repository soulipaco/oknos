"""Progression along a curriculum (docs/SPEC.md §5.4, phase 5b).

A curriculum is an ordered list of stages: a book's lessons, or the open course for a learner
without a book. Every item belongs to one stage. The daily session serves only items of stages
the learner has reached, the current stage first, so nothing hard comes before the simple
things it builds on.

Where an item belongs, in order of precedence:
  1. a topic tag `stage:<stage id>` (what the coach writes);
  1b. the words and check items of a stage's chapter (phase 5c: the chapter teaches them);
  2. the first stage whose `include` rules match it (unit tags, packs, items, verb lemma and
     tense, grammar tags, part of speech, type, level, topics);
  3. a level pool: an otherwise unplaced item of level A1 opens at the pool's `from_stage`;
  4. nowhere: it is never served in a daily session (it can still be practised on purpose).

A stage is done when MASTERY of its words and verb forms are learned (answered right the last
time they came up), or when the learner passed its stage check. Long-term memory is the review
schedule's job: learned items keep coming back at growing intervals in later stages, and an item
with an interval of SECURE_DAYS or more is shown as "secure". A review
stage is done when the stages it reviews are secure together. The current stage is the first
one not done. A stage with no words or forms of its own is done as soon as it is reached.

Teach before testing (phase 5c): a stage that has a chapter is "taught" once the learner has
finished reading it. Until then its new items stay out of daily sessions; reviews never wait.
A stage without a chapter counts as taught.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from greek_coach import coachfiles, db, paths, scheduler
from greek_coach.packs import Catalog, FormItem, Item, VocabItem

log = logging.getLogger("greek_coach.curriculum")

CURRICULA_DIR = paths.REPO_ROOT / "curricula"
SECURE_DAYS = 6
MASTERY = 0.8
CHECK_PASS = 0.8
CHECK_SIZE = 20
LEVEL_RANK = {"A1": 0, "A2": 1, "B1": 2}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Words(Strict):
    en: str
    tr: str | None = None
    el: str | None = None


class Rule(Strict):
    """Matches an item when every constraint given is met (an empty rule matches nothing)."""

    units: list[str] = []      # the item has topic "unit:<id>"
    packs: list[str] = []
    items: list[str] = []      # full item keys
    lemmas: list[str] = []     # form items: cue lemma
    tenses: list[str] = []     # form items: cue tense
    persons: list[str] = []    # form items: cue person
    grammar: list[str] = []    # form items: a grammar tag starting with one of these
    pos: list[str] = []        # vocab items: part of speech
    types: list[str] = []
    levels: list[str] = []
    topics: list[str] = []     # any of these topics

    def matches(self, key: str, pack_id: str, item) -> bool:
        if not any((self.units, self.packs, self.items, self.lemmas, self.tenses, self.persons,
                    self.grammar, self.pos, self.types, self.levels, self.topics)):
            return False
        if self.items and key not in self.items:
            return False
        if self.packs and pack_id not in self.packs:
            return False
        if self.units and not any(f"unit:{u}" in item.topics for u in self.units):
            return False
        if self.types and item.type not in self.types:
            return False
        if self.levels and item.level not in self.levels:
            return False
        if self.topics and not any(t in item.topics for t in self.topics):
            return False
        if self.pos and not (isinstance(item, VocabItem) and item.pos in self.pos):
            return False
        if self.lemmas or self.tenses or self.persons or self.grammar:
            if not isinstance(item, FormItem):
                return False
            cue = item.cue
            if self.lemmas and not (cue and cue.lemma in self.lemmas):
                return False
            if self.tenses and not (cue and cue.tense in self.tenses):
                return False
            if self.persons and not (cue and cue.person in self.persons):
                return False
            if self.grammar and not any(g.startswith(p) for g in item.grammar for p in self.grammar):
                return False
        return True


class Stage(Strict):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    title: Words
    theme: Words | None = None
    level: Literal["A1", "A2", "B1"]
    unit: str | None = None          # the book unit it follows, if any
    review_of: list[str] = []        # a review stage: the stages it consolidates
    include: list[Rule] = []
    can_do: list[Words] = []         # what the learner can do after it, in plain words


class Pool(Strict):
    level: Literal["A1", "A2", "B1"]
    from_stage: str


class Curriculum(Strict):
    id: str
    title: Words
    source: str
    for_pack: str | None = None      # a book curriculum applies when this (private) pack is loaded
    stages: list[Stage] = Field(min_length=1)
    pools: list[Pool] = []

    @model_validator(mode="after")
    def _consistent(self) -> "Curriculum":
        ids = [s.id for s in self.stages]
        if len(set(ids)) != len(ids):
            raise ValueError("two stages have the same id")
        for s in self.stages:
            bad = [r for r in s.review_of if r not in ids or ids.index(r) >= ids.index(s.id)]
            if bad:
                raise ValueError(f"stage {s.id} reviews {bad}, which are not earlier stages")
        for p in self.pools:
            if p.from_stage not in ids:
                raise ValueError(f"pool {p.level} opens at unknown stage {p.from_stage}")
        return self

    def index(self, stage_id: str) -> int:
        return next(i for i, s in enumerate(self.stages) if s.id == stage_id)


_adapter = TypeAdapter(Curriculum)


def load_file(path: Path) -> Curriculum:
    return _adapter.validate_python(json.loads(path.read_text(encoding="utf-8-sig")))


def available(catalog: Catalog) -> dict[str, Curriculum]:
    """Tracked curricula in curricula/, and a book's own in its pack folder (curriculum.json)."""
    files = sorted(CURRICULA_DIR.glob("*.json")) if CURRICULA_DIR.is_dir() else []
    files += [p.path / "curriculum.json" for p in catalog.packs if (p.path / "curriculum.json").is_file()]
    out: dict[str, Curriculum] = {}
    for f in files:
        try:
            c = load_file(f)
        except (json.JSONDecodeError, ValidationError, OSError) as e:
            log.warning("curriculum %s skipped: %s", f, e.__class__.__name__)
            continue
        out[c.id] = c
    return out


def _profile() -> dict:
    try:
        data = coachfiles.read_json(paths.profile_path())
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, ValueError, OSError):
        return {}


def active(catalog: Catalog) -> Curriculum | None:
    """profile.curriculum if it names one; else a book's curriculum whose pack is loaded; else the open one."""
    found = available(catalog)
    wanted = _profile().get("curriculum")
    if wanted == "off":  # an advanced learner who wants every pack open; the level still limits it
        return None
    if wanted in found:
        return found[wanted]
    loaded = {p.id for p in catalog.packs}
    book = [c for c in found.values() if c.for_pack and c.for_pack in loaded]
    if book:
        return book[0]
    open_ = [c for c in found.values() if not c.for_pack]
    return open_[0] if open_ else None


# ---------- assignment ----------

_cache: dict[tuple, tuple[dict[str, int | None], set[str]]] = {}


def assignment(cur: Curriculum, catalog: Catalog) -> dict[str, int | None]:
    """item_key -> stage index (None: not placed; never in a daily session)."""
    return placed(cur, catalog)[0]


def placed(cur: Curriculum, catalog: Catalog) -> tuple[dict[str, int | None], set[str]]:
    """(item_key -> stage index, the keys placed only by a level pool). Pool items are extra
    material once their stage is reached; they never count towards a stage being done."""
    key = (cur.id, id(catalog), len(catalog.items))
    if key in _cache:
        return _cache[key]
    pooled: set[str] = set()
    ids = {s.id: i for i, s in enumerate(cur.stages)}
    pools = {p.level: ids[p.from_stage] for p in cur.pools}
    by_chapter: dict[str, int] = {}
    for i, s in enumerate(cur.stages):
        ch = catalog.chapter(cur.id, s.id)
        if ch is not None:
            for k in ch.word_keys() + ch.check_keys():
                by_chapter.setdefault(k, i)
    out: dict[str, int | None] = {}
    for k, (pack, item) in catalog.items.items():
        idx = None
        for t in item.topics:
            if t.startswith("stage:") and t[6:] in ids:
                idx = ids[t[6:]]
                break
        if idx is None:
            idx = by_chapter.get(k)
        if idx is None:
            for i, s in enumerate(cur.stages):
                if any(r.matches(k, pack.id, item) for r in s.include):
                    idx = i
                    break
        if idx is None:
            idx = pools.get(item.level)
            if idx is not None:
                pooled.add(k)
        out[k] = idx
    if len(_cache) > 8:
        _cache.clear()
    _cache[key] = (out, pooled)
    return out, pooled


def core(item: Item) -> bool:
    """Words and verb forms: what a stage's mastery is measured on."""
    return isinstance(item, (VocabItem, FormItem))


@dataclass
class Progress:
    curriculum: Curriculum
    current: int
    stages: list[dict] = field(default_factory=list)
    assigned: dict[str, int | None] = field(default_factory=dict)
    pooled: set[str] = field(default_factory=set)
    taught: set[int] = field(default_factory=set)   # stage indexes whose chapter is read, or that have none

    def unlocked(self, key: str) -> bool:
        idx = self.assigned.get(key)
        return idx is not None and idx <= self.current

    def stage_of(self, key: str) -> int | None:
        return self.assigned.get(key)

    def introducible(self, key: str) -> bool:
        """May a daily session show this item for the first time? Its stage is reached and taught."""
        idx = self.assigned.get(key)
        return idx is not None and idx <= self.current and idx in self.taught


def chapter_reads(conn: sqlite3.Connection, cur_id: str) -> dict[str, sqlite3.Row]:
    try:
        return {r["stage"]: r for r in conn.execute("SELECT * FROM chapter_reads WHERE curriculum=?", (cur_id,))}
    except sqlite3.OperationalError:
        return {}


def mark_read(conn: sqlite3.Connection, cur_id: str, stage: str, version: int, section: int | None = None,
              finished: bool = False) -> dict:
    """Record that a chapter was opened, a section of it seen, or the whole of it finished."""
    row = conn.execute("SELECT * FROM chapter_reads WHERE curriculum=? AND stage=?", (cur_id, stage)).fetchone()
    seen = json.loads(row["sections_json"]) if row else []
    if section is not None and section not in seen:
        seen.append(section)
    with conn:
        if row is None:
            conn.execute("INSERT INTO chapter_reads(curriculum, stage, chapter_version, opened_at, finished_at, sections_json) "
                         "VALUES (?, ?, ?, ?, ?, ?)", (cur_id, stage, version, db.now(), db.now() if finished else None,
                                                       json.dumps(seen)))
        else:
            conn.execute("UPDATE chapter_reads SET sections_json=?, chapter_version=?, "
                         "finished_at=COALESCE(finished_at, ?) WHERE curriculum=? AND stage=?",
                         (json.dumps(seen), version, db.now() if finished else None, cur_id, stage))
    row = conn.execute("SELECT * FROM chapter_reads WHERE curriculum=? AND stage=?", (cur_id, stage)).fetchone()
    return {"stage": stage, "opened_at": row["opened_at"], "finished_at": row["finished_at"], "sections": seen}


def passed_checks(conn: sqlite3.Connection, cur_id: str) -> set[str]:
    try:
        return {r[0] for r in conn.execute("SELECT stage FROM stage_checks WHERE curriculum=? AND passed=1", (cur_id,))}
    except sqlite3.OperationalError:
        return set()


def progress(conn: sqlite3.Connection, catalog: Catalog, cur: Curriculum | None = None,
             record: bool = False) -> Progress | None:
    """Where the learner is. With record=True (the session builder), a stage that has just been
    mastered is written down, so it stays done: a later mistake brings its items back as reviews,
    it does not send the learner back a lesson."""
    cur = cur or active(catalog)
    if cur is None:
        return None
    assigned, pooled = placed(cur, catalog)
    states = scheduler.all_states(conn)
    seen = {r[0] for r in conn.execute("SELECT DISTINCT item_key FROM attempts")}
    passed = passed_checks(conn, cur.id)
    reads = chapter_reads(conn, cur.id)
    taught: set[int] = set()
    per: list[dict] = [{"core": [], "other": 0, "pool": 0} for _ in cur.stages]
    for k, idx in assigned.items():
        if idx is None:
            continue
        if k in pooled:
            per[idx]["pool"] += 1
            continue
        item = catalog.items[k][1]
        if item.status != "ok":
            continue
        if core(item):
            per[idx]["core"].append(k)
        else:
            per[idx]["other"] += 1
    stages = []
    current = None
    for i, s in enumerate(cur.stages):
        keys = list(per[i]["core"])
        if s.review_of:
            for r in s.review_of:
                keys += per[cur.index(r)]["core"]
        learned = sum(1 for k in keys if k in states and states[k].reps >= 1)
        secure = sum(1 for k in keys if k in states and states[k].interval_days >= SECURE_DAYS)
        tried = sum(1 for k in keys if k in seen)
        share = learned / len(keys) if keys else 1.0
        mastered_now = bool(keys) and share >= MASTERY
        done = s.id in passed or mastered_now or not keys
        if record and mastered_now and s.id not in passed and current is None:
            try:
                with conn:
                    conn.execute("INSERT INTO stage_checks(curriculum, stage, session_id, started_at, finished_at, score, passed) "
                                 "VALUES (?, ?, NULL, ?, ?, ?, 1)", (cur.id, s.id, db.now(), db.now(), round(share, 3)))
                passed.add(s.id)
            except sqlite3.OperationalError:
                pass
        ch = catalog.chapter(cur.id, s.id)
        read = reads.get(s.id)
        # a passed "test me" check also counts: the learner showed they know it without reading
        if ch is None or (read is not None and read["finished_at"]) or s.id in passed:
            taught.add(i)
        chapter = None if ch is None else {
            "minutes": ch.minutes, "title": ch.title.model_dump(), "read": bool(read and read["finished_at"]),
            "opened": read is not None, "sections": len(ch.sections),
            "sections_seen": len(json.loads(read["sections_json"])) if read else 0}
        stages.append({"id": s.id, "order": i, "chapter": chapter, "title": s.title.model_dump(), "theme": s.theme.model_dump() if s.theme else None,
                       "level": s.level, "unit": s.unit, "review": bool(s.review_of),
                       "words": sum(1 for k in per[i]["core"] if isinstance(catalog.items[k][1], VocabItem)),
                       "forms": sum(1 for k in per[i]["core"] if isinstance(catalog.items[k][1], FormItem)),
                       "tasks": per[i]["other"], "extra_from_pool": per[i]["pool"], "core": len(keys), "learned": learned, "secure": secure, "tried": tried,
                       "share": round(share, 3), "passed_check": s.id in passed, "mastered": done,
                       "can_do": [c.model_dump() for c in s.can_do]})
        if current is None and not done:
            current = i
    if current is None:
        current = len(cur.stages) - 1
    for st in stages:
        st["state"] = "done" if st["order"] < current else "current" if st["order"] == current else "locked"
    # a stage reached but not yet mastered stays "current"; earlier stages may be mastered ahead of time
    return Progress(curriculum=cur, current=current, stages=stages, assigned=assigned, pooled=pooled, taught=taught)


def summary(conn: sqlite3.Connection, catalog: Catalog) -> dict | None:
    p = progress(conn, catalog)
    if p is None:
        return None
    cur = p.stages[p.current]
    return {"curriculum": p.curriculum.id, "title": p.curriculum.title.model_dump(), "current": cur,
            "stages_done": p.current, "stages_total": len(p.stages), "stages": p.stages,
            "secure_days": SECURE_DAYS, "mastery": MASTERY}


def next_action(p: "Progress | None", today_state: str, due_reviews: int) -> dict:
    """The one thing the home screen offers first (phase 5c).

    read: the current stage has a chapter not read yet (reading comes before anything new);
    daily: otherwise, the daily session (reviews and the current stage's new items).
    `then` is the quieter second option."""
    if p is not None:
        st = p.stages[p.current]
        if st["chapter"] and not st["chapter"]["read"]:
            return {"kind": "read", "stage": st["id"], "title": st["title"], "minutes": st["chapter"]["minutes"],
                    "opened": st["chapter"]["opened"],
                    "then": "daily" if due_reviews and today_state != "done" else None}
        if st["chapter"]:
            return {"kind": "daily", "stage": st["id"], "title": st["title"], "share": st["share"],
                    "then": "practise_stage"}
    return {"kind": "daily", "stage": None, "then": None}


# ---------- stage checks: "I know this lesson, test me" ----------

def start_check(conn: sqlite3.Connection, catalog: Catalog, stage_id: str, ui_lang: str) -> dict:
    """A practice session of up to CHECK_SIZE items of one stage. Passing marks the stage done."""
    from greek_coach import session

    p = progress(conn, catalog)
    if p is None or stage_id not in [s.id for s in p.curriculum.stages]:
        raise ValueError(f"unknown stage {stage_id}")
    idx = p.curriculum.index(stage_id)
    if idx > p.current + 1:
        raise ValueError("a check is open for the current stage and the one after it")
    keys = [k for k, i in p.assigned.items() if i == idx and k not in p.pooled and catalog.items[k][1].status == "ok"
            and catalog.items[k][1].type not in ("write", "speak")]
    keys.sort(key=lambda k: (not core(catalog.items[k][1]), k))
    if not keys:
        raise ValueError("this stage has nothing to check")
    step = max(1, len(keys) // CHECK_SIZE)
    picked = keys[::step][:CHECK_SIZE]
    out = session.practice(conn, catalog, ui_lang, picked)
    with conn:
        conn.execute("UPDATE sessions SET kind='check' WHERE id=?", (out["session_id"],))
        conn.execute("INSERT INTO stage_checks(curriculum, stage, session_id, started_at) VALUES (?, ?, ?, ?)",
                     (p.curriculum.id, stage_id, out["session_id"], db.now()))
    out["kind"] = "check"
    out["stage"] = stage_id
    return out


def finish_check(conn: sqlite3.Connection, session_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM stage_checks WHERE session_id=?", (session_id,)).fetchone()
    if row is None:
        return None
    planned = json.loads(conn.execute("SELECT plan_json FROM sessions WHERE id=?", (session_id,)).fetchone()[0] or "[]")
    scores = [r["score"] or 0.0 for r in conn.execute(
        "SELECT score FROM attempts WHERE session_id=? AND correct IS NOT NULL", (session_id,))]
    score = sum(scores) / len(planned) if planned else 0.0  # an unanswered item counts as wrong
    passed = len(scores) == len(planned) and score >= CHECK_PASS
    with conn:
        conn.execute("UPDATE stage_checks SET finished_at=?, score=?, passed=? WHERE session_id=?",
                     (db.now(), round(score, 3), int(passed), session_id))
    return {"stage": row["stage"], "score": round(score, 3), "passed": passed, "needed": CHECK_PASS,
            "answered": len(scores), "of": len(planned)}


def json_schema() -> dict:
    return _adapter.json_schema()
