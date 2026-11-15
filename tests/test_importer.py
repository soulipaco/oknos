"""The importer, on a small synthetic source folder (never on anyone's real material)."""

import json

import pytest

from greek_coach import packs, paths
from greek_coach.importer import core, enrich
from greek_coach.importer.mapping import Mapping

FAKE_INDEX = {
    "version": enrich.INDEX_VERSION,
    "nouns": {"φαρμακείο": ["n"], "γιατρός": ["m", "f"], "κάλτσες": ["f"], "υπογράφω": []},
    "verbs": {},
    "glosses": {"φαρμακείο|noun": "pharmacy", "γιατρός|noun": "doctor", "κάλτσες|noun": "nominative plural of κάλτσα",
                "υπογράφω|verb": "to sign"},
}


@pytest.fixture
def source(tmp_path):
    src = tmp_path / "material"
    (src / "audio").mkdir(parents=True)
    vocab = [
        {"g": "φαρμακείο", "e": "pharmacy", "p": "n", "lvl": "Beginner", "src": {"doc": "list.pdf", "page": 2}},
        {"g": "φαρμακείο", "e": "chemist's", "p": "n", "lvl": "Elementary", "src": {"doc": "list.pdf", "page": 7}},
        {"g": "γιατρός", "e": "doctor", "p": "n", "lvl": "Beginner", "src": {"doc": "list.pdf", "page": 3}},
        {"g": "κάλτσες", "e": "socks", "p": "n", "lvl": "Beginner", "src": {"doc": "list.pdf", "page": 3}},
        {"g": "υπογ ράφω", "e": "sign", "p": "v", "lvl": "Beginner", "src": {"doc": "list.pdf", "page": 4}},
        {"g": "ἄνθρωπος", "e": "person", "p": "n", "lvl": "Beginner", "src": {"doc": "list.pdf", "page": 4}},
        {"g": "κάμερα web", "e": "webcam", "p": "n", "lvl": "Beginner", "src": {"doc": "list.pdf", "page": 5}},
        {"g": "δουλειά", "e": "WO UNIT 1 HELLO PAGE 9 job", "p": "n", "lvl": "Beginner", "src": {"doc": "list.pdf", "page": 9}},
    ]
    (src / "vocab.json").write_text(json.dumps({"rows": vocab}, ensure_ascii=False), encoding="utf-8")
    (src / "lessons.json").write_text(json.dumps([
        {"key": "l1", "n": 1, "name": "Lesson 1", "topic": "Shops", "path": "C:/Users/someone/scan.jpg"},
        {"key": "l2", "n": 2, "name": "Lesson 2", "topic": "Health"},
    ]), encoding="utf-8")
    (src / "pages.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in [
        {"lesson": "l2", "text": "Πάω στο φαρμακείο και στον γιατρό."},
        {"lesson": "l1", "text": "Ο γιατρός μένει εδώ."},
    ]), encoding="utf-8")
    (src / "exercises.json").write_text(json.dumps([
        {"id": "e1", "body": "1 Ἀκούω καὶ γράφω τις λέξεις που λείπουν στο κείμενο.", "lesson": "l1", "pg": 10, "file": "C:/secret/book.pdf"},
        {"id": "e2", "body": "1 Ἀκούω καὶ γράφω τις λέξεις που λείπουν στο κείμενο.", "lesson": "l1", "pg": 11},
        {"id": "e3", "body": "ab", "lesson": "l1", "pg": 12},
        {"id": "e4", "body": "Λύσεις: 1 πήγα, 2 ήρθε, 3 έφαγαν, 4 είδαμε το φαρμακείο.", "lesson": "l2", "pg": 99, "key": True},
    ], ensure_ascii=False), encoding="utf-8")
    (src / "audio" / "01.mp3").write_bytes(b"ID3fake")
    (src / "transcripts.json").write_text(json.dumps({"01.mp3": "Καλημέρα.", "02.mp3": "Γεια."}, ensure_ascii=False), encoding="utf-8")
    return src


MAPPING = {
    "pack": {"id": "my-book", "title": {"en": "My book"}},
    "vocabulary": {"file": "vocab.json", "lists": ["rows"],
                   "fields": {"greek": "g", "en": "e", "pos": "p", "level": "lvl", "doc": "src.doc", "page": "src.page"},
                   "levels": {"Beginner": "A1", "Elementary": "A1"}, "pos": {"n": "noun", "v": "verb"}},
    "pages": {"file": "pages.jsonl", "fields": {"unit": "lesson", "text": "text"}},
    "units": {"file": "lessons.json", "fields": {"id": "key", "order": "n", "title": "name", "theme": "topic"}},
    "raw": [{"name": "exercises", "file": "exercises.json",
             "fields": {"id": "id", "text": "body", "unit": "lesson", "page": "pg", "doc": "file"},
             "kind_rules": [{"field": "key", "equals": True, "kind": "answer_key"}]}],
    "audio": {"dir": "audio", "transcripts": "transcripts.json"},
}


def run(source, learner, monkeypatch, tmp_path):
    monkeypatch.setattr(enrich, "load_index", lambda: FAKE_INDEX)
    monkeypatch.setattr(paths, "CONTENT_DIR", tmp_path / "content")
    return core.run(Mapping.model_validate(MAPPING), source)


def test_import_writes_a_clean_private_pack(source, learner, monkeypatch, tmp_path):
    out, report = run(source, learner, monkeypatch, tmp_path)
    assert out == (tmp_path / "content" / "private" / "my-book").resolve()
    pack, problems, _ = packs.load_pack(out, "private")
    assert problems == [] and pack.manifest.visibility == "private"
    items = {i.lemma: i for i in pack.items.values()}

    # Deduped with senses and sources merged; article from the dictionary; unit link from the pages.
    f = items["φαρμακείο"]
    assert f.el == "το φαρμακείο" and f.gender == "n"
    assert "pharmacy" in f.en and "chemist's" in f.en
    assert f.source["also"] == [{"doc": "list.pdf", "page": 7}]
    assert f.topics == ["unit:l2"]
    assert items["γιατρός"].el == "ο/η γιατρός" and items["γιατρός"].topics == ["unit:l1"]
    assert items["κάλτσες"].el == "οι κάλτσες"
    assert "υπογράφω" in items, "the OCR-split word is joined again"
    assert "άνθρωπος" in items, "polytonic is folded to monotonic"

    # Damaged entries are flagged and kept out, not imported silently.
    flagged = json.loads((out / "raw" / "vocab_flagged.json").read_text(encoding="utf-8"))
    assert {e["greek"] for e in flagged} == {"κάμερα web", "δουλειά"}
    assert report.counts["vocab_duplicates_merged"] == 1

    # Lessons import without absolute paths; exercises go to raw/ with reasons for drops.
    units = json.loads((out / "units.json").read_text(encoding="utf-8"))
    assert [u["id"] for u in units] == ["l1", "l2"] and "path" not in json.dumps(units)
    raw = json.loads((out / "raw" / "exercises.json").read_text(encoding="utf-8"))
    assert [r["id"] for r in raw] == ["e1", "e4"]
    assert raw[0]["text"].startswith("1 Ακούω και") and raw[0]["doc"] == "book.pdf"
    assert raw[1]["kind"] == "answer_key"
    assert report.counts["raw_exercises"]["dropped_by_reason"] == {"duplicate": 1, "too_short": 1}
    assert "C:/" not in json.dumps(raw)

    # Audio that exists is copied and flagged for review; the missing file is listed.
    audio = json.loads((out / "raw" / "audio.json").read_text(encoding="utf-8"))
    assert [a["file"] for a in audio["files"]] == ["audio/01.mp3"] and audio["files"][0]["status"] == "needs_review"
    assert audio["missing"] == ["02.mp3"]
    assert (out / "IMPORT_REPORT.md").read_text(encoding="utf-8").startswith("# Import report: my-book")


def test_turkish_overlay_survives_reimport(source, learner, monkeypatch, tmp_path):
    out, _ = run(source, learner, monkeypatch, tmp_path)
    (out / "overlays").mkdir()
    (out / "overlays" / "tr.json").write_text(json.dumps({"words": {"φαρμακειο|noun": {"tr": "eczane"}}}), encoding="utf-8")
    out, report = run(source, learner, monkeypatch, tmp_path)
    pack, _, _ = packs.load_pack(out, "private")
    f = next(i for i in pack.items.values() if i.lemma == "φαρμακείο")
    assert f.tr == "eczane" and f.source["tr"] == "coach, unverified"
    assert report.counts["vocab_tr_from_overlay"] == 1


def test_import_refuses_tracked_folders(source, learner, monkeypatch, tmp_path):
    with pytest.raises(core.ImportError_):
        core.run(Mapping.model_validate(MAPPING), source, paths.CONTENT_DIR / "open" / "leak")
    with pytest.raises(core.ImportError_):
        core.run(Mapping.model_validate(MAPPING), source, tmp_path / "anywhere")


def test_builtin_mapping_is_valid_and_has_no_absolute_paths():
    from greek_coach.importer import mapping

    path = paths.REPO_ROOT / "src" / "greek_coach" / "importer" / "mappings" / "greek-helper.json"
    m = mapping.load(path)
    assert m.pack.id == "greek-helper" and "C:" not in path.read_text(encoding="utf-8")
