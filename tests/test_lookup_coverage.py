"""Phase 5d: every Greek word you can tap has a meaning; no question hidden behind "Translate"."""

import json
import random

from test_chapters import STAGE, book, chapter_data  # noqa: F401  (the book fixture)

from greek_coach import chapters, db, lint, lookup, packs, report, session, wordscan
from greek_coach.packs import TrueFalseItem


def test_every_tappable_word_of_the_open_packs_has_a_meaning(full_catalog):
    # the open packs alone, the open book included: a fresh clone has nothing else
    gaps = wordscan.scan(full_catalog.packs, lookup.Index(full_catalog))
    assert gaps.total > 1000
    missing = {place: sorted(words) for place, words in gaps.missing.items() if words}
    assert not missing, f"tappable words with no meaning (run `greek-coach words content/open --write`): {missing}"


def test_the_test_chapter_has_no_unexplained_word(book, learner):
    catalog = packs.load_all()
    pack = next(p for p in catalog.packs if p.id == "test-book")
    gaps = wordscan.scan([pack], lookup.Index(catalog))
    assert gaps.total and not gaps.unexplained, sorted(gaps.unexplained)


def test_the_scan_reads_what_the_screen_makes_tappable(catalog):
    _, item = catalog.items["open-verbs-a1a2/f-vlepo-future-3sg"]
    texts = list(wordscan.item_texts(item))
    # the sentence with its answer filled in, as shown after checking; never the wrong choices
    assert any("θα δει" in t for t in texts)
    wrong = {o for opts in (item.options or {}).values() for o in opts} - {a for ans in item.answer.values() for a in ans}
    assert not any(w in t for w in wrong for t in texts)
    ch = chapters.parse(chapter_data())
    words = wordscan.tappable(wordscan.chapter_texts(ch))
    assert "παρακαλώ" in words and "είσαι" in words
    assert "Νίκος" not in words  # the speaker's name is shown, but not as tappable Greek


def test_a_form_finds_its_word_and_says_it_is_a_form(catalog, client):
    index = lookup.Index(catalog)
    entries, how = index.find("ακούστε")
    assert how == "form" and entries[0].el == "ακούω" and entries[0].form_of == "ακούω"
    entries, how = index.find("Διαλέξτε")  # capitalised at the start of a rubric
    assert how == "form" and entries[0].el == "διαλέγω"
    entries, how = index.find("Διαλέγω")
    assert how == "exact" and entries[0].form_of is None
    entries, how = index.find("τη")  # an article's variants are not "forms of" another article
    assert how == "exact" and entries[0].form_of is None
    r = client.post("/api/lookup", json={"word": "απαντήσεις", "ui_lang": "tr"}).json()
    assert r["match"] == "form" and r["entries"][0]["form_of"] == "απάντηση" and r["entries"][0]["meaning"] == "cevap"


def test_names_and_places(catalog):
    index = lookup.Index(catalog)
    entries, how = index.find("Μεχμέτ")
    assert how == "name" and entries[0].tr.startswith("özel isim")
    entries, how = index.find("Νάξο")
    assert how == "name" and entries[0].el == "Νάξος" and entries[0].en == "a place name"
    entries, how = index.find("Γιώργου")  # a form of a known name, by its stem
    assert how == "name" and entries[0].el == "Γιώργος"
    assert index.find("νάξο")[1] != "name"  # lower case is not a name


def test_a_chapter_speaker_is_a_name(book, learner):
    data = chapter_data()
    data["sections"][1]["blocks"][0]["lines"][0]["who"] = "Ζαφείρης"
    (book / "lessons" / f"{STAGE}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    index = lookup.Index(packs.load_all())
    entries, how = index.find("Ζαφείρη")  # the vocative / accusative of the speaker
    assert how == "name" and entries[0].el == "Ζαφείρης"


def test_a_glossary_is_checked(tmp_path, catalog):
    pack_dir = tmp_path / "gloss"
    (pack_dir / "items").mkdir(parents=True)
    (pack_dir / "pack.json").write_text(json.dumps({
        "id": "gloss", "title": {"en": "Gloss"}, "version": 1, "levels": ["A1"], "visibility": "generated",
        "licence": "private", "source": "tests"}), encoding="utf-8")
    (pack_dir / "items" / "a.json").write_text(json.dumps([
        {"id": "s", "type": "true_false", "skill": "reading", "level": "A1",
         "statements": [{"el": "Η χρυσόσκονη είναι κλειστό σήμερα.", "answer": True}]}], ensure_ascii=False), encoding="utf-8")
    (pack_dir / "glossary.json").write_text(json.dumps({"words": [{"el": "η χρυσόσκονη"}]}, ensure_ascii=False), encoding="utf-8")
    pack, problems, _ = packs.load_pack(pack_dir)
    assert pack.glossary is None and any("glossary.json" in p and "meaning" in p for p in problems)

    (pack_dir / "glossary.json").write_text(json.dumps({
        "words": [{"el": "η χρυσόσκονη", "en": "gold dust", "tr": "altın tozu"}],
        "forms": {"κλειστό": "κλειστός", "σήμερα": "σήμερον"}}, ensure_ascii=False), encoding="utf-8")
    pack, problems, _ = packs.load_pack(pack_dir)
    assert not problems and pack.glossary.words[0].tr == "altın tozu"
    problems, notes = wordscan.lint_pack(pack, packs.load_all())
    assert any("'σήμερον'" in p for p in problems)  # a form pointing at nothing is a problem
    entries, how = lookup.Index(packs.load_all()).find("χρυσόσκονη")
    assert entries == []  # the pack is outside the content folders, so the app does not load it
    loaded = packs.load_all()
    loaded.packs.append(pack)
    entries, how = lookup.Index(loaded).find("χρυσόσκονη")
    assert how == "exact" and entries[0].tr == "altın tozu"


def test_a_question_only_in_the_translation_is_flagged(catalog, full_catalog):
    hidden = TrueFalseItem.model_validate({
        "id": "signs", "type": "true_false", "skill": "reading", "level": "A1",
        "statements": [{"el": "ΣΤΑΣΗ", "en": "The sign ΣΤΑΣΗ shows a bus stop.", "tr": "ΣΤΑΣΗ bir durak gösterir.",
                        "answer": True}]})
    fixed = hidden.model_copy(update={"statements": [hidden.statements[0].model_copy(
        update={"el": "Η ΣΤΑΣΗ είναι για το λεωφορείο."})]})
    asked = hidden.model_copy(update={"ask": packs.Text(en="Is this the bus stop sign?", tr="Bu otobüs durağı tabelası mı?")})
    pack = catalog.packs[0]
    for item, flagged in ((hidden, True), (fixed, False), (asked, False)):
        pack_items = pack.items
        pack.items = {"signs": item}
        try:
            notes = lint.hidden_questions(pack)
        finally:
            pack.items = pack_items
        assert bool(notes) == flagged, (item, notes)
    assert "the Greek must carry the question" in lint.hidden_questions(type(pack)(pack.manifest, pack.path, {"signs": hidden}))[0]
    card = session.task_card("x/signs", asked, random.Random(0))
    assert card["ask"]["tr"] == "Bu otobüs durağı tabelası mı?"
    assert not [n for p in full_catalog.packs for n in lint.hidden_questions(p)]  # none in the open packs


def test_a_question_or_an_instruction_only_in_the_translation_is_found():
    hides = lint._hides_question
    # the question is only in the translation (the maintainer's flag: «ποτέ» / "How is ποτέ read?")
    assert hides("ποτέ", ["How is ποτέ read?", "ποτέ nasıl okunur?"])
    assert hides("210", ["How is 210 (the Athens area code) read digit by digit?"])
    # a bare instruction whose real task is in the translation
    assert hides("Αντιστοιχίζω.", ["Match each word with how it is read.", "Her kelimeyi okunuşuyla eşleştir."])
    assert hides("Ποια πρόταση είναι σωστή;", ['Which sentence is right? ("I am waiting for you", to one friend)'])
    # a plain translation, or a generic instruction, is fine
    assert not hides("Συμπληρώνω.", ["Fill in the gaps.", "Boşlukları doldur."])
    assert not hides("Πόσο κάνει;", ["How much is it?"])
    assert not hides("Θα πάνε σινεμά το βράδυ.", ["They will go to the cinema in the evening."])
    assert not hides("Γράψτε ένα e-mail (40–60 λέξεις).", ["Write an e-mail (40–60 words)."])
    assert not hides("— Βλέπεις τηλεόραση; — Όχι, …", ["— Do you watch TV? — No, …"])


def test_the_report_counts_the_words_that_find_nothing(open_book, full_catalog):
    rep = report.build(db.open_db(), full_catalog)
    tap = rep["tap_a_word"]
    assert rep["report_version"] == 4 and tap["total"] > 1000 and tap["unexplained"] == 0 and tap["share"] == 0
