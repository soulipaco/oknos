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


def test_the_home_screen_shows_words_with_pictures_first(learner, client):
    home = client.get("/api/home").json()
    words = home["words"]
    assert words is not None and set(words) == {"lesson", "new", "new_count"}
    assert len(words["lesson"]) <= 4 and len(words["new"]) <= 4
    shown = words["lesson"] + words["new"]
    assert all(w["el"] and "key" in w for w in shown)
    for group in (words["lesson"], words["new"]):  # those with a picture come first
        flags = [w["picture"] is None for w in group]
        assert flags == sorted(flags)


def _scene_pack(tmp_path, with_file: bool):
    pack_dir = tmp_path / "story"
    (pack_dir / "pictures").mkdir(parents=True)
    (pack_dir / "items").mkdir()
    (pack_dir / "pack.json").write_text(json.dumps({"id": "story", "title": {"en": "S"}, "version": 1, "levels": ["A1"],
                                                    "visibility": "open", "licence": "CC-BY-SA-4.0", "source": "t"}))
    if with_file:
        (pack_dir / "pictures" / "scene-bakery.webp").write_bytes(b"RIFF0000WEBP")
    item = {"id": "q-bakery", "type": "true_false", "skill": "reading", "level": "A1",
            "stimulus": {"pictures": ["scene-bakery.webp"]},
            "statements": [{"el": "Η Ζεϊνέπ αγοράζει ψωμί.", "answer": True}]}
    (pack_dir / "items" / "scene.json").write_text(json.dumps([item], ensure_ascii=False), encoding="utf-8")
    return packs.load_pack(pack_dir, "open")


def test_a_task_can_show_a_scene_of_the_story(tmp_path):
    pack, problems, _ = _scene_pack(tmp_path, with_file=True)
    assert not problems and "q-bakery" in pack.items
    card = session.task_card("story/q-bakery", pack.items["q-bakery"], random.Random(1))
    assert card["stimulus"]["pictures"] == ["/pictures/story/scene-bakery.webp"]


def test_a_task_whose_scene_is_missing_is_skipped(tmp_path):
    pack, problems, _ = _scene_pack(tmp_path, with_file=False)
    assert "q-bakery" not in pack.items
    assert any("scene-bakery.webp" in p for p in problems)


def test_a_scene_name_cannot_leave_the_pictures_folder():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        packs.Stimulus.model_validate({"pictures": ["../pack.json"]})
    with pytest.raises(ValidationError):
        packs.Stimulus.model_validate({"pictures": ["a.webp", "b.webp", "c.webp"]})
    from oknos import chapters

    d = chapters.Dialogue.model_validate({"type": "dialogue", "picture": "scene.webp",
                                          "lines": [{"who": "A", "el": "Γεια.", "tr": "Selam.", "en": "Hi."}] * 2})
    assert d.picture == "scene.webp"


def test_the_practise_screen_counts_what_is_waiting(learner, client):
    counts = client.get("/api/practise").json()
    assert {"words", "verbs", "reading", "listening", "writing", "speaking", "review"} <= set(counts)
    assert counts["words"]["total"] > 0 and counts["words"]["new"] >= 0
    assert set(counts["review"]) == {"due", "mistakes"}


def test_the_book_and_the_word_list_carry_pictures(learner, client):
    words = client.get("/api/words").json()["words"]
    assert any(w["picture"] for w in words) and all("picture" in w for w in words)
    cur = client.get("/api/curriculum").json()
    if cur.get("curriculum"):
        assert isinstance(cur["pictures"], dict)
        for pics in cur["pictures"].values():
            assert len(pics) <= 4 and all(p["picture"].startswith("/pictures/") for p in pics)
