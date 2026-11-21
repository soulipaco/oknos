"""Phase 5b: progression along a curriculum, stage checks, chosen practice, the word and verb lists."""

import json
import random
from datetime import date, datetime, timedelta

import pytest

from oknos import curriculum, db, packs, scheduler, session
from oknos.checking import check


def _clock(d: date, hour: int = 9):
    db.set_clock(lambda: datetime(d.year, d.month, d.day, hour, 0))


def _answer_all(conn, catalog, s, right=True):
    import sys
    sys.path.insert(0, "tests")
    from test_scheduler import _answer
    for card in s["cards"]:
        item = catalog.items[card["item_key"]][1]
        response = _answer(card, item, right) if item.type not in ("write", "speak") else {"skipped": True}
        result = check(item, card, response)
        with conn:
            conn.execute("INSERT INTO attempts(session_id, item_key, ts, response_json, score, correct, latency_ms) "
                         "VALUES (?, ?, ?, '{}', ?, ?, 15000)", (s["session_id"], card["item_key"], db.now(),
                                                                 result.score, None if result.correct is None else int(result.correct)))
            if result.correct is not None:
                scheduler.record(conn, card["item_key"], item.type, result.correct, result.score)


def test_the_open_curriculum_places_every_open_item(catalog):
    cur = curriculum.active(catalog)
    assert cur.id == "open-a1-b1"
    a = curriculum.assignment(cur, catalog)
    assert all(v is not None for v in a.values())
    first = [k for k, v in a.items() if v == 0]
    assert {k.split("/")[0] for k in first} == {"open-alphabet", "open-shared-words-tr"}
    last = len(cur.stages) - 1
    assert all(a[k] == last for k in catalog.items if k.startswith("open-b1-bridge/"))
    # the past tense is taught after the present and the future
    past = cur.index("past")
    assert all(a[k] == past for k, (_, i) in catalog.items.items()
               if getattr(i, "cue", None) and i.cue.tense == "aorist" and i.level != "B1")


def test_a_new_learner_only_meets_the_first_stage_and_moves_on_in_order(learner, catalog):
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    cur = curriculum.active(catalog)
    start = date(2026, 1, 5)
    reached = []
    for day in range(40):
        _clock(start + timedelta(days=day))
        prog = curriculum.progress(conn, catalog)
        reached.append(prog.current)
        s = session.build(conn, catalog, "en", 20, rng=random.Random(day))
        for c in s["cards"]:
            assert prog.assigned[c["item_key"]] <= prog.current, (c["item_key"], prog.current)
        _answer_all(conn, catalog, s, right=True)
        session.end(conn, s["session_id"])
    assert reached[0] == 0 and reached == sorted(reached)          # never goes back, never skips ahead
    assert reached[-1] >= 2                                         # but it does move on with steady practice
    assert cur.stages[reached[-1]].id != "b1-bridge"


def test_nothing_from_a_later_stage_before_the_earlier_is_done(learner, catalog):
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    _clock(date(2026, 1, 5))
    cards = session.plan(conn, catalog, "en", 30)
    assert {c["item_key"].split("/")[0] for c in cards} <= {"open-alphabet", "open-shared-words-tr"}
    assert not any(c["type"] in ("form", "write", "speak", "table_fill") for c in cards)


def test_a_passed_check_opens_the_next_stage(learner, client, catalog):
    first = client.get("/api/curriculum").json()
    assert first["current"]["id"] == "reading" and first["stages"][1]["state"] == "locked"
    s = client.post("/api/curriculum/stages/reading/check").json()
    assert s["kind"] == "check" and 0 < len(s["cards"]) <= curriculum.CHECK_SIZE
    import sys
    sys.path.insert(0, "tests")
    from test_scheduler import _answer
    for card in s["cards"]:
        item = catalog.items[card["item_key"]][1]
        client.post("/api/attempt", json={"session_id": s["session_id"], "item_key": card["item_key"], "card": card,
                                          "response": _answer(card, item, True)})
    summary = client.post(f"/api/session/{s['session_id']}/end").json()
    assert summary["check"]["passed"] is True
    after = client.get("/api/curriculum").json()
    assert after["current"]["id"] == "first-words" and after["stages"][0]["state"] == "done"
    # a check of a stage two ahead is refused
    assert client.post("/api/curriculum/stages/past/check").status_code == 409


def test_a_failed_check_keeps_the_stage(learner, client, catalog):
    s = client.post("/api/curriculum/stages/reading/check").json()
    import sys
    sys.path.insert(0, "tests")
    from test_scheduler import _answer
    for card in s["cards"][:3]:  # answering only some counts the rest as wrong
        item = catalog.items[card["item_key"]][1]
        client.post("/api/attempt", json={"session_id": s["session_id"], "item_key": card["item_key"], "card": card,
                                          "response": _answer(card, item, True)})
    summary = client.post(f"/api/session/{s['session_id']}/end").json()
    assert summary["check"]["passed"] is False
    assert client.get("/api/curriculum").json()["current"]["id"] == "reading"


def test_chosen_practice_stays_inside_the_reached_stages(learner, client):
    s = client.post("/api/session", json={"kind": "choose", "what": "verbs", "minutes": 10}).json()
    assert s["cards"] == [] and s["available"] == 0  # no verbs in the reading stage
    s = client.post("/api/session", json={"kind": "choose", "what": "words", "minutes": 5}).json()
    assert s["cards"] and all(c["type"] == "vocab" for c in s["cards"])
    assert all(c["item_key"].split("/")[0] in ("open-alphabet", "open-shared-words-tr") for c in s["cards"])
    assert client.post("/api/session", json={"kind": "choose", "what": "nonsense"}).status_code == 422
    s = client.post("/api/session", json={"kind": "choose", "what": "all", "stage": "reading", "minutes": 5}).json()
    assert s["cards"]


def test_word_and_verb_lists(learner, client):
    words = client.get("/api/words").json()
    by_key = {w["key"]: w for w in words["words"]}
    assert by_key["open-alphabet/l-alfa"]["open"] and by_key["open-alphabet/l-alfa"]["status"] == "new"
    assert by_key["open-shared-words-tr/v-kafes"]["stage"] == "reading"
    assert not any(w["open"] for w in words["words"] if w["stage"] == "b1-bridge")
    vdata = client.get("/api/verbs").json()
    verbs = vdata["verbs"]
    eimai = next(v for v in verbs if v["lemma"] == "είμαι")
    assert not eimai["open"] and eimai["forms"]  # είμαι comes in the second stage
    # the screen groups verbs by the lesson they first appear in, and folds the lessons not reached
    assert vdata["current"] == 0 and vdata["stages"][eimai["first_stage"]]["id"] == "first-words"
    assert vdata["stages"][0]["title"]["en"]
    stage = client.get("/api/curriculum/stages/first-words").json()
    assert stage["state"] == "locked" and stage["forms_list"] and stage["can_check"]
    assert client.get("/api/curriculum/stages/nope").status_code == 404


def test_a_coach_item_can_name_its_stage(learner, catalog):
    root = learner / "generated" / "coach-practice"
    (root / "items").mkdir(parents=True)
    (root / "pack.json").write_text(json.dumps({"id": "coach-practice", "title": {"en": "c"}, "version": 1, "levels": ["A1"],
                                                "visibility": "generated", "licence": "private", "source": "t"}))
    (root / "items" / "a.json").write_text(json.dumps([
        {"id": "w1", "type": "vocab", "skill": "vocab", "level": "A1", "topics": ["stage:reading"], "el": "η μπάλα", "en": "ball"},
        {"id": "w2", "type": "vocab", "skill": "vocab", "level": "A1", "topics": ["stage:past"], "el": "η πόρτα", "en": "door"},
    ], ensure_ascii=False), encoding="utf-8")
    cat = packs.load_all()
    cur = curriculum.active(cat)
    a = curriculum.assignment(cur, cat)
    assert a["coach-practice/w1"] == 0 and a["coach-practice/w2"] == cur.index("past")


def test_the_curriculum_can_be_switched_off(learner, catalog):
    (learner).mkdir(parents=True, exist_ok=True)
    (learner / "profile.json").write_text('{"curriculum": "off", "level": "A2"}', encoding="utf-8")
    assert curriculum.active(catalog) is None
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    _clock(date(2026, 1, 5))
    levels = {catalog.items[c["item_key"]][1].level for c in session.plan(conn, catalog, "en", 30)}
    assert "A2" in levels or "A1" in levels and "B1" not in levels


def test_curriculum_files_are_valid():
    for path in sorted(curriculum.CURRICULA_DIR.glob("*.json")):
        cur = curriculum.load_file(path)
        assert cur.stages[0].level == "A1"
    with pytest.raises(Exception, match="earlier"):
        curriculum.Curriculum.model_validate({
            "id": "x", "title": {"en": "x"}, "source": "t",
            "stages": [{"id": "a", "title": {"en": "a"}, "level": "A1", "review_of": ["b"]},
                       {"id": "b", "title": {"en": "b"}, "level": "A1"}]})


def test_the_home_screen_only_counts_what_is_open(learner, catalog):
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    _clock(date(2026, 1, 5))
    stats = session.home_stats(conn, catalog, "en")
    assert stats["verbs_new_available"] == 0  # no verbs in the reading stage, so the home line names none
    assert stats["new_available"] > 0
