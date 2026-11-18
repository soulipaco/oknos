"""Readiness per exam unit, and coverage per exam task (docs/SPEC.md §5.3).

The learner books an exam from these numbers, so false confidence is worse than no number.
The rules, each of which the screen states:

- Evidence is the FIRST attempt at each item tagged for the exam (exam_task), at the exam's
  level or above, in the last EVIDENCE_DAYS days, at most PER_TASK_MAX per task. A second
  attempt at the same item measures memory of that item, not exam ability, so it never counts.
- A task's share is the mean item score (share of sub-answers right), with a Wilson interval
  in which n is the number of items, not sub-answers (the parts of one item are not
  independent). Unit points are the task points times the share; the interval adds the task
  intervals (conservative), and a task with no evidence spans its whole range.
- A unit with fewer than UNIT_MIN first attempts, or with no evidence for a task worth at least
  MAJOR_TASK_SHARE of its points, shows "not enough evidence" instead of a number.
- Writing and speaking count only the coach's marks (feedback scores), at least COACH_MIN
  pieces. The app itself never scores them.
- The exam verdict applies the exam's real pass rule to the low ends (would pass) and to the
  high ends (would not pass); anything in between is "can't tell yet".
"""

from __future__ import annotations

import math
import sqlite3
from collections import defaultdict
from datetime import timedelta
from typing import Any

from greek_coach import coachfiles, db, exams
from greek_coach.packs import TASK_TYPES, Catalog, FormItem, servable

EVIDENCE_DAYS = 90
PER_TASK_MAX = 20
UNIT_MIN = 6
COACH_MIN = 2
MAJOR_TASK_SHARE = 0.25
Z = 1.2816  # 80% two-sided
LEVEL_RANK = {"A1": 0, "A2": 1, "B1": 2}


def wilson(successes: float, n: int, z: float = Z) -> tuple[float, float]:
    """Wilson score interval for a proportion; successes may be fractional (item scores)."""
    if n <= 0:
        return 0.0, 1.0
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def first_attempts(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    """The first checked attempt at every item: {item_key: {ts, score, kind}}."""
    rows = conn.execute(
        """
        SELECT a.item_key, a.ts, a.score, COALESCE(s.kind, '') AS kind FROM attempts a
        JOIN (SELECT item_key, MIN(id) AS first_id FROM attempts WHERE correct IS NOT NULL GROUP BY item_key) f
          ON a.id = f.first_id
        LEFT JOIN sessions s ON s.id = a.session_id
        """
    ).fetchall()
    return {r["item_key"]: {"ts": r["ts"], "score": r["score"] or 0.0, "kind": r["kind"]} for r in rows}


def coach_marks(conn: sqlite3.Connection, catalog: Catalog, bp: exams.Blueprint, since: str) -> dict[str, list[dict]]:
    """Marked writing and speaking for this exam, per task: [{ts, share, unverified, mock}]."""
    out: dict[str, list[dict]] = defaultdict(list)
    for r in conn.execute("SELECT s.id, s.item_key, s.ts, COALESCE(se.kind, '') AS kind FROM submissions s "
                          "LEFT JOIN sessions se ON se.id = s.session_id WHERE s.ts >= ?", (since,)):
        fb = coachfiles.feedback(r["id"])
        if not fb or not fb.score or fb.score.points is None or not fb.score.out_of:
            continue
        entry = catalog.items.get(r["item_key"])
        task = fb.score.task or (entry[1].exam_task if entry else None)
        if not task or task not in bp.task_ids():
            continue
        if fb.score.exam and fb.score.exam != bp.id:
            continue
        share = max(0.0, min(1.0, fb.score.points / fb.score.out_of))
        out[task].append({"ts": r["ts"], "share": share, "unverified": fb.score.unverified, "mock": r["kind"] == "mock"})
    return out


def _evidence_items(catalog: Catalog, bp: exams.Blueprint) -> dict[str, str]:
    """item_key -> exam_task, for items that count as evidence for this exam."""
    ids = bp.task_ids()
    need = LEVEL_RANK[bp.level]
    return {k: item.exam_task for k, (_, item) in catalog.items.items()
            if item.exam_task in ids and LEVEL_RANK.get(item.level, 0) >= need}


def unit_readiness(bp: exams.Blueprint, unit: exams.UnitSpec, per_task: dict[str, list[dict]]) -> dict:
    """Points estimate for one unit from per-task evidence [{share, ts, timed}] (newest first)."""
    tasks = []
    n_total = 0
    timed = 0
    last = None
    lo_sum = hi_sum = est_sum = 0.0
    shares_seen: list[tuple[float, int]] = []
    major_missing = []
    for t in unit.tasks:
        ev = per_task.get(t.id, [])[:PER_TASK_MAX]
        n = len(ev)
        n_total += n
        timed += sum(1 for e in ev if e.get("timed"))
        if ev:
            last = max(last or "", max(e["ts"] for e in ev))
            s = sum(e["share"] for e in ev)
            share = s / n
            lo, hi = wilson(s, n)
            shares_seen.append((share, n))
            lo_sum += t.points * lo
            hi_sum += t.points * hi
            est_sum += t.points * share
            tasks.append({"id": t.id, "points": t.points, "n": n, "share": round(share, 3),
                          "low": round(t.points * lo, 2), "high": round(t.points * hi, 2)})
        else:
            hi_sum += t.points
            if t.points >= MAJOR_TASK_SHARE * unit.points:
                major_missing.append(t.id)
            tasks.append({"id": t.id, "points": t.points, "n": 0, "share": None, "low": 0.0, "high": t.points})
    # A task with no evidence: the estimate assumes the mean share of the other tasks (flagged).
    assumed = [t for t in tasks if t["n"] == 0]
    if shares_seen and assumed:
        mean = sum(s * n for s, n in shares_seen) / sum(n for _, n in shares_seen)
        est_sum += sum(t["points"] for t in assumed) * mean
    pass_line = bp.pass_line(unit)
    minimum = COACH_MIN if unit.marked_by == "coach" else UNIT_MIN
    out = {
        "unit": unit.id, "skill": unit.skill, "points": unit.points, "pass_line": pass_line,
        "marked_by": unit.marked_by, "evidence": n_total, "evidence_needed": minimum, "timed": timed,
        "last": last[:10] if last else None, "tasks": tasks,
        "assumed_tasks": [t["id"] for t in assumed] if shares_seen else [],
    }
    if n_total < minimum or major_missing:
        out.update(state="no_evidence", estimate=None, low=None, high=None,
                   reason="not_scored" if unit.marked_by == "coach" and n_total == 0 else
                   "major_task_missing" if major_missing and n_total >= minimum else "too_few",
                   missing_tasks=major_missing)
        return out
    low, high = round(lo_sum, 1), round(hi_sum, 1)
    state = "above" if low >= pass_line else "below" if high < pass_line else "unclear"
    out.update(state=state, estimate=round(est_sum, 1), low=low, high=high, reason="ok", missing_tasks=[])
    return out


def verdict(bp: exams.Blueprint, units: list[dict]) -> dict:
    """The exam's pass rule applied to the low and high ends of every unit."""
    if all(u["state"] == "no_evidence" for u in units):
        return {"state": "no_evidence"}
    lows = {u["unit"]: (u["low"] if u["low"] is not None else 0.0) for u in units}
    highs = {u["unit"]: (u["high"] if u["high"] is not None else u["points"]) for u in units}
    if exams.passes(bp, lows):
        state = "pass"
    elif not exams.passes(bp, highs):
        state = "fail"
    else:
        state = "unclear"
    est = {u["unit"]: u["estimate"] for u in units}
    total_low = round(sum(lows.values()), 1)
    total_high = round(sum(highs.values()), 1)
    return {
        "state": state,
        "total_low": total_low, "total_high": total_high,
        "below": [u["unit"] for u in units if u["state"] == "below"],
        "unclear": [u["unit"] for u in units if u["state"] == "unclear"],
        "no_evidence": [u["unit"] for u in units if u["state"] == "no_evidence"],
        "estimate_total": round(sum(v for v in est.values() if v is not None), 1) if all(v is not None for v in est.values()) else None,
    }


def for_blueprint(conn: sqlite3.Connection, catalog: Catalog, bp: exams.Blueprint,
                  firsts: dict[str, dict] | None = None) -> dict:
    today = db.today()
    since = (today - timedelta(days=EVIDENCE_DAYS - 1)).isoformat()
    firsts = firsts if firsts is not None else first_attempts(conn)
    tagged = _evidence_items(catalog, bp)
    per_task: dict[str, list[dict]] = defaultdict(list)
    for key, task in tagged.items():
        f = firsts.get(key)
        # an item first met inside a chapter ("try it") was seen with its explanation: not a cold attempt
        if f and f["ts"][:10] >= since and f["kind"] != "lesson":
            per_task[task].append({"ts": f["ts"], "share": f["score"], "timed": f["kind"] == "mock"})
    for task, marks in coach_marks(conn, catalog, bp, since).items():
        per_task[task].extend({"ts": m["ts"], "share": m["share"], "timed": m["mock"]} for m in marks)
    for ev in per_task.values():
        ev.sort(key=lambda e: e["ts"], reverse=True)
    units = [unit_readiness(bp, u, per_task) for u in bp.units]
    try:
        from greek_coach import mock
        latest = mock.latest_unit_results(conn, bp.id)
    except Exception:  # no mock tables yet, or a broken mock file: readiness still works
        latest = {}
    for u in units:
        u["mock"] = latest.get(u["unit"])
    return {"exam": bp.id, "short": bp.short, "level": bp.level, "total_points": bp.total_points,
            "pass_rule": bp.pass_rule.model_dump(), "units": units, "verdict": verdict(bp, units),
            "window_days": EVIDENCE_DAYS}


def all_readiness(conn: sqlite3.Connection, catalog: Catalog) -> dict[str, dict]:
    firsts = first_attempts(conn)
    return {bp.id: for_blueprint(conn, catalog, bp, firsts) for bp in exams.load_blueprints().values()}


# ---------- coverage ----------

def coverage(conn: sqlite3.Connection, catalog: Catalog, bp: exams.Blueprint, ui_lang: str = "en") -> dict:
    """Per task: items available, tried, attempts and last practice. Plus the B1 additions."""
    avail = {k: i for k, _, i in servable(catalog, ui_lang)}
    stats = {r["item_key"]: (r["n"], r["last"], r["right"]) for r in conn.execute(
        "SELECT item_key, COUNT(*) AS n, MAX(ts) AS last, AVG(correct) AS right FROM attempts "
        "WHERE correct IS NOT NULL OR item_key IN (SELECT item_key FROM submissions) GROUP BY item_key")}
    need = LEVEL_RANK[bp.level]
    tasks = []
    for u in bp.units:
        for t in u.tasks:
            keys = [k for k, i in avail.items() if i.exam_task == t.id]
            at_level = [k for k in keys if LEVEL_RANK.get(avail[k].level, 0) >= need]
            tried = [k for k in keys if k in stats]
            last = max((stats[k][1] for k in tried), default=None)
            tasks.append({"id": t.id, "unit": u.id, "available": len(keys), "available_at_level": len(at_level),
                          "unseen_at_level": sum(1 for k in at_level if k not in stats),
                          "tried": len(tried), "attempts": sum(stats[k][0] for k in tried),
                          "last": last[:10] if last else None})
    general = defaultdict(lambda: {"available": 0, "tried": 0})
    for k, i in avail.items():
        if isinstance(i, TASK_TYPES) and not i.exam_task:
            general[i.skill]["available"] += 1
            general[i.skill]["tried"] += 1 if k in stats else 0
    beyond = []
    for b in bp.beyond_a2:
        keys = []
        for k, i in avail.items():
            grammar = i.grammar if isinstance(i, FormItem) else []
            if (any(g.startswith(p) for g in grammar for p in b.match.grammar)
                    or any(tp in i.topics for tp in b.match.topics) and LEVEL_RANK.get(i.level, 0) >= need
                    or i.exam_task in b.match.exam_tasks):
                keys.append(k)
        tried = [k for k in keys if k in stats]
        rights = [stats[k][2] for k in tried if stats[k][2] is not None]
        beyond.append({"id": b.id, "area": b.area, "title": b.title.model_dump(), "available": len(keys),
                       "tried": len(tried), "accuracy": round(sum(rights) / len(rights), 3) if rights else None})
    return {"exam": bp.id, "tasks": tasks, "general_practice": dict(general), "beyond_a2": beyond}


def all_coverage(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str = "en") -> dict[str, dict]:
    return {bp.id: coverage(conn, catalog, bp, ui_lang) for bp in exams.load_blueprints().values()}
