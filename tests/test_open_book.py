"""The open course's book (content/open/open-book): a chapter for every stage of the open curriculum."""

import json

from greek_coach import curriculum, db, packs, paths

BOOK = paths.CONTENT_DIR / "open" / "open-book"


def _open_curriculum():
    return curriculum.load_file(paths.REPO_ROOT / "curricula" / "open-a1-b1.json")


def test_every_open_stage_has_a_reviewed_chapter(full_catalog):
    cur = _open_curriculum()
    for stage in cur.stages:
        found = full_catalog.chapters.get((cur.id, stage.id))
        assert found is not None, f"no chapter for {stage.id}"
        pack, chapter = found
        assert pack.id == "open-book" and chapter.level == stage.level
        assert (BOOK / "lessons" / "review" / f"{stage.id}.md").is_file(), f"no review note for {stage.id}"
    manifest = json.loads((BOOK / "pack.json").read_text(encoding="utf-8"))
    assert manifest["visibility"] == "open" and manifest["licence"] == "CC-BY-SA-4.0"


def test_chapter_items_belong_to_their_stage(full_catalog):
    for path in sorted((BOOK / "items").glob("chapter-*.json")):
        stage = path.stem.removeprefix("chapter-")
        for raw in json.loads(path.read_text(encoding="utf-8")):
            _, item = full_catalog.items[f"open-book/{raw['id']}"]
            assert f"stage:{stage}" in item.topics, raw["id"]
            assert item.source and item.source.get("doc") == "chapter" and item.source.get("stage") == stage, raw["id"]


def test_the_open_book_has_no_load_problems(full_catalog):
    assert not [p for p in full_catalog.problems if "open-book" in p]


def test_a_fresh_learner_starts_by_reading_the_first_chapter(open_book, full_catalog):
    conn = db.open_db()
    packs.sync_items(conn, full_catalog)
    prog = curriculum.progress(conn, full_catalog)
    assert prog.curriculum.id == "open-a1-b1"
    action = curriculum.next_action(prog, "fresh", 0)
    assert action["kind"] == "read" and action["stage"] == "reading"


def _book_with_curriculum(tmp_path, follows):
    """A private book with its own two-stage curriculum, one chapter, and the word το σπίτι."""
    pack = tmp_path / "private" / "my-book"
    (pack / "items").mkdir(parents=True)
    (pack / "lessons").mkdir()
    (pack / "pack.json").write_text(json.dumps({
        "id": "my-book", "title": {"en": "My book"}, "version": 1, "levels": ["A1"],
        "visibility": "private", "licence": "private", "source": "tests"}), encoding="utf-8")
    (pack / "curriculum.json").write_text(json.dumps({
        "id": "my-book-course", "title": {"en": "My book"}, "source": "tests", "for_pack": "my-book",
        "stages": [{"id": "lesson-01", "title": {"en": "One"}, "level": "A1"},
                   {"id": "lesson-02", "title": {"en": "Two"}, "level": "A1"}],
        "pools": [{"level": "A1", "from_stage": "lesson-02"}],
        "follows": follows}), encoding="utf-8")
    (pack / "items" / "words.json").write_text(json.dumps([
        {"id": "w-spiti", "type": "vocab", "skill": "vocab", "level": "A1", "el": "το σπίτι", "en": "house",
         "tr": "ev", "topics": ["stage:lesson-01"]}], ensure_ascii=False), encoding="utf-8")
    (pack / "lessons" / "lesson-01.json").write_text(json.dumps({
        "id": "my-book-course.lesson-01", "curriculum": "my-book-course", "stage": "lesson-01", "level": "A1",
        "title": {"tr": "Bir", "en": "One"}, "minutes": 6, "sections": [
            {"kind": "intro", "blocks": [{"type": "prose", "tr": "Ev.", "en": "A house."}]},
            {"kind": "text", "blocks": [{"type": "dialogue", "lines": [
                {"who": "Νίκος", "el": "Το σπίτι.", "tr": "Ev.", "en": "The house."},
                {"who": "Μαρία", "el": "Ναι.", "tr": "Evet.", "en": "Yes."}]}]},
            {"kind": "grammar", "blocks": [{"type": "prose", "tr": "Yok.", "en": "None."}]},
            {"kind": "words", "blocks": [{"type": "words", "items": ["my-book/w-spiti"]}]},
            {"kind": "try", "blocks": [{"type": "check", "items": ["my-book/w-spiti"]}]}]},
        ensure_ascii=False), encoding="utf-8")


def test_the_open_book_supports_a_private_books_curriculum(open_book, tmp_path):
    _book_with_curriculum(tmp_path, {"open-a1-b1": {"first-words": "lesson-01"}})
    catalog = packs.load_all()
    cur = curriculum.available(catalog)["my-book-course"]
    assert curriculum.active(catalog).id == "my-book-course"
    placed, pooled = curriculum.placed(cur, catalog)
    # a word the book already has is not served twice
    assert placed["open-book/ch02-spiti"] is None
    # a practice item of a mapped stage is an extra at the stage it maps to
    assert placed["open-book/ch02-try-eimaste"] == 0 and "open-book/ch02-try-eimaste" in pooled
    # a word the book lacks, of an unmapped stage, goes to its level pool, as an extra
    assert placed["open-book/ch03-synithos"] == 1 and "open-book/ch03-synithos" in pooled
    # the book's own word is placed as before, and counts
    assert placed["my-book/w-spiti"] == 0 and "my-book/w-spiti" not in pooled
    # under the open curriculum the open book is at home again
    open_cur = curriculum.available(catalog)["open-a1-b1"]
    placed, pooled = curriculum.placed(open_cur, catalog)
    assert placed["open-book/ch02-spiti"] == 1 and "open-book/ch02-spiti" not in pooled


def test_follows_must_name_real_stages(open_book, tmp_path):
    _book_with_curriculum(tmp_path, {"open-a1-b1": {"first-words": "lesson-99"}})
    assert "my-book-course" not in curriculum.available(packs.load_all())
