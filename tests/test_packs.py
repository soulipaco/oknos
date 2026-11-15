import json
import re
import unicodedata
from pathlib import Path

import pytest

from greek_coach import packs, paths

OPEN = paths.CONTENT_DIR / "open"
OPEN_PACKS = sorted(p for p in OPEN.iterdir() if (p / "pack.json").exists())


def test_there_is_an_open_pack():
    assert OPEN_PACKS


@pytest.mark.parametrize("pack_dir", OPEN_PACKS, ids=lambda p: p.name)
def test_open_pack_loads_cleanly(pack_dir):
    pack, problems, _ = packs.load_pack(pack_dir, "open")
    assert problems == []
    assert pack is not None and len(pack.items) >= 10


@pytest.mark.parametrize("pack_dir", OPEN_PACKS, ids=lambda p: p.name)
def test_open_packs_are_open_and_openly_licensed(pack_dir):
    manifest = json.loads((pack_dir / "pack.json").read_text(encoding="utf-8"))
    assert manifest["visibility"] == "open"
    assert manifest["licence"] in packs.OPEN_LICENCES


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)


@pytest.mark.parametrize("pack_dir", OPEN_PACKS, ids=lambda p: p.name)
def test_greek_text_is_nfc_monotonic_with_final_sigma(pack_dir):
    medial_sigma_at_end = re.compile(r"σ(?![Ͱ-Ͽἀ-῿])")
    polytonic = re.compile(r"[ἀ-῿]")
    for file in [pack_dir / "pack.json", *sorted((pack_dir / "items").glob("*.json"))]:
        for s in _strings(json.loads(file.read_text(encoding="utf-8"))):
            assert unicodedata.is_normalized("NFC", s), f"{file.name}: not NFC: {s!r}"
            assert not polytonic.search(s), f"{file.name}: polytonic character in {s!r}"
            assert not medial_sigma_at_end.search(s), f"{file.name}: σ at the end of a word in {s!r}"


@pytest.mark.parametrize("pack_dir", OPEN_PACKS, ids=lambda p: p.name)
def test_vocab_meanings_are_unique(pack_dir):
    # Choice cards need distinct right answers, or two options could both be right.
    pack, _, _ = packs.load_pack(pack_dir, "open")
    vocab = [i for i in pack.items.values() if isinstance(i, packs.VocabItem)]
    for field in ("el", "en", "tr"):
        values = [getattr(i, field) for i in vocab if getattr(i, field)]
        assert len(values) == len(set(values)), f"duplicate {field} meaning"


def _write_pack(root: Path, items, manifest=None):
    (root / "items").mkdir(parents=True)
    (root / "pack.json").write_text(json.dumps(manifest or {
        "id": "test-pack", "title": {"en": "Test"}, "version": 1, "levels": ["A1"],
        "visibility": "private", "licence": "private", "source": "test",
    }), encoding="utf-8")
    (root / "items" / "a.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


def test_invalid_items_are_skipped_not_fatal(tmp_path):
    good = {"id": "ok", "type": "vocab", "skill": "vocab", "level": "A1", "el": "το ταξί", "en": "taxi"}
    _write_pack(tmp_path / "p", [
        good,
        {"id": "no-meaning", "type": "vocab", "skill": "vocab", "level": "A1", "el": "το ταξί"},
        {"id": "bad-answer", "type": "mcq", "skill": "vocab", "level": "A1", "prompt": {"el": "?"}, "options": ["α", "β"], "answer": 5},
        {"id": "later", "type": "table_fill", "skill": "reading", "level": "B1"},
        {"id": "typo", "type": "vocab", "skill": "vocab", "level": "A1", "el": "ο φίλος", "en": "friend", "colour": "x"},
        {"id": "ok", "type": "vocab", "skill": "vocab", "level": "A1", "el": "το ταξί", "en": "taxi"},
        "not an object",
    ])
    pack, problems, later = packs.load_pack(tmp_path / "p", "private")
    assert list(pack.items) == ["ok"]
    assert later == 1
    assert len(problems) == 5
    assert any("meaning" in p for p in problems)
    assert any("used twice" in p for p in problems)


def test_visibility_must_match_folder(tmp_path):
    _write_pack(tmp_path / "p", [])
    pack, problems, _ = packs.load_pack(tmp_path / "p", "open")
    assert pack is None and "visibility" in problems[0]


def test_needs_review_items_are_not_served(learner, tmp_path, monkeypatch):
    gen = learner / "generated" / "g"
    _write_pack(gen, [
        {"id": "a", "type": "vocab", "skill": "vocab", "level": "A1", "el": "το ταξί", "en": "taxi"},
        {"id": "b", "type": "vocab", "skill": "vocab", "level": "A1", "el": "η πίτσα", "en": "pizza", "status": "needs_review"},
    ], manifest={"id": "gen", "title": {"en": "G"}, "version": 1, "levels": ["A1"], "visibility": "generated",
                 "licence": "private", "source": "coach"})
    catalog = packs.load_all()
    keys = {k for k, _, _ in packs.servable(catalog, "en")}
    assert "gen/a" in keys and "gen/b" not in keys
