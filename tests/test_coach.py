"""Phase 4: the report, submissions and feedback, coach files, flags, scheduling and the Greek lint."""

import json
import random
import sys
from datetime import date, datetime, timedelta

import pytest

from oknos import cli, coachfiles, db, lint, packs, paths, report, scheduler, scheduling, session

WRITE_KEY = "open-everyday-a1a2/w-lift-broken"
SPEAK_KEY = "open-everyday-a1a2/s-neighbourhood"
GEN_MANIFEST = {"id": "coach-practice", "title": {"en": "Coach"}, "version": 1, "levels": ["A1", "A2"],
                "visibility": "generated", "licence": "private", "source": "coach"}


def _write_gen_pack(learner, items, manifest=GEN_MANIFEST):
    root = learner / "generated" / manifest["id"]
    (root / "items").mkdir(parents=True, exist_ok=True)
    (root / "pack.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "items" / "2026-11-16-checkin.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    return root


def _write_coach_file(learner, rel, data):
    path = learner / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _clock(d: date, hour: int = 9):
    db.set_clock(lambda: datetime(d.year, d.month, d.day, hour, 0))


def _attempt(conn, key, correct, ts_day: date):
    _clock(ts_day)
    with conn:
        conn.execute("INSERT INTO sessions(started_at, kind) VALUES (?, 'daily')", (db.now(),))
        sid = conn.execute("SELECT MAX(id) FROM sessions").fetchone()[0]
        conn.execute("INSERT INTO attempts(session_id, item_key, ts, response_json, score, correct, latency_ms) "
                     "VALUES (?, ?, ?, '{}', ?, ?, 12000)", (sid, key, db.now(), float(correct), int(correct)))


# ---------- writing and speaking ----------

def test_writing_round_trip_with_feedback(client, learner):
    s = client.post("/api/session", json={"kind": "practice", "items": [WRITE_KEY]}).json()
    card = s["cards"][0]
    assert card["type"] == "write" and card["words"] == [40, 60] and card["must_include"]
    r = client.post("/api/attempt", json={"session_id": s["session_id"], "item_key": WRITE_KEY, "card": card,
                                          "response": {"text": "Αγαπητέ κύριε, το ασανσέρ δεν δουλεύει."}}).json()
    sid = r["submission_id"]
    assert sid and r["correct"] is None and r["score"] is None
    listed = client.get("/api/submissions").json()["submissions"]
    assert listed[0]["id"] == sid and listed[0]["status"] == "new" and listed[0]["word_count"] == 6

    home = client.get("/api/home").json()
    assert home["coach"]["submissions_waiting"] == 1 and not home["coach"]["feedback_ready"]
    conn = db.open_db()
    assert report.submissions(conn, packs.load_all())["pending"][0]["text"].startswith("Αγαπητέ")

    _write_coach_file(learner, f"feedback/{sid}.json", {
        "submission_id": sid, "item_key": WRITE_KEY, "kind": "writing", "lang": "en", "marked_at": db.now(),
        "summary": "Clear and polite.", "corrected": "Αγαπητέ κύριε, το ασανσέρ δεν λειτουργεί.",
        "errors": [{"original": "δουλεύει", "fix": "λειτουργεί", "why": "For machines, λειτουργεί."}],
        "score": {"exam": "a2ltr", "points": 6, "out_of": 10}})
    home = client.get("/api/home").json()
    assert home["coach"]["feedback_ready"] == [{"id": sid, "kind": "writing"}]
    detail = client.get(f"/api/submissions/{sid}").json()
    assert detail["feedback"]["corrected"].endswith("λειτουργεί.") and detail["text"]
    assert client.get("/api/home").json()["coach"]["feedback_ready"] == []  # seen now
    row = conn.execute("SELECT status, feedback_path FROM submissions WHERE id=?", (sid,)).fetchone()
    assert row["status"] == "marked" and row["feedback_path"] == f"feedback/{sid}.json"
    assert report.submissions(conn, packs.load_all())["pending"] == []


def test_skipping_writing_makes_no_submission(client):
    s = client.post("/api/session", json={"kind": "practice", "items": [WRITE_KEY]}).json()
    r = client.post("/api/attempt", json={"session_id": s["session_id"], "item_key": WRITE_KEY, "card": s["cards"][0],
                                          "response": {"skipped": True}}).json()
    assert r["submission_id"] is None
    assert client.get("/api/submissions").json()["submissions"] == []


def test_speaking_upload_and_traversal(client, learner):
    up = client.post("/api/recording", content=b"\x1aE\xdf\xa3fake-webm", headers={"Content-Type": "audio/webm;codecs=opus"})
    assert up.status_code == 200
    name = up.json()["recording"]
    s = client.post("/api/session", json={"kind": "practice", "items": [SPEAK_KEY]}).json()
    bad = client.post("/api/attempt", json={"session_id": s["session_id"], "item_key": SPEAK_KEY, "card": s["cards"][0],
                                            "response": {"recording": "recordings/../profile.json"}})
    assert bad.status_code == 422
    r = client.post("/api/attempt", json={"session_id": s["session_id"], "item_key": SPEAK_KEY, "card": s["cards"][0],
                                          "response": {"recording": name}}).json()
    sid = r["submission_id"]
    assert (learner / "recordings" / f"{sid}.webm").is_file()
    assert client.get(f"/recordings/{sid}.webm").content.startswith(b"\x1aE")
    assert client.get("/recordings/..%2Fprofile.json").status_code == 404
    assert client.post("/api/recording", content=b"x", headers={"Content-Type": "text/plain"}).status_code == 415
    pending = report.submissions(db.open_db(), packs.load_all())["pending"][0]
    assert pending["kind"] == "speaking" and pending["transcribed"] is False


# ---------- coach files ----------

def test_broken_coach_files_never_break_the_app(client, learner):
    _write_coach_file(learner, "coach/message.json", "{not json")
    _write_coach_file(learner, "coach/watch.json", {"checked_at": "x", "entries": [{"what": 1}]})
    _write_coach_file(learner, "coach/resolved-flags.json", "[{]")
    home = client.get("/api/home")
    assert home.status_code == 200 and home.json()["coach"]["message"] is None
    assert cli.main(["validate", str(learner)]) == 1


def test_message_dates_and_restart(client, learner):
    today = db.today()
    _write_coach_file(learner, "coach/message.json", {"date": today.isoformat(), "en": "Verbs are better.",
                                                       "tr": "Fiiller daha iyi.",
                                                       "restart": {"minutes": 4, "until": today.isoformat()}})
    _write_coach_file(learner, "coach/watch.json", {"checked_at": db.now(), "entries": [
        {"what": "B1 May", "date": (today + timedelta(days=100)).isoformat(),
         "registration": {"opens": (today + timedelta(days=30)).isoformat()}, "source_url": "https://x"},
        {"what": "old", "date": (today - timedelta(days=3)).isoformat(), "source_url": "https://y"}]})
    coach = client.get("/api/home").json()["coach"]
    assert coach["message"]["tr"] == "Fiiller daha iyi."
    assert [e["what"] for e in coach["dates"]["entries"]] == ["B1 May"]
    assert client.post("/api/session", json={"kind": "daily"}).json()["minutes"] == 4
    assert cli.main(["validate", str(learner)]) == 0


def test_old_message_is_hidden(learner):
    _write_coach_file(learner, "coach/message.json", {"date": "2020-01-01", "en": "old"})
    assert coachfiles.message_for_home(db.today()) is None


# ---------- flags ----------

def test_flagged_items_wait_for_the_coach(client, learner):
    _write_coach_file(learner, "profile.json", {"level": "A2", "curriculum": "off"})  # mechanics, not order
    _write_gen_pack(learner, [{"id": "2026-11-16-w1", "type": "vocab", "skill": "vocab", "level": "A1",
                               "el": "το ασανσέρ", "en": "lift", "tr": "asansör"}])
    client.post("/api/reload")
    key = "coach-practice/2026-11-16-w1"
    flag_id = client.post("/api/flag", json={"item_key": key, "reason": "wrong"}).json()["flag_id"]
    conn = db.open_db()
    catalog = packs.load_all()
    assert key not in {c["item_key"] for c in session.plan(conn, catalog, "en", 10)}
    flags = report.open_flags(conn, catalog)
    assert flags[0]["flag_id"] == flag_id and flags[0]["item"]["item"]["el"] == "το ασανσέρ"

    _write_coach_file(learner, "coach/resolved-flags.json",
                      [{"flag_id": flag_id, "resolution": "kept", "note": "it is right"}])
    assert report.open_flags(conn, catalog) == []
    assert key in {c["item_key"] for c in session.plan(conn, catalog, "en", 10)}
    client.post("/api/reload")
    row = conn.execute("SELECT resolved_at, resolution FROM flags WHERE id=?", (flag_id,)).fetchone()
    assert row["resolved_at"] and row["resolution"] == "kept: it is right"


# ---------- session planning ----------

def test_coach_items_come_first_in_every_segment(learner):
    _write_coach_file(learner, "profile.json", {"level": "A2", "curriculum": "off"})  # mechanics, not order
    _write_gen_pack(learner, [
        {"id": "2026-11-16-f1", "type": "form", "skill": "grammar", "level": "A2", "text": "Χθες {1} στο γραφείο.",
         "cue": {"lemma": "πηγαίνω", "person": "1sg", "tense": "aorist"}, "answer": {"1": ["πήγα"]}},
        {"id": "2026-11-16-t1", "type": "mcq", "skill": "reading", "level": "A1",
         "prompt": {"el": "Πού είναι το ΚΕΠ;"}, "options": ["Στην πλατεία.", "Στο σπίτι."], "answer": 0},
        {"id": "2026-11-16-v1", "type": "vocab", "skill": "vocab", "level": "A1", "el": "η εφορία", "en": "tax office"},
    ])
    conn = db.open_db()
    catalog = packs.load_all()
    packs.sync_items(conn, catalog)
    cards = session.plan(conn, catalog, "en", 8, rng=random.Random(1))  # under 10 min: no writing slot
    first = {seg: next(c["item_key"] for c in cards if c["segment"] == seg) for seg in ("verbs", "task", "new")}
    assert first == {"verbs": "coach-practice/2026-11-16-f1", "task": "coach-practice/2026-11-16-t1",
                     "new": "coach-practice/2026-11-16-v1"}


def test_weekly_writing_then_speaking(client, learner):
    _write_coach_file(learner, "profile.json", {"level": "A2", "curriculum": "off"})  # mechanics, not order
    day = date(2026, 4, 6)
    _clock(day)
    s = client.post("/api/session", json={"kind": "daily"}).json()
    writes = [c for c in s["cards"] if c["type"] == "write"]
    assert len(writes) == 1 and writes[0]["segment"] == "task"
    client.post("/api/attempt", json={"session_id": s["session_id"], "item_key": writes[0]["item_key"],
                                      "card": writes[0], "response": {"text": "Γεια σας, γράφω για το ασανσέρ."}})
    _clock(day + timedelta(days=1))  # never two writing/speaking days in a row
    assert not {"write", "speak"} & {c["type"] for c in session.plan(db.open_db(), packs.load_all(), "en", 10)}
    _clock(day + timedelta(days=2))
    cards = session.plan(db.open_db(), packs.load_all(), "en", 10)
    types = [c["type"] for c in cards]
    assert "write" not in types and types.count("speak") == 1
    cards5 = session.plan(db.open_db(), packs.load_all(), "en", 5)  # too short a day for either
    assert not {"write", "speak"} & {c["type"] for c in cards5}


def test_a_skipped_card_waits_three_days(client, learner):
    _write_coach_file(learner, "profile.json", {"level": "A2", "curriculum": "off"})  # mechanics, not order
    day = date(2026, 4, 6)
    _clock(day)
    s = client.post("/api/session", json={"kind": "daily"}).json()
    card = next(c for c in s["cards"] if c["type"] == "write")
    client.post("/api/attempt", json={"session_id": s["session_id"], "item_key": card["item_key"], "card": card,
                                      "response": {"skipped": True}})
    seen = []
    for n in range(1, 5):
        _clock(day + timedelta(days=n))
        seen.append([c["type"] for c in session.plan(db.open_db(), packs.load_all(), "en", 10)
                     if c["type"] in ("write", "speak")])
    assert seen[:2] == [[], ["speak"]]  # the write waits; from day 3 the empty days count as time away


def test_lighter_session_after_time_away(learner):
    conn = db.open_db()
    catalog = packs.load_all()
    packs.sync_items(conn, catalog)
    words = [k for k, (_, i) in catalog.items.items() if isinstance(i, packs.VocabItem)]
    day = date(2026, 4, 1)
    _clock(day)
    with conn:
        for k in words[:20]:
            scheduler.save(conn, scheduler.State(item_key=k, due_at=day.isoformat()))
    _attempt(conn, words[0], True, day)
    _clock(day + timedelta(days=5))
    assert session.days_away(conn) == 5
    cards = session.plan(conn, catalog, "en", 10, rng=random.Random(2))
    assert len([c for c in cards if c["segment"] == "review"]) <= session.AWAY_REVIEW_CAP
    assert len([c for c in cards if c["segment"] == "new"]) <= session.AWAY_NEW
    assert not any(c["type"] in ("write", "speak") for c in cards)


# ---------- the report ----------

def test_report_shape(client, learner):
    conn = db.open_db()
    catalog = packs.load_all()
    day = db.today() - timedelta(days=2)
    _attempt(conn, "open-shared-words-tr/v-kafes", False, day)
    _attempt(conn, "open-shared-words-tr/v-kafes", True, day + timedelta(days=1))
    db.set_clock(None)
    data = report.build(conn, catalog, days=14, with_words=True)
    for key in ("profile", "profile_missing", "activity", "accuracy", "recent_wrong", "hardest", "lookups", "covered",
                "due", "open_flags", "submissions", "generated_stock", "inbox", "coach", "learner_dir"):
        assert key in data, key
    assert data["activity"]["answers"] == 2 and data["activity"]["days_since_last_practice"] == 1
    assert data["recent_wrong"][0]["right"]["el"] == "ο καφές"
    assert data["covered"]["word_list"][0]["el"] == "ο καφές"
    assert "goal" in data["profile_missing"]
    json.dumps(data, ensure_ascii=False)  # serialisable
    assert report.parse_days("3w") == 21 and report.parse_days("10d") == 10


def test_report_command_prints_json(learner, capsys):
    assert cli.main(["report", "--since", "7d"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["window_days"] == 7 and out["learner_dir"] == str(learner.resolve())


# ---------- validate and the Greek lint ----------

@pytest.mark.parametrize("text,needle", [
    ("Καλo πρωί", "Latin"),
    ("Ο Νίκος πίνει καφεσ.", "σ instead of ς"),
    ("Ο Νίκοςμένει εδώ.", "ς inside"),
    ("ὁ καφές", "polytonic"),
    ("Καλημέρα", "NFC"),
])
def test_lint_problems(text, needle):
    problems, _ = lint.check_text(text)
    assert any(needle in p for p in problems), problems


def test_lint_accepts_good_greek():
    for text in ("Το όνομά μου είναι Νίκος. Πού είναι το ΚΕΠ;", "ΚΛΕΙΣΤΟ ΤΗΝ ΚΥΡΙΑΚΗ", "Τι κάνεις; Καλά, ευχαριστώ!"):
        assert lint.check_text(text) == ([], []), text
    assert lint.check_text("φαρμακειο")[1]  # missing accent is a note


def test_validate_reports_greek_problems_in_generated_packs(learner, capsys):
    root = _write_gen_pack(learner, [{"id": "a", "type": "vocab", "skill": "vocab", "level": "A1",
                                      "el": "το φαρμακεiο", "en": "pharmacy"}])
    assert cli.main(["validate", str(root), "--quick"]) == 1
    assert "Latin" in capsys.readouterr().out


# ---------- scheduled runs ----------

def test_run_logs_failures_and_success(learner, monkeypatch):
    monkeypatch.setenv("OKNOS_AGENT_CMD", json.dumps([sys.executable, "-c", "import sys; print('Not logged in'); sys.exit(3)"]))
    ok, detail = scheduling.run("daily-prep", "claude")
    assert not ok and "exit=3" in detail and "last=Not logged in" in detail
    problems = coachfiles.run_problems()
    assert problems and problems[0]["skill"] == "daily-prep" and problems[0]["problem"] == "failed"
    monkeypatch.setenv("OKNOS_AGENT_CMD", json.dumps([sys.executable, "-c", "print('prepared')"]))
    ok, _ = scheduling.run("daily-prep", "claude")
    assert ok and coachfiles.run_problems() == []
    lines = (learner / "coach" / "runs.log").read_text(encoding="utf-8").splitlines()
    assert [l.split()[2] for l in lines] == ["failed", "ok"]
    assert any(p.name.endswith("daily-prep.log") for p in (learner / "logs" / "runs").iterdir())


def test_a_missing_agent_is_a_logged_failure(learner, monkeypatch):
    monkeypatch.delenv("OKNOS_AGENT_CMD", raising=False)
    monkeypatch.setattr(scheduling, "find_agent", lambda name: None)
    ok, detail = scheduling.run("watch", "codex")
    assert not ok and "not found" in detail
    assert coachfiles.runs()[-1]["ok"] is False


def test_stale_schedule_is_reported(learner):
    old = (db.current() - timedelta(days=5)).isoformat(timespec="seconds")
    _write_coach_file(learner, "coach/schedule.json",
                      {"agent": "claude", "tasks": {"daily-prep": {"every": "day", "at": "05:00", "created": old}}})
    problems = coachfiles.run_problems()
    assert problems == [{"skill": "daily-prep", "problem": "not_run", "since": old, "detail": ""}]


def test_raw_needs_a_private_pack(capsys):
    assert cli.main(["raw", "no-such-pack"]) == 1


def test_coach_forms_get_through_a_verb_backlog(learner):
    _write_coach_file(learner, "profile.json", {"level": "A2", "curriculum": "off"})  # mechanics, not order
    _write_gen_pack(learner, [
        {"id": f"2026-11-16-f{n}", "type": "form", "skill": "grammar", "level": "A2", "text": "Χθες {1} στη λαϊκή.",
         "cue": {"lemma": "πηγαίνω", "person": "1sg", "tense": "aorist"}, "answer": {"1": ["πήγα"]}} for n in range(5)])
    conn = db.open_db()
    catalog = packs.load_all()
    packs.sync_items(conn, catalog)
    day = date(2026, 4, 1)
    _clock(day)
    old_forms = [k for k, (p, i) in catalog.items.items() if isinstance(i, packs.FormItem) and p.id != "coach-practice"]
    with conn:
        for k in old_forms[:12]:
            scheduler.save(conn, scheduler.State(item_key=k, due_at=day.isoformat(), reps=1, interval_days=1))
    verbs = [c["item_key"] for c in session.plan(conn, catalog, "en", 10) if c["segment"] == "verbs"]
    assert len([k for k in verbs if k.startswith("coach-practice/")]) == session.COACH_VERB_SHARE
    assert len(verbs) == session.VERB_SLOT_MAX
