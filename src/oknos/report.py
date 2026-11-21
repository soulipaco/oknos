"""`oknos report`: one JSON document the coach reads instead of the database (SPEC §5.2).

Read-only. It is the stable contract between app and agent: add fields freely, but do not
rename or remove them without updating docs/COACHING.md and the skills.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from oknos import coachfiles, curriculum, db, mock, paths, plan, readiness, scheduler, session
from oknos.packs import Catalog, FormItem, SELECTION_TASKS, SpeakItem, VocabItem, WriteItem

REPORT_VERSION = 4  # 3: chapters (phase 5c); 4: tap_a_word (phase 5d)
PROFILE_QUESTIONS = ("ui_lang", "minutes", "goal", "target_exam", "interests")


def _read_profile() -> dict:
    try:
        data = coachfiles.read_json(paths.profile_path())
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def item_summary(catalog: Catalog, key: str) -> dict[str, Any] | None:
    """The item as the coach needs it to judge or fix it: its content plus where it lives."""
    entry = catalog.items.get(key)
    if entry is None:
        return None
    pack, item = entry
    data = item.model_dump(mode="json", exclude_defaults=True)
    data.update(type=item.type, level=item.level, skill=item.skill)
    try:
        where = str(pack.path.relative_to(paths.REPO_ROOT))
    except ValueError:
        where = str(pack.path)
    return {"key": key, "pack": pack.id, "visibility": pack.manifest.visibility, "pack_path": where, "item": data}


def _rate(values: list[float]) -> dict[str, Any]:
    return {"rate": round(sum(values) / len(values), 3), "n": len(values)} if values else {"rate": None, "n": 0}


def _since(today: date, days: int) -> str:
    return (today - timedelta(days=days - 1)).isoformat()


def activity(conn: sqlite3.Connection, today: date, days: int) -> dict:
    since = _since(today, days)
    per_day = {r["d"]: {"answers": r["n"], "minutes": round(r["ms"] / 60000, 1)} for r in conn.execute(
        "SELECT substr(ts,1,10) AS d, COUNT(*) AS n, SUM(MIN(COALESCE(latency_ms, 20000), 120000)) AS ms "
        "FROM attempts WHERE ts >= ? GROUP BY d", (since,))}
    sessions = Counter(r["d"] for r in conn.execute(
        "SELECT substr(started_at,1,10) AS d FROM sessions WHERE started_at >= ? AND items_done > 0", (since,)))
    daily = []
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        daily.append({"date": d, "sessions": sessions.get(d, 0), **per_day.get(d, {"answers": 0, "minutes": 0})})
    last = conn.execute("SELECT MAX(substr(ts,1,10)) FROM attempts").fetchone()[0]
    first = conn.execute("SELECT MIN(substr(ts,1,10)) FROM attempts").fetchone()[0]
    return {
        "days": daily,
        "days_practised": sum(1 for d in daily if d["answers"]),
        "minutes": round(sum(d["minutes"] for d in daily), 1),
        "answers": sum(d["answers"] for d in daily),
        "answers_all_time": conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0],
        "first_practice": first,
        "last_practice": last,
        "days_since_last_practice": (today - date.fromisoformat(last)).days if last else None,
    }


def accuracy(conn: sqlite3.Connection, catalog: Catalog, today: date, days: int) -> dict:
    groups: dict[str, dict[str, list[float]]] = {k: defaultdict(list) for k in
                                                 ("area", "skill", "exam_task", "topic", "grammar", "level", "pack")}
    for r in conn.execute("SELECT item_key, score, correct FROM attempts WHERE ts >= ? AND correct IS NOT NULL",
                          (_since(today, days),)):
        entry = catalog.items.get(r["item_key"])
        if not entry:
            continue
        pack, item = entry
        c = float(r["correct"])
        groups["area"][session._area(item)].append(c)
        groups["skill"][item.skill].append(c)
        groups["level"][item.level].append(c)
        groups["pack"][pack.id].append(c)
        if item.exam_task:
            groups["exam_task"][item.exam_task].append(c)
        for t in item.topics:
            if not t.startswith("unit:"):
                groups["topic"][t].append(c)
        if isinstance(item, FormItem):
            for g in item.grammar:
                groups["grammar"][g].append(c)
    out = {}
    for name, g in groups.items():
        rows = [{"key": k, **_rate(v)} for k, v in g.items()]
        out[name] = sorted(rows, key=lambda x: (x["n"] < session.EVIDENCE_MIN, x["rate"]))
    out["evidence_min"] = session.EVIDENCE_MIN
    return out


def recent_wrong(conn: sqlite3.Connection, catalog: Catalog, today: date, days: int, limit: int = 40) -> list[dict]:
    out = []
    for r in conn.execute(
        "SELECT item_key, ts, response_json, score, accent_note, lookups FROM attempts "
        "WHERE ts >= ? AND correct = 0 ORDER BY id DESC LIMIT ?", (_since(today, days), limit)
    ):
        entry = catalog.items.get(r["item_key"])
        if not entry:
            continue
        try:
            rec = json.loads(r["response_json"])
        except ValueError:
            rec = {}
        card = rec.get("card", {})
        out.append({
            "key": r["item_key"], "ts": r["ts"], "type": entry[1].type, "score": r["score"],
            "direction": card.get("direction"), "given": rec.get("response"),
            "right": _right_answer(entry[1], card),
        })
    return out


def _right_answer(item, card: dict) -> Any:
    if isinstance(item, VocabItem):
        return {"el": item.el, "en": item.en, "tr": item.tr}
    if isinstance(item, FormItem):
        return {"text": item.text, "answer": item.answer, "cue": item.cue.model_dump(exclude_none=True) if item.cue else None}
    data = item.model_dump(mode="json", exclude_defaults=True)
    return {k: data[k] for k in ("prompt", "options", "answer", "statements", "left", "right", "bank", "text",
                                  "categories", "items", "columns", "rows") if k in data}


def hardest(conn: sqlite3.Connection, catalog: Catalog, limit: int = 15) -> list[dict]:
    out = []
    for r in conn.execute("SELECT item_key, lapses, reps, ease, due_at FROM review_state WHERE lapses >= 2 "
                          "ORDER BY lapses DESC, ease LIMIT ?", (limit,)):
        entry = catalog.items.get(r["item_key"])
        if entry:
            out.append({"key": r["item_key"], "lapses": r["lapses"], "ease": round(r["ease"], 2), "due": r["due_at"],
                        "right": _right_answer(entry[1], {})})
    return out


def lookups(conn: sqlite3.Connection, today: date, days: int, limit: int = 20) -> list[dict]:
    rows = conn.execute("SELECT word, found, COUNT(*) AS n FROM lookups WHERE ts >= ? GROUP BY word "
                        "ORDER BY n DESC, word LIMIT ?", (_since(today, days), limit)).fetchall()
    return [{"word": r["word"], "times": r["n"], "explained_by": r["found"]} for r in rows]


def covered(conn: sqlite3.Connection, catalog: Catalog, with_words: bool) -> dict:
    states = scheduler.all_states(conn)
    attempted = {r[0] for r in conn.execute("SELECT DISTINCT item_key FROM attempts")}
    seen = set(states) | attempted
    words = {"learning": 0, "known": 0, "by_level": Counter()}
    word_list = []
    verbs: dict[str, set[str]] = defaultdict(set)
    units: set[str] = set()
    task_types = Counter()
    for key in seen:
        entry = catalog.items.get(key)
        if not entry:
            continue
        pack, item = entry
        if isinstance(item, VocabItem):
            known = key in states and states[key].interval_days >= scheduler.KNOWN_DAYS
            words["known" if known else "learning"] += 1
            words["by_level"][item.level] += 1
            units.update(t[5:] for t in item.topics if t.startswith("unit:"))
            if with_words:
                word_list.append({"el": item.el, "status": "known" if known else "learning", "level": item.level})
        elif isinstance(item, FormItem) and item.cue and item.cue.lemma:
            verbs[item.cue.lemma].add(item.cue.tense or "?")
        else:
            task_types[item.type] += 1
    out = {
        "words": {**{k: v for k, v in words.items() if k != "by_level"}, "by_level": dict(words["by_level"])},
        "verbs": {lemma: sorted(t) for lemma, t in sorted(verbs.items())},
        "book_units_met": sorted(units),
        "task_types_done": dict(task_types),
    }
    if with_words:
        out["word_list"] = sorted(word_list, key=lambda w: w["el"])
    return out


def open_flags(conn: sqlite3.Connection, catalog: Catalog) -> list[dict]:
    done = coachfiles.resolved_flag_ids()
    out = []
    for r in conn.execute("SELECT * FROM flags WHERE resolved_at IS NULL ORDER BY id"):
        if r["id"] in done:
            continue
        if r["item_key"].startswith("chapter:"):
            out.append({"flag_id": r["id"], "ts": r["ts"], "reason": r["reason"], "note": r["note"],
                        "chapter": chapter_flag_target(catalog, r["item_key"])})
            continue
        out.append({"flag_id": r["id"], "ts": r["ts"], "reason": r["reason"], "note": r["note"],
                    "item": item_summary(catalog, r["item_key"]) or {"key": r["item_key"], "missing": True}})
    return out


def chapter_flag_target(catalog: Catalog, key: str) -> dict:
    """A flag on a chapter section ("chapter:<curriculum>/<stage>#<section>"): the file and the section."""
    cur_stage, _, section = key[len("chapter:"):].partition("#")
    cur_id, _, stage = cur_stage.partition("/")
    entry = catalog.chapters.get((cur_id, stage))
    out: dict[str, Any] = {"key": key, "curriculum": cur_id, "stage": stage, "section": int(section or 0)}
    if entry is None:
        out["missing"] = True
        return out
    pack, ch = entry
    try:
        out["file"] = str((pack.path / "lessons" / f"{stage}.json").relative_to(paths.REPO_ROOT))
    except ValueError:
        out["file"] = str(pack.path / "lessons" / f"{stage}.json")
    if 0 <= out["section"] < len(ch.sections):
        out["content"] = ch.sections[out["section"]].model_dump(exclude_defaults=True)
    return out


def chapters_state(conn: sqlite3.Connection, catalog: Catalog) -> dict:
    """Which stages of the active curriculum have a chapter, and which the learner has read."""
    cur = curriculum.active(catalog)
    if cur is None:
        return {"curriculum": None, "stages": []}
    reads = curriculum.chapter_reads(conn, cur.id)
    stages = []
    for s in cur.stages:
        ch = catalog.chapter(cur.id, s.id)
        r = reads.get(s.id)
        stages.append({"stage": s.id, "chapter": ch is not None,
                       "version": ch.version if ch else None,
                       "opened_at": r["opened_at"] if r else None, "finished_at": r["finished_at"] if r else None,
                       "sections_seen": len(json.loads(r["sections_json"])) if r else 0,
                       "sections": len(ch.sections) if ch else 0})
    return {"curriculum": cur.id, "with_chapter": sum(1 for x in stages if x["chapter"]),
            "read": sum(1 for x in stages if x["finished_at"]), "stages": stages}


def submissions(conn: sqlite3.Connection, catalog: Catalog) -> dict:
    pending, marked = [], 0
    for r in conn.execute("SELECT * FROM submissions ORDER BY id"):
        if r["status"] == "marked" or coachfiles.feedback(r["id"]):
            marked += 1
            continue
        entry = catalog.items.get(r["item_key"])
        item = entry[1] if entry else None
        task: dict[str, Any] = {}
        if isinstance(item, (WriteItem, SpeakItem)):
            task = item.model_dump(mode="json", exclude_defaults=True)
        rec: dict[str, Any] = {"submission_id": r["id"], "kind": r["kind"], "ts": r["ts"], "item_key": r["item_key"],
                               "task": task, "feedback_file": f"feedback/{r['id']}.json"}
        if r["kind"] == "writing":
            rec.update(text=r["text"], word_count=r["word_count"])
        else:
            tr = coachfiles.transcript(r["id"])
            rec.update(recording=r["recording_path"], transcript=tr.get("text") if tr else None,
                       transcribed=bool(tr))
        pending.append(rec)
    return {"pending": pending, "marked": marked}


def generated_stock(conn: sqlite3.Connection, catalog: Catalog) -> list[dict]:
    seen = {r[0] for r in conn.execute("SELECT item_key FROM review_state UNION SELECT DISTINCT item_key FROM attempts")}
    out = []
    for pack in catalog.packs:
        if pack.manifest.visibility != "generated":
            continue
        keys = [f"{pack.id}/{i}" for i in pack.items]
        unseen = [k for k in keys if k not in seen]
        out.append({"pack": pack.id, "items": len(keys), "unseen": len(unseen),
                    "unseen_by_type": dict(Counter(catalog.items[k][1].type for k in unseen)),
                    "needs_review": sum(1 for i in pack.items.values() if i.status != "ok")})
    return out


def inbox() -> list[dict]:
    folder = coachfiles.inbox_dir()
    if not folder.is_dir():
        return []
    out = []
    for p in sorted(folder.iterdir()):
        if p.is_file() and not p.name.startswith("."):
            out.append({"file": f"inbox/{p.name}", "bytes": p.stat().st_size})
    return out


def coach_state(today: date) -> dict:
    cdir = coachfiles.coach_dir()
    msg = coachfiles.message()
    notes = cdir / "notes.md"
    watch = coachfiles.watch()
    watch_age = None
    if watch:
        try:
            watch_age = (today - date.fromisoformat(watch.checked_at[:10])).days
        except ValueError:
            pass
    logs = sorted((cdir / "tutor-log").glob("*.md")) if (cdir / "tutor-log").is_dir() else []
    return {
        "last_checkin": msg.date if msg else None,
        "notes_file": "coach/notes.md" if notes.is_file() else None,
        "watch_checked_at": watch.checked_at if watch else None,
        "watch_age_days": watch_age,
        "tutor_logs": [f"coach/tutor-log/{p.name}" for p in logs[-5:]],
        "runs": coachfiles.runs(limit=10),
        "run_problems": coachfiles.run_problems(),
        "schedule": coachfiles.schedule().model_dump() if coachfiles.schedule() else None,
    }


def mocks_state(conn: sqlite3.Connection, catalog: Catalog) -> dict:
    mock.expire(conn, catalog)
    return {"defined": mock.definitions(catalog), "runs": mock.runs(conn, catalog, limit=10),
            "reserved_items": len(mock.reserved_keys(conn))}


def tap_a_word(catalog: Catalog) -> dict:
    """How many of the Greek words on screen find a meaning when tapped (phase 5d). The coach
    fills the gaps: `oknos words <pack> --write`, then glossary entries for the rest."""
    from oknos import lookup, wordscan

    gaps = wordscan.scan(catalog.packs, lookup.Index(catalog))
    by_pack: dict[str, int] = {}
    for place, words in gaps.missing.items():
        n = len([w for w in words if w not in gaps.left])
        if n:
            by_pack[place.split("/")[0]] = by_pack.get(place.split("/")[0], 0) + n
    return {"total": gaps.total, "unexplained": len(gaps.unexplained), "share": round(gaps.share, 4),
            "left_on_purpose": len(gaps.unexplained) - len(gaps.without_reason), "by_pack": by_pack,
            "sample": sorted(gaps.without_reason)[:30]}


def build(conn: sqlite3.Connection, catalog: Catalog, days: int = 14, with_words: bool = False) -> dict:
    today = db.today()
    profile = _read_profile()
    ready = readiness.all_readiness(conn, catalog)
    return {
        "report_version": REPORT_VERSION,
        "generated_at": db.now(),
        "today": today.isoformat(),
        "learner_dir": str(paths.learner_dir()),
        "window_days": days,
        "profile": profile,
        "profile_missing": [k for k in PROFILE_QUESTIONS if not profile.get(k)],
        "activity": activity(conn, today, days),
        "accuracy": accuracy(conn, catalog, today, days),
        "recent_wrong": recent_wrong(conn, catalog, today, days),
        "hardest": hardest(conn, catalog),
        "lookups": lookups(conn, today, days),
        "covered": covered(conn, catalog, with_words),
        "due": session.home_stats(conn, catalog, profile.get("ui_lang") or "en")["due"],
        "open_flags": open_flags(conn, catalog),
        "submissions": submissions(conn, catalog),
        "generated_stock": generated_stock(conn, catalog),
        "inbox": inbox(),
        "coach": coach_state(today),
        "curriculum": curriculum.summary(conn, catalog),
        "chapters": chapters_state(conn, catalog),
        "readiness": ready,
        "readiness_rules": {"first_attempts_only": True, "window_days": readiness.EVIDENCE_DAYS,
                            "per_task_max": readiness.PER_TASK_MAX, "unit_min": readiness.UNIT_MIN,
                            "coach_min": readiness.COACH_MIN, "interval": "Wilson 80%, n = items"},
        "coverage": readiness.all_coverage(conn, catalog, profile.get("ui_lang") or "en"),
        "plan_inputs": plan.inputs(conn, profile, ready),
        "plan_progress": plan.progress(conn, catalog),
        "mocks": mocks_state(conn, catalog),
        "tap_a_word": tap_a_word(catalog),
        "content": {"packs": [{"id": p.id, "visibility": p.manifest.visibility, "items": len(p.items)} for p in catalog.packs],
                    "problems": catalog.problems[:20]},
    }


def parse_days(text: str) -> int:
    text = text.strip().lower()
    if text.endswith("d"):
        text = text[:-1]
    elif text.endswith("w"):
        return int(text[:-1]) * 7
    days = int(text)
    if not 1 <= days <= 365:
        raise ValueError("the window must be 1 to 365 days")
    return days
