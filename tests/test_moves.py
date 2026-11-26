"""A learner's private book became an open pack (2026-11-26): the history moves with it, and the
same card is never served twice (src/oknos/moves.py, packs.apply_replaces, curriculum `formerly`)."""

import json

from oknos import curriculum, db, packs, paths


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _vocab(iid, el, en, **kw):
    return {"id": iid, "type": "vocab", "skill": "vocab", "level": "A1", "el": el, "en": en, **kw}


MCQ = {"id": "q-where", "type": "mcq", "skill": "reading", "level": "A1", "prompt": {"el": "Πού;"},
       "options": ["εδώ", "εκεί"], "answer": 0}


def _chapter(cur, words):
    return {"id": f"{cur}.s1", "curriculum": cur, "stage": "s1", "level": "A1", "title": {"tr": "t", "en": "t"},
            "minutes": 5, "version": 1, "sections": [
                {"kind": "intro", "blocks": [{"type": "prose", "tr": "x", "en": "x"}]},
                {"kind": "text", "blocks": [{"type": "dialogue", "lines": [{"who": "Α", "el": "Γεια.", "tr": "Merhaba.", "en": "Hi."},
                                                                      {"who": "Β", "el": "Γεια.", "tr": "Merhaba.", "en": "Hi."}]}]},
                {"kind": "grammar", "blocks": [{"type": "prose", "tr": "x", "en": "x"}]},
                {"kind": "words", "blocks": [{"type": "words", "items": words}]},
                {"kind": "try", "blocks": [{"type": "check", "items": [words[0].split("/")[0] + "/q-where"]}]}]}


def _curriculum(cid, pack, formerly=()):
    return {"id": cid, "title": {"en": cid}, "source": "test", "for_pack": pack, "formerly": list(formerly),
            "stages": [{"id": "s1", "title": {"en": "S1"}, "level": "A1"},
                       {"id": "s2", "title": {"en": "S2"}, "level": "A1", "include": [{"packs": ["old", "new"]}]}]}


def _make(tmp_path, with_new: bool):
    priv = tmp_path / "c" / "private" / "old"
    _write(priv / "pack.json", {"id": "old", "title": {"en": "old"}, "version": 1, "levels": ["A1"],
                                "visibility": "private", "licence": "private", "source": "test"})
    _write(priv / "items" / "a.json", [_vocab("v-giatros", "ο γιατρός", "doctor (pdf)"),
                                       _vocab("v-spiti", "το σπίτι", "house (pdf)"),
                                       _vocab("v-other", "η θάλασσα", "sea"), MCQ])
    _write(priv / "lessons" / "s1.json", _chapter("old-book", ["old/v-giatros", "old/v-spiti"]))
    _write(priv / "curriculum.json", _curriculum("old-book", "old"))
    opn = tmp_path / "c" / "open" / "new"
    if with_new:
        _write(opn / "pack.json", {"id": "new", "title": {"en": "new"}, "version": 1, "levels": ["A1"],
                                   "visibility": "open", "licence": "CC-BY-SA-4.0", "source": "test",
                                   "replaces": ["old"]})
        _write(opn / "items" / "a.json", [_vocab("v-giatros", "ο γιατρός", "doctor"),
                                          _vocab("ch01-spiti", "το σπίτι", "house"), MCQ])
        _write(opn / "lessons" / "s1.json", _chapter("new-book", ["new/v-giatros", "new/ch01-spiti"]))
        _write(opn / "curriculum.json", _curriculum("new-book", "new", formerly=["old-book"]))
    return [("open", tmp_path / "c" / "open"), ("private", tmp_path / "c" / "private"),
            ("generated", tmp_path / "gen")]


def test_history_moves_to_the_open_pack(learner, tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "content_roots", lambda: _make(tmp_path, with_new=False))
    conn = db.open_db()
    old = packs.load_all()
    packs.sync_items(conn, old)
    assert curriculum.active(old).id == "old-book"
    with conn:
        conn.execute("INSERT INTO sessions(started_at, kind, plan_json) VALUES (?, 'daily', ?)",
                     (db.now(), json.dumps([{"item_key": "old/v-spiti"}, {"item_key": "old/v-other"}])))
        for k in ("old/v-giatros", "old/v-spiti", "old/q-where", "old/v-other"):
            conn.execute("INSERT INTO attempts(session_id, item_key, ts, response_json, correct, score) VALUES (1, ?, ?, '{}', 1, 1.0)", (k, db.now()))
            conn.execute("INSERT INTO review_state(item_key, due_at, reps, last_seen_at) VALUES (?, '2026-12-01', 2, ?)", (k, db.now()))
        conn.execute("INSERT INTO flags(ts, item_key, reason) VALUES (?, 'chapter:old-book/s1#2', 'wrong')", (db.now(),))
        conn.execute("INSERT INTO flags(ts, item_key, reason) VALUES (?, 'old/v-spiti', 'wrong')", (db.now(),))
    curriculum.mark_read(conn, "old-book", "s1", 1, finished=True)
    with conn:
        conn.execute("INSERT INTO stage_checks(curriculum, stage, started_at, passed) VALUES ('old-book', 's1', ?, 1)", (db.now(),))

    monkeypatch.setattr(paths, "content_roots", lambda: _make(tmp_path, with_new=True))
    cat = packs.load_all()
    # never served twice: the old copies are gone, the word with another id too; the rest stays
    assert "old/v-giatros" not in cat.items and "old/v-spiti" not in cat.items and "old/q-where" not in cat.items
    assert "old/v-other" in cat.items and "new/ch01-spiti" in cat.items
    assert cat.moved["old/v-spiti"] == "new/ch01-spiti" and cat.moved["old/v-giatros"] == "new/v-giatros"
    assert ("old-book", "s1") not in cat.chapters and cat.chapter("new-book", "s1") is not None
    assert "new-book" in curriculum.available(cat) and "old-book" not in curriculum.available(cat)
    assert curriculum.active(cat).id == "new-book"

    packs.sync_items(conn, cat)
    states = {r[0]: r[1] for r in conn.execute("SELECT item_key, reps FROM review_state")}
    assert states == {"new/v-giatros": 2, "new/ch01-spiti": 2, "new/q-where": 2, "old/v-other": 2}
    keys = sorted(r[0] for r in conn.execute("SELECT item_key FROM attempts"))
    assert keys == ["new/ch01-spiti", "new/q-where", "new/v-giatros", "old/v-other"]
    flags = sorted(r[0] for r in conn.execute("SELECT item_key FROM flags"))
    assert flags == ["chapter:new-book/s1#2", "new/ch01-spiti"]
    plan = json.loads(conn.execute("SELECT plan_json FROM sessions WHERE id=1").fetchone()[0])
    assert [c["item_key"] for c in plan] == ["new/ch01-spiti", "old/v-other"]
    assert [tuple(r) for r in conn.execute("SELECT curriculum, stage FROM chapter_reads")] == [("new-book", "s1")]
    assert [r[0] for r in conn.execute("SELECT curriculum FROM stage_checks")] == ["new-book"]
    prog = curriculum.progress(conn, cat)
    assert prog.curriculum.id == "new-book" and prog.stages[0]["chapter"]["read"] and prog.stages[0]["passed_check"]

    # a second sync finds nothing left to move
    from oknos import moves
    assert moves.adopt(conn, cat.moved, curriculum.renames(cat)) == {"items": 0, "review_state": 0, "plans": 0, "curricula": 0}


def test_a_profile_naming_the_old_curriculum_gets_the_new_one(learner, tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "content_roots", lambda: _make(tmp_path, with_new=True))
    (learner / "profile.json").parent.mkdir(parents=True, exist_ok=True)
    (learner / "profile.json").write_text(json.dumps({"curriculum": "old-book"}), encoding="utf-8")
    assert curriculum.active(packs.load_all()).id == "new-book"


def test_the_open_book_replaces_the_maintainers_private_pack():
    """The tracked book declares what it took over, so a maintainer's private copy is never
    served beside it and their history follows."""
    manifest = json.loads((paths.CONTENT_DIR / "open" / "oknos-book" / "pack.json").read_text(encoding="utf-8"))
    assert manifest["replaces"] == ["greek-helper"] and manifest["visibility"] == "open"
    cur = curriculum.load_file(paths.REPO_ROOT / "curricula" / "oknos-book.json")
    assert cur.formerly == ["greek-helper-book"] and cur.for_pack == "oknos-book" and len(cur.stages) == 26
