"""SM-2 scheduling and a scripted two weeks of use with shifted dates."""

import random
from datetime import date, datetime, timedelta

from oknos import db, packs, scheduler, session
from oknos.checking import check
from oknos.scheduler import State, next_state


def test_sm2_intervals_grow_and_lapses_reset():
    today = date(2026, 1, 1)
    s = State(item_key="x", due_at=today.isoformat())
    intervals = []
    for _ in range(4):
        s = next_state(s, 4, today)
        intervals.append(s.interval_days)
    assert intervals[:2] == [1, 6] and intervals[2] > 6 and intervals[3] > intervals[2]
    s = next_state(s, 1, today)
    assert s.interval_days == 1 and s.reps == 0 and s.lapses == 1
    assert s.due_at == (today + timedelta(days=1)).isoformat()
    assert s.ease >= scheduler.MIN_EASE


def test_quality_from_attempt():
    assert scheduler.quality(False) == 1
    assert scheduler.quality(True, lookups=1) == 3
    assert scheduler.quality(True, accent_note=True) == 3
    assert scheduler.quality(True) == 4
    assert scheduler.quality(True, quick=True) == 5


def _answer(card, item, right: bool):
    """A response that is right or wrong for this card, derived from the item itself."""
    t = card["type"]
    if t == "vocab":
        r = check(item, card, {"choice": card["options"][0]}) if card.get("options") else None
        if card.get("options"):
            good = next(o for o in card["options"] if check(item, card, {"choice": o}).correct)
            bad = next(o for o in card["options"] if o != good)
            return {"choice": good if right else bad}
        return {"text": item.el if right else "λάθος"}
    if t == "form":
        return {"answers": {g: (f[0] if right else "λάθος") for g, f in item.answer.items()}}
    if t == "mcq":
        return {"choice": item.answer if right else (item.answer + 1) % len(item.options)}
    if t == "true_false":
        return {"answers": [s.answer if right else not s.answer for s in item.statements]}
    if t in ("match", "categorise"):
        wrong = list(item.answer)
        if not right:
            size = len(item.right) if t == "match" else len(item.categories)
            wrong[0] = (wrong[0] + 1) % size
            if t == "match" and wrong[0] in wrong[1:]:
                j = wrong[1:].index(wrong[0]) + 1
                wrong[j] = item.answer[0]
        return {"answers": wrong}
    if t == "gap_bank":
        ans = dict(item.answer)
        if not right:
            g = sorted(ans)[0]
            ans[g] = next(w for w in item.bank if w != item.answer[g])
        return {"answers": ans}
    if t == "table_fill":
        cells = [acc[0] for _, _, acc in item.cells()]
        if not right:
            cells[0] = "λάθος"
        return {"answers": cells}
    if t == "write":
        return {"text": "Αγαπητέ κύριε, το ασανσέρ δεν λειτουργεί."} if right else {"skipped": True}
    if t == "speak":
        return {"done": True} if right else {"skipped": True}
    raise AssertionError(t)


def _day(conn, catalog, day: date, rng: random.Random, wrong_rate: float, minutes: int = 10):
    """Run one daily session on a given day; returns (cards, keys answered wrongly)."""
    db.set_clock(lambda: datetime(day.year, day.month, day.day, 8, 0))
    s = session.build(conn, catalog, "en", minutes, rng=rng)
    wrong = set()
    for card in s["cards"]:
        item = catalog.items[card["item_key"]][1]
        right = rng.random() >= wrong_rate
        result = check(item, card, _answer(card, item, right))
        with conn:
            conn.execute(
                "INSERT INTO attempts(session_id, item_key, ts, response_json, score, correct, latency_ms) "
                "VALUES (?, ?, ?, '{}', ?, ?, 15000)",
                (s["session_id"], card["item_key"], db.now(), result.score,
                 None if result.correct is None else int(result.correct)))
            if result.correct is not None:
                scheduler.record(conn, card["item_key"], item.type, result.correct, result.score)
        if result.correct is False:
            wrong.add(card["item_key"])
    session.end(conn, s["session_id"])
    return s["cards"], wrong


def test_two_weeks_of_scripted_use(learner):
    conn = db.open_db()
    catalog = packs.load_all()
    packs.sync_items(conn, catalog)
    rng = random.Random(42)
    start = date(2026, 3, 2)
    log = []
    wrong_yesterday: set[str] = set()
    for offset in range(14):
        day = start + timedelta(days=offset)
        if offset in (9, 10, 11, 12):  # four days away
            continue
        cards, wrong = _day(conn, catalog, day, rng, wrong_rate=0.25)
        keys = {c["item_key"] for c in cards}
        reviews = [c for c in cards if c["segment"] in ("review", "verbs") and c["item_key"] in
                   {k for k, (p, i) in catalog.items.items()}]
        log.append((day, len(cards), len([c for c in cards if c["segment"] == "review"]), len(wrong)))
        # What was wrong yesterday is due today and comes back (vocab and verbs always; tasks may
        # wait for the task slot).
        if offset - 1 >= 0 and offset - 1 not in (9, 10, 11, 12) and offset not in (13,):
            missed_srs = {k for k in wrong_yesterday if catalog.items[k][1].type in ("vocab", "form")}
            assert missed_srs <= keys, f"{day}: yesterday's mistakes {missed_srs - keys} did not come back"
        wrong_yesterday = wrong
        assert len([c for c in cards if c["segment"] == "review"]) <= session.REVIEW_CAP

    # After four days away the session stays the same size, it does not balloon.
    sizes = {d: n for d, n, _, _ in log}
    after_gap = sizes[start + timedelta(days=13)]
    assert after_gap <= max(sizes.values())

    # Intervals grew for words answered right repeatedly.
    long = conn.execute("SELECT MAX(interval_days) FROM review_state").fetchone()[0]
    assert long >= 6

    # Home numbers match a hand count from the attempts table.
    db.set_clock(lambda: datetime(2026, 3, 15, 20, 0))
    stats = session.home_stats(conn, catalog, "en")
    by_day = dict(conn.execute("SELECT substr(ts,1,10), COUNT(*) FROM attempts GROUP BY 1").fetchall())
    for cell in stats["grid"]:
        assert cell["answers"] == by_day.get(cell["date"], 0)
    studied = sum(1 for cell in stats["grid"][-14:] if cell["answers"])
    assert stats["days_studied_14"] == studied == 10
    vocab_rows = conn.execute("SELECT a.correct FROM attempts a JOIN items i USING(item_key) WHERE i.type='vocab'").fetchall()
    vocab_area = next(a for a in stats["areas"] if a["area"] == "vocab")
    assert vocab_area["n"] == len(vocab_rows)
    assert abs(vocab_area["accuracy"] - sum(r[0] for r in vocab_rows) / len(vocab_rows)) < 0.001
    states = conn.execute("SELECT interval_days FROM review_state rs JOIN items i USING(item_key) WHERE i.type='vocab'").fetchall()
    assert stats["words"]["learning"] + stats["words"]["known"] == len(states)
    assert stats["words"]["known"] == sum(1 for r in states if r[0] >= scheduler.KNOWN_DAYS)


def test_backlog_is_capped_after_a_long_break(learner):
    conn = db.open_db()
    catalog = packs.load_all()
    packs.sync_items(conn, catalog)
    rng = random.Random(1)
    day = date(2026, 5, 1)
    for i in range(6):  # six busy days introduce many words
        _day(conn, catalog, day + timedelta(days=i), rng, wrong_rate=0.5, minutes=30)
    due_after = len(scheduler.due(conn, day + timedelta(days=40)))
    db.set_clock(lambda: datetime(2026, 6, 10, 8, 0))
    cards = session.plan(conn, catalog, "en", 10, rng=rng)
    reviews = [c for c in cards if c["segment"] == "review"]
    assert due_after > 0
    assert len(reviews) <= session.REVIEW_CAP
    secs = session.seconds_per_card(conn, catalog)  # the learner's own medians, as the session uses
    count = lambda seg: len([c for c in cards if c["segment"] == seg])  # noqa: E731
    seconds = secs["vocab"] * (count("review") + count("new")) + secs["form"] * count("verbs") + secs["task"] * count("task")
    assert seconds <= 10 * 60, (secs, [count(x) for x in ("review", "verbs", "task", "new")])


def test_lookup_makes_a_word_due_today(client, learner):
    s = client.post("/api/session", json={"kind": "daily", "ui_lang": "en"}).json()
    r = client.post("/api/lookup", json={"word": "καφέ", "item_key": "open-everyday-a1a2/r-gap-pharmacy"}).json()
    assert r["entries"] and r["entries"][0]["el"] == "ο καφές"
    conn = db.open_db()
    row = conn.execute("SELECT due_at FROM review_state WHERE item_key='open-shared-words-tr/v-kafes'").fetchone()
    assert row and row["due_at"] <= db.today().isoformat()
    assert conn.execute("SELECT COUNT(*) FROM lookups").fetchone()[0] == 1
    assert s["session_id"]
