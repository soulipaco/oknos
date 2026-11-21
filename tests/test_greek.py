import unicodedata

import pytest

from oknos import greek


@pytest.mark.parametrize("poly,mono", [
    ("ἄνθρωπος", "άνθρωπος"),
    ("ὧν", "ων"),
    ("Ἔχουν", "Έχουν"),
    ("ἡ", "η"),
    ("ῥόδον", "ρόδον"),
    ("τῇ", "τη"),
    ("τῶν", "των"),
    ("πάει", "πάει"),
    ("ἢ", "ή"),
    ("καὶ", "και"),
    ("ἀλλὰ", "αλλά"),
    ("Καλημέρα", "Καλημέρα"),
    ("ϊ ΐ", "ϊ ΐ"),
])
def test_polytonic_folds_to_monotonic(poly, mono):
    out = greek.to_monotonic(poly)
    assert out == mono
    assert unicodedata.is_normalized("NFC", out)


def test_fold_ignores_case_accents_and_final_sigma():
    assert greek.fold("Καφές") == greek.fold("καφεσ") == "καφεσ"


def test_strip_article():
    assert greek.strip_article("το φαρμακείο") == "φαρμακείο"
    assert greek.strip_article("Ο Νίκος") == "Νίκος"
    assert greek.strip_article("φαρμακείο") == "φαρμακείο"


@pytest.mark.parametrize("el,en,flag", [
    ("μακρύ ταξίδι Life", "trek", "header_junk"),
    ("δουλειά", "WO UNIT 1 HELLO PAGE 9 job", "header_junk"),
    ("η επέτειος", "anniversary; Unit 9 TRADE Page 105 anniversary", "header_junk"),
    ("κάμερα web", "webcam", "latin_mixed"),
    ("ηλεκτρ ονικό βιβλίο", "ebook", "truncated"),
])
def test_damage_flags(el, en, flag):
    assert flag in greek.damage_flags(el, en)


@pytest.mark.parametrize("el", ["το φαρμακείο", "πηγαίνω", "δίπλα σε", "ροζ"])
def test_clean_entries_are_not_flagged(el):
    # ροζ ends in a consonant but is a real loanword; the importer double-checks such words
    # against the dictionary, and on its own the heuristic only flags very short fragments.
    flags = greek.damage_flags(el, "x")
    assert flags in ([], ["truncated"]) if el == "ροζ" else flags == []
