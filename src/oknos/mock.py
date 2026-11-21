"""Timed mock exams (docs/SPEC.md §5.4).

The coach writes a mock as `learner/coach/mocks/<id>.json`: an exam blueprint and, per unit, the
items of that section in paper order. The app runs it:

- one section per exam unit, timed with the blueprint's minutes, on the server's clock;
- no feedback during a section; answers are saved as drafts as the learner gives them, and
  can be changed until the section closes;
- a section closes when the learner hands it in, or when time is up. Time keeps running while
  the learner is away, as in the exam: coming back in time resumes with the time left, coming
  back late finds the section closed with what was saved (closed_by 'time_away');
- on closing, every answered item is graded into a normal attempt (session kind 'mock'), so the
  result feeds readiness; writing and speaking become submissions that the coach marks;
- section points follow the blueprint: each task's points times the share of its questions
  answered right, an unanswered item counting as wrong.

OKNOS_MOCK_SPEED (development only) makes mock time pass faster, to check the timing.
"""

from __future__ import annotations

import json
import os
import random
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from oknos import coachfiles, db, exams, paths, scheduler, session
from oknos.checking import CheckError, check
from oknos.packs import (
    OPEN_TASKS,
    Catalog,
    CategoriseItem,
    GapBankItem,
    MatchItem,
    SpeakItem,
    TableFillItem,
    TrueFalseItem,
    WriteItem,
)


class MockError(ValueError):
    """Something the learner's browser asked for that does not fit the mock's state."""


def speed() -> float:
    try:
        value = float(paths.env("MOCK_SPEED", "1"))
    except ValueError:
        return 1.0
    return value if value > 0 else 1.0


def _now() -> datetime:
    return db.current()


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts).astimezone(_now().tzinfo)


def parts_of(item) -> int:
    """How many scored questions an item holds (its sub-answers)."""
    if isinstance(item, TrueFalseItem):
        return len(item.statements)
    if isinstance(item, MatchItem):
        return len(item.left)
    if isinstance(item, CategoriseItem):
        return len(item.items)
    if isinstance(item, GapBankItem):
        return len(item.answer)
    if isinstance(item, TableFillItem):
        return len(item.cells())
    return 1


# ---------- definitions ----------

def definitions(catalog: Catalog) -> list[dict]:
    """The coach's mocks, with what is wrong with each (a broken mock is shown, not hidden)."""
    bps = exams.load_blueprints()
    out = []
    for m in coachfiles.mocks():
        bp = bps.get(m.blueprint)
        problems = []
        sections = []
        if bp is None:
            problems.append(f"unknown exam {m.blueprint}")
        for s in m.sections:
            unit = bp.unit(s.unit) if bp else None
            if bp and unit is None:
                problems.append(f"unknown unit {s.unit}")
            missing = [k for k in s.items if k not in catalog.items]
            if missing:
                problems.append(f"{s.unit}: {len(missing)} item(s) not found ({', '.join(missing[:3])})")
            if unit:
                tasks = {t.id for t in unit.tasks}
                wrong = [k for k in s.items if k in catalog.items and catalog.items[k][1].exam_task not in tasks]
                if wrong:
                    problems.append(f"{s.unit}: {len(wrong)} item(s) are not tagged with a {s.unit} task of "
                                    f"{bp.id} ({', '.join(wrong[:3])})")
            sections.append({"unit": s.unit, "items": len(s.items),
                             "minutes": unit.minutes if unit else None, "points": unit.points if unit else None})
        out.append({"id": m.id, "blueprint": m.blueprint, "created": m.created,
                    "title": m.title.model_dump() if m.title else None,
                    "note": m.note.model_dump() if m.note else None,
                    "sections": sections, "problems": problems, "ok": not problems})
    return out


def _definition(mock_id: str) -> coachfiles.MockDef:
    m = next((m for m in coachfiles.mocks() if m.id == mock_id), None)
    if m is None:
        raise MockError(f"there is no mock {mock_id!r}")
    return m


def reserved_keys(conn: sqlite3.Connection) -> set[str]:
    """Items of mocks not yet taken. Daily sessions leave them alone, so they stay unseen."""
    done = {r[0] for r in conn.execute("SELECT DISTINCT mock_id FROM mock_runs WHERE status != 'running' "
                                       "OR finished_at IS NOT NULL")}
    keys: set[str] = set()
    for m in coachfiles.mocks():
        if m.id not in done:
            for s in m.sections:
                keys.update(s.items)
    return keys


# ---------- runs and sections ----------

def start_run(conn: sqlite3.Connection, catalog: Catalog, mock_id: str) -> int:
    m = _definition(mock_id)
    defn = next(d for d in definitions(catalog) if d["id"] == mock_id)
    if not defn["ok"]:
        raise MockError("this mock has problems: " + "; ".join(defn["problems"]))
    row = conn.execute("SELECT id FROM mock_runs WHERE mock_id=? AND status='running' ORDER BY id DESC LIMIT 1",
                       (mock_id,)).fetchone()
    if row:
        return row["id"]
    with conn:
        cur = conn.execute("INSERT INTO mock_runs(blueprint, mock_id, started_at) VALUES (?, ?, ?)",
                           (m.blueprint, m.id, db.now()))
    return cur.lastrowid


def _run(conn: sqlite3.Connection, run_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM mock_runs WHERE id=?", (run_id,)).fetchone()
    if row is None:
        raise MockError(f"there is no mock run {run_id}")
    return row


def _section_row(conn: sqlite3.Connection, section_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM mock_sections WHERE id=?", (section_id,)).fetchone()
    if row is None:
        raise MockError(f"there is no mock section {section_id}")
    return row


def start_section(conn: sqlite3.Connection, catalog: Catalog, run_id: int, unit_id: str, ui_lang: str = "en") -> int:
    run = _run(conn, run_id)
    if run["status"] != "running":
        raise MockError("this mock is over")
    existing = conn.execute("SELECT id FROM mock_sections WHERE run_id=? AND unit=?", (run_id, unit_id)).fetchone()
    if existing:
        return existing["id"]
    open_one = conn.execute("SELECT unit FROM mock_sections WHERE run_id=? AND closed_at IS NULL", (run_id,)).fetchone()
    if open_one:
        raise MockError(f"finish the {open_one['unit']} section first")
    m = _definition(run["mock_id"])
    bp = exams.load_blueprints()[m.blueprint]
    unit = bp.unit(unit_id)
    sec = next((s for s in m.sections if s.unit == unit_id), None)
    if unit is None or sec is None:
        raise MockError(f"this mock has no {unit_id} section")
    rng = random.Random(f"{run_id}-{unit_id}")
    cards = []
    for n, key in enumerate(sec.items, start=1):
        _, item = catalog.items[key]
        cards.append({**session.task_card(key, item, rng), "segment": "mock", "number": n})
    start = _now()
    ends = start + timedelta(seconds=unit.minutes * 60 / speed())
    with conn:
        cur = conn.execute(
            "INSERT INTO sessions(started_at, kind, planned_minutes, items_planned, plan_json) VALUES (?, 'mock', ?, ?, ?)",
            (start.isoformat(timespec="seconds"), unit.minutes, len(cards), json.dumps(cards, ensure_ascii=False)))
        sid = cur.lastrowid
        cur = conn.execute("INSERT INTO mock_sections(run_id, unit, session_id, started_at, ends_at) VALUES (?, ?, ?, ?, ?)",
                           (run_id, unit_id, sid, start.isoformat(timespec="seconds"),
                            ends.isoformat(timespec="milliseconds")))
    return cur.lastrowid


AWAY_GRACE_SECONDS = 20  # an open page hands the section in itself at 0; give it time to do so


def expire(conn: sqlite3.Connection, catalog: Catalog) -> int:
    """Close every open section whose time ran out while no page was there to hand it in."""
    now = _now()
    closed = 0
    for r in conn.execute("SELECT id, ends_at FROM mock_sections WHERE closed_at IS NULL").fetchall():
        if _parse(r["ends_at"]) + timedelta(seconds=AWAY_GRACE_SECONDS) <= now:
            close_section(conn, catalog, r["id"], "time_away")
            closed += 1
    return closed


def save_answer(conn: sqlite3.Connection, catalog: Catalog, section_id: int, item_key: str, response: dict) -> dict:
    expire(conn, catalog)
    sec = _section_row(conn, section_id)
    if sec["closed_at"]:
        raise MockError("time is up: this section is closed")
    if _parse(sec["ends_at"]) <= _now():
        close_section(conn, catalog, section_id, "time")
        raise MockError("time is up: this section is closed")
    cards = json.loads(conn.execute("SELECT plan_json FROM sessions WHERE id=?", (sec["session_id"],)).fetchone()[0])
    card = next((c for c in cards if c["item_key"] == item_key), None)
    if card is None:
        raise MockError(f"{item_key} is not in this section")
    item = catalog.items[item_key][1]
    if not isinstance(item, OPEN_TASKS):
        try:
            check(item, card, response)  # the shape must be right now, not at the end
        except CheckError as e:
            raise MockError(str(e))
    answers = json.loads(sec["answers_json"])
    answers[item_key] = {"response": response, "ts": db.now()}
    with conn:
        conn.execute("UPDATE mock_sections SET answers_json=?, last_saved_at=? WHERE id=?",
                     (json.dumps(answers, ensure_ascii=False), db.now(), section_id))
    return {"saved": len(answers), "of": len(cards)}


def save_submission(conn: sqlite3.Connection, item, item_key: str, session_id: int, attempt_id: int,
                    response: dict) -> int | None:
    """A writing text or a speaking recording, for the coach to mark (shared with daily sessions)."""
    if response.get("skipped"):
        return None
    if isinstance(item, WriteItem):
        text = (response.get("text") or "").strip()
        if not text:
            return None
        cur = conn.execute(
            "INSERT INTO submissions(item_key, session_id, attempt_id, ts, kind, text, word_count) "
            "VALUES (?, ?, ?, ?, 'writing', ?, ?)",
            (item_key, session_id, attempt_id, db.now(), text, word_count(text)))
        return cur.lastrowid
    recording = recording_file(response.get("recording")) if isinstance(response.get("recording"), str) else None
    if recording is None:
        return None
    cur = conn.execute("INSERT INTO submissions(item_key, session_id, attempt_id, ts, kind) VALUES (?, ?, ?, ?, 'speaking')",
                       (item_key, session_id, attempt_id, db.now()))
    sid = cur.lastrowid
    final = recording.with_name(f"{sid}{recording.suffix}")
    recording.replace(final)
    conn.execute("UPDATE submissions SET recording_path=? WHERE id=?",
                 (final.relative_to(paths.learner_dir()).as_posix(), sid))
    return sid


def word_count(text: str) -> int:
    return len([w for w in text.split() if any(c.isalnum() for c in w)])


def recording_file(name: str | None):
    if not name:
        return None
    base = coachfiles.recordings_dir().resolve()
    target = (paths.learner_dir() / name).resolve()
    return target if base in target.parents and target.is_file() else None


def close_section(conn: sqlite3.Connection, catalog: Catalog, section_id: int, by: str) -> dict:
    """Grade the section: every answered item becomes an attempt; points follow the blueprint."""
    sec = _section_row(conn, section_id)
    if sec["closed_at"]:
        return json.loads(sec["result_json"] or "{}")
    if by not in ("learner", "time", "time_away"):
        raise MockError("closed_by must be learner, time or time_away")
    run = _run(conn, sec["run_id"])
    bp = exams.load_blueprints()[run["blueprint"]]
    unit = bp.unit(sec["unit"])
    cards = json.loads(conn.execute("SELECT plan_json FROM sessions WHERE id=?", (sec["session_id"],)).fetchone()[0])
    answers = json.loads(sec["answers_json"])
    per_task: dict[str, list[float]] = {}
    unanswered = 0
    not_recorded = 0  # speaking parts said aloud without a recording: done, but nothing to mark
    submissions = []
    with conn:
        for card in cards:
            key = card["item_key"]
            entry = catalog.items.get(key)
            if entry is None:
                continue
            item = entry[1]
            task = item.exam_task if item.exam_task in {t.id for t in unit.tasks} else None
            saved = answers.get(key)
            if isinstance(item, OPEN_TASKS):
                if saved:
                    cur = conn.execute(
                        "INSERT INTO attempts(session_id, item_key, ts, response_json, score, correct, latency_ms) "
                        "VALUES (?, ?, ?, ?, NULL, NULL, NULL)",
                        (sec["session_id"], key, db.now(), json.dumps({"card": card, "response": saved["response"]},
                                                                       ensure_ascii=False)))
                    sid = save_submission(conn, item, key, sec["session_id"], cur.lastrowid, saved["response"])
                    if sid:
                        submissions.append(sid)
                    elif isinstance(item, SpeakItem) and saved["response"].get("done"):
                        not_recorded += 1
                    else:
                        unanswered += 1
                else:
                    unanswered += 1
                continue
            n_parts = parts_of(item)
            right = 0.0
            if saved:
                result = check(item, card, saved["response"])
                right = (result.score or 0.0) * n_parts
                conn.execute(
                    "INSERT INTO attempts(session_id, item_key, ts, response_json, score, correct, latency_ms, accent_note) "
                    "VALUES (?, ?, ?, ?, ?, ?, NULL, ?)",
                    (sec["session_id"], key, db.now(), json.dumps({"card": card, "response": saved["response"]},
                                                                   ensure_ascii=False),
                     result.score, int(bool(result.correct)), result.accent_note))
                scheduler.record(conn, key, item.type, result.correct, result.score,
                                 accent_note=bool(result.accent_note))
            else:
                unanswered += 1
            if task:
                parts = per_task.setdefault(task, [0.0, 0.0])
                parts[0] += right
                parts[1] += n_parts
        result = {"unit": unit.id, "closed_by": by, "unanswered": unanswered, "not_recorded": not_recorded,
                  "items": len(cards),
                  "submissions": submissions, "tasks": {}}
        if unit.marked_by == "app":
            points = out_of = 0.0
            for t in unit.tasks:
                if t.id in per_task:
                    right, total = per_task[t.id]
                    got = t.points * right / total if total else 0.0
                    result["tasks"][t.id] = {"points": round(got, 2), "out_of": t.points,
                                             "right": round(right, 2), "questions": int(total)}
                    points += got
                    out_of += t.points
            result.update(points=round(points, 1), out_of=out_of, complete=out_of == unit.points)
        else:
            result.update(points=None, out_of=unit.points, waiting_for_coach=bool(submissions))
        now = db.now()
        conn.execute("UPDATE mock_sections SET closed_at=?, closed_by=?, result_json=? WHERE id=?",
                     (now, by, json.dumps(result, ensure_ascii=False), section_id))
        conn.execute("UPDATE sessions SET ended_at=?, items_done=(SELECT COUNT(*) FROM attempts WHERE session_id=?) "
                     "WHERE id=?", (now, sec["session_id"], sec["session_id"]))
    _maybe_finish(conn, sec["run_id"])
    return result


def _coach_points(conn: sqlite3.Connection, bp: exams.Blueprint, unit: exams.UnitSpec, result: dict) -> dict:
    """Writing and speaking: the coach's marks, scaled to the blueprint's task points."""
    subs = result.get("submissions") or []
    if not subs:
        return {**result, "points": None, "status": "not_answered" if result.get("unanswered") else "empty"}
    got = out_of = 0.0
    waiting = 0
    tasks = {}
    for sid in subs:
        fb = coachfiles.feedback(sid)
        if not fb or not fb.score or fb.score.points is None or not fb.score.out_of:
            waiting += 1
            continue
        task_id = fb.score.task
        spec = bp.task(task_id) if task_id else None
        points = spec[1].points if spec else unit.points / max(1, len(unit.tasks))
        share = max(0.0, min(1.0, fb.score.points / fb.score.out_of))
        tasks[task_id or f"submission-{sid}"] = {"points": round(points * share, 2), "out_of": points,
                                                  "unverified": fb.score.unverified}
        got += points * share
        out_of += points
    if waiting:
        return {**result, "points": None, "status": "waiting_for_coach", "waiting": waiting, "tasks": tasks}
    return {**result, "points": round(got, 1), "out_of": out_of, "status": "marked", "tasks": tasks,
            "waiting_for_coach": False, "complete": abs(out_of - unit.points) < 1e-6}


def _maybe_finish(conn: sqlite3.Connection, run_id: int) -> None:
    run = _run(conn, run_id)
    if run["status"] != "running":
        return
    m = next((m for m in coachfiles.mocks() if m.id == run["mock_id"]), None)
    units = [s.unit for s in m.sections] if m else []
    closed = {r["unit"] for r in conn.execute("SELECT unit FROM mock_sections WHERE run_id=? AND closed_at IS NOT NULL",
                                              (run_id,))}
    if units and all(u in closed for u in units):
        with conn:
            conn.execute("UPDATE mock_runs SET status='finished', finished_at=? WHERE id=?", (db.now(), run_id))


def abandon(conn: sqlite3.Connection, catalog: Catalog, run_id: int) -> None:
    for r in conn.execute("SELECT id FROM mock_sections WHERE run_id=? AND closed_at IS NULL", (run_id,)).fetchall():
        close_section(conn, catalog, r["id"], "learner")
    with conn:
        conn.execute("UPDATE mock_runs SET status='abandoned', finished_at=? WHERE id=? AND status='running'",
                     (db.now(), run_id))


# ---------- views ----------

def section_view(conn: sqlite3.Connection, section_id: int) -> dict:
    sec = _section_row(conn, section_id)
    cards = json.loads(conn.execute("SELECT plan_json FROM sessions WHERE id=?", (sec["session_id"],)).fetchone()[0])
    answers = json.loads(sec["answers_json"])
    remaining = max(0.0, (_parse(sec["ends_at"]) - _now()).total_seconds())
    return {"section_id": sec["id"], "run_id": sec["run_id"], "unit": sec["unit"], "session_id": sec["session_id"],
            "started_at": sec["started_at"], "ends_at": sec["ends_at"], "remaining_seconds": round(remaining, 1),
            "speed": speed(), "closed": bool(sec["closed_at"]), "closed_by": sec["closed_by"],
            "cards": cards, "answers": {k: v["response"] for k, v in answers.items()},
            "result": json.loads(sec["result_json"]) if sec["result_json"] else None}


def run_view(conn: sqlite3.Connection, catalog: Catalog, run_id: int) -> dict:
    expire(conn, catalog)
    run = _run(conn, run_id)
    bp = exams.load_blueprints().get(run["blueprint"])
    m = next((m for m in coachfiles.mocks() if m.id == run["mock_id"]), None)
    rows = {r["unit"]: r for r in conn.execute("SELECT * FROM mock_sections WHERE run_id=?", (run_id,))}
    sections = []
    total = total_out = 0.0
    complete = bool(bp and m)
    for s in (m.sections if m else []):
        unit = bp.unit(s.unit) if bp else None
        r = rows.get(s.unit)
        res = json.loads(r["result_json"]) if r is not None and r["result_json"] else None
        if res and unit and unit.marked_by == "coach":
            res = _coach_points(conn, bp, unit, res)
        state = "not_started" if r is None else "open" if not r["closed_at"] else "closed"
        if res and res.get("points") is not None:
            total += res["points"]
            total_out += res.get("out_of") or 0
        else:
            complete = False
        sections.append({"unit": s.unit, "items": len(s.items), "minutes": unit.minutes if unit else None,
                         "points": unit.points if unit else None, "pass_line": bp.pass_line(unit) if unit else None,
                         "state": state, "section_id": r["id"] if r is not None else None,
                         "closed_by": r["closed_by"] if r is not None else None, "result": res})
    out = {"run_id": run["id"], "mock_id": run["mock_id"], "blueprint": run["blueprint"], "status": run["status"],
           "started_at": run["started_at"], "finished_at": run["finished_at"], "sections": sections,
           "total": round(total, 1), "total_out_of": total_out}
    out["would_pass"], out["verdict_note"] = _would_pass(bp, m, sections)
    if bp and complete and total_out == bp.total_points:
        out["verdict_note"] = "complete"
    if run["status"] == "finished":
        with conn:
            conn.execute("UPDATE mock_runs SET unit_scores_json=? WHERE id=?",
                         (json.dumps({s["unit"]: s["result"] for s in sections}, ensure_ascii=False), run_id))
    return out


def _would_pass(bp, m, sections: list[dict]) -> tuple[bool | None, str]:
    """The exam's pass rule on the mock. Points that could not be scored (a task the mock did
    not include, a speaking part said aloud without a recording) count as 0 for "would pass"
    and as full marks for "would not pass"; in between, the mock cannot say."""
    if bp is None or m is None:
        return None, "unknown_exam"
    by_unit = {s["unit"]: s for s in sections}
    lows, highs = {}, {}
    for u in bp.units:
        s = by_unit.get(u.id)
        res = s["result"] if s else None
        if s is None or s["state"] != "closed" or res is None:
            if s is not None:
                return None, "sections_open"
            lows[u.id], highs[u.id] = 0.0, u.points      # a unit the mock did not include
            continue
        if res.get("status") == "waiting_for_coach":
            return None, "waiting_for_coach"
        got = res.get("points") or 0.0
        scored = res.get("out_of") if res.get("points") is not None else 0.0
        lows[u.id], highs[u.id] = got, got + max(0.0, u.points - (scored or 0.0))
    if exams.passes(bp, lows):
        return True, "pass_even_with_unscored_at_zero"
    if not exams.passes(bp, highs):
        return False, "fail_even_with_unscored_at_full"
    return None, "unscored_parts_decide"


def runs(conn: sqlite3.Connection, catalog: Catalog, limit: int = 20) -> list[dict]:
    ids = [r[0] for r in conn.execute("SELECT id FROM mock_runs ORDER BY id DESC LIMIT ?", (limit,))]
    return [run_view(conn, catalog, i) for i in ids]


def latest_unit_results(conn: sqlite3.Connection, blueprint: str) -> dict[str, dict]:
    """The most recent closed mock section per unit of this exam, for the readiness view."""
    bp = exams.load_blueprints().get(blueprint)
    out: dict[str, dict] = {}
    for r in conn.execute(
        "SELECT s.unit, s.closed_at, s.closed_by, s.result_json FROM mock_sections s JOIN mock_runs m ON m.id = s.run_id "
        "WHERE m.blueprint=? AND s.closed_at IS NOT NULL ORDER BY s.closed_at DESC", (blueprint,)
    ):
        if r["unit"] in out or not r["result_json"]:
            continue
        res = json.loads(r["result_json"])
        unit = bp.unit(r["unit"]) if bp else None
        if unit and unit.marked_by == "coach":
            res = _coach_points(conn, bp, unit, res)
        out[r["unit"]] = {"date": r["closed_at"][:10], "points": res.get("points"), "out_of": res.get("out_of"),
                          "closed_by": r["closed_by"], "unanswered": res.get("unanswered", 0),
                          "status": res.get("status")}
    return out
