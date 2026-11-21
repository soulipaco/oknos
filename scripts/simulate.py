"""Simulate weeks of use with shifted dates, to see the scheduler and the home numbers behave.

    uv run python scripts/simulate.py [--days 14] [--skip 9,10,11,12] [--wrong 0.25] [--seed 1]
    uv run python scripts/simulate.py --days 21 --recent --learner-dir <folder>   # keep a realistic history

Runs in a throwaway learner folder by default (the real learner/ is never touched), on all the
content this checkout has, including private packs. Each simulated day builds the daily session,
answers it (right or wrong at random, with a few word lookups), and prints one line.
At the end it cross-checks the home-screen numbers against a hand count from the database.

With --learner-dir and --recent, the simulated days end yesterday, so the result can be used
to try the coach on a learner with a few weeks of history: the aorist is made a weak spot
(--weak-aorist), and two items get flagged. Writing and speaking cards are skipped; submit
those through the app.
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
    ap.add_argument("--weak-aorist", type=float, default=None, help="wrong rate for aorist verb forms (a weak spot)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--minutes", type=int, default=10)
    ap.add_argument("--learner-dir", default=None, help="use (and keep) this learner folder instead of a temporary one")
    ap.add_argument("--recent", action="store_true", help="end the simulated days yesterday instead of in March 2026")
    ap.add_argument("--flags", action="store_true", help="flag two items along the way, as a learner would")
    args = ap.parse_args()
    if args.learner_dir:
        Path(args.learner_dir).mkdir(parents=True, exist_ok=True)
        os.environ["OKNOS_LEARNER_DIR"] = str(Path(args.learner_dir).resolve())
    else:
        os.environ["OKNOS_LEARNER_DIR"] = tempfile.mkdtemp(prefix="oknos-sim-")
    tmp = os.environ["OKNOS_LEARNER_DIR"]

    from oknos import db, packs, scheduler, session
    from oknos.checking import check
    sys.path.insert(0, str(ROOT / "tests"))
    from test_scheduler import _answer  # the same right/wrong answer helper the tests use

    conn = db.open_db()
    catalog = packs.load_all()
    packs.sync_items(conn, catalog)
    rng = random.Random(args.seed)
    skip = {int(x) for x in args.skip.split(",") if x.strip()}
    start = date.today() - timedelta(days=args.days) if args.recent else date(2026, 3, 2)
    print(f"learner folder: {tmp}")
    print(f"content: {len(catalog.packs)} packs, {len(catalog.items)} items\n")
    print("day        cards  review verbs task new | wrong  back-from-yesterday | due tomorrow | stage (learned/core)")
    from oknos import curriculum
    wrong_before: set[str] = set()
    flag_days = {3: "confusing", 8: "wrong"} if args.flags else {}
    for n in range(args.days):
        day = start + timedelta(days=n)
        if n in skip:
            print(f"{day}   (no practice)")
            continue
        db.set_clock(lambda d=day: datetime(d.year, d.month, d.day, 8, 0))
        # Read first (phase 5c): a stage with an unread chapter gets read before the session.
        action = curriculum.next_action(curriculum.progress(conn, catalog), "fresh", 0)
        read = ""
        if action["kind"] == "read":
            ch = catalog.chapter(curriculum.active(catalog).id, action["stage"])
            curriculum.mark_read(conn, curriculum.active(catalog).id, action["stage"], ch.version, finished=True)
            read = f"  (read the chapter of {action['stage']})"
        s = session.build(conn, catalog, "en", args.minutes, rng=rng)
        seg = Counter(c["segment"] for c in s["cards"])
        keys = {c["item_key"] for c in s["cards"]}
        wrong: set[str] = set()
        for i, card in enumerate(s["cards"]):
            db.set_clock(lambda d=day, i=i: datetime(d.year, d.month, d.day, 8, 0) + timedelta(seconds=20 * i))
            item = catalog.items[card["item_key"]][1]
            rate = args.wrong
            if args.weak_aorist is not None and item.type == "form" and item.cue and item.cue.tense == "aorist":
                rate = args.weak_aorist
            right = rng.random() >= rate
            response = _answer(card, item, right) if item.type not in ("write", "speak") else {"skipped": True}
            result = check(item, card, response)
            lookups = 1 if rng.random() < 0.05 else 0
            with conn:
                conn.execute(
                    "INSERT INTO attempts(session_id, item_key, ts, response_json, score, correct, latency_ms, lookups) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (s["session_id"], card["item_key"], db.now(),
                     json.dumps({"card": card, "response": response}, ensure_ascii=False),
                     result.score, None if result.correct is None else int(result.correct),
                     rng.randint(6000, 30000), lookups))
                if result.correct is not None:
                    scheduler.record(conn, card["item_key"], item.type, result.correct, result.score, lookups=lookups)
                if lookups and item.type == "vocab":
                    conn.execute("INSERT INTO lookups(ts, item_key, word, found) VALUES (?, ?, ?, ?)",
                                 (db.now(), None, item.el.split()[-1], card["item_key"]))
            if result.correct is False:
                wrong.add(card["item_key"])
        if n in flag_days:
            pick = next((c for c in s["cards"] if c["type"] != "vocab" or flag_days[n] == "confusing"), s["cards"][0])
            with conn:
                conn.execute("INSERT INTO flags(ts, item_key, reason, note) VALUES (?, ?, ?, ?)",
                             (db.now(), pick["item_key"], flag_days[n], "simulated flag"))
        session.end(conn, s["session_id"])
        srs_wrong = {k for k in wrong_before if catalog.items[k][1].type in ("vocab", "form")}
        back = f"{len(srs_wrong & keys)}/{len(srs_wrong)}" if srs_wrong else "-"
        due_tomorrow = len(scheduler.due(conn, day + timedelta(days=1)))
        prog = curriculum.progress(conn, catalog)
        where = f"{prog.stages[prog.current]['id']} ({prog.stages[prog.current]['learned']}/{prog.stages[prog.current]['core']})" if prog else "-"
        print(f"{day}   {len(s['cards']):5}  {seg['review']:6} {seg['verbs']:5} {seg['task']:4} {seg['new']:3} | "
              f"{len(wrong):5}  {back:>19} | {due_tomorrow:12} | {where}{read}")
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

    # Readiness per exam unit (SPEC §5.3): what the exam screen would show on the last day.
    from oknos import readiness
    print("\nreadiness (first attempts only, last 90 days):")
    for exam, r in readiness.all_readiness(conn, catalog).items():
        print(f"  {exam}: verdict {r['verdict']['state']}")
        for u in r["units"]:
            nums = (f"{u['estimate']} [{u['low']}-{u['high']}] of {u['points']}, line {u['pass_line']}"
                    if u["estimate"] is not None else f"no number ({u['reason']})")
            print(f"    {u['unit']:<10} {u['state']:<12} n={u['evidence']:<3} {nums}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
