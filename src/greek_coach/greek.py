"""Greek text helpers shared by the importer, the answer checker and lookups.

Everything here works on NFC strings and returns NFC strings.
"""

from __future__ import annotations

import re
import unicodedata

# Combining marks in decomposed (NFD) Greek.
_ACUTE = "́"
_GRAVE = "̀"
_PERISPOMENI = "͂"
_PSILI = "̓"
_DASIA = "̔"
_YPOGEGRAMMENI = "ͅ"
_DIAERESIS = "̈"
_TO_ACUTE = {_GRAVE, _PERISPOMENI, "̃"}  # varia, perispomeni, and tilde (OCR reads perispomeni as tilde)
_DROP = {_PSILI, _DASIA, _YPOGEGRAMMENI, "̄", "̆", "̓"}  # breathings, iota subscript, macron, breve, koronis
# Spacing forms of polytonic marks that OCR sometimes leaves on their own.
_SPACING_MARKS = dict.fromkeys(map(ord, "᾽ι᾿῀῁῍῎῏῝῞῟῭΅`´῾΄΅"), None)

GREEK_LETTER = r"[Ͱ-Ͽἀ-῿]"
_WORD_RE = re.compile(r"[Ͱ-Ͽἀ-῿̀-ͯ]+(?:['’][Ͱ-Ͽἀ-῿]+)?")
_LATIN_RE = re.compile(r"[A-Za-z]")
_VOWELS = set("αεηιουω")

ARTICLES = ("ο", "η", "το", "οι", "τα", "τον", "την", "τη", "του", "της", "των", "τους", "τις")
ARTICLE_FOR_GENDER = {"m": "ο", "f": "η", "n": "το"}


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


_KEEP_MONOSYLLABLE_ACCENT = {"ή", "πού", "πώς"}


def to_monotonic(text: str) -> str:
    """Fold polytonic Greek (as OCR often produces it) to monotonic: ἄ→ά, ὧν→ών, ῥ→ρ, ᾳ→α.

    A one-syllable word whose accent was a grave or circumflex (καὶ, τῇ, τῶν) loses it, as
    monotonic spelling has no accent on monosyllables (except ή, πού, πώς).
    """
    if any(m in unicodedata.normalize("NFD", text) for m in (_GRAVE, _PERISPOMENI)):
        def fix(m: re.Match) -> str:
            word = m.group(0)
            nfd = unicodedata.normalize("NFD", word)
            folded = _fold_marks(word)
            if (_GRAVE in nfd or _PERISPOMENI in nfd) and syllables(folded) < 2 and folded not in _KEEP_MONOSYLLABLE_ACCENT:
                return strip_accents(folded)
            return word
        text = _WORD_RE.sub(fix, text)
    return _fold_marks(text)


def _fold_marks(text: str) -> str:
    text = text.translate(_SPACING_MARKS)
    out: list[str] = []
    for ch in unicodedata.normalize("NFD", text):
        if ch in _DROP:
            continue
        if ch in _TO_ACUTE:
            ch = _ACUTE
        if ch == _ACUTE and out and out[-1] == _ACUTE:
            continue  # two accents on one letter collapse into one
        out.append(ch)
    return nfc("".join(out))


def strip_accents(text: str) -> str:
    return nfc("".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c)))


def norm_answer(text: str) -> str:
    """NFC, trim, collapse spaces, lower-case with final sigma folded (SPEC §4.6)."""
    text = " ".join(nfc(text).split()).lower()
    return text.replace("ς", "σ")


def fold(text: str) -> str:
    """Accent-free, case-free key for matching: Καφές → καφεσ."""
    return strip_accents(norm_answer(text))


def strip_article(text: str) -> str:
    parts = text.split(" ", 1)
    if len(parts) == 2 and norm_answer(parts[0]) in {norm_answer(a) for a in ARTICLES}:
        return parts[1]
    return text


def words(text: str) -> list[str]:
    """Greek word tokens in a text, in order."""
    return _WORD_RE.findall(nfc(text))


def has_greek(text: str) -> bool:
    return re.search(GREEK_LETTER, text) is not None


def greek_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if re.match(GREEK_LETTER, c)) / len(letters)


def syllables(word: str) -> int:
    """A rough vowel-group count, enough to tell one-syllable words from longer ones."""
    base = fold(word)
    return len(re.findall(r"[αεηιουω]+", base))


def is_accented(word: str) -> bool:
    return _ACUTE in unicodedata.normalize("NFD", word)


# Word endings that occur in Greek (ς, ν, ρ and vowels), plus consonants that common loanwords end in.
_NATIVE_FINAL = _VOWELS | {"σ", "ν", "ρ"}
_LOAN_FINAL = {"ξ", "ψ", "φ", "κ", "τ", "π", "λ", "ζ", "μ", "γ", "β", "δ", "θ", "χ"}


def damage_flags(greek: str, meaning: str = "") -> list[str]:
    """Heuristic OCR-damage flags for a word-list entry (SPEC §10: latin_mixed, header_junk, truncated)."""
    flags: list[str] = []
    if (re.search(r"\b(PAGE|PAG ES|UNIT|WO)\b|\bLife\b", greek + " " + meaning)
            or re.search(r"[A-Z]{3,}\s+[A-Z0-9]{2,}", meaning)
            or re.search(r"\b(page|unit)\s*\d+", meaning, re.IGNORECASE)):
        flags.append("header_junk")
    if _LATIN_RE.search(greek):
        flags.append("latin_mixed")
    toks = words(greek)
    if not toks:
        flags.append("no_greek")
        return flags
    for tok in toks:
        if tok in ARTICLES or syllables(tok) < 2:
            continue
        if not is_accented(tok):
            # Every Greek word of two or more syllables carries an accent; a missing one means
            # a fragment (ηλεκτρ ονικό) or a cut-off word.
            flags.append("truncated")
            break
    else:
        last = fold(toks[-1])[-1:]
        if last and last not in _NATIVE_FINAL and len(toks[-1]) <= 3:
            flags.append("truncated")
    return flags
