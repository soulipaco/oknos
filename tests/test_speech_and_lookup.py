"""What the voice reads, which language a meaning is in, and what a tapped word finds."""

import random

from oknos import chapters, lookup, packs, session
from oknos.checking import meaning, meaning_lang
from oknos.packs import VocabItem


def test_letter_cards_say_the_name_and_an_example_not_the_letters(catalog):
    _, sigma = catalog.items["open-alphabet/l-sigma"]
    assert sigma.el == "Σ σ ς" and sigma.say == "σίγμα. σούπα"
    letters = [i for k, (p, i) in catalog.items.items() if p.id == "open-alphabet" and i.pos in ("letter", "digraph")]
    assert letters and all(i.say for i in letters)
    words = [(k, p, i) for k, (p, i) in catalog.items.items() if isinstance(i, VocabItem)]
    card = session.vocab_card("open-alphabet/l-sigma", *catalog.items["open-alphabet/l-sigma"], "en", "el_meaning",
                              session.Distractors(words), random.Random(0), None, catalog)
    assert card["speak"] == "σίγμα. σούπα" and card["el"] == "Σ σ ς"
    assert card["learn"]["say"] == "σίγμα. σούπα"


def test_a_meaning_that_falls_back_says_which_language_it_is_in():
    only_en = VocabItem(id="x", type="vocab", skill="vocab", level="B1", el="η επιρροή", en="influence")
    both = VocabItem(id="y", type="vocab", skill="vocab", level="A1", el="ο καφές", en="coffee", tr="kahve")
    assert (meaning(only_en, "tr"), meaning_lang(only_en, "tr")) == ("influence", "en")
    assert (meaning(both, "tr"), meaning_lang(both, "tr")) == ("kahve", "tr")


def test_lookup_finds_function_words_and_words_inside_phrases(catalog):
    index = lookup.Index(catalog)
    entries, how = index.find("την")
    assert how == "exact" and entries[0].tr.startswith("belirli artikel")
    entries, how = index.find("από")
    assert entries and "from" in entries[0].en
    # a word that only occurs inside a phrase item finds the phrase
    phrase = VocabItem(id="p", type="vocab", skill="vocab", level="A1", el="καλή όρεξη", pos="phrase", en="enjoy your meal")
    pack = catalog.packs[0]
    catalog.items["test/p"] = (pack, phrase)
    entries, how = lookup.Index(catalog).find("όρεξη")
    assert how == "phrase" and entries[0].el == "καλή όρεξη"
    data = lookup.as_json(entries, how, "tr")
    assert data["entries"][0]["meaning_lang"] == "en"


def test_a_table_cell_can_be_an_explanation_in_both_languages():
    ch = chapters.parse({
        "id": "c", "curriculum": "open-a1-b1", "stage": "reading", "level": "A1", "title": {"tr": "t", "en": "t"},
        "minutes": 8, "sections": [
            {"kind": "intro", "blocks": [{"type": "prose", "tr": "a", "en": "a"}]},
            {"kind": "text", "blocks": [{"type": "examples", "items": [{"el": "το τσάι", "tr": "çay", "en": "tea"}]}]},
            {"kind": "grammar", "blocks": [{"type": "table", "head": ["", {"tr": "Okunuş", "en": "Sound"}],
                                            "rows": [["τσ", {"tr": "ç gibi", "en": "ts as in cats"}]]}]},
            {"kind": "words", "blocks": [{"type": "words", "items": ["open-alphabet/d-ts"]}]},
            {"kind": "try", "blocks": [{"type": "check", "items": ["open-alphabet/d-ts"]}]},
        ]})
    assert ch.table_cells() == ["", "τσ"]  # only the Greek cells are Greek


def test_the_verb_pack_puts_the_standard_form_first(catalog):
    first = {i.id: next(iter(i.answer.values()))[0] for k, (p, i) in catalog.items.items() if p.id == "open-verbs-a1a2"}
    assert first["f-vlepo-future-3sg"] == "θα δει"
    assert first["f-vrisko-aorist-2sg"] == "βρήκες"
    assert first["f-kano-aorist-3pl"] == "έκαναν"
    old = ("θα ιδ", "ηύρ", "θα εύρ", "κάμ", "έκαμ", "σθ")
    assert not [f for f in first.values() if any(o in f for o in old)]
    assert all(i.translation.tr for k, (p, i) in catalog.items.items() if p.id == "open-verbs-a1a2")


def test_tapping_a_function_word_through_the_api(client):
    r = client.post("/api/lookup", json={"word": "την", "ui_lang": "tr"})
    assert r.status_code == 200 and r.json()["entries"][0]["meaning"].startswith("belirli artikel")
    r = client.post("/api/lookup", json={"word": "από", "ui_lang": "en"})
    assert r.status_code == 200 and "from" in r.json()["entries"][0]["meaning"]
