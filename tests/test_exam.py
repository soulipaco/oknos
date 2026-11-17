"""Phase 5: blueprints, table_fill, tagging, readiness, mock exams and the plan."""

import json
import random
from datetime import date, datetime, timedelta

import pytest

from greek_coach import coachfiles, db, exams, lint, mock, packs, plan, readiness, report, session
from greek_coach.checking import CheckError, check

A2_READING = ["open-everyday-a1a2/r-pharmacy-hours", "open-everyday-a1a2/r-kep-notice"]


def _clock(d: date, hour: int = 9, minute: int = 0, second: int = 0):
    db.set_clock(lambda: datetime(d.year, d.month, d.day, hour, minute, second))


def _write(learner, rel, data):
    path = learner / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _gen_pack(learner, pack_id, items, levels=("A2", "B1")):
    root = learner / "generated" / pack_id
    _write(learner, f"generated/{pack_id}/pack.json", {"id": pack_id, "title": {"en": pack_id}, "version": 1,
                                                       "levels": list(levels), "visibility": "generated",
                                                       "licence": "private", "source": "test"})
    _write(learner, f"generated/{pack_id}/items/a.json", items)
    return root


def _gap(i):
    return {"id": f"gap-{i}", "type": "gap_bank", "skill": "reading", "exam_task": "a2ltr.reading.gapbank", "level": "A2",
            "text": "Το φαρμακείο είναι {1} σήμερα.", "bank": ["ανοιχτό", "κλειστό"], "answer": {"1": "ανοιχτό"}}


def _tf(i, n=5, task="a2ltr.reading.notices_tf", level="A2", skill="reading"):
    return {"id": f"tf-{i}", "type": "true_false", "skill": skill, "exam_task": task, "level": level,
            "stimulus": {"text": f"Ανακοίνωση {i}: Το γραφείο είναι κλειστό τη Δευτέρα."},
            "statements": [{"el": f"Πρόταση {j}.", "answer": j % 2 == 0} for j in range(n)]}


def _attempt(conn, key, score, day: date, kind="daily", correct=None):
    _clock(day)
    with conn:
        cur = conn.execute("INSERT INTO sessions(started_at, kind) VALUES (?, ?)", (db.now(), kind))
        conn.execute("INSERT INTO attempts(session_id, item_key, ts, response_json, score, correct, latency_ms) "
                     "VALUES (?, ?, ?, '{}', ?, ?, 20000)",
                     (cur.lastrowid, key, db.now(), score, int(score == 1.0) if correct is None else correct))


# ---------- blueprints ----------

def test_both_blueprints_load_and_add_up():
    bps = exams.load_blueprints()
    assert set(bps) == {"a2ltr", "b1-keg"}
    a2, b1 = bps["a2ltr"], bps["b1-keg"]
    assert [u.id for u in a2.units] == ["history", "listening", "reading", "writing", "speaking"]
    assert all(u.points == 20 for u in a2.units) and a2.total_points == 100
    assert all(u.points == 25 for u in b1.units) and len(b1.units) == 4
    assert b1.unit("reading").minutes == 40 and b1.unit("writing").minutes == 55
    assert b1.task("b1keg.reading.compare")[1].types == ["table_fill"]
    assert all(t.id.startswith("a2ltr.") for t in a2.units[0].tasks)
    assert all(u.technique.en and u.technique.tr for bp in bps.values() for u in bp.units)
    assert {b.id for b in b1.beyond_a2} >= {"grammar.passive", "task.table", "text.writing150"}
    # every watch page of an exam moved into its blueprint
    assert all(bp.watch.urls for bp in bps.values())
    sources = json.loads((exams.EXAMS_DIR / "watch-sources.json").read_text(encoding="utf-8"))["sources"]
    assert [s["kind"] for s in sources] == ["course"]


def test_a2ltr_pass_rule_survives_one_weak_unit_but_not_a_low_total():
    a2 = exams.load_blueprints()["a2ltr"]
    pts = {"history": 18, "listening": 10, "reading": 12, "writing": 10, "speaking": 2}
    assert exams.passes(a2, pts)  # 52 in total, four units at half or more
    assert not exams.passes(a2, {**pts, "history": 15.9})  # 49.9 in total
    assert not exams.passes(a2, {**pts, "writing": 9.5, "history": 20})  # two weak units, though 51.5


def test_b1_pass_rule_fails_on_any_single_skill():
    b1 = exams.load_blueprints()["b1-keg"]
    good = {"reading": 15, "listening": 15, "writing": 15, "speaking": 15}
    assert exams.passes(b1, good)
    for unit in good:
        assert not exams.passes(b1, {**good, unit: 14.5, **{u: 25 for u in good if u != unit}})


def test_blueprint_model_rejects_points_that_do_not_add_up(tmp_path):
    data = json.loads((exams.EXAMS_DIR / "a2ltr.json").read_text(encoding="utf-8"))
    data["units"][0]["tasks"][0]["points"] = 6
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Exception, match="add up"):
        exams.load_file(path)


# ---------- tagging ----------

def test_open_packs_are_tagged_with_real_blueprint_tasks():
    catalog = packs.load_all()
    open_packs = [p for p in catalog.packs if p.manifest.visibility == "open"]
    assert any(p.id == "open-b1-bridge" for p in open_packs)
    for pack in open_packs:
        problems, _ = lint.lint_tags(pack)
        assert problems == [], problems
    tags = {i.exam_task for p in open_packs for i in p.items.values() if i.exam_task}
    # every unit the app checks itself has open items, except A2-LTR history: by the spec, that
    # pack is built (privately, from the official syllabus) only when the plan targets an A2-LTR session
    for bp in exams.load_blueprints().values():
        for u in bp.units:
            if u.marked_by == "app" and (bp.id, u.id) != ("a2ltr", "history"):
                assert any(t.id in tags for t in u.tasks), f"no open item trains {bp.id} {u.id}"


def test_lint_reports_unknown_and_mismatched_tags(tmp_path):
    root = tmp_path / "p"
    (root / "items").mkdir(parents=True)
    (root / "pack.json").write_text(json.dumps({"id": "p", "title": {"en": "p"}, "version": 1, "levels": ["A2"],
                                                "visibility": "generated", "licence": "private", "source": "t"}))
    items = [_tf(1, task="a2ltr.reading.nope"), _tf(2, task="a2ltr.reading.gapbank"),
             _tf(3, skill="listening"), {**_tf(4), "exam_task": None}]
    (root / "items" / "a.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    pack, problems, _ = packs.load_pack(root, "generated")
    tag_problems, notes = lint.lint_tags(pack)
    assert any("not a task" in p for p in tag_problems)
    assert any("trained by" in p for p in tag_problems)
    assert any("skill" in p for p in tag_problems)
    assert any("without exam_task" in n for n in notes)


# ---------- table_fill ----------

def test_table_fill_checks_each_cell_accent_tolerantly(catalog):
    _, item = catalog.items["open-b1-bridge/r-b1-compare-courses"]
    cells = item.cells()
    assert len(cells) == 10
    right = [acc[0] for _, _, acc in cells]
    r = check(item, {}, {"answers": right})
    assert r.correct and r.score == 1.0
    loose = list(right)
    loose[6] = "οχι"  # no accent
    r = check(item, {}, {"answers": loose})
    assert r.correct and r.accent_note == "όχι"
    loose[0] = "εφτά"  # wrong cell
    r = check(item, {}, {"answers": loose})
    assert not r.correct and r.parts[0] is False and r.score == 0.9
    with pytest.raises(CheckError):
        check(item, {}, {"answers": right[:3]})


def test_table_fill_rejects_bad_shapes():
    base = {"id": "t", "type": "table_fill", "skill": "reading", "level": "B1", "columns": ["A", "B"], "rows": ["x"]}
    adapter = packs._item_adapter
    with pytest.raises(Exception, match="cell"):
        adapter.validate_python({**base, "answer": [[["1"]]]})
    with pytest.raises(Exception, match="asks for nothing"):
        adapter.validate_python({**base, "answer": [[None, None]]})
    ok = adapter.validate_python({**base, "answer": [[None, ["2", "δύο"]]], "given": [["1", None]]})
    assert ok.cells() == [(0, 1, ["2", "δύο"])]


def test_table_fill_round_trip_through_the_api(client):
    key = "open-b1-bridge/l-b1-compare-flats"
    s = client.post("/api/session", json={"kind": "practice", "items": [key]}).json()
    card = s["cards"][0]
    assert card["type"] == "table_fill" and card["columns"] == ["Κυψέλη", "Παγκράτι"]
    assert card["cells"] == [[True, True]] * 5 and "answer" not in card
    answers = ["3", "1", "450", "520", "ναι", "όχι", "όχι", "ναι", "σαράντα", "20"]
    r = client.post("/api/attempt", json={"session_id": s["session_id"], "item_key": key, "card": card,
                                          "response": {"answers": answers}}).json()
    assert r["correct"] is True and r["parts"] == [True] * 10


def test_stimulus_range_needs_audio():
    with pytest.raises(Exception, match="audio"):
        packs.Stimulus(tts="x", start=1, end=4)
    with pytest.raises(Exception, match="after"):
        packs.Stimulus(audio="audio/a.mp3", start=5, end=4)
    assert packs.Stimulus(audio="audio/a.mp3", start=5, end=40).end == 40


# ---------- readiness ----------

def test_no_practice_means_no_numbers(learner, catalog):
    conn = db.open_db()
    r = readiness.all_readiness(conn, catalog)
    for exam in r.values():
        assert exam["verdict"]["state"] == "no_evidence"
        assert all(u["state"] == "no_evidence" and u["estimate"] is None for u in exam["units"])
    writing = next(u for u in r["a2ltr"]["units"] if u["unit"] == "writing")
    assert writing["reason"] == "not_scored"


def test_readiness_counts_first_attempts_only_and_by_level(learner):
    _gen_pack(learner, "coach-practice", [_tf(i) for i in range(8)] + [_tf(99, level="A1"), _gap(1), _gap(2)])
    catalog = packs.load_all()
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    today = date(2026, 11, 16)
    keys = [f"coach-practice/tf-{i}" for i in range(8)]
    for k in keys[:5]:
        _attempt(conn, k, 0.6, today - timedelta(days=3))
    # a repeat at full marks must not raise the estimate; an A1 item must not count at all
    for k in keys[:5]:
        _attempt(conn, k, 1.0, today - timedelta(days=1))
    _attempt(conn, "coach-practice/tf-99", 1.0, today - timedelta(days=1))
    _clock(today)
    unit = next(u for u in readiness.for_blueprint(conn, catalog, exams.load_blueprints()["a2ltr"])["units"]
                if u["unit"] == "reading")
    assert unit["evidence"] == 5 and unit["state"] == "no_evidence" and unit["reason"] == "too_few"
    _attempt(conn, keys[5], 0.6, today - timedelta(days=1))
    _clock(today)
    unit = next(u for u in readiness.for_blueprint(conn, catalog, exams.load_blueprints()["a2ltr"])["units"]
                if u["unit"] == "reading")
    # 6 first attempts, all on notices_tf: the gap-fill task is 6 of 20 points (30%) with no
    # evidence, so there is still no number
    assert unit["evidence"] == 6 and unit["state"] == "no_evidence" and unit["reason"] == "major_task_missing"
    assert unit["missing_tasks"] == ["a2ltr.reading.gapbank"]
    _attempt(conn, "coach-practice/gap-1", 1.0, today - timedelta(days=1))
    _attempt(conn, "coach-practice/gap-2", 0.0, today - timedelta(days=1))
    _clock(today)
    unit = next(u for u in readiness.for_blueprint(conn, catalog, exams.load_blueprints()["a2ltr"])["units"]
                if u["unit"] == "reading")
    assert unit["evidence"] == 8
    tf = next(t for t in unit["tasks"] if t["id"] == "a2ltr.reading.notices_tf")
    gap = next(t for t in unit["tasks"] if t["id"] == "a2ltr.reading.gapbank")
    assert tf["n"] == 6 and tf["share"] == 0.6 and gap["n"] == 2 and gap["share"] == 0.5
    tlo, thi = readiness.wilson(3.6, 6)
    glo, ghi = readiness.wilson(1.0, 2)
    assert unit["low"] == round(14 * tlo + 6 * glo, 1) and unit["high"] == round(14 * thi + 6 * ghi, 1)
    assert unit["estimate"] == round(14 * 0.6 + 6 * 0.5, 1) == 11.4
    assert unit["state"] == "unclear" and unit["low"] < 10 < unit["high"]


def test_wilson_is_wide_for_few_items_and_narrow_for_many():
    lo3, hi3 = readiness.wilson(2, 3)
    lo60, hi60 = readiness.wilson(40, 60)
    assert hi3 - lo3 > 0.3 > hi60 - lo60
    assert readiness.wilson(0, 0) == (0.0, 1.0)


def test_verdict_applies_each_exams_rule():
    a2 = exams.load_blueprints()["a2ltr"]
    units = [{"unit": u.id, "points": u.points, "state": "above", "low": 12.0, "high": 18.0, "estimate": 15.0}
             for u in a2.units]
    units[-1].update(state="no_evidence", low=None, high=None, estimate=None)  # speaking: no evidence
    v = readiness.verdict(a2, units)
    # low ends: four units at 12 (≥ 10) but 48 in total, under 50: not a sure pass;
    # high ends: 72 + 20 for the unknown unit passes easily: so "can't tell yet"
    assert v["total_low"] == 48.0 and v["state"] == "unclear" and v["no_evidence"] == ["speaking"]
    for u in units[:4]:
        u["low"] = 13.0
    assert readiness.verdict(a2, units)["state"] == "pass"  # 52 with one unit unknown: survives


def test_verdict_low_total_is_not_a_pass():
    a2 = exams.load_blueprints()["a2ltr"]
    units = [{"unit": u.id, "points": u.points, "state": "above", "low": 11.0, "high": 18.0, "estimate": 15.0}
             for u in a2.units]
    units[-1].update(state="no_evidence", low=None, high=None, estimate=None)
    v = readiness.verdict(a2, units)
    assert v["total_low"] == 44.0 and v["state"] == "unclear"
    b1 = exams.load_blueprints()["b1-keg"]
    units = [{"unit": u.id, "points": u.points, "state": "above", "low": 16.0, "high": 20.0, "estimate": 18.0}
             for u in b1.units]
    units[1].update(state="below", low=5.0, high=12.0, estimate=8.0)
    assert readiness.verdict(b1, units)["state"] == "fail"


def test_writing_readiness_comes_from_coach_scores(learner, client):
    key = "open-everyday-a1a2/w-lift-broken"
    ids = []
    for _ in range(2):
        s = client.post("/api/session", json={"kind": "practice", "items": [key]}).json()
        r = client.post("/api/attempt", json={"session_id": s["session_id"], "item_key": key, "card": s["cards"][0],
                                              "response": {"text": "Αγαπητέ κύριε, το ασανσέρ δεν λειτουργεί."}}).json()
        ids.append(r["submission_id"])
    for sid, pts in zip(ids, (6, 8)):
        _write(learner, f"feedback/{sid}.json", {
            "submission_id": sid, "item_key": key, "kind": "writing", "lang": "en", "marked_at": "2026-11-16T10:00:00",
            "summary": "ok", "corrected": "Αγαπητέ κύριε.",
            "score": {"exam": "a2ltr", "task": "a2ltr.writing.email_formal", "points": pts, "out_of": 10}})
    conn = db.open_db()
    unit = next(u for u in readiness.for_blueprint(conn, packs.load_all(), exams.load_blueprints()["a2ltr"])["units"]
                if u["unit"] == "writing")
    task = next(t for t in unit["tasks"] if t["id"] == "a2ltr.writing.email_formal")
    assert unit["evidence"] == 2 and task["share"] == 0.7
    # the friendly e-mail (half the unit) has no mark yet: still no number
    assert unit["state"] == "no_evidence" and unit["missing_tasks"] == ["a2ltr.writing.email_friendly"]


# ---------- mock exams ----------

def _mock_files(learner, catalog):
    reading = [k for k, (_, i) in catalog.items.items() if i.exam_task and i.exam_task.startswith("a2ltr.reading")
               and k.startswith("open-")]
    writing = [k for k, (_, i) in catalog.items.items() if i.exam_task and i.exam_task.startswith("a2ltr.writing")]
    _write(learner, "coach/mocks/m1.json", {"id": "m1", "blueprint": "a2ltr", "created": "2026-11-16",
                                            "sections": [{"unit": "reading", "items": reading},
                                                         {"unit": "writing", "items": writing}]})
    return reading, writing


def test_mock_definition_is_validated(learner):
    _write(learner, "coach/mocks/m2.json", {"id": "other", "blueprint": "a2ltr", "created": "2026-11-16",
                                            "sections": [{"unit": "maths", "items": ["x/y"]}]})
    problems = coachfiles.validate_learner(learner)
    assert any("does not match the file name" in p for p in problems)
    assert any("maths" in p for p in problems)


def test_mock_items_stay_out_of_daily_sessions_until_taken(learner, catalog):
    reading, _ = _mock_files(learner, catalog)
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    assert set(reading) <= mock.reserved_keys(conn)
    for day in range(10):
        _clock(date(2026, 11, 1) + timedelta(days=day))
        cards = session.plan(conn, catalog, "en", 20, kind="extra")
        assert not {c["item_key"] for c in cards} & set(reading)


def test_mock_run_timing_scoring_and_interruption(learner, catalog):
    from test_scheduler import _answer

    reading, writing = _mock_files(learner, catalog)
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    day = date(2026, 11, 16)
    _clock(day, 10)
    run_id = mock.start_run(conn, catalog, "m1")
    assert mock.start_run(conn, catalog, "m1") == run_id  # a running mock is continued, not restarted
    sid = mock.start_section(conn, catalog, run_id, "reading")
    view = mock.section_view(conn, sid)
    assert view["remaining_seconds"] == 30 * 60 and not view["closed"]
    with pytest.raises(mock.MockError):
        mock.start_section(conn, catalog, run_id, "writing")  # one section at a time
    # answer half right; an interrupted learner comes back 10 minutes later with the time left
    first = view["cards"][0]
    item = catalog.items[first["item_key"]][1]
    mock.save_answer(conn, catalog, sid, first["item_key"], _answer(first, item, True))
    _clock(day, 10, 10)
    again = mock.section_view(conn, sid)
    assert again["remaining_seconds"] == 20 * 60 and first["item_key"] in again["answers"]
    second = view["cards"][1]
    mock.save_answer(conn, catalog, sid, second["item_key"], _answer(second, catalog.items[second["item_key"]][1], False))
    # at the very end, an open page hands it in itself: the server waits a little before
    # deciding the learner was away
    _clock(day, 10, 30, 5)
    assert mock.expire(conn, catalog) == 0
    # away until well after the end: the next request finds it closed by time, with what was saved
    _clock(day, 10, 45)
    assert mock.expire(conn, catalog) == 1
    view = mock.section_view(conn, sid)
    assert view["closed"] and view["closed_by"] == "time_away"
    with pytest.raises(mock.MockError):
        mock.save_answer(conn, catalog, sid, first["item_key"], _answer(first, item, True))
    res = view["result"]
    assert res["unanswered"] == len(reading) - 2
    # points: each task's points × (questions right / questions in the section's items for it)
    by_task: dict = {}
    for c in view["cards"]:
        it = catalog.items[c["item_key"]][1]
        n = mock.parts_of(it)
        got = n if c["item_key"] == first["item_key"] else (check(it, c, _answer(c, it, False)).score * n
                                                          if c["item_key"] == second["item_key"] else 0)
        t = by_task.setdefault(it.exam_task, [0.0, 0])
        t[0] += got
        t[1] += n
    bp = exams.load_blueprints()["a2ltr"]
    expected = sum(bp.task(t)[1].points * r / n for t, (r, n) in by_task.items())
    assert res["points"] == round(expected, 1) and res["out_of"] == 20
    # graded answers are ordinary first attempts in a mock session: timed readiness evidence
    kinds = {r["kind"] for r in conn.execute("SELECT s.kind FROM attempts a JOIN sessions s ON s.id=a.session_id")}
    assert kinds == {"mock"}
    firsts = readiness.first_attempts(conn)
    assert firsts[first["item_key"]]["kind"] == "mock"
    # writing: handed in by the learner, waits for the coach, then counts
    _clock(day, 11)
    wid = mock.start_section(conn, catalog, run_id, "writing")
    mock.save_answer(conn, catalog, wid, writing[0], {"text": "Αγαπητέ κύριε, το ασανσέρ δεν λειτουργεί από τη Δευτέρα."})
    mock.close_section(conn, catalog, wid, "learner")
    run = mock.run_view(conn, catalog, run_id)
    assert run["status"] == "finished" and run["would_pass"] is None
    w = next(s for s in run["sections"] if s["unit"] == "writing")
    assert w["result"]["status"] == "waiting_for_coach"
    sub = conn.execute("SELECT id FROM submissions").fetchone()["id"]
    _write(learner, f"feedback/{sub}.json", {
        "submission_id": sub, "item_key": writing[0], "kind": "writing", "lang": "en", "marked_at": "2026-11-16T12:00:00",
        "summary": "ok", "corrected": "Αγαπητέ κύριε.",
        "score": {"exam": "a2ltr", "task": "a2ltr.writing.email_formal", "points": 7, "out_of": 10}})
    w = next(s for s in mock.run_view(conn, catalog, run_id)["sections"] if s["unit"] == "writing")
    assert w["result"]["status"] == "marked" and w["result"]["points"] == 7.0 and w["result"]["out_of"] == 10
    assert not w["result"]["complete"]  # the friendly e-mail was not in this mock
    latest = mock.latest_unit_results(conn, "a2ltr")
    assert latest["reading"]["closed_by"] == "time_away" and latest["writing"]["points"] == 7.0
    assert mock.reserved_keys(conn) == set()  # taken: the items may now appear in daily sessions


def test_mock_api_and_speed(learner, client, catalog, monkeypatch):
    monkeypatch.setenv("GREEK_COACH_MOCK_SPEED", "60")
    _mock_files(learner, catalog)
    exam = client.get("/api/exam").json()
    assert exam["mocks"]["defined"][0]["ok"] and len(exam["exams"]) == 2
    run = client.post("/api/mocks/m1/start").json()
    sec = client.post(f"/api/mock-runs/{run['run_id']}/sections/reading").json()
    assert sec["remaining_seconds"] == pytest.approx(30, abs=1)  # 30 minutes at 60×
    assert all("answer" not in c for c in sec["cards"])
    bad = client.post(f"/api/mock-sections/{sec['section_id']}/answer", json={"item_key": "nope/x", "response": {}})
    assert bad.status_code == 409
    closed = client.post(f"/api/mock-sections/{sec['section_id']}/close", json={"by": "time"}).json()
    assert closed["closed"] and closed["closed_by"] == "time" and closed["result"]["points"] == 0
    home = client.get("/api/home").json()
    assert set(home["readiness"]) == {"a2ltr", "b1-keg"}


# ---------- the plan ----------

PLAN = {"made_at": "2026-11-16", "exam": "b1-keg",
        "target": {"exam": "b1-keg", "session": "2027-05-13", "registration_closes": "2027-03-14"},
        "budget_minutes_week": 100, "verdict": {"realistic": "no", "en": "Not realistic.", "tr": "Gerçekçi değil."},
        "weeks": [{"start": "2026-11-09", "minutes": 100, "focus": ["foundations"], "content": {"en": "Verbs."}},
                  {"start": "2026-11-16", "minutes": 100, "focus": ["reading"], "content": {"en": "Notices."},
                   "beyond_a2": ["task.table"]},
                  {"start": "2026-11-23", "minutes": 100, "focus": ["listening"], "content": {"en": "Notes."}}]}


def test_plan_file_is_validated(learner):
    _write(learner, "coach/plan.json", {**PLAN, "weeks": [{**PLAN["weeks"][0], "focus": ["history"]}]})
    problems = coachfiles.validate_learner(learner)
    assert any("history" in p and "not units of b1-keg" in p for p in problems)
    _write(learner, "coach/plan.json", {**PLAN, "weeks": list(reversed(PLAN["weeks"]))})
    assert any("date order" in p for p in coachfiles.validate_learner(learner))
    _write(learner, "coach/plan.json", PLAN)
    assert coachfiles.validate_learner(learner) == []


def test_plan_progress_and_inputs(learner, catalog):
    _write(learner, "coach/plan.json", PLAN)
    _write(learner, "coach/watch.json", {"checked_at": "2026-11-16T10:00:00+02:00", "entries": [
        {"what": "Ελληνομάθεια B1, May 2027", "kind": "exam", "exam": "b1-keg", "date": "2027-05-13",
         "registration": {"opens": "2027-02-01", "closes": "2027-03-14"}, "source_url": "https://example.org"},
        {"what": "Old session", "kind": "exam", "exam": "b1-keg", "date": "2026-10-23", "source_url": "https://example.org"}]})
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    for d in (date(2026, 11, 10), date(2026, 11, 11)):
        for _ in range(30):  # 30 answers × 20 s = 10 minutes a day
            _attempt(conn, next(k for k in catalog.items if k.startswith("open-verbs")), 1.0, d)
    _clock(date(2026, 11, 17))
    prog = plan.progress(conn, catalog)
    past = prog["weeks_so_far"]
    assert past[0]["start"] == "2026-11-09" and past[0]["done_minutes"] == 20.0 and past[0]["state"] == "short"
    assert past[0]["practised"] == {"foundations": 60}
    assert past[1]["state"] == "current" and past[1]["missed_focus"] == ["reading"]
    assert [w["start"] for w in prog["next_weeks"]] == ["2026-11-23"]
    assert session.plan_focus_tasks(date(2026, 11, 17)) == {
        t.id for t in exams.load_blueprints()["b1-keg"].unit("reading").tasks}
    inputs = plan.inputs(conn, {"minutes": 20, "days_per_week": 5})
    assert inputs["budget_minutes_week"] == 100
    [c] = inputs["candidates"]  # the past session is left out
    assert c["exam"] == "b1-keg" and c["registration_closes"] == "2027-03-14"
    assert c["weeks_left"] == round((date(2027, 5, 13) - date(2026, 11, 17)).days / 7, 1)
    assert c["hint"] == "no" and inputs["exams_without_announced_date"] == ["a2ltr"]


def test_report_has_the_exam_fields(learner, catalog):
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    r = report.build(conn, catalog)
    assert r["report_version"] == 2
    assert set(r["readiness"]) == {"a2ltr", "b1-keg"} and r["readiness_rules"]["first_attempts_only"]
    assert {t["id"] for t in r["coverage"]["b1-keg"]["tasks"]} == exams.load_blueprints()["b1-keg"].task_ids()
    assert r["plan_inputs"]["candidates"] == [] and r["plan_progress"] is None
    assert r["mocks"] == {"defined": [], "runs": [], "reserved_items": 0}


def test_page_hand_in_at_zero_is_not_away_and_unrecorded_speaking_is_not_unanswered(learner, catalog):
    speak = [k for k, (_, i) in catalog.items.items() if i.type == "speak" and i.exam_task == "a2ltr.speaking.personal"]
    reading = [k for k, (_, i) in catalog.items.items() if i.exam_task == "a2ltr.reading.gapbank"]
    _write(learner, "coach/mocks/m3.json", {"id": "m3", "blueprint": "a2ltr", "created": "2026-11-16",
                                            "sections": [{"unit": "speaking", "items": speak},
                                                         {"unit": "reading", "items": reading}]})
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    day = date(2026, 11, 16)
    _clock(day, 9)
    run = mock.start_run(conn, catalog, "m3")
    sid = mock.start_section(conn, catalog, run, "speaking")
    mock.save_answer(conn, catalog, sid, speak[0], {"done": True})
    _clock(day, 9, 12, 1)  # one second after the end: the page's own hand-in arrives
    res = mock.close_section(conn, catalog, sid, "time")
    assert res["closed_by"] == "time" and res["not_recorded"] == 1 and res["unanswered"] == len(speak) - 1
    # saving after the end closes the section by time instead of accepting the answer
    rid = mock.start_section(conn, catalog, run, "reading")
    _clock(day, 9, 42, 10)  # just after the end, inside the grace period
    with pytest.raises(mock.MockError):
        mock.save_answer(conn, catalog, rid, reading[0], {"answers": {}})
    assert mock.section_view(conn, rid)["closed_by"] == "time"


def test_mock_items_must_belong_to_their_section(learner, catalog):
    reading = [k for k, (_, i) in catalog.items.items() if i.exam_task == "a2ltr.reading.gapbank"]
    _write(learner, "coach/mocks/m4.json", {"id": "m4", "blueprint": "a2ltr", "created": "2026-11-16",
                                            "sections": [{"unit": "listening", "items": reading}]})
    problems = coachfiles.validate_learner(learner)
    assert any("not a listening task" in p for p in problems)
    defn = next(d for d in mock.definitions(catalog) if d["id"] == "m4")
    assert not defn["ok"] and "not tagged with a listening task" in defn["problems"][0]


def test_mock_verdict_counts_unscored_parts_both_ways():
    a2 = exams.load_blueprints()["a2ltr"]
    m = coachfiles.MockDef(id="x", blueprint="a2ltr", created="2026-11-16",
                           sections=[coachfiles.MockSection(unit=u.id, items=["p/i"]) for u in a2.units])

    def sec(unit, points, out_of, status="marked"):
        return {"unit": unit, "state": "closed", "result": {"points": points, "out_of": out_of, "status": status}}

    base = [sec("history", 20, 20), sec("listening", 16, 20), sec("reading", 20, 20), sec("writing", 9, 20)]
    # speaking scored on 6 of its 20 points: at 0 for the rest it fails (3 units), at full it passes
    assert mock._would_pass(a2, m, base + [sec("speaking", 3.5, 6)]) == (None, "unscored_parts_decide")
    assert mock._would_pass(a2, m, base + [sec("speaking", 12, 20)])[0] is True
    weak = [sec("history", 2, 20), sec("listening", 3, 20), sec("reading", 4, 20), sec("writing", 3, 20)]
    assert mock._would_pass(a2, m, weak + [sec("speaking", 1, 6)]) == (False, "fail_even_with_unscored_at_full")
    assert mock._would_pass(a2, m, base + [sec("speaking", None, 20, "waiting_for_coach")])[1] == "waiting_for_coach"


def test_a_beginner_never_gets_items_above_their_level(learner, catalog):
    """The maintainer's first real session got B1 passives and a 150-word letter (2026-11-17)."""
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    for day in range(14):
        _clock(date(2026, 11, 2) + timedelta(days=day))
        cards = session.plan(conn, catalog, "en", 20)
        levels = {catalog.items[c["item_key"]][1].level for c in cards}
        assert levels <= {"A1"}, levels
        assert not {"write", "speak"} & {c["type"] for c in cards}  # the open prompts are A2 and up
    _write(learner, "profile.json", {"level": "A2"})
    _clock(date(2026, 11, 20))
    levels = {catalog.items[c["item_key"]][1].level for c in session.plan(conn, catalog, "en", 20, kind="extra")}
    assert "B1" not in levels


def test_a_stale_planned_session_is_replaced_not_resumed(learner, catalog):
    _write(learner, "profile.json", {"level": "B1", "curriculum": "off"})
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    _clock(date(2026, 11, 17), 9)
    first = session.build(conn, catalog, "en", 20, rng=random.Random(0))
    assert any(c["item_key"].split("/")[0] not in ("open-alphabet", "open-shared-words-tr") for c in first["cards"])
    _write(learner, "profile.json", {"level": "B1"})  # the curriculum is back on: only its first stage is open
    assert session.today_status(conn, catalog)["state"] == "fresh"
    again = session.build(conn, catalog, "en", 20)
    assert not again["resumed"] and again["kind"] == "daily" and again["session_id"] != first["session_id"]
    assert {c["item_key"].split("/")[0] for c in again["cards"]} <= {"open-alphabet", "open-shared-words-tr"}
    assert session.today_status(conn, catalog)["state"] == "resume"  # the fresh plan is the one resumed now
