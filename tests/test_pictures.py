"""Phase 9: a word's picture, on its cards and in "pick the picture"."""

import json
import random

from oknos import checking, packs, scheduler, session


def test_a_word_finds_its_picture_with_or_without_its_article(catalog):
    _, kafes = catalog.items["open-shared-words-tr/v-kafes"]
    assert packs.picture_url(kafes) == "/pictures/open-pictures/v-kafes.webp"
    from oknos import greek

    assert packs.picture_keys("ο καφές") == {greek.fold("ο καφές"), greek.fold("καφές")}
    assert len(packs.all_picture_urls()) >= 12


def test_the_same_word_in_another_pack_shares_the_picture(catalog):
    item = packs.VocabItem.model_validate({"id": "x", "type": "vocab", "skill": "vocab", "level": "A1", "el": "η ντομάτα", "en": "tomato"})
    assert packs.picture_url(item) == "/pictures/open-pictures/v-ntomata.webp"
    other = packs.VocabItem.model_validate({"id": "y", "type": "vocab", "skill": "vocab", "level": "A1", "el": "η ντομάτες", "en": "tomatoes"})
    assert packs.picture_url(other) is None


def test_pick_the_picture_card_and_its_check(catalog):
    pack, kafes = catalog.items["open-shared-words-tr/v-kafes"]
    seen = scheduler.State(item_key="open-shared-words-tr/v-kafes", due_at="2026-01-01", reps=2)
    distract = session.Distractors([("open-shared-words-tr/v-kafes", pack, kafes)])
    cards = [session.vocab_card("open-shared-words-tr/v-kafes", pack, kafes, "tr", "el_meaning", distract,
                                random.Random(seed), seen) for seed in range(40)]
    pic = [c for c in cards if c["direction"] == "el_picture"]
    assert pic and len(pic) < len(cards)  # sometimes, not always
    card = pic[0]
    right = "/pictures/open-pictures/v-kafes.webp"
    assert len(card["options"]) == 4 and right in card["options"] and card["prompt"] == "ο καφές"
    assert card["meaning"] and card["picture"] == right
    ok = checking.check(kafes, card, {"choice": right})
    wrong = checking.check(kafes, card, {"choice": next(o for o in card["options"] if o != right)})
    assert ok.correct and not wrong.correct and wrong.answer == right
    # a new word is taught first, with its picture, and never starts as "pick the picture"
    new = session.vocab_card("open-shared-words-tr/v-kafes", pack, kafes, "tr", "el_meaning", distract, random.Random(1), None)
    assert new["direction"] == "el_meaning" and new["learn"]["picture"] == right


def test_the_picture_is_served_and_nothing_else(client):
    r = client.get("/pictures/open-pictures/v-kafes.webp")
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
    assert client.get("/pictures/open-pictures/pictures.json").status_code == 404
    assert client.get("/pictures/open-pictures/..%2Fpack.json").status_code == 404
    assert client.get("/pictures/nope/v-kafes.webp").status_code == 404


def test_a_missing_picture_file_is_a_problem(tmp_path):
    pack_dir = tmp_path / "pics"
    (pack_dir / "pictures").mkdir(parents=True)
    (pack_dir / "pack.json").write_text(json.dumps({"id": "pics", "title": {"en": "P"}, "version": 1, "levels": ["A1"],
                                                    "visibility": "open", "licence": "CC-BY-SA-4.0", "source": "t"}))
    (pack_dir / "pictures" / "pictures.json").write_text(json.dumps(
        {"source": "t", "licence": "CC-BY-SA-4.0", "pictures": [{"word": "το ψωμί", "file": "psomi.webp"}]}, ensure_ascii=False),
        encoding="utf-8")
    pack, problems, _ = packs.load_pack(pack_dir, "open")
    assert any("psomi.webp" in p and "missing" in p for p in problems)
