"""The open course's book (content/open/open-book): a chapter for every stage of the open curriculum."""

import json

from oknos import curriculum, db, packs, paths

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
    # a fresh clone's course is the Oknos book; the shorter open course is one profile line away
    conn = db.open_db()
    packs.sync_items(conn, full_catalog)
    prog = curriculum.progress(conn, full_catalog)
    assert prog.curriculum.id == "oknos-book"
    action = curriculum.next_action(prog, "fresh", 0)
    assert action["kind"] == "read" and action["stage"] == "intro"
    (open_book / "profile.json").write_text(json.dumps({"curriculum": "open-a1-b1"}), encoding="utf-8")
    prog = curriculum.progress(conn, full_catalog)
    assert prog.curriculum.id == "open-a1-b1"
    action = curriculum.next_action(prog, "fresh", 0)
    assert action["kind"] == "read" and action["stage"] == "reading"


def test_every_stage_of_the_oknos_book_has_a_chapter(full_catalog):
    cur = curriculum.available(full_catalog)["oknos-book"]
    assert len(cur.stages) == 26
    for stage in cur.stages:
        found = full_catalog.chapters.get((cur.id, stage.id))
        assert found is not None and found[0].id == "oknos-book", stage.id
        assert found[1].level == stage.level
    assert not [p for p in full_catalog.problems if "oknos-book" in p]
    book = paths.CONTENT_DIR / "open" / "oknos-book"
    # nothing points back at the private pack it came from or the textbook it once followed
    # (pack.json names that pack only in `replaces`, which moves the maintainer's history)
    manifest = json.loads((book / "pack.json").read_text(encoding="utf-8"))
    manifest.pop("replaces")
    text = json.dumps(manifest, ensure_ascii=False) + " ".join(f.read_text(encoding="utf-8") for f in book.glob("*/*.json"))
    for trace in ("greek-helper", "Greek_Helper", "Wordlist", ".pdf", "units.json", "Ders kitab"):
        assert trace not in text, trace


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


def test_comprehension_questions_carry_the_dialogue_outside_the_chapter(full_catalog):
    # "According to the dialogue": in a daily session the question comes without the chapter, so
    # its card carries the dialogue; in the reader it sits under the dialogue and does not.
    import random

    from oknos import session

    cur = _open_curriculum()
    checked = 0
    for stage in cur.stages:
        _, chapter = full_catalog.chapters[(cur.id, stage.id)]
        texts = chapter.comprehension_texts()
        for key, text in texts.items():
            _, item = full_catalog.items[key]
            if item.type in ("vocab", "form") or item.stimulus:
                continue
            card = session.task_card(key, item, random.Random(0))
            assert card["stimulus"] == {"text": text} and ": " in text.splitlines()[0]
            assert session.task_card(key, item, random.Random(0), in_chapter=True)["stimulus"] is None
            checked += 1
    assert checked >= 12


def test_a_letter_table_row_is_read_as_its_alphabet_card(full_catalog):
    # "Listen to each letter with ▶": a letter's row reads its name and example, not "Α α".
    from oknos.session import table_say

    assert table_say("Α α", full_catalog) == "άλφα. ταξί"
    assert table_say("Σ σ ς", full_catalog).startswith("σίγμα")
    assert table_say("γάλα", full_catalog) == "γάλα"
    assert table_say({"tr": "ses", "en": "sound"}, full_catalog) is None
    assert table_say("Ϙ ϙ", full_catalog) is None  # a lone letter with no card: nothing worth reading
