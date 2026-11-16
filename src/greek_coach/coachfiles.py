"""Files the coach writes for the app, and how the app takes them in (docs/COACHING.md, SPEC §5).

The coach never writes the database. It writes these files; the app reads them leniently (a
broken file is logged and skipped, never fatal) and updates its own tables:

  coach/message.json        the note on the home screen
  coach/watch.json          exam and course dates
  coach/resolved-flags.json the coach's verdict on flagged items -> flags.resolved_at
  coach/schedule.json       written by `greek-coach schedule`; what should run and when
  coach/runs.log            one line per scheduled run, written by `greek-coach run`
  feedback/<id>.json        marking of submission <id> -> submissions.status = 'marked'
  profile.json              the learner profile
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, field_validator, model_validator

from greek_coach import db, paths

log = logging.getLogger("greek_coach.coachfiles")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MESSAGE_MAX_AGE_DAYS = 14


def coach_dir() -> Path:
    return paths.learner_dir() / "coach"


def feedback_dir() -> Path:
    return paths.learner_dir() / "feedback"


def recordings_dir() -> Path:
    return paths.learner_dir() / "recordings"


def inbox_dir() -> Path:
    return paths.learner_dir() / "inbox"


def runs_log() -> Path:
    return coach_dir() / "runs.log"


class Loose(BaseModel):
    model_config = ConfigDict(extra="allow")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _date(value: str | None) -> str | None:
    if value is not None and not DATE_RE.match(value):
        raise ValueError(f"'{value}' is not a date in the form YYYY-MM-DD")
    return value


# ---------- message.json ----------

class Restart(Strict):
    minutes: int = Field(ge=2, le=60)
    until: str

    _check_until = field_validator("until")(lambda cls, v: _date(v))


class Message(Strict):
    date: str
    en: str | None = None
    tr: str | None = None
    restart: Restart | None = None

    _check_date = field_validator("date")(lambda cls, v: _date(v))

    @model_validator(mode="after")
    def _has_text(self) -> "Message":
        if not (self.en or self.tr):
            raise ValueError("the message needs an 'en' or 'tr' text")
        for text in (self.en, self.tr):
            if text and len(text) > 400:
                raise ValueError("keep the message short: at most 400 characters per language")
        return self


# ---------- watch.json ----------

class Window(Strict):
    opens: str | None = None
    closes: str | None = None

    _check = field_validator("opens", "closes")(lambda cls, v: _date(v))


class WatchEntry(Strict):
    what: str                       # English, e.g. "Ελληνομάθεια B1 written exam, May 2027"
    what_tr: str | None = None
    kind: Literal["exam", "course", "other"] = "exam"
    exam: str | None = None         # the blueprint id (exams/<id>.json) for an exam entry
    date: str | None = None         # the exam or course start date, if announced
    registration: Window | None = None
    source_url: str
    changed: bool = False           # new or different since the previous check
    note: str | None = None

    _check_date = field_validator("date")(lambda cls, v: _date(v))


class Watch(Strict):
    checked_at: str
    entries: list[WatchEntry] = []


# ---------- feedback/<id>.json ----------

class Criterion(Strict):
    name: str
    points: float | None = None
    out_of: float | None = None
    comment: str | None = None


class Score(Strict):
    exam: str | None = None          # "a2ltr" or "b1-keg"
    task: str | None = None          # e.g. "a2ltr.writing.email_formal"
    points: float | None = None
    out_of: float | None = None
    criteria: list[Criterion] = []
    unverified: bool = True          # true until the criteria are checked against the official guide


class Error(Strict):
    original: str
    fix: str
    why: str


class Feedback(Strict):
    submission_id: int
    item_key: str
    kind: Literal["writing", "speaking"]
    lang: Literal["en", "tr"]
    marked_at: str
    summary: str
    score: Score | None = None
    corrected: str | None = None     # writing: the whole text, corrected
    heard: str | None = None         # speaking: what the transcription heard
    errors: list[Error] = Field(default=[], max_length=3)
    exercises: list[str] = []        # item keys written for recurring errors
    by: str | None = None            # which agent marked it

    @model_validator(mode="after")
    def _kind_fields(self) -> "Feedback":
        if self.kind == "writing" and not self.corrected:
            raise ValueError("writing feedback needs the corrected text in 'corrected'")
        if self.kind == "speaking" and self.heard is None:
            raise ValueError("speaking feedback needs 'heard' (what the transcription heard)")
        return self


# ---------- resolved-flags.json ----------

class Resolution(Strict):
    flag_id: int
    resolution: Literal["fixed", "retired", "kept"]
    note: str | None = None
    item_key: str | None = None


_resolutions = TypeAdapter(list[Resolution])


# ---------- schedule.json ----------

class Task(Strict):
    every: Literal["day", "week"]
    at: str = "05:00"
    day: Literal["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"] | None = None
    created: str | None = None

    @field_validator("at")
    @classmethod
    def _time(cls, v: str) -> str:
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("'at' must be a time such as 05:00")
        return v


class Schedule(Strict):
    agent: Literal["claude", "codex"] = "claude"
    tasks: dict[str, Task] = {}


# ---------- profile.json ----------

class Profile(Loose):
    ui_lang: Literal["en", "tr"] | None = None
    minutes: int | None = Field(default=None, ge=1, le=120)
    days_per_week: int | None = Field(default=None, ge=1, le=7)
    name: str | None = None
    goal: str | None = None
    target_exam: Literal["a2ltr", "b1-keg", "undecided"] | None = None
    target_session: str | None = None
    interests: list[str] = []
    work: str | None = None
    course: dict[str, Any] | None = None
    edge_tts_ok: bool | None = None
    whisper_ok: bool | None = None


# ---------- plan.json ----------

Realistic = Literal["yes", "tight", "no", "unknown"]


class Words(Strict):
    en: str
    tr: str | None = None


class PlanTarget(Strict):
    exam: str                               # a blueprint id
    session: str | None = None              # the exam date, from watch.json
    registration_closes: str | None = None
    source_url: str | None = None

    _check = field_validator("session", "registration_closes")(lambda cls, v: _date(v))


class PlanOption(Strict):
    exam: str
    session: str | None = None
    realistic: Realistic
    why: Words

    _check = field_validator("session")(lambda cls, v: _date(v))


class PlanVerdict(Strict):
    realistic: Realistic
    en: str
    tr: str | None = None


class PlanWeek(Strict):
    start: str                              # the Monday of the week
    minutes: int = Field(ge=0, le=3000)
    focus: list[str] = []                   # unit ids of the target exam, or "foundations"
    content: Words
    beyond_a2: list[str] = []               # ids from the B1 blueprint's beyond_a2
    checkpoint: Words | None = None
    mock: bool = False

    _check = field_validator("start")(lambda cls, v: _date(v))


class Plan(Strict):
    made_at: str
    exam: str                               # the blueprint the weeks aim at
    target: PlanTarget | None = None        # None: no realistic announced session yet
    budget_minutes_week: int = Field(ge=0, le=3000)
    pace_minutes_week: float | None = None  # what actually happened, last 4 weeks
    verdict: PlanVerdict
    options: list[PlanOption] = []
    behind: Words | None = None             # said plainly when the learner is behind
    drop: list[Words] = []                  # what to drop to catch up
    weeks: list[PlanWeek] = Field(min_length=1)

    _check = field_validator("made_at")(lambda cls, v: _date(v))

    @model_validator(mode="after")
    def _weeks_in_order(self) -> "Plan":
        starts = [w.start for w in self.weeks]
        if starts != sorted(starts) or len(set(starts)) != len(starts):
            raise ValueError("weeks must be in date order, one entry per week")
        return self


# ---------- coach/mocks/<id>.json ----------

class MockSection(Strict):
    unit: str
    items: list[str] = Field(min_length=1)  # item keys, in paper order


class MockDef(Strict):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    blueprint: str
    created: str
    title: Words | None = None
    note: Words | None = None
    sections: list[MockSection] = Field(min_length=1)

    _check = field_validator("created")(lambda cls, v: _date(v))

    @model_validator(mode="after")
    def _units_once(self) -> "MockDef":
        units = [s.unit for s in self.sections]
        if len(set(units)) != len(units):
            raise ValueError("each unit may appear only once in a mock")
        return self


# ---------- reading ----------

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load(model, path: Path):
    """The parsed file, or None (missing or broken; broken ones are logged)."""
    if not path.is_file():
        return None
    try:
        data = read_json(path)
        return model.validate_python(data) if isinstance(model, TypeAdapter) else model.model_validate(data)
    except (json.JSONDecodeError, ValidationError, OSError) as e:
        log.warning("coach file %s skipped: %s", path, e.__class__.__name__)
        return None


def message() -> Message | None:
    return _load(Message, coach_dir() / "message.json")


def watch() -> Watch | None:
    return _load(Watch, coach_dir() / "watch.json")


def plan() -> Plan | None:
    return _load(Plan, coach_dir() / "plan.json")


def mocks_dir() -> Path:
    return coach_dir() / "mocks"


def mocks() -> list[MockDef]:
    """Every valid mock definition (a broken one is logged and skipped)."""
    folder = mocks_dir()
    out = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        m = _load(MockDef, path)
        if m and m.id == path.stem:
            out.append(m)
        elif m:
            log.warning("mock %s skipped: its id %s does not match the file name", path.name, m.id)
    return out


def schedule() -> Schedule | None:
    return _load(Schedule, coach_dir() / "schedule.json")


def resolutions() -> list[Resolution]:
    return _load(_resolutions, coach_dir() / "resolved-flags.json") or []


def feedback(submission_id: int) -> Feedback | None:
    fb = _load(Feedback, feedback_dir() / f"{submission_id}.json")
    return fb if fb and fb.submission_id == submission_id else None


def transcript(submission_id: int) -> dict | None:
    path = recordings_dir() / f"{submission_id}.json"
    try:
        return read_json(path) if path.is_file() else None
    except (json.JSONDecodeError, OSError):
        return None


# ---------- taking the files in ----------

def sync(conn: sqlite3.Connection) -> dict[str, int]:
    """Apply feedback files and flag resolutions to the database. Safe to call often."""
    marked = 0
    resolved = 0
    with conn:
        for row in conn.execute("SELECT id FROM submissions WHERE status='new'").fetchall():
            if feedback(row["id"]):
                conn.execute("UPDATE submissions SET status='marked', feedback_path=? WHERE id=?",
                             (f"feedback/{row['id']}.json", row["id"]))
                marked += 1
        for r in resolutions():
            cur = conn.execute(
                "UPDATE flags SET resolved_at=?, resolution=? WHERE id=? AND resolved_at IS NULL",
                (db.now(), r.resolution + (f": {r.note}" if r.note else ""), r.flag_id),
            )
            resolved += cur.rowcount
    return {"marked": marked, "resolved": resolved}


def resolved_flag_ids() -> set[int]:
    return {r.flag_id for r in resolutions()}


# ---------- home-screen views ----------

def message_for_home(today: date) -> dict | None:
    m = message()
    if m is None:
        return None
    try:
        age = (today - date.fromisoformat(m.date)).days
    except ValueError:
        return None
    if age > MESSAGE_MAX_AGE_DAYS or age < -1:
        return None
    return {"date": m.date, "en": m.en, "tr": m.tr}


def restart_minutes(today: date) -> int | None:
    """A smaller first session after time away, when the coach asked for one."""
    m = message()
    if m and m.restart and today.isoformat() <= m.restart.until and m.date <= today.isoformat():
        return m.restart.minutes
    return None


def next_dates(today: date, limit: int = 2) -> dict | None:
    """The next exam or course dates and open registration windows from watch.json."""
    w = watch()
    if w is None:
        return None
    upcoming = []
    for e in w.entries:
        reg = e.registration
        if e.kind != "exam" and reg and reg.closes and reg.closes < today.isoformat():
            continue  # a course whose registration has closed is no use on the home screen
        candidates = [d for d in (e.date, reg.opens if reg else None, reg.closes if reg else None) if d]
        future = [d for d in candidates if d >= today.isoformat()]
        if not future:
            continue
        upcoming.append((min(future), e))
    upcoming.sort(key=lambda x: x[0])
    return {
        "checked_at": w.checked_at,
        "entries": [e.model_dump() for _, e in upcoming[:limit]],
    }


# ---------- scheduled runs ----------

_RUN_RE = re.compile(r"^(\S+)\s+(\S+)\s+(ok|failed)\b(.*)$")
PERIOD_DAYS = {"day": 1, "week": 7}


def runs(limit: int = 200) -> list[dict]:
    try:
        lines = runs_log().read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    except OSError:
        return []
    out = []
    for line in lines:
        m = _RUN_RE.match(line.strip())
        if m:
            out.append({"ts": m.group(1), "skill": m.group(2), "ok": m.group(3) == "ok", "detail": m.group(4).strip()})
    return out


def append_run(skill: str, ok: bool, detail: str = "") -> None:
    coach_dir().mkdir(parents=True, exist_ok=True)
    detail = " ".join(detail.split())[:300]
    with runs_log().open("a", encoding="utf-8") as f:
        f.write(f"{db.now()} {skill} {'ok' if ok else 'failed'} {detail}".rstrip() + "\n")


def run_problems(now: datetime | None = None) -> list[dict]:
    """Scheduled skills whose last run failed, or that have not run for two periods."""
    now = now or db.current()
    sched = schedule()
    history = runs()
    problems = []
    skills = set(sched.tasks) if sched else set()
    skills |= {r["skill"] for r in history}
    for skill in sorted(skills):
        mine = [r for r in history if r["skill"] == skill]
        last = mine[-1] if mine else None
        if last and not last["ok"]:
            problems.append({"skill": skill, "problem": "failed", "since": last["ts"], "detail": last["detail"]})
            continue
        task = sched.tasks.get(skill) if sched else None
        if not task:
            continue
        limit = timedelta(days=2 * PERIOD_DAYS[task.every])
        ref = last["ts"] if last else task.created
        try:
            ref_dt = datetime.fromisoformat(ref) if ref else None
        except ValueError:
            ref_dt = None
        if ref_dt is not None and now - ref_dt.astimezone(now.tzinfo) > limit:
            problems.append({"skill": skill, "problem": "not_run", "since": ref, "detail": ""})
    return problems


# ---------- validation of a learner folder ----------

FILES = {
    "coach/message.json": Message,
    "coach/watch.json": Watch,
    "coach/schedule.json": Schedule,
    "coach/resolved-flags.json": _resolutions,
    "coach/plan.json": Plan,
    "profile.json": Profile,
}


def validate_learner(folder: Path) -> list[str]:
    """Plain-language problems in the coach files of a learner folder."""
    problems: list[str] = []

    def check(rel: str, model) -> None:
        path = folder / rel
        if not path.is_file():
            return
        try:
            data = read_json(path)
        except json.JSONDecodeError as e:
            problems.append(f"{rel} is not valid JSON (line {e.lineno}): {e.msg}")
            return
        try:
            model.validate_python(data) if isinstance(model, TypeAdapter) else model.model_validate(data)
        except ValidationError as e:
            for err in e.errors():
                where = ".".join(str(x) for x in err["loc"])
                problems.append(f"{rel} {where}: {err['msg'].removeprefix('Value error, ')}")

    for rel, model in FILES.items():
        check(rel, model)
    for path in sorted((folder / "coach" / "mocks").glob("*.json")):
        rel = f"coach/mocks/{path.name}"
        check(rel, MockDef)
        try:
            data = read_json(path)
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict) and data.get("id") != path.stem:
            problems.append(f"{rel}: id {data.get('id')!r} does not match the file name")
        problems.extend(f"{rel}: {p}" for p in _mock_problems(data))
    plan_data = None
    try:
        plan_data = read_json(folder / "coach" / "plan.json") if (folder / "coach" / "plan.json").is_file() else None
    except (json.JSONDecodeError, OSError):
        pass
    if isinstance(plan_data, dict):
        problems.extend(f"coach/plan.json: {p}" for p in _plan_problems(plan_data))
    for path in sorted((folder / "feedback").glob("*.json")):
        check(f"feedback/{path.name}", Feedback)
        try:
            sid = read_json(path).get("submission_id")
            if str(sid) != path.stem:
                problems.append(f"feedback/{path.name}: submission_id {sid} does not match the file name")
        except (json.JSONDecodeError, AttributeError, OSError):
            pass
    return problems


def _mock_problems(data: Any) -> list[str]:
    """Checks a mock definition against the blueprints (the model checks the shape)."""
    from greek_coach import exams

    if not isinstance(data, dict):
        return []
    bps = exams.load_blueprints()
    bp = bps.get(data.get("blueprint"))
    if bp is None:
        return [f"blueprint {data.get('blueprint')!r} is not one of {sorted(bps)}"]
    from greek_coach import packs

    out = []
    catalog = None
    for s in data.get("sections") or []:
        if not isinstance(s, dict):
            continue
        unit = bp.unit(s.get("unit"))
        if unit is None:
            out.append(f"unit {s.get('unit')!r} is not a unit of {bp.id} ({[u.id for u in bp.units]})")
            continue
        catalog = catalog or packs.load_all()
        tasks = {t.id for t in unit.tasks}
        for key in s.get("items") or []:
            entry = catalog.items.get(key)
            if entry is None:
                out.append(f"{unit.id}: item {key} was not found (check the pack and id)")
            elif entry[1].exam_task not in tasks:
                out.append(f"{unit.id}: item {key} has exam_task {entry[1].exam_task!r}, not a {unit.id} task of {bp.id}")
    return out


def _plan_problems(data: dict) -> list[str]:
    from greek_coach import exams

    bps = exams.load_blueprints()
    out = []
    if data.get("exam") not in bps:
        out.append(f"exam {data.get('exam')!r} is not one of {sorted(bps)}")
        return out
    bp = bps[data["exam"]]
    units = {u.id for u in bp.units} | {"foundations"}
    beyond = {b.id for b2 in bps.values() for b in b2.beyond_a2}
    for i, w in enumerate(data.get("weeks") or []):
        if not isinstance(w, dict):
            continue
        bad = [f for f in w.get("focus") or [] if f not in units]
        if bad:
            out.append(f"weeks[{i}].focus: {bad} are not units of {bp.id} (use {sorted(units)})")
        bad = [b for b in w.get("beyond_a2") or [] if b not in beyond]
        if bad:
            out.append(f"weeks[{i}].beyond_a2: {bad} are not in any blueprint's beyond_a2")
    return out
