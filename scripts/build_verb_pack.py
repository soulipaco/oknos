"""Build the open verb pack content/open/open-verbs-a1a2/ (run: uv run python scripts/build_verb_pack.py).

The sentences and the choice of verbs are original to this project. Every verb form is taken
from, and so checked against, the English Wiktionary's Greek conjugation tables (CC BY-SA 4.0,
via kaikki.org); the few cells Wiktionary does not tabulate are written out in OVERRIDES below.
The script needs the dictionary cache (see docs/IMPORTING.md); the pack it writes does not.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from greek_coach import greek  # noqa: E402
from greek_coach.importer import enrich  # noqa: E402

PACK = ROOT / "content" / "open" / "open-verbs-a1a2"
PERSONS = ["1sg", "2sg", "3sg", "1pl", "2pl", "3pl"]
SUBJECT = {"1sg": "(εγώ)", "2sg": "(εσύ)", "3sg": "ο Νίκος", "1pl": "(εμείς)", "2pl": "(εσείς)", "3pl": "τα παιδιά"}
SUBJECT_EN = {"1sg": "I", "2sg": "you", "3sg": "Nikos", "1pl": "we", "2pl": "you (pl.)", "3pl": "the children"}
PERSON_LABEL = {"1sg": "εγώ", "2sg": "εσύ", "3sg": "αυτός", "1pl": "εμείς", "2pl": "εσείς", "3pl": "αυτοί"}
ADVERB = {"present": ("Κάθε μέρα", "Every day"), "past": ("Χθες", "Yesterday"), "future": ("Αύριο", "Tomorrow")}

# lemma, English (base, 3sg, past), Turkish, complement (el, en), past tense used, irregular past?
# Ordered roughly by how early a learner needs them.
VERBS = [
    ("είμαι", ("be", "is", "was"), "olmak", ("στο σπίτι", "at home"), "imperfect", True),
    ("έχω", ("have", "has", "had"), "sahip olmak", ("πολλή δουλειά", "a lot of work"), "imperfect", True),
    ("πηγαίνω", ("go", "goes", "went"), "gitmek", ("στη λαϊκή", "to the street market"), "aorist", True),
    ("έρχομαι", ("come", "comes", "came"), "gelmek", ("στο γραφείο", "to the office"), "aorist", True),
    ("κάνω", ("do", "does", "did"), "yapmak", ("τα ψώνια", "the shopping"), "aorist", True),
    ("θέλω", ("want", "wants", "wanted"), "istemek", ("ένα καφέ", "a coffee"), "imperfect", False),
    ("τρώω", ("eat", "eats", "ate"), "yemek", ("σουβλάκι", "souvlaki"), "aorist", True),
    ("πίνω", ("drink", "drinks", "drank"), "içmek", ("καφέ", "coffee"), "aorist", True),
    ("μένω", ("stay", "stays", "stayed"), "kalmak", ("στο σπίτι", "at home"), "aorist", True),
    ("δουλεύω", ("work", "works", "worked"), "çalışmak", ("μέχρι αργά", "until late"), "aorist", False),
    ("μιλάω", ("speak", "speaks", "spoke"), "konuşmak", ("ελληνικά", "Greek"), "aorist", False),
    ("λέω", ("say", "says", "said"), "söylemek", ("την αλήθεια", "the truth"), "aorist", True),
    ("βλέπω", ("see", "sees", "saw"), "görmek", ("τον Γιώργο", "Giorgos"), "aorist", True),
    ("παίρνω", ("take", "takes", "took"), "almak", ("το λεωφορείο", "the bus"), "aorist", True),
    ("αγοράζω", ("buy", "buys", "bought"), "satın almak", ("ψωμί", "bread"), "aorist", False),
    ("πληρώνω", ("pay", "pays", "paid"), "ödemek", ("τον λογαριασμό", "the bill"), "aorist", False),
    ("ξέρω", ("know", "knows", "knew"), "bilmek", ("την απάντηση", "the answer"), "imperfect", True),
    ("δίνω", ("give", "gives", "gave"), "vermek", ("ψωμί στον σκύλο", "bread to the dog"), "aorist", True),
    ("βρίσκω", ("find", "finds", "found"), "bulmak", ("τα κλειδιά", "the keys"), "aorist", True),
    ("διαβάζω", ("read", "reads", "read"), "okumak", ("την εφημερίδα", "the newspaper"), "aorist", False),
    ("γράφω", ("write", "writes", "wrote"), "yazmak", ("ένα γράμμα", "a letter"), "aorist", False),
    ("ακούω", ("listen to", "listens to", "listened to"), "dinlemek", ("μουσική", "music"), "aorist", False),
    ("ρωτάω", ("ask", "asks", "asked"), "sormak", ("τον γιατρό", "the doctor"), "aorist", False),
    ("μπαίνω", ("get into", "gets into", "got into"), "girmek", ("στο μετρό", "the metro"), "aorist", True),
    ("βγαίνω", ("go out", "goes out", "went out"), "dışarı çıkmak", ("με φίλους", "with friends"), "aorist", True),
    ("φεύγω", ("leave", "leaves", "left"), "ayrılmak", ("νωρίς", "early"), "aorist", True),
    ("ξυπνάω", ("wake up", "wakes up", "woke up"), "uyanmak", ("στις επτά", "at seven"), "aorist", False),
    ("κοιμάμαι", ("sleep", "sleeps", "slept"), "uyumak", ("νωρίς", "early"), "aorist", True),
    ("καταλαβαίνω", ("understand", "understands", "understood"), "anlamak", ("τον δάσκαλο", "the teacher"), "aorist", True),
    ("μαθαίνω", ("learn", "learns", "learnt"), "öğrenmek", ("καινούριες λέξεις", "new words"), "aorist", True),
    ("περιμένω", ("wait for", "waits for", "waited for"), "beklemek", ("το λεωφορείο", "the bus"), "aorist", True),
    ("ανοίγω", ("open", "opens", "opened"), "açmak", ("το παράθυρο", "the window"), "aorist", False),
    ("κλείνω", ("close", "closes", "closed"), "kapatmak", ("την πόρτα", "the door"), "aorist", False),
    ("φέρνω", ("bring", "brings", "brought"), "getirmek", ("γλυκά", "sweets"), "aorist", True),
    ("στέλνω", ("send", "sends", "sent"), "göndermek", ("ένα μήνυμα", "a message"), "aorist", True),
    ("ανεβαίνω", ("go up", "goes up", "went up"), "yukarı çıkmak", ("στον τρίτο όροφο", "to the third floor"), "aorist", True),
    ("κατεβαίνω", ("go down", "goes down", "went down"), "aşağı inmek", ("στην παραλία", "to the beach"), "aorist", True),
    ("θυμάμαι", ("remember", "remembers", "remembered"), "hatırlamak", ("τη διεύθυνση", "the address"), "aorist", True),
    ("χρειάζομαι", ("need", "needs", "needed"), "ihtiyaç duymak", ("βοήθεια", "help"), "aorist", True),
    ("τηλεφωνώ", ("phone", "phones", "phoned"), "telefon etmek", ("στη μητέρα μου", "my mother"), "aorist", False),
    ("αρχίζω", ("start", "starts", "started"), "başlamak", ("τη δουλειά", "work"), "aorist", False),
    ("ταξιδεύω", ("travel", "travels", "travelled"), "seyahat etmek", ("στην Κρήτη", "to Crete"), "aorist", False),
    ("πουλάω", ("sell", "sells", "sold"), "satmak", ("φρούτα στη λαϊκή", "fruit at the street market"), "aorist", False),
    ("νιώθω", ("feel", "feels", "felt"), "hissetmek", ("καλά", "well"), "aorist", False),
]

# Cells Wiktionary's tables do not give in the form we need (είμαι has no aorist; it is listed
# without the usual tags). Standard forms, first one preferred.
OVERRIDES = {
    ("είμαι", "present"): {"1sg": ["είμαι"], "2sg": ["είσαι"], "3sg": ["είναι"], "1pl": ["είμαστε"],
                           "2pl": ["είστε", "είσαστε"], "3pl": ["είναι"]},
    ("είμαι", "imperfect"): {"1sg": ["ήμουν", "ήμουνα"], "2sg": ["ήσουν", "ήσουνα"], "3sg": ["ήταν", "ήτανε"],
                             "1pl": ["ήμασταν", "ήμαστε"], "2pl": ["ήσασταν", "ήσαστε"], "3pl": ["ήταν", "ήτανε"]},
    ("είμαι", "future"): {"1sg": ["θα είμαι"], "2sg": ["θα είσαι"], "3sg": ["θα είναι"], "1pl": ["θα είμαστε"],
                          "2pl": ["θα είστε", "θα είσαστε"], "3pl": ["θα είναι"]},
    ("έχω", "future"): {"1sg": ["θα έχω"], "2sg": ["θα έχεις"], "3sg": ["θα έχει"], "1pl": ["θα έχουμε"],
                        "2pl": ["θα έχετε"], "3pl": ["θα έχουν", "θα έχουνε"]},
    ("ξέρω", "future"): {"1sg": ["θα ξέρω"], "2sg": ["θα ξέρεις"], "3sg": ["θα ξέρει"], "1pl": ["θα ξέρουμε"],
                         "2pl": ["θα ξέρετε"], "3pl": ["θα ξέρουν", "θα ξέρουνε"]},
    ("θέλω", "future"): {"1sg": ["θα θέλω"], "2sg": ["θα θέλεις"], "3sg": ["θα θέλει"], "1pl": ["θα θέλουμε"],
                         "2pl": ["θα θέλετε"], "3pl": ["θα θέλουν", "θα θέλουνε"]},
}


ARCHAIC = ("θα ιδ", "ηύρ", "θα εύρ", "κάμ", "έκαμ", "σθ")
# Turkish translations of the sentences, by item id (written for this project; CC BY-SA 4.0 with the pack).
TR_SENTENCES = json.loads((Path(__file__).with_name("verb_pack_tr.json")).read_text(encoding="utf-8"))


def preferred(forms: set[str]) -> list[str]:
    """Order accepted variants so the standard modern form comes first (ήρθαν before ήλθανε,
    λένε before λεν, δίνουμε before δίνομε, έδωσα before έδωκα)."""
    def key(f):
        last = f.split(" ")[-1]
        # a spoken form without the augment (κάναν, ξέραν, φύγαν) goes after the one with it
        unaugmented = any(greek.fold(o).endswith(greek.fold(f)) and len(o) == len(f) + 1 for o in forms if o != f)
        return (
            # older or rare stems Wiktionary also lists: θα ιδεί, ηύρες, θα εύρει, έκαμε, θα χρειασθείς
            any(old in f for old in ARCHAIC),
            "λθ" in f or "δωκ" in f,
            unaugmented,
            last.endswith(("ουνε", "ανε", "ενε", "ονε")),
            last.endswith("ομε") and not last.endswith("ουμε"),
            not greek.is_accented(last) and greek.syllables(last) >= 1 and any(greek.is_accented(o.split(" ")[-1]) for o in forms),
            "-" in f,
            len(f),
            f,
        )
    return sorted(forms, key=key)


def cell(index: dict, lemma: str, tense: str, person: str) -> list[str]:
    if (lemma, tense) in OVERRIDES:
        return OVERRIDES[(lemma, tense)][person]
    forms = enrich.verb_forms(index, lemma, person, tense)
    if tense == "present" and lemma.endswith("άω"):
        # Wiktionary lists the -άω verbs' contracted 3sg (μιλά) only under the -ώ lemma.
        forms |= enrich.verb_forms(index, lemma[:-2] + "ώ", person, tense)
    return preferred(forms)


def english(verb_en, tense: str, person: str) -> str:
    base, third, past = verb_en
    if verb_en[0] == "be":
        return {"present": {"1sg": "am", "3sg": "is"}.get(person, "are"),
                "past": "was" if person in ("1sg", "3sg") else "were", "future": "will be"}[tense]
    if tense == "present":
        return third if person == "3sg" else base
    if tense == "past":
        return past
    return f"will {base}"


def main() -> int:
    index = enrich.load_index()
    if index is None:
        print("The dictionary cache is missing; see docs/IMPORTING.md (enrichment).")
        return 1
    items, problems = [], []
    chunk = 6
    for start in range(0, len(VERBS), chunk):
        group = VERBS[start:start + chunk]
        for tense in ("present", "past", "future"):
            for offset, (lemma, verb_en, verb_tr, (comp, comp_en), past_kind, irregular) in enumerate(group):
                i = start + offset
                real_tense = past_kind if tense == "past" else tense
                persons = [PERSONS[(i + {"present": 0, "past": 1, "future": 2}[tense] + k) % 6] for k in (0, 3)]
                for person in persons:
                    forms = cell(index, lemma, real_tense, person)
                    if not forms:
                        problems.append(f"{lemma} {real_tense} {person}: Wiktionary has no form; item skipped")
                        continue
                    others = []
                    for p2 in PERSONS:
                        if p2 != person:
                            alt = cell(index, lemma, real_tense, p2)
                            if alt and alt[0] not in forms and alt[0] not in others:
                                others.append(alt[0])
                    for t2 in ("present", past_kind, "future"):
                        if t2 != real_tense:
                            alt = cell(index, lemma, t2, person)
                            if alt and alt[0] not in forms and alt[0] not in others:
                                others.insert(0, alt[0])
                    options = [forms[0]] + others[:3]
                    adv, adv_en = ADVERB[tense]
                    subject = SUBJECT[person]
                    text = f"{adv} {subject} {{1}} {comp}."
                    en = f"{adv_en} {SUBJECT_EN[person]} {english(verb_en, tense, person)} {comp_en}."
                    tags = [f"verb.{real_tense}"]
                    if irregular and real_tense in ("aorist", "imperfect", "future"):
                        tags.append(f"verb.{real_tense}.irregular")
                    tags.append("verb.deponent" if lemma.endswith("μαι") else "verb.class_b" if lemma.endswith(("άω", "ώ")) else "verb.class_a")
                    slug = greek.fold(lemma)
                    ascii_slug = "".join(enrich_translit(c) for c in slug)
                    items.append({
                        "id": f"f-{ascii_slug}-{real_tense}-{person}",
                        "type": "form", "skill": "grammar", "level": "A1" if i < 24 else "A2",
                        "topics": ["verbs"],
                        "text": text,
                        "cue": {"lemma": lemma, "person": person, "tense": real_tense},
                        "answer": {"1": forms},
                        "options": {"1": options},
                        "grammar": tags,
                        "translation": {"en": en, "tr": TR_SENTENCES.get(f"f-{ascii_slug}-{real_tense}-{person}")},
                        "explain": {"en": f"{lemma} ({verb_en[0]}), {real_tense}, {PERSON_LABEL[person]}: {forms[0]}",
                                    "tr": f"{lemma} ({verb_tr}), {TENSE_TR[real_tense]}, {PERSON_LABEL[person]}: {forms[0]}"},
                    })
    (PACK / "items").mkdir(parents=True, exist_ok=True)
    for old in (PACK / "items").glob("*.json"):
        old.unlink()
    per_file = 60
    for n in range(0, len(items), per_file):
        (PACK / "items" / f"verbs-{n // per_file + 1:02d}.json").write_text(
            json.dumps(items[n:n + per_file], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    manifest = {
        "id": "open-verbs-a1a2",
        "title": {"en": "Everyday verbs", "tr": "Günlük fiiller", "el": "Καθημερινά ρήματα"},
        "version": 1,
        "levels": ["A1", "A2"],
        "visibility": "open",
        "licence": "CC-BY-SA-4.0",
        "source": "Original sentences written for Greek Coach. Verb forms checked against the English "
                  "Wiktionary's Greek conjugation tables (CC BY-SA 4.0, https://en.wiktionary.org, via kaikki.org).",
        "exam_blueprints": ["a2ltr", "b1-keg"],
    }
    (PACK / "pack.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(items)} form items for {len(VERBS)} verbs written to {PACK}")
    for p in problems:
        print("  -", p)
    return 0


TENSE_TR = {"present": "şimdiki/geniş zaman", "aorist": "geçmiş zaman (aorist)", "imperfect": "geçmiş zaman (sürekli)",
            "future": "gelecek zaman"}
_TR = dict(zip("αβγδεζηθικλμνξοπρσςτυφχψω", ["a", "v", "g", "d", "e", "z", "i", "th", "i", "k", "l", "m", "n", "x", "o", "p", "r", "s", "s", "t", "y", "f", "ch", "ps", "o"]))


def enrich_translit(c: str) -> str:
    return _TR.get(c, c if c.isascii() and c.isalnum() else "-")


if __name__ == "__main__":
    raise SystemExit(main())
