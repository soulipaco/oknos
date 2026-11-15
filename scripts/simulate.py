"""Simulate weeks of use with shifted dates, to see the scheduler and the home numbers behave.

    uv run python scripts/simulate.py [--days 14] [--skip 9,10,11,12] [--wrong 0.25] [--seed 1]

Runs in a throwaway learner folder (the real learner/ is never touched), on all the content
this checkout has, including private packs. Each simulated day builds the daily session,
answers it (right or wrong at random, with a few word lookups), and prints one line.
At the end it cross-checks the home-screen numbers against a hand count from the database.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tempfile
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--skip", default="9,10,11,12", help="day numbers (0-based) with no practice")
    ap.add_argument("--wrong", type=float, default=0.25, help="share of answers given wrongly")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--minutes", type=int, default=10)
    args = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="greek-coach-sim-")
    os.environ["GREEK_COACH_LEARNER_DIR"] = tmp

    from greek_coach import db, packs, scheduler, session
    from greek_coach.checking import check
    sys.path.insert(0, str(ROOT / "tests"))
    from test_scheduler import _answer  # the same right/wrong answer helper the tests use

    conn = db.open_db()
    catalog = packs.load_all()
    packs.sync_items(conn, catalog)
    rng = random.Random(args.seed)
    skip = {int(x) for x in args.skip.split(",") if x.strip()}
    start = date(2026, 3, 2)
    print(f"learner folder: {tmp}")
    print(f"content: {len(catalog.packs)} packs, {len(catalog.items)} items\n")
    print("day        cards  review verbs task new | wrong  back-from-yesterday | due tomorrow")
    wrong_before: set[str] = set()
    for n in range(args.days):
        day = start + timedelta(days=n)
        if n in skip:
            print(f"{day}   (no practice)")
            continue
        db.set_clock(lambda d=day: datetime(d.year, d.month, d.day, 8, 0))
        s = session.build(conn, catalog, "en", args.minutes, rng=rng)
        seg = Counter(c["segment"] for c in s["cards"])
        keys = {c["item_key"] for c in s["cards"]}
        wrong: set[str] = set()
        for card in s["cards"]:
            item = catalog.items[card["item_key"]][1]
            right = rng.random() >= args.wrong
            result = check(item, card, _answer(card, item, right))
            lookups = 1 if rng.random() < 0.05 else 0
            with conn:
                conn.execute(
                    "INSERT INTO attempts(session_id, item_key, ts, response_json, score, correct, latency_ms, lookups) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (s["session_id"], card["item_key"], db.now(), json.dumps({"card": card}, ensure_ascii=False),
                     result.score, int(result.correct),
                     rng.randint(6000, 30000), lookups))
                scheduler.record(conn, card["item_key"], item.type, result.correct, result.score, lookups=lookups)
            if not result.correct:
                wrong.add(card["item_key"])
        session.end(conn, s["session_id"])
        srs_wrong = {k for k in wrong_before if catalog.items[k][1].type in ("vocab", "form")}
        back = f"{len(srs_wrong & keys)}/{len(srs_wrong)}" if srs_wrong else "-"
        due_tomorrow = len(scheduler.due(conn, day + timedelta(days=1)))
        print(f"{day}   {len(s['cards']):5}  {seg['review']:6} {seg['verbs']:5} {seg['task']:4} {seg['new']:3} | "
              f"{len(wrong):5}  {back:>19} | {due_tomorrow}")
        wrong_before = wrong

    end = start + timedelta(days=args.days - 1)
    db.set_clock(lambda: datetime(end.year, end.month, end.day, 21, 0))
    stats = session.home_stats(conn, catalog, "en")
    print("\nhome screen on", end)
    print("  due now:", stats["due"], "| new words available:", stats["new_available"])
    print("  words:", stats["words"], "| verbs:", stats["verbs"])
    print("  practised on", stats["days_studied_14"], "of the last 14 days; retention", stats["retention"])
    print("  weakest:", stats["weakest"])
    for a in stats["areas"]:
        print(f"    {a['area']:<22} {a['accuracy']:.0%}  n={a['n']}{'' if a['enough'] else '  (not enough yet)'}")
    longest = conn.execute("SELECT MAX(interval_days), AVG(ease) FROM review_state").fetchone()
    print(f"  longest interval {longest[0]} days, mean ease {longest[1]:.2f}")

    # Cross-check the dashboard against the raw attempts.
    by_day = dict(conn.execute("SELECT substr(ts,1,10), COUNT(*) FROM attempts GROUP BY 1").fetchall())
    assert all(c["answers"] == by_day.get(c["date"], 0) for c in stats["grid"]), "grid does not match attempts"
    vocab = conn.execute("SELECT correct FROM attempts a JOIN items i USING(item_key) WHERE i.type='vocab'").fetchall()
    area = next(a for a in stats["areas"] if a["area"] == "vocab")
    assert area["n"] == len(vocab) and abs(area["accuracy"] - sum(r[0] for r in vocab) / len(vocab)) < 1e-3
    print("\ncross-check: grid, vocabulary accuracy and counts match the attempts table.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
