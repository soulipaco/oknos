"""Phase 5c: chapters (read first, then practise), teach-before-test gating, learn cards."""

import json
import random
import sqlite3
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from greek_coach import chapters, curriculum, db, lint, packs, paths, readiness, report, scheduler, session

STAGE = "first-words"  # the second stage of the open curriculum


def chapter_data(**over):
    data = {
        "id": "open-a1-b1.first-words", "curriculum": "open-a1-b1", "stage": STAGE, "level": "A1",
        "title": {"tr": "İlk cümleler", "en": "First sentences"}, "minutes": 8,
        "sections": [
            {"kind": "intro", "blocks": [{"type": "prose", "tr": "Bu bölümde **kahve** ısmarlarsın.", "en": "You order a **coffee**."}]},
            {"kind": "text", "blocks": [{"type": "dialogue", "lines": [
                {"who": "Νίκος", "el": "Ένας καφές, παρακαλώ.", "tr": "Bir kahve lütfen.", "en": "A coffee, please."},
                {"who": "Μαρία", "el": "Και ένα τσάι.", "tr": "Ve bir çay.", "en": "And a tea."}]}]},
            {"kind": "grammar", "blocks": [
                {"type": "table", "head": ["", "είμαι"], "rows": [["εγώ", "είμαι"], ["εσύ", "είσαι"]]},
                {"type": "examples", "items": [{"el": "Ο καφές είναι ζεστός.", "tr": "Kahve sıcak.", "en": "The coffee is hot."}]}]},
            {"kind": "words", "blocks": [{"type": "words", "items": [
                "open-shared-words-tr/v-kafes", "open-shared-words-tr/v-tsai", "test-book/tb-word", "test-book/tb-free"]}]},
            {"kind": "try", "blocks": [{"type": "check", "items": ["open-shared-words-tr/q-kimas-where"]}]},
        ],
    }
    data.update(over)
    return data


@pytest.fixture
def book(learner, tmp_path):
    """A private pack with one chapter for the open curriculum's second stage, and one new word."""
    pack = tmp_path / "private" / "test-book"
    (pack / "items").mkdir(parents=True)
    (pack / "lessons").mkdir()
    (pack / "pack.json").write_text(json.dumps({
        "id": "test-book", "title": {"en": "Test book"}, "version": 1, "levels": ["A1"],
        "visibility": "private", "licence": "private", "source": "tests"}), encoding="utf-8")
    (pack / "items" / "chapter-first-words.json").write_text(json.dumps([
        {"id": "tb-word", "type": "vocab", "skill": "vocab", "level": "A1", "el": "παρακαλώ", "pos": "phrase",
         "en": "please", "tr": "lütfen", "topics": [f"stage:{STAGE}"]},
        # no tag, and level B1 so no level pool takes it: only the chapter's words block places it
        {"id": "tb-free", "type": "vocab", "skill": "vocab", "level": "B1", "el": "η ζάχαρη", "pos": "noun", "gender": "f",
         "en": "sugar", "tr": "şeker"}], ensure_ascii=False), encoding="utf-8")
    (pack / "lessons" / f"{STAGE}.json").write_text(json.dumps(chapter_data(), ensure_ascii=False), encoding="utf-8")
    return pack


def _at_second_stage(conn):
    """The first stage passed by a check, so the chapter's stage is the current one."""
    with conn:
        conn.execute("INSERT INTO stage_checks(curriculum, stage, started_at, finished_at, score, passed) "
                     "VALUES ('open-a1-b1', 'reading', ?, ?, 1.0, 1)", (db.now(), db.now()))


# ---------- the format ----------

def test_a_good_chapter_parses_and_knows_what_it_refers_to():
    ch = chapters.parse(chapter_data())
    assert ch.word_keys() == ["open-shared-words-tr/v-kafes", "open-shared-words-tr/v-tsai", "test-book/tb-word",
                              "test-book/tb-free"]
    assert ch.check_keys() == ["open-shared-words-tr/q-kimas-where"]
    assert [ln["el"] for ln in ch.greek_lines()][:2] == ["Ένας καφές, παρακαλώ.", "Και ένα τσάι."]
    assert "είσαι" in ch.table_cells() and "Νίκος" in ch.speakers()
    assert 0 < ch.estimated_minutes("tr") < 10


@pytest.mark.parametrize("change, message", [
    (lambda d: d["sections"].reverse(), "order"),
    (lambda d: d["sections"].pop(), "missing section"),
    (lambda d: d["sections"][0]["blocks"][0].pop("en"), "en"),
    (lambda d: d["sections"][2]["blocks"][0]["rows"].append(["εμείς"]), "row 3"),
    (lambda d: d["sections"][4]["blocks"][0].update(items=["a/b"] * 6), "at most 5"),
])
def test_a_broken_chapter_is_explained(change, message):
    data = chapter_data()
    change(data)
    with pytest.raises(ValidationError) as e:
        chapters.parse(data)
    assert message in chapters.describe(e.value)


def test_a_broken_chapter_file_is_skipped_and_reported(book, learner):
    (book / "lessons" / "past.json").write_text("{not json", encoding="utf-8")
    (book / "lessons" / "future.json").write_text(json.dumps(chapter_data()), encoding="utf-8")  # wrong stage name
    catalog = packs.load_all()
    assert catalog.chapter("open-a1-b1", STAGE) is not None
    assert any("past.json is not valid JSON" in p for p in catalog.problems)
    assert any("file name must be the stage id" in p for p in catalog.problems)


def test_the_outline_is_not_a_chapter(book, learner):
    (book / "lessons" / "outline.json").write_text(json.dumps({"stages": []}), encoding="utf-8")
    catalog = packs.load_all()
    assert not [p for p in catalog.problems if "outline" in p]


# ---------- placement and gating ----------

def test_the_words_block_places_its_words_in_the_chapter_stage(book, learner):
    catalog = packs.load_all()
    cur = curriculum.active(catalog)
    a = curriculum.assignment(cur, catalog)
    idx = cur.index(STAGE)
    assert a["test-book/tb-free"] == idx                      # placed nowhere else: the chapter places it
    assert a["open-shared-words-tr/q-kimas-where"] == idx     # a check item belongs to the stage too
    # the first stage's include rule already places this word: a later chapter never pushes it later
    assert a["open-shared-words-tr/v-kafes"] == 0
    assert a["open-shared-words-tr/v-flitzani"] == 0


def test_new_items_wait_for_the_chapter_but_reviews_do_not(book, learner):
    catalog = packs.load_all()
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    _at_second_stage(conn)
    # a word of the stage that was already seen (in a "test me" check, say) is a review
    scheduler.record(conn, "open-shared-words-tr/v-tsai", "vocab", True, 1.0)
    allowed, _ = session.gate(conn, catalog)
    item = lambda k: catalog.items[k][1]  # noqa: E731
    assert not allowed("test-book/tb-word", item("test-book/tb-word"))
    assert not allowed("test-book/tb-free", item("test-book/tb-free"))
    assert allowed("open-shared-words-tr/v-tsai", item("open-shared-words-tr/v-tsai"))
    assert allowed("open-shared-words-tr/v-flitzani", item("open-shared-words-tr/v-flitzani"))  # a stage with no chapter
    keys = {c["item_key"] for c in session.plan(conn, catalog, "en", 20, rng=random.Random(1))}
    assert "test-book/tb-word" not in keys
    assert curriculum.next_action(curriculum.progress(conn, catalog), "fresh", 3)["kind"] == "read"

    curriculum.mark_read(conn, "open-a1-b1", STAGE, 1, finished=True)
    allowed, _ = session.gate(conn, catalog)
    assert allowed("test-book/tb-word", item("test-book/tb-word"))
    keys = {c["item_key"] for c in session.plan(conn, catalog, "en", 20, rng=random.Random(1))}
    assert "test-book/tb-word" in keys
    assert curriculum.next_action(curriculum.progress(conn, catalog), "fresh", 3)["kind"] == "daily"


def test_a_passed_check_counts_as_taught(book, learner):
    catalog = packs.load_all()
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    _at_second_stage(conn)
    with conn:
        conn.execute("INSERT INTO stage_checks(curriculum, stage, started_at, finished_at, score, passed) "
                     "VALUES ('open-a1-b1', ?, ?, ?, 1.0, 1)", (STAGE, db.now(), db.now()))
    prog = curriculum.progress(conn, catalog)
    assert prog.curriculum.index(STAGE) in prog.taught


def test_without_chapters_nothing_changes(learner, catalog):
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    prog = curriculum.progress(conn, catalog)
    assert prog.taught == set(range(len(prog.curriculum.stages)))
    assert curriculum.next_action(prog, "fresh", 0)["kind"] == "daily"


# ---------- learn cards ----------

def test_a_new_word_gets_a_learn_card_with_a_chapter_example(book, learner):
    catalog = packs.load_all()
    pack, item = catalog.items["test-book/tb-word"]
    distract = session.Distractors([(k, p, i) for k, (p, i) in catalog.items.items() if i.type == "vocab"])
    card = session.vocab_card("test-book/tb-word", pack, item, "tr", "el_meaning", distract, random.Random(0), None, catalog)
    assert card["learn"]["meaning"] == "lütfen"
    assert card["learn"]["example"]["el"] == "Ένας καφές, παρακαλώ."
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    state = scheduler.record(conn, "test-book/tb-word", "vocab", True, 1.0)
    seen = session.vocab_card("test-book/tb-word", pack, item, "tr", "el_meaning", distract, random.Random(0), state, catalog)
    assert "learn" not in seen


# ---------- the API, the report and readiness ----------

def test_reading_and_practising_a_chapter_through_the_api(book, client):
    conn = db.open_db()
    _at_second_stage(conn)
    home = client.get("/api/home").json()
    assert home["next_action"]["kind"] == "read" and home["next_action"]["stage"] == STAGE

    ch = client.get(f"/api/chapters/{STAGE}").json()
    words = next(b for s in ch["sections"] for b in s["blocks"] if b["type"] == "words")["words"]
    assert {w["key"] for w in words} >= {"test-book/tb-word"} and words[0]["status"] == "new"
    assert ch["read"]["opened_at"] and ch["read"]["finished_at"] is None
    assert ch["prev_chapter"] is None and ch["next_chapter"] is None  # the only chapter: no neighbours
    assert client.post(f"/api/chapters/{STAGE}/progress", json={"section": 1}).json()["sections"] == [1]
    assert client.post(f"/api/chapters/{STAGE}/progress", json={"section": 99}).status_code == 422

    checks = client.post(f"/api/chapters/{STAGE}/checks", json={"items": ["open-shared-words-tr/q-kimas-where"]}).json()
    assert checks["kind"] == "lesson" and len(checks["cards"]) == 1

    s = client.post(f"/api/chapters/{STAGE}/practice", json={}).json()
    keys = [c["item_key"] for c in s["cards"]]
    stage_of = curriculum.assignment(curriculum.active(packs.load_all()), packs.load_all())
    assert keys and all(stage_of[k] == 1 for k in keys)
    assert keys[0] in ch["sections"][3]["blocks"][0]["items"]  # the chapter's own words come first
    assert client.get("/api/home").json()["next_action"]["kind"] == "daily"

    flag = client.post(f"/api/chapters/{STAGE}/flag", json={"section": 2, "note": "typo"})
    assert flag.status_code == 200
    rep = report.build(db.open_db(), packs.load_all())
    assert rep["report_version"] == 3
    entry = next(x for x in rep["chapters"]["stages"] if x["stage"] == STAGE)
    assert entry["chapter"] and entry["finished_at"] and entry["sections_seen"] == 1
    chapter_flag = next(f for f in rep["open_flags"] if "chapter" in f)
    assert chapter_flag["chapter"]["section"] == 2 and chapter_flag["chapter"]["content"]["kind"] == "grammar"
    assert client.get("/api/chapters/no-such-stage").status_code == 404


def test_answers_inside_a_chapter_are_not_exam_evidence(learner, catalog):
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    key = next(k for k, (_, i) in catalog.items.items() if i.exam_task and i.exam_task.startswith("a2ltr.reading") and i.level == "A2")

    def evidence(kind):
        conn.execute("DELETE FROM attempts")
        cur = conn.execute("INSERT INTO sessions(started_at, kind) VALUES (?, ?)", (db.now(), kind))
        conn.execute("INSERT INTO attempts(session_id, item_key, ts, response_json, score, correct) VALUES (?, ?, ?, '{}', 1, 1)",
                     (cur.lastrowid, key, db.now()))
        conn.commit()
        r = readiness.all_readiness(conn, catalog)["a2ltr"]
        return next(u for u in r["units"] if u["unit"] == "reading")["evidence"]

    assert evidence("practice") == 1
    assert evidence("lesson") == 0


# ---------- validate ----------

def test_validate_notes_untaught_words_and_wrong_references(book, learner):
    data = chapter_data()
    data["sections"][1]["blocks"][0]["lines"].append(
        {"who": "Νίκος", "el": "Θέλω ένα κρουασάν σοκολάτα.", "tr": "Çikolatalı kruvasan istiyorum.", "en": "I want a chocolate croissant."})
    data["sections"][3]["blocks"][0]["items"].append("test-book/no-such-word")
    (book / "lessons" / f"{STAGE}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    catalog = packs.load_all()
    pack = next(p for p in catalog.packs if p.id == "test-book")
    problems, notes = lint.chapter_checks(pack, catalog)
    assert any("no-such-word" in p for p in problems)
    untaught = next(n for n in notes if "no stage up to this one teaches" in n)
    assert "κρουασάν" in untaught and "σοκολάτα" in untaught
    assert "είσαι" not in untaught and "Νίκος" not in untaught  # taught by the table; a speaker's name


def test_the_greek_lint_reads_chapters(book):
    data = chapter_data()
    data["sections"][1]["blocks"][0]["lines"][0]["el"] = "Ενας καφέσ."  # no accent, final σ
    (book / "lessons" / f"{STAGE}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    problems, notes = lint.lint_chapter_files(book)
    assert any("ends a word with σ" in p for p in problems)


# ---------- the migration ----------

def test_migration_0006_on_an_older_database(tmp_path):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    for f in sorted(paths.MIGRATIONS_DIR.glob("000[1-5]_*.sql")):
        conn.executescript(f.read_text(encoding="utf-8"))
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', '5')")
    conn.commit()
    assert db.migrate(conn) == 6
    assert conn.execute("SELECT COUNT(*) FROM chapter_reads").fetchone()[0] == 0


def test_a_review_stage_chapter_does_not_move_words(book, learner):
    catalog = packs.load_all()
    cur = curriculum.active(catalog)
    review = next(s for s in cur.stages if s.review_of)
    data = chapter_data(stage=review.id, id=f"open-a1-b1.{review.id}")
    data["sections"][3]["blocks"][0]["items"] = ["open-shared-words-tr/v-flitzani"]
    (book / "lessons" / f"{review.id}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    catalog = packs.load_all()
    assert catalog.chapter(cur.id, review.id) is not None
    assert curriculum.assignment(cur, catalog)["open-shared-words-tr/v-flitzani"] == 0  # stays in its own stage


def test_validate_catches_swapped_languages(book):
    data = chapter_data()
    data["sections"][0]["blocks"][0] = {"type": "prose", "en": "Bu bölümde bir kahve ısmarlarsın.", "tr": "You order a coffee in this chapter."}
    (book / "lessons" / f"{STAGE}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    problems, _ = lint.lint_chapter_files(book)
    assert any("swapped" in p for p in problems)
