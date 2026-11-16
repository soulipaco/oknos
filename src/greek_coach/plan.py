"""The numbers behind the plan to the exam date (docs/SPEC.md §6, the `plan` skill).

The coach writes `coach/plan.json`. The app supplies what the plan must rest on, in the report
(`plan_inputs`), and checks what actually happened against it (`plan_progress`):

- the candidate sessions: the real dates in coach/watch.json, matched to the blueprints;
- the learner's real pace (minutes per week over the last 4 weeks) next to the budget;
- the hours practised so far, and ΚΕΓ's rough teaching-hour estimates per level;
- per candidate session, the hours there is time for at the real pace, and a rough hint.

The hint is deliberately crude: teaching hours in a class are not minutes in an app. It is
there so the coach cannot write "realistic" for a session the arithmetic rules out.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

from greek_coach import coachfiles, db, exams

PACE_WEEKS = 4
MINUTE_CAP_MS = 120_000  # one answer counts at most 2 minutes, as on the home screen


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def minutes_between(conn: sqlite3.Connection, start: date, end: date) -> float:
    """Answering time from start (inclusive) to end (exclusive), as on the home screen."""
    ms = conn.execute(
        "SELECT SUM(MIN(COALESCE(latency_ms, 20000), ?)) FROM attempts WHERE substr(ts,1,10) >= ? AND substr(ts,1,10) < ?",
        (MINUTE_CAP_MS, start.isoformat(), end.isoformat())).fetchone()[0]
    return round((ms or 0) / 60000, 1)


def budget_minutes_week(profile: dict) -> int | None:
    minutes = profile.get("minutes")
    if not isinstance(minutes, int):
        return None
    days = profile.get("days_per_week")
    days = days if isinstance(days, int) and 1 <= days <= 7 else 7
    return minutes * days


def pace(conn: sqlite3.Connection, today: date) -> dict:
    this_week = monday(today)
    weeks = []
    for i in range(PACE_WEEKS, 0, -1):
        start = this_week - timedelta(days=7 * i)
        weeks.append({"start": start.isoformat(), "minutes": minutes_between(conn, start, start + timedelta(days=7))})
    first = conn.execute("SELECT MIN(substr(ts,1,10)) FROM attempts").fetchone()[0]
    total = minutes_between(conn, date(2000, 1, 1), today + timedelta(days=1))
    practised_weeks = [w["minutes"] for w in weeks if first and w["start"] >= monday(date.fromisoformat(first)).isoformat()]
    return {
        "weeks": weeks,
        "minutes_week": round(sum(practised_weeks) / len(practised_weeks), 1) if practised_weeks else None,
        "this_week_so_far": minutes_between(conn, this_week, today + timedelta(days=1)),
        "hours_total": round(total / 60, 1),
        "first_practice": first,
    }


def _exam_of(entry: coachfiles.WatchEntry, bps: dict) -> str | None:
    if entry.exam in bps:
        return entry.exam
    text = f"{entry.what} {entry.what_tr or ''}".lower()
    if "b1" in text or "β1" in text:
        return "b1-keg" if "b1-keg" in bps else None
    if "a2" in text and ("history" in text or "residence" in text or "ιστορ" in text):
        return "a2ltr" if "a2ltr" in bps else None
    return None


def inputs(conn: sqlite3.Connection, profile: dict, readiness: dict | None = None) -> dict:
    """What the coach must base the plan on. Never invents a date: only watch.json's."""
    today = db.today()
    bps = exams.load_blueprints()
    p = pace(conn, today)
    budget = budget_minutes_week(profile)
    watch = coachfiles.watch()
    candidates: list[dict[str, Any]] = []
    for e in watch.entries if watch else []:
        if e.kind != "exam":
            continue
        exam = _exam_of(e, bps)
        if not exam or not e.date or e.date < today.isoformat():
            continue
        bp = bps[exam]
        weeks_left = round((date.fromisoformat(e.date) - today).days / 7, 1)
        lo, hi = bp.hours_estimate
        done = p["hours_total"]
        need = [max(0.0, lo - done), max(0.0, hi - done)]
        at_pace = round(weeks_left * (p["minutes_week"] or 0) / 60, 1)
        at_budget = round(weeks_left * budget / 60, 1) if budget else None
        hint_budget = (None if at_budget is None else "yes" if at_budget >= need[1]
                       else "tight" if at_budget >= need[0] else "no")
        verdict = (readiness or {}).get(exam, {}).get("verdict", {}).get("state")
        if verdict == "pass":
            hint = "yes"
        elif at_pace >= need[1]:
            hint = "yes"
        elif at_pace >= need[0]:
            hint = "tight"
        elif at_budget is not None and at_budget >= need[0]:
            hint = "only_at_budget"   # possible if the budget is really kept, which it is not yet
        else:
            hint = "no"
        closes = e.registration.closes if e.registration else None
        candidates.append({
            "exam": exam, "what": e.what, "date": e.date, "registration_opens": e.registration.opens if e.registration else None,
            "registration_closes": closes, "registration_open_now": bool(e.registration and (e.registration.opens or "") <= today.isoformat() <= (closes or "")),
            "source_url": e.source_url, "weeks_left": weeks_left,
            "hours_needed": [round(need[0]), round(need[1])], "hours_at_pace": at_pace, "hours_at_budget": at_budget,
            "hint": hint,
            "hint_at_budget": hint_budget,   # if the budget were kept every week from now on
            "pace_measured": p["minutes_week"] is not None,
        })
    candidates.sort(key=lambda c: c["date"])
    no_date = [bp.id for bp in bps.values() if bp.id not in {c["exam"] for c in candidates}]
    return {
        "today": today.isoformat(),
        "budget_minutes_week": budget,
        "budget_source": "profile.minutes × profile.days_per_week (7 if missing)",
        "pace": p,
        "hours_estimate": {bp.id: bp.hours_estimate for bp in bps.values()},
        "hours_note": "ΚΕΓ teaching-hour estimates, cumulative from zero; minutes in the app are not class hours. A rough guide only.",
        "candidates": candidates,
        "exams_without_announced_date": no_date,
        "watch_checked_at": watch.checked_at if watch else None,
    }


def progress(conn: sqlite3.Connection, catalog, plan: coachfiles.Plan | None = None) -> dict | None:
    """Planned against done for every plan week up to this one, and the next weeks."""
    plan = plan or coachfiles.plan()
    if plan is None:
        return None
    today = db.today()
    bp = exams.load_blueprints().get(plan.exam)
    unit_of_task = {t.id: u.id for u in bp.units for t in u.tasks} if bp else {}
    this_week = monday(today).isoformat()
    past, upcoming = [], []
    for w in plan.weeks:
        start = date.fromisoformat(w.start)
        if w.start > this_week:
            upcoming.append(w.model_dump())
            continue
        end = start + timedelta(days=7)
        done = minutes_between(conn, start, min(end, today + timedelta(days=1)))
        touched: dict[str, int] = {}
        for r in conn.execute("SELECT item_key FROM attempts WHERE substr(ts,1,10) >= ? AND substr(ts,1,10) < ?",
                              (start.isoformat(), end.isoformat())):
            entry = catalog.items.get(r["item_key"])
            if not entry:
                continue
            item = entry[1]
            unit = unit_of_task.get(item.exam_task) or ("foundations" if item.type in ("vocab", "form") else None)
            if unit:
                touched[unit] = touched.get(unit, 0) + 1
        current = w.start == this_week or (start <= today < end)
        state = "current" if current else "done" if done >= 0.8 * w.minutes else "short"
        past.append({**w.model_dump(), "done_minutes": done, "practised": touched,
                     "missed_focus": [f for f in w.focus if not touched.get(f)], "state": state})
    behind_weeks = sum(1 for w in past if w["state"] == "short")
    return {"made_at": plan.made_at, "exam": plan.exam, "verdict": plan.verdict.model_dump(),
            "target": plan.target.model_dump() if plan.target else None,
            "weeks_so_far": past, "next_weeks": upcoming[:4], "short_weeks": behind_weeks,
            "stale": (today - date.fromisoformat(plan.made_at)).days > 14}
