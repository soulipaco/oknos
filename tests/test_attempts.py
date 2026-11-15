import json
import sqlite3
import unicodedata


def _db(learner):
    conn = sqlite3.connect(learner / "greek-coach.db")
    conn.row_factory = sqlite3.Row
    return conn


def test_session_attempt_lands_in_sqlite_with_greek_intact(client, learner):
    s = client.post("/api/session", json={"kind": "daily", "ui_lang": "tr"}).json()
    assert s["cards"], "a session must have cards"
    card = next(c for c in s["cards"] if c["type"] == "vocab" and c["direction"] == "el_meaning")
    # Answer from the item itself: the first vocab card is ο καφές, whose Turkish is kahve.
    item_meaning = {"open-shared-words-tr/v-kafes": "kahve"}.get(card["item_key"])
    choice = item_meaning or card["options"][0]

    r = client.post("/api/attempt", json={
        "session_id": s["session_id"], "item_key": card["item_key"], "card": card,
        "response": {"choice": choice}, "latency_ms": 1234, "audio_plays": 1,
    })
    assert r.status_code == 200, r.text
    result = r.json()
    assert "example" in result

    row = _db(learner).execute("SELECT * FROM attempts").fetchone()
    assert row["item_key"] == card["item_key"]
    assert row["latency_ms"] == 1234 and row["audio_plays"] == 1
    assert row["correct"] == int(result["correct"])
    raw = row["response_json"]
    assert "\\u" not in raw, "Greek must be stored as text, not escapes"
    stored = json.loads(raw)
    assert stored["card"]["prompt"] == card["prompt"]
    assert unicodedata.is_normalized("NFC", stored["card"]["prompt"])
    assert any("Ͱ" <= ch <= "Ͽ" for ch in stored["card"]["prompt"]), "prompt should be Greek"


def test_first_session_new_words_start_with_kafes(client):
    s = client.post("/api/session", json={"kind": "daily", "ui_lang": "tr"}).json()
    new = [c for c in s["cards"] if c["segment"] == "new"]
    assert new[0]["item_key"] == "open-shared-words-tr/v-kafes"
    assert new[0]["prompt"] == "ο καφές"
    assert "kahve" in new[0]["options"] and len(new[0]["options"]) == 4


def test_server_decides_correctness(client):
    s = client.post("/api/session", json={"kind": "daily", "ui_lang": "en"}).json()
    tf = {"item_key": "open-everyday-a1a2/r-tf-supermarket", "type": "true_false"}
    n = 3
    r = client.post("/api/attempt", json={
        "session_id": s["session_id"], "item_key": tf["item_key"], "card": tf,
        "response": {"answers": [True] * n},
    }).json()
    assert len(r["parts"]) == n
    assert r["correct"] is all(r["parts"])


def _first_vocab(cards):
    return next(c for c in cards if c["type"] == "vocab")


def test_bad_requests_are_rejected(client):
    s = client.post("/api/session", json={"kind": "daily"}).json()
    card = _first_vocab(s["cards"])
    assert client.post("/api/attempt", json={"session_id": s["session_id"], "item_key": "nope/x", "response": {}}).status_code == 404
    assert client.post("/api/attempt", json={"session_id": 9999, "item_key": card["item_key"], "card": card,
                                             "response": {"choice": card["options"][0]}}).status_code == 404
    assert client.post("/api/attempt", json={"session_id": s["session_id"], "item_key": card["item_key"], "card": card,
                                             "response": {"choice": 3}}).status_code == 422


def test_daily_session_has_all_segments_and_fits_the_budget(client):
    daily = client.post("/api/session", json={"kind": "daily"}).json()
    assert daily["minutes"] == 10
    segments = [c["segment"] for c in daily["cards"]]
    assert segments == sorted(segments, key=["review", "verbs", "task", "new"].index), "segments come in order"
    assert segments.count("verbs") == 4 and segments.count("task") == 1
    assert 5 <= segments.count("new") <= 12
    seconds = 20 * segments.count("new") + 30 * segments.count("verbs") + 90 * segments.count("task")
    assert seconds <= 600


def test_daily_session_resumes_then_offers_more(client):
    first = client.post("/api/session", json={"kind": "daily"}).json()
    card = _first_vocab(first["cards"])
    client.post("/api/attempt", json={"session_id": first["session_id"], "item_key": card["item_key"], "card": card,
                                      "response": {"choice": card["options"][0]}})
    client.post(f"/api/session/{first['session_id']}/end")
    again = client.post("/api/session", json={"kind": "daily"}).json()
    assert again["resumed"] and again["session_id"] == first["session_id"]
    assert len(again["cards"]) == len(first["cards"]) - 1
    assert card["item_key"] not in {c["item_key"] for c in again["cards"]}


def test_end_session_summary_and_home(client, learner):
    s = client.post("/api/session", json={"kind": "daily", "ui_lang": "tr"}).json()
    vocab = [c for c in s["cards"] if c["type"] == "vocab"][:3]
    for card in vocab:
        client.post("/api/attempt", json={"session_id": s["session_id"], "item_key": card["item_key"], "card": card,
                                          "response": {"choice": card["options"][0]}})
    summary = client.post(f"/api/session/{s['session_id']}/end").json()
    assert summary["done"] == 3
    assert summary["by_area"]["vocab"]["done"] == 3
    assert all(w["el"] for w in summary["missed"])
    assert summary["due_tomorrow"] == 3, "every word seen today comes back tomorrow"
    row = _db(learner).execute("SELECT ended_at, items_done FROM sessions WHERE id=?", (s["session_id"],)).fetchone()
    assert row["ended_at"] and row["items_done"] == 3

    home = client.get("/api/home").json()
    assert home["stats"]["answers_total"] == 3
    assert home["stats"]["words"]["learning"] == 3
    assert home["stats"]["today"]["state"] == "resume"
    assert home["stats"]["grid"][-1]["answers"] == 3


def test_profile_language_is_saved(client, learner):
    assert client.post("/api/profile", json={"ui_lang": "tr"}).json()["ui_lang"] == "tr"
    saved = json.loads((learner / "profile.json").read_text(encoding="utf-8"))
    assert saved["ui_lang"] == "tr"
    assert client.get("/api/home").json()["ui_lang"] == "tr"


def test_static_front_end_is_served_with_module_mime_type(client):
    assert "<main id=\"app\"" in client.get("/").text
    js = client.get("/app.js")
    assert js.headers["content-type"].startswith("text/javascript")
    tr = client.get("/i18n/tr.json").json()
    assert tr["start_daily"] == "Bugünün {minutes} dakikası"
