# Specification

Status: **agreed (2026-11-15).** The maintainer accepted the exam strategy in §1.4. Where this file and `docs/DESIGN.md` disagree, this file wins.

Exam facts were checked against official sources on **2026-11-15**. Each claim below is marked as **verified** (seen in an official source on that date) or **unverified** (taken from a secondary source or from memory, and still to be checked). Phase 5 checks all of them again.

---

## 1. The exam

### 1.1 What the law actually requires

Long-term resident status is covered by article 160 of the Migration Code (ν. 5038/2023), as amended by art. 37 of ν. 5275/2026. Paragraph 1 lists the ways to prove knowledge of Greek and of Greek history and culture. **Any one of them is enough.** The ones that matter for an adult who has lived in Greece for some years without Greek schooling are:

| Route | What it is | Level | Verified |
|---|---|---|---|
| **(ε) Special certificate** | "Ειδικό πιστοποιητικό επαρκούς γνώσης της ελληνικής γλώσσας και στοιχείων ελληνικής ιστορίας και πολιτισμού". An exam run by the Ministry of Education's General Secretariat for vocational education and lifelong learning, together with the Centre for the Greek Language. | **A2**, plus history and culture | yes |
| **(δ) Ελληνομάθεια B1** | Certificate of Attainment in Greek, level B1 or higher, from the Centre for the Greek Language | B1 | yes |
| **(στ) ΠΕΓΠ** | Certificate of Sufficient Knowledge for Naturalisation, run by the Ministry of the Interior | about B1 for language, plus civics, history, geography and culture | yes for the route, unverified for the level |
| (η) 12 years' residence | Twelve consecutive years of legal residence before applying | none | yes, but it does not apply yet after 8 years |

Paragraph 2: someone holding only an A1 or A2 Ελληνομάθεια certificate also has to pass the history and culture part.

**The design's premise was wrong.** `DESIGN.md` assumed a B1 exam. For long-term residence the lowest route is **A2 plus a history and culture test (route ε)**. B1 is one option, not a requirement.

Sources:
- [ν. 5038/2023 art. 160 (current text)](https://www.taxheaven.gr/law/5038/2023/arthro/160) and [ν. 5275/2026 art. 37 (the amendment)](https://www.taxheaven.gr/law/5275/2026/arthro/37). These are a legal database, not the Government Gazette; the ΦΕΚ text should be checked once.
- [Decentralised Administration of Attica, document list](https://apdattikis.gov.gr/en/documents/). Its section 4.1.1 lists "A2+" from the General Secretariat or B1 Ελληνομάθεια. It still cites the old ν. 4251/2014, so treat it as confirming the practice, not as current law.

> Before booking any exam, confirm with your lawyer or the permit office that your current permit type leads to long-term status through art. 160. That is a legal question about your file, and this app cannot answer it.

### 1.2 The three candidate exams compared

| | **A2 + history (route ε)** — "A2-LTR" in this spec | **Ελληνομάθεια B1** | **ΠΕΓΠ** |
|---|---|---|---|
| Who runs it | General Secretariat (ΓΓΕΕΚΔΒΜ), Ministry of Education, with the Centre for the Greek Language | Centre for the Greek Language (ΚΕΓ), Thessaloniki | Ministry of the Interior |
| What it is for | Long-term residence only | Long-term residence, and widely accepted elsewhere (jobs, universities) | Naturalisation. It also satisfies long-term residence. |
| Sections | 5 units of 20 points each: history & culture, listening, reading, writing, speaking | 4 skills of 25 points each: reading, listening, writing, speaking | Knowledge questions (geography, history, culture, institutions), reading, writing, listening, speaking |
| Timings | History 25 min, listening 25 min, reading 30 min, writing 40 min, then a separate speaking test | Reading 40 min, listening 25 min, writing 55 min (2 h written in total), speaking about 12 min per pair | About 150 min written. Listening and speaking about 15 min each (unverified). |
| Pass mark | At least 50/100 **and** at least 50% in 4 of the 5 units, so one weak unit is survivable. History-only candidates: 10/20. | **At least 60% in each of the four skills.** Failing one skill fails the whole exam. (Verified in the [ΚΕΓ exam guide, 2022](https://www.greek-language.gr/certification/sites/greeklanguage.gr.certification/files/odigos_ell_2022.pdf).) | At least 20 on knowledge, at least 40 on language, at least 70 overall |
| Teaching hours, ΚΕΓ estimate | A2 needs about 120–180 h | B1 needs about 180–250 h | — |
| How often | Usually twice a year: May 2026 took place, earlier years were May/Oct or May/Nov. **No 2027 date announced yet.** | Once a year in May, plus an October session (in Greece only) for B1. **May 2027: registration 1 Feb – 14 Mar 2027, B1 written exam Thu 13 May 2027.** | Twice a year, about May and November. Procurement for Nov 2026 and Apr 2027 is published. |
| Fee | €50, or €20 for history only (2024 call). Places are capped (2,300 in 2024) and allocated by order of application. | Unverified | A fee applies; the amount is unverified |
| Past papers | Official papers, answer keys and audio for 2010–2026, plus the history syllabus | Official sample papers on the ΚΕΓ site | Official published question bank (the language part alone is 400+ pages) |

Verified: the A2-LTR structure and points, from the [2026A written paper](https://www.gsvetlly.minedu.gov.gr/ellinomatheia) and the exam page. The B1 structure, from the [ΚΕΓ B1 structure table](https://www.greek-language.gr/certification/node/119.html). The [May 2027 registration dates](https://www.greek-language.gr/certification/news/show.html?id=94). The ΠΕΓΠ sections and pass marks, from [mitos.gov.gr](https://mitos.gov.gr/index.php/%CE%94%CE%94:%CE%95%CE%BE%CE%B5%CF%84%CE%AC%CF%83%CE%B5%CE%B9%CF%82_%CE%B1%CF%80%CF%8C%CE%BA%CF%84%CE%B7%CF%83%CE%B7%CF%82_%CE%A0%CE%B9%CF%83%CF%84%CE%BF%CF%80%CE%BF%CE%B9%CE%B7%CF%84%CE%B9%CE%BA%CE%BF%CF%8D_%CE%95%CF%80%CE%AC%CF%81%CE%BA%CE%B5%CE%B9%CE%B1%CF%82_%CE%93%CE%BD%CF%8E%CF%83%CE%B5%CF%89%CE%BD_%CE%B3%CE%B9%CE%B1_%CE%A0%CE%BF%CE%BB%CE%B9%CF%84%CE%BF%CE%B3%CF%81%CE%AC%CF%86%CE%B7%CF%83%CE%B7).

Unverified, still to check:
- The B1 date of 13 May 2027 comes from a Ministry of Foreign Affairs copy of the ΚΕΓ schedule.
- The A2-LTR fee and cap come from a 2024 news report of the official call ([alfavita](https://www.alfavita.gr/ekpaideysi/446349_pote-tha-diexahthoyn-oi-exetaseis-pistopoiisis-ellinikis-glossas-gia-polites)).
- A2-LTR speaking parts and timing. Phase 5 reads them from the 2026A oral paper.

### 1.3 The A2-LTR exam in detail (from the 2026A paper)

| Unit | Points | Time | Part 1 | Part 2 | Part 3 |
|---|---|---|---|---|---|
| History & culture | 20 | 25 min | Match sentence halves, 10 × 0.5 (5 pts) | Multiple choice, 10 × 1 (10 pts) | Put people or events in their era, 10 × 0.5 (5 pts) |
| Listening | 20 | 25 min | Voice message: fill in the missing information from options, with distractors (5 pts) | Dialogue heard twice: multiple choice (10 pts) | Six short dialogues: pick the place where each happens, with distractors (5 pts) |
| Reading | 20 | 30 min | Gapped text with a word bank and distractors (6 pts) | Ten public notices (pharmacy hours, offices…): 14 true/false statements (14 pts) | — |
| Writing | 20 | 40 min | Semi-formal e-mail, 40–60 words, with required content points (10 pts) | Friendly e-mail or invitation, 40–60 words (10 pts) | — |
| Speaking | 20 | separate | Recorded test with examiners, including a short role-play between candidates (details unverified) | | |

Two things about this exam shape the app:

- **About 60 of the 100 points are selection tasks** (matching, multiple choice, true/false, word bank, categorising). The app can mark these deterministically, so most daily practice needs no agent.
- **History & culture is 20 points of memorisable facts**, written in A2-level Greek, with an [official 17-page syllabus text](https://www.gsvetlly.minedu.gov.gr/publications/ellinomatheia/ylh_ellinikis_istorias_politismou.pdf). It is the most predictable unit and the cheapest one to secure.

The exam rubrics are in Greek ("Συμπληρώστε τα κενά", "ΣΩΣΤΟ / ΛΑΘΟΣ", "όπως στο παράδειγμα"). The app uses the exam's own rubric wording in Greek, with a translation the learner can tap, so reading the instructions is not a surprise on the day.

### 1.4 Exam strategy: track two, decide from data (accepted 2026-11-15)

The maintainer leans towards **Ελληνομάθεια B1**. B1 sessions are on a fixed, announced calendar, and A2-LTR felt rare. He also wants exam dates watched automatically.

The facts that bear on the choice:
- **Availability favours B1 in practice.** The maintainer's experience is that A2-LTR sessions open rarely, and the record agrees: dates are announced late, places are capped, and there is no 2027 date yet. B1 has a fixed national calendar (May, plus October in Greece) and is offered at many accredited exam centres (universities, language schools), so it is easier to get a seat.
  - Only the Centre for the Greek Language's certificate counts under the law (art. 160 §1δ cites π.δ. 363/1998). Other institutes act as exam centres for that same exam; they do not issue their own certificates.
- **B1's pass rule is harsher.** It needs at least 60% in *every* skill. A2-LTR needs 50 overall and lets one unit be weak.
- **The starting point matters most.** The learner currently reads Greek letters slowly and plans 20 minutes a day. That is about 2.3 hours a week, or 10 a month. ΚΕΓ's rough estimate is 120–180 teaching hours for A2 and 180–250 for B1. On the app alone, that puts A2 about 12–18 months away and B1 about 18–24 months away. An evening course at 6 h/week roughly triples the pace. That would make A2 by mid-2027 and B1 by late 2027 plausible.
- **May 2027 B1 is not realistic from here without a course.** The app will say so in numbers rather than let the learner find out at the exam.

**Decision: version 1 ships both blueprints, `b1-keg` and `a2ltr`.** The learning path is the same for the first months, since A2 is on the way to B1. The readiness screen shows the learner's standing against both pass rules. The plan picks the first realistic session of either and re-plans as dates are announced. The learner decides what to book.

ΠΕΓΠ (citizenship, which also covers long-term residence) is not built now. It is a third blueprint if citizenship becomes the goal.

An exam is a **blueprint file** (`exams/<id>.json`, see §4.5). Adding one needs no schema change.

### 1.5 How exam tasks map to exercise types

| Exercise type | A2-LTR tasks | Also used by B1 / ΠΕΓΠ |
|---|---|---|
| `match` | History p1 | B1 reading 1 |
| `mcq` | History p2, listening p2 | most papers |
| `categorise` | History p3 (eras), listening p3 (places) | — |
| `gap_bank` | Reading p1, listening p1 | B1 reading 4 |
| `true_false` | Reading p2 | B1 reading 3 |
| `write` | Writing p1, p2 | B1 writing, ΠΕΓΠ short text |
| `speak` | Speaking | all |
| `vocab` | (underlies everything) | |
| `form` | (grammar: verb and noun forms) | (underlies B1 writing) |
| `table_fill` | — | B1 reading 2, listening 1–2 (notes and comparison tables) |

Any selection type can have an audio stimulus, which makes it a listening task. Every item carries an `exam_task` tag (e.g. `a2ltr.reading.notices_tf`), so readiness and coverage can be computed per unit.

---

## 2. The learner, and the motivation problem

What the maintainer has told us so far (2026-11-15):

- **Goal:** the long-term residence exam. The date is flexible. Leans towards B1; see §1.4.
- **Level now:** reads Greek letters slowly. Effectively a beginner with 8 years of passive exposure.
- **Time:** about 20 minutes on a normal weekday, split between the app and the agent.
- **Why earlier attempts stopped:** boring material.
- **What he wants to read about:** his own needs ("I don't know the verbs"), real-life things he runs into, and news and daily life.
- **AI:** wants to *use* the subscription he pays for. That means a chat tutor in Greek, fresh content every day, feedback on speaking, and agent work that runs on a schedule.
- **Devices:** laptop and phone.
- **Course:** wants the University of Athens programme ([program of courses](https://en.greekcourses.uoa.gr/program_of_courses)). Thought the next enrolment was around May, so planned to cover A1–A2 alone until then and treat the course as extra.
  - **Correction from the research:** registration is still open for the **6-month course, 1 Dec 2026 – 14 May 2027**, at 8 h/week or 15 h/week. A **3-month course** runs **22 Feb – 14 May 2027** at 15 h/week. The online A1/A2 courses also take a second-semester intake in March 2027.
  - The 8-month and citizenship courses are closed.
  - A placement test is held before each course, a teaching hour is 45 minutes, and the minimum class size is 15. Fees and textbook are not listed on the page.
  - **The maintainer's answer:** he will enrol in the first course that fits, but **it must be after 17:00**. None of the currently open courses fits on dates or hours. So the course page is watched (§6, `watch`), and the class side of `capture` is built but not on the critical path.
- **Interface language:** Turkish and English, both required.
- **Tools:** happy to install free tools. Nothing paid beyond the existing Claude Code / Codex subscription.
- **Harnesses:** Claude Code first, Codex second. Copilot is not a goal.

These are recorded here because they shape the product. From now on, personal details go into the learner's profile (`learner/profile.json`), not into this tracked file. Phase 6 trims this section before the repo goes public.

### What the answers change

- **Verbs are a first-class track.** There is a `form` exercise type (§4.4) and a daily verb segment. Greek verb forms are the learner's own stated gap and the backbone of A2 and B1 grammar.
- **Real life comes in through `capture`.** Anything met in daily life can be dropped in `learner/inbox/` or sent to the tutor from the phone: a photo of a notice, a letter, a menu, or "how do I say X to my landlord?". The coach turns it into vocabulary and a reading task the same day.
  - These documents often hold personal data (names, ΑΦΜ, addresses). They stay in `learner/`.
  - Personal details are replaced with invented ones before the material becomes an exercise.
- **The agent is used much more, but the app still never depends on it.** Four additions:
  1. A **tutor** skill for live chat practice.
  2. A **scheduled daily prep** that writes tomorrow's content.
  3. **Speaking feedback** through local transcription.
  4. A **watch** that tracks exam and course dates.

  If any of them stops running, the daily app session still works from the content already prepared.
- **Phone:**
  - The tutor works from the phone through the agent's own mobile access, for example Claude Code Remote Control into the session on the laptop.
  - The web app gets an opt-in "open on my home Wi-Fi" switch (§3).

### Motivation decisions already made (from the design, sharpened)

- **The first win comes in the first five minutes.** The open starter pack is *"Words you already know"*: Greek–Turkish shared vocabulary (καφές/kahve, ταψί/tepsi, φλιτζάνι/fincan, μπακάλης/bakkal, χαλί/halı…). It is original content, specific to Turkish speakers, and makes Greek feel less foreign on day one. English speakers get the Greek–English equivalent (internationalisms such as τηλέφωνο, ταξί).
- **Exam content and real-life content are the same content.** A2-LTR reading part 2 is literally about pharmacy hours and office notices, and B1 writing asks for complaints and requests. Practising them *is* practising Greek bureaucracy. Generic textbook sentences are the last resort.
- **Honest numbers, no decorative gamification.** No streaks to break, no XP, no badges. The home screen shows real counts, a 28-day consistency grid, and estimated points per exam unit, with the evidence behind each.
- **After time away, the next session gets smaller, not bigger.** The overdue review backlog is capped.

---

## 3. First version: scope

"Version 1" is what exists after phases 2–5.

**In:**
- Local web app on `127.0.0.1`, one learner per install.
- UI in **English and Turkish** from day one, switchable on the home screen. Exercise rubrics are in Greek, with a tap-to-translate.
- Exercise types: `vocab`, `form`, `mcq`, `true_false`, `match`, `gap_bank`, `categorise`, `table_fill`, `write`, `speak`, with optional audio stimuli.
- Spaced repetition, a daily session sized to a time budget, lookup on tap, and flagging an item as wrong.
- Greek audio: browser speech for words and sentences, and audio files pre-generated by the coach for listening passages (§9).
- An on-screen Greek keyboard for the few typed answers. Answer checking ignores accents and reports missing ones.
- Coach skills: setup, check-in, capture (class and real life), tutor, daily prep, watch, writing and speaking feedback, rebuilding imported material, import, plan, mock exam (§6).
- Speaking: the learner records themselves in the browser and compares with a model answer. Recordings stay in `learner/recordings/`. The coach transcribes them locally with faster-whisper (an optional install, with the learner's OK for the model download) and gives feedback.
- Scheduled agent runs (daily prep, weekly watch), set up only with the learner's explicit OK, through the operating system's scheduler or the harness's own scheduled tasks.
- An opt-in **home Wi-Fi mode**, so a phone on the same network can open the app.
  - Off by default.
  - When on, the app binds to the LAN address and asks for a short PIN shown on the laptop.
- The `b1-keg` and `a2ltr` blueprints, readiness against each pass rule, timed mock exams, and a plan to a target session.
- Importer for the earlier project (§10) and a short guide for other people's material.

**Out, explicitly:**
- Live speech recognition inside the app, and pronunciation scoring. Speaking feedback is after the fact, from the coach.
- The ΠΕΓΠ blueprint.
- Any LLM call from the app; any account, sync or telemetry; cloud TTS, except the opt-in edge-tts fallback in §9.
- Access from outside the home network: no tunnels, no port forwarding.
- Picture-based tasks (describing a photo), apart from a speaking card with an image.
- Content editing inside the app. Content is written by the coach or the importer.
- Multiple learners in one install, and Copilot-specific instructions.

---

## 4. Content packs

### 4.1 Layout

```
content/open/<pack-id>/        tracked: original or openly licensed
content/private/<pack-id>/     gitignored: textbook imports, handouts, official papers
learner/generated/<pack-id>/   gitignored: written by the coach for this learner

<pack-id>/
  pack.json                    manifest
  items/*.json                 each file is a JSON array of items; split however is convenient
  audio/*.mp3|*.wav|*.ogg      optional, referenced by items
  raw/*.json                   optional, private packs only: source material that is not shown as exercises
```

The app loads every pack in all three roots at start-up and on a "reload content" request from the coach. An invalid item is skipped and logged, never fatal. `uv run greek-coach validate <path>` checks a pack and prints problems in plain language; the coach runs it after every write.

### 4.2 Manifest (`pack.json`)

```json
{
  "id": "open-shared-words-tr",
  "title": {"en": "Words you already know", "tr": "Zaten bildiğin kelimeler"},
  "version": 1,
  "levels": ["A1"],
  "visibility": "open",
  "licence": "CC-BY-SA-4.0",
  "source": "Original, written for Greek Coach",
  "exam_blueprints": ["a2ltr"],
  "for_ui_lang": ["tr"]
}
```

`visibility` is `open`, `private` or `generated`. A pack in `content/open/` must have `visibility: "open"` and an open `licence`; a test enforces this. `for_ui_lang` is optional (by default a pack is for everyone).

### 4.3 Item fields (all types)

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Unique within the pack. The app's global key is `<pack-id>/<id>`. |
| `type` | yes | One of the types in §4.4. |
| `skill` | yes | `vocab`, `grammar`, `history`, `listening`, `reading`, `writing`, `speaking` |
| `exam_task` | no | Blueprint task id, e.g. `a2ltr.history.mcq`. Untagged items still count as general practice. |
| `level` | yes | `A1`, `A2`, `B1` |
| `topics` | no | Free tags: `pharmacy`, `office`, `neighbourhood`, `work`… The coach uses them to match interests. |
| `rubric` | no | The Greek instruction line, with `en` and `tr` translations. |
| `stimulus` | no | `{ "text": "...", "audio": "audio/x.mp3", "tts": "...", "plays": 2 }`. `tts` means "speak this with the browser voice"; `audio` takes precedence. |
| `explain` | no | Short explanation after answering: `{ "en": "...", "tr": "..." }` |
| `source` | yes for private packs | Provenance, e.g. `{ "doc": "...", "page": 41 }` |
| `status` | no | `ok` (default) or `needs_review`. Items marked `needs_review` are not served. |

Greek text is NFC-normalised UTF-8 and monotonic. Final sigma is `ς`. Translations are optional per language. A missing `tr` falls back to `en`, then to nothing.

### 4.4 Types, with one worked example each

**`vocab`**: one word or phrase. The app derives the card directions itself: Greek→meaning (choice), meaning→Greek (choice, later typed), audio→meaning.

```json
{"id": "v-farmakeio", "type": "vocab", "skill": "vocab", "level": "A1", "topics": ["pharmacy"],
 "el": "το φαρμακείο", "lemma": "φαρμακείο", "pos": "noun", "gender": "n",
 "en": "pharmacy", "tr": "eczane",
 "example": {"el": "Το φαρμακείο είναι κλειστό την Κυριακή.", "en": "The pharmacy is closed on Sunday.", "tr": "Eczane pazar günü kapalı."}}
```

**`form`**: produce one word form in context, such as a verb in a person and tense, or a noun in a case. It is typed (with the on-screen keyboard) or chosen from `options` when present. `grammar` describes what is being trained, so errors can be grouped.

```json
{"id": "f-pigaino-aor-1sg", "type": "form", "skill": "grammar", "level": "A2", "topics": ["market"],
 "text": "Χθες {1} στη λαϊκή και αγόρασα ντομάτες.",
 "cue": {"lemma": "πηγαίνω", "person": "1sg", "tense": "aorist"},
 "answer": {"1": ["πήγα"]},
 "grammar": ["verb.aorist.irregular"],
 "explain": {"en": "πηγαίνω has an irregular past: πήγα, πήγες, πήγε…", "tr": "πηγαίνω fiilinin geçmiş zamanı düzensizdir: πήγα, πήγες, πήγε…"}}
```

`answer` lists every accepted form, so variants such as επτά/εφτά both count.

**`mcq`**: one question, 3–4 options, exactly one correct.

```json
{"id": "h-parthenon", "type": "mcq", "skill": "history", "exam_task": "a2ltr.history.mcq", "level": "A2",
 "prompt": {"el": "Πού είναι ο Παρθενώνας;"},
 "options": ["Στη Θεσσαλονίκη.", "Στην Ακρόπολη της Αθήνας.", "Στους Δελφούς."],
 "answer": 1,
 "explain": {"en": "The Parthenon is the temple on the Acropolis of Athens.", "tr": "Parthenon, Atina Akropolisi'ndeki tapınaktır."}}
```

**`true_false`**: one text, several statements.

```json
{"id": "r-kep-notice", "type": "true_false", "skill": "reading", "exam_task": "a2ltr.reading.notices_tf", "level": "A2", "topics": ["office"],
 "rubric": {"el": "Σημειώστε ΣΩΣΤΟ ή ΛΑΘΟΣ.", "en": "Mark TRUE or FALSE.", "tr": "DOĞRU veya YANLIŞ işaretleyin."},
 "stimulus": {"text": "ΚΕΠ – Ωράριο λειτουργίας: Δευτέρα έως Παρασκευή, 8:00–15:00. Για ραντεβού καλέστε στο 1500."},
 "statements": [
   {"el": "Το ΚΕΠ είναι ανοιχτό το Σάββατο.", "answer": false},
   {"el": "Για ραντεβού τηλεφωνείτε στο 1500.", "answer": true}
 ]}
```

**`match`**: left items, right items (right may include distractors). The answer maps left index to right index.

```json
{"id": "h-match-01", "type": "match", "skill": "history", "exam_task": "a2ltr.history.match", "level": "A2",
 "left":  ["Ο Σωκράτης ήταν", "Η Ελληνική Επανάσταση άρχισε", "Ο Παρθενώνας είναι"],
 "right": ["το 1821.", "φιλόσοφος.", "ναός στην Ακρόπολη.", "βασιλιάς της Σπάρτης."],
 "answer": [1, 0, 2]}
```

**`gap_bank`**: text with numbered gaps `{1}`, `{2}`…, a word bank that includes distractors, and an answer per gap.

```json
{"id": "r-pharmacy-gaps", "type": "gap_bank", "skill": "reading", "exam_task": "a2ltr.reading.gapbank", "level": "A2", "topics": ["pharmacy"],
 "text": "Το φαρμακείο είναι {1} από τις 8:00 ως τις 14:00. Το Σάββατο δεν δουλεύουμε, είναι {2}.",
 "bank": ["ανοιχτό", "κλειστό", "ακριβό", "μακριά"],
 "answer": {"1": "ανοιχτό", "2": "κλειστό"}}
```

**`categorise`**: put each item into one of the categories (historical eras, places heard in a dialogue).

```json
{"id": "h-eras-01", "type": "categorise", "skill": "history", "exam_task": "a2ltr.history.era", "level": "A2",
 "categories": ["Αρχαία Ελλάδα", "Βυζάντιο", "Νεότερη Ελλάδα"],
 "items": ["Περικλής", "Ιουστινιανός", "Ελευθέριος Βενιζέλος"],
 "answer": [0, 1, 2]}
```

**`table_fill`**: complete cells of a table from a text or recording (B1 reading 2, listening 1–2). Each cell answer is a short word or number, checked like `form`.

```json
{"id": "r-gyms-compare", "type": "table_fill", "skill": "reading", "exam_task": "b1keg.reading.compare", "level": "B1", "topics": ["neighbourhood"],
 "stimulus": {"text": "Το γυμναστήριο «Άλφα» ανοίγει στις 7:00 και κοστίζει 30 ευρώ τον μήνα. Το «Βήτα» ανοίγει στις 9:00, κοστίζει 25 ευρώ και έχει πισίνα."},
 "columns": ["Άλφα", "Βήτα"],
 "rows": ["Ανοίγει στις", "Τιμή τον μήνα (€)", "Πισίνα (ναι/όχι)"],
 "answer": [["7:00", "9:00"], ["30", "25"], ["όχι", "ναι"]]}
```

**Listening** is any selection type with an audio stimulus:

```json
{"id": "l-nikos-time", "type": "mcq", "skill": "listening", "exam_task": "a2ltr.listening.mcq", "level": "A2",
 "stimulus": {"tts": "Γεια σου, Μαρία. Είμαι ο Νίκος. Θα έρθω στις έξι, όχι στις πέντε.", "plays": 2},
 "prompt": {"el": "Τι ώρα θα έρθει ο Νίκος;"},
 "options": ["Στις πέντε.", "Στις έξι.", "Στις επτά."],
 "answer": 1}
```

**`write`**: a prompt in exam format. The app saves the text and the coach marks it later.

```json
{"id": "w-lift-broken", "type": "write", "skill": "writing", "exam_task": "a2ltr.writing.email_formal", "level": "A2", "topics": ["neighbourhood"],
 "prompt": {"el": "Το ασανσέρ στην πολυκατοικία σας δεν λειτουργεί εδώ και μία εβδομάδα. Γράψτε ένα e-mail στον διαχειριστή. Πείτε ποιο είναι το πρόβλημα και τι θέλετε να γίνει. Μην υπογράψετε με το όνομά σας.",
            "en": "The lift in your building has not worked for a week. Write an e-mail to the building manager...",
            "tr": "Apartmanınızdaki asansör bir haftadır çalışmıyor. Yöneticiye bir e-posta yazın..."},
 "words": [40, 60],
 "must_include": ["the problem", "since when", "what you want done"]}
```

**`speak`**: a speaking card. The learner records an answer, then plays it back next to the model answer. The app records "done"; there is no score.

```json
{"id": "s-neighbourhood", "type": "speak", "skill": "speaking", "exam_task": "a2ltr.speaking.monologue", "level": "A2",
 "prompt": {"el": "Μιλήστε για τη γειτονιά σας: πού μένετε, τι σας αρέσει και τι δεν σας αρέσει."},
 "seconds": 60,
 "model": {"el": "Μένω σε μια γειτονιά κοντά στο κέντρο. Μου αρέσει γιατί έχει μια ωραία πλατεία και πολλά μαγαζιά. Δεν μου αρέσει η κίνηση και ότι δεν βρίσκω εύκολα θέση για το αυτοκίνητο."},
 "useful": ["Μένω σε…", "Μου αρέσει γιατί…", "Δεν μου αρέσει…"]}
```

### 4.5 Exam blueprints (`exams/<id>.json`, tracked)

These are facts about a public exam: units, points, times, task ids with type and point value, pass rule, and source links with the date they were checked. Each blueprint also has a `watch` list: the official pages where dates and registration windows are announced, which the `watch` skill checks. Phase 5 writes `exams/a2ltr.json` from §1.3 and `exams/b1-keg.json` from the ΚΕΓ structure table and exam guide. Official papers are never copied into the repo; the coach can download them into `content/private/official-a2ltr/` for the learner, after asking.

### 4.6 Answer checking (deterministic, in the app)

- Selection types: exact index or value match. `true_false`, `match`, `gap_bank`, `categorise` and `table_fill` score per sub-answer. An item's score is the fraction correct; it counts as "correct" for scheduling only if everything is right.
- Typed answers (vocab recall, `form`, `table_fill` cells): NFC, trim, collapse spaces, lower-case including final-sigma folding. If the answer matches only when accents are ignored, it is **correct, with a note "watch the accent: φαρμακείο"**. A leading article is optional unless the card asks for it.
- `write` and `speak` are never auto-scored.

---

## 5. Learner data (`learner/`, gitignored)

```
learner/
  greek-coach.db          SQLite: everything the app records
  profile.json            goal, exam, budget, interests, UI language (the coach writes it; the app reads it and can change ui_lang/minutes)
  coach/
    notes.md              the coach's running notes to its future self
    message.json          the short note shown on the home screen {date, en, tr}
    plan.json             week-by-week plan (phase 5)
    watch.json            exam and course dates found by the watch skill {checked_at, entries:[{what, date, registration, source_url, changed}]}
    tutor-log/<date>.md   short summary of each tutor chat: new words, recurring errors
    runs.log              one line per scheduled run (time, skill, ok/failed), so a silent failure shows up
  feedback/<submission-id>.json   writing or speaking feedback the app shows next to the original
  generated/<pack-id>/    coach-written packs
  inbox/                  learner drops handouts, photos, letters, notes; anything to "capture"
  recordings/<id>.webm    speaking recordings
  backups/                zip copies made by the backup command
```

Copying the folder to another machine must keep working, so the database stores only paths relative to `learner/`.

### 5.1 Database tables

| Table | Columns (main) | Written by |
|---|---|---|
| `meta` | key, value: `schema_version` and similar | app |
| `items` | item_key (pack/id) PK, pack_id, type, skill, exam_task, level, content_hash, first_seen_at, retired_at | app, when loading packs |
| `sessions` | id, started_at, ended_at, kind (`daily`, `extra`, `mock`, `practice`), planned_minutes, items_planned, items_done | app |
| `attempts` | id, session_id, item_key, ts, response_json, score (0–1), correct (bool, null for write/speak), latency_ms, lookups, audio_plays, accent_note | app |
| `review_state` | item_key PK, due_at, interval_days, ease, reps, lapses, last_score | app (scheduler) |
| `lookups` | id, ts, item_key, word | app |
| `flags` | id, ts, item_key, reason (`wrong`, `confusing`, `audio`), note, resolved_at, resolution | app; the coach resolves |
| `submissions` | id, item_key, ts, kind (`writing`, `speaking`), text, recording_path, word_count, status (`new`, `marked`), feedback_path | app; the coach marks |
| `mock_runs` | id, blueprint, started_at, finished_at, unit_scores_json, status | app (phase 5) |

Migrations are numbered SQL files applied at start-up, so an older database upgrades itself (phase 6 tests this).

**Scheduler:** SM-2-style spaced repetition (Anki's lineage), implemented in about 50 lines in the repo with no dependency. It was chosen because it is well understood and explainable on a dashboard. The state columns are generic enough to move to FSRS later.

### 5.2 How the coach reads the data

The coach does not parse SQLite by hand. `uv run greek-coach report [--since 14d]` prints one JSON document covering:
- sessions and minutes per day;
- accuracy per skill, `exam_task` and topic;
- the items that are hardest (most lapses) and most looked up;
- open flags and unmarked submissions;
- the current readiness estimate.

This is the stable contract between app and agent. The coach writes only files (packs, feedback, notes, message, plan, profile), never the database.

---

## 6. Coach commands (agent skills)

Each skill is a folder with a `SKILL.md`. **The canonical copy is `.agents/skills/<name>/SKILL.md`**, which is where Codex looks (verified, [Codex skills docs](https://learn.chatgpt.com/docs/build-skills)). Claude Code looks in `.claude/skills/<name>/SKILL.md`. That file carries the same `name` and `description` and a single instruction to read and follow the canonical file. A test checks that the two stay in step. Symlinks were rejected because they are unreliable on Windows. `AGENTS.md` lists the skills in one line each, for any harness that reads only that file. Codex reads `AGENTS.md` automatically and caps project instructions at about 32 KiB by default (from memory, not re-checked), so `AGENTS.md` stays short and the detail lives in the skills.

The learner never has to know skill names. Plain sentences ("set this up", "coach", "we did the past tense today") must trigger them through their descriptions.

| Skill | When | Reads | Writes | Phase |
|---|---|---|---|---|
| `setup` | "set this up for me" | system state | installs uv, `uv sync`, starts the app, checks `/health`, creates the desktop shortcut, writes the initial `profile.json` | 2 |
| `coach` (check-in) | "coach", "how am I doing?" | `report`, profile, `coach/notes.md`, flags, submissions | `coach/message.json`; 10–30 new items in `generated/`; feedback for pending writing; resolved flags; updated notes | 4 |
| `capture` | "today we covered…", "what does this letter say?", a file in `inbox/` | the learner's words, `inbox/` files, profile | a private pack: vocabulary, a reading task, verb forms met. Personal data in real documents is replaced with invented details. | 4 |
| `tutor` | "let's practise", "role-play the landlord", "correct this", including from the phone | profile, `report`, recent tutor logs | a live chat in Greek at the learner's level, with explanations in Turkish or English. Afterwards: `tutor-log/<date>.md` and the words and errors from the chat as review items | 4 |
| `mark` | runs inside check-in, daily prep, or on request | `submissions` (text, or recordings transcribed locally with faster-whisper), the blueprint's criteria | `feedback/<id>.json`: score estimate against the blueprint, corrected text, the 2–3 errors that matter most, explanation in the UI language; for speaking, "what I heard" plus fixes. Exercises for recurring errors. | 4 |
| `daily-prep` | scheduled, about 05:00, or "prepare tomorrow" | `report`, profile, plan, `inbox/` | tomorrow's fresh items (news-style texts at level, verbs due, capture leftovers) in `generated/`; marks pending submissions; one line in `runs.log` | 4 |
| `watch` | scheduled weekly, or in check-in if older than 7 days, or "any exam dates?" | the `watch` URLs in the blueprints and the course page | `coach/watch.json`. The app shows the next date or registration window on the home screen, and the coach mentions changes in plain words. | 4 |
| `rebuild-imported` | "turn lesson 5 into exercises" | `content/private/*/raw/` | clean, checkable items in the private pack, `status: ok` only after self-check | 4 |
| `import-material` | "import my old project / this book" | the source folder plus a mapping | a private pack plus an import report with counts | 3 |
| `plan` | inside check-in, or "make me a plan" | profile (target session, minutes/week), `report`, blueprint | `coach/plan.json`, plus an honest one-line verdict on whether the target is realistic | 5 |
| `mock-exam` | "give me a mock exam" | blueprint, generated and private items | a mock pack in `generated/`; after the run, marks the writing and records the result | 5 |
| `update`, `backup` | "update the app", "back up my progress" | git, `learner/` | `git pull` + `uv sync` + migration check; a zip in `learner/backups/` | 6 |

**Scheduling** is set up by `setup` or on request, and only after the learner says yes, because it is standing configuration on their machine.
- The harness-neutral way is the OS scheduler running the agent headless: Task Scheduler on Windows, launchd on macOS, cron on Linux, calling `claude -p "<skill>"` or `codex exec "<skill>"` in the repo folder.
- The harness's own scheduled tasks are used where available.
- Scheduled runs use the learner's subscription. A run that fails leaves yesterday's content in place and a line in `runs.log`, which the next check-in reports.

Quality rule for everything the coach generates: validate against the schema, re-read each item for exactly one defensible answer, stay within the learner's level and covered material, and mark anything doubtful as `needs_review` instead of shipping it.

---

## 7. A ten-minute daily session, screen by screen

1. **Home.** One large button, *"Start today's 10 minutes"* / *"Bugünün 10 dakikası"*. Under it:
   - the coach's note from its last check-in, one or two lines (hidden if older than 14 days);
   - one small bar per exam unit of the selected blueprint (B1 or A2-LTR, switchable), showing estimated points or "not enough practice yet", with that exam's pass line marked;
   - the next exam date or registration window from `watch.json`;
   - a 28-day consistency grid;
   - one line naming the weakest unit.

   Nothing else competes with the button.
2. **Session.** Three segments shown as a thin progress bar at the top:
   - **Review** (about 4 min): due spaced-repetition cards, with the backlog capped at about 25.
   - **Exam task** (about 4 min): one small task in exam format, rotating through units with the weakest weighted up. For example, five true/false statements on a pharmacy notice, or ten history matches.
   - **New** (about 2 min): five new words or verb forms from today's prepared content, drawn first from what the learner captured, then from the current theme, or one history fact card.

   Once a week the exam-task segment is replaced by a writing prompt, and once a week by a speaking card. Feedback from the coach appears on the home screen when ready.

   The other ten minutes of the daily budget belong to the tutor chat, which happens in the agent, not the app. The app's home screen offers it as a line: *"Want to practise talking about your landlord? Open your agent and say 'tutor'."*

   Each screen shows large Greek text. Every word can be tapped for its meaning (logged as a lookup), there is a speaker button, and answers get immediate right/wrong feedback with a one-line explanation in the UI language. A small "this item is wrong" flag sits in the corner.
3. **Stopping.** "Enough for today" is always visible. Everything is already saved per answer, so leaving the tab loses nothing.
4. **Summary.** What you did (items, minutes, accuracy), what comes back tomorrow, and one plain sentence (e.g. *"History: 34 facts seen, 80% right. Reading notices: still your weakest."*). Two buttons: *"5 more minutes"* and *"Done"*.

The session is built from the time budget in `profile.json`, using the learner's own median time per item type. With no history, the app assumes 20 s per card and 90 s per exam task.

---

## 8. Install flow for a non-technical person

The person needs a computer, internet, and a Claude Code or Codex subscription. Prerequisites the agent installs: **uv** (it brings Python), and **git** if it is missing. The app runs from the repo with `uv run greek-coach start`, binds to `127.0.0.1:8642` (or the next free port), and opens the browser.

**Windows**
1. Install the Claude desktop app (or Codex) and sign in. This is the only step the person does alone.
2. In the app, pick a folder (e.g. Documents) and type: *"Download https://github.com/<owner>/greek-coach and set it up for me."*
3. The agent:
   - checks for git and installs it with `winget install Git.Git` if missing, telling the person a Windows prompt may appear;
   - clones the repo;
   - installs uv with the official per-user installer (no admin rights);
   - runs `uv sync` and starts the app;
   - checks `/health` and that a Greek test string survives a round trip through the database.
4. The agent creates a **"Greek Coach" shortcut on the Desktop** and says: *"Double-click Greek Coach on your desktop whenever you want to study. You don't need me open for that."*
5. Optional, and done by the person, never by the agent: adding the Greek voice in *Settings → Time & language → Speech → Add voices → Greek*. The agent checks first; on this maintainer's machine it was already present.

**macOS**
1–2. As on Windows.
3. If git is missing, macOS offers to install the Command Line Tools; the agent says "click Install in the window that appears". It installs uv with the official shell installer, then runs `uv sync`, starts the app and checks it.
4. The shortcut is `Greek Coach.command` on the Desktop. The agent explains the first-run "are you sure you want to open it" dialog in one sentence.
5. Optional Greek voice: *System Settings → Accessibility → Spoken Content → System voice → Manage Voices → Greek (Melina)* (unverified on current macOS).

**Linux**: the same steps, with a `.desktop` launcher in `~/.local/share/applications` and on the Desktop. Browser Greek voices on Linux are poor, so listening relies on pre-generated audio.

Every step is checked by the agent before it reports success. The person is never shown a command, an error message or a choice between technical options.

---

## 9. Speaking and listening: what local, free tooling can do

**Browser speech synthesis.**
- Windows: Chromium exposes the local **Microsoft Stefanos (el-GR)** voice and Microsoft Tolga (tr-TR). Verified on this machine on 2026-11-15, in a Chromium 156 browser. Stefanos comes with the Greek language pack; Microsoft lists it as the only Greek voice and it sounds robotic.
- Edge additionally offers online neural Greek voices. Those send the text to Microsoft, so the app does not rely on them, but it does not block them if they are the browser default.
- Chrome's own "Google" voices have no Greek (from memory, unverified).
- **Use:** single words, short sentences, the vocab audio direction. The app picks an `el-GR` voice that is `localService`, and hides the speaker button if there is none.

**Pre-generated audio for listening passages.**
- The coach generates audio files ahead of time with **Piper** (MIT engine). The official `el_GR-rapunzelina` voice is trained on a CC0 dataset.
- Piper is an *optional* dependency the coach installs on demand (`uv run --with piper-tts`). The app itself never needs it.
- **Risk:** users report the Greek Piper voice sometimes produces garbled sentences. Phase 3 must listen to samples and decide. The fallback is Stefanos recorded through the browser, which is ugly but correct.
- **Approved fallback (2026-11-15): edge-tts.** It is free and needs no account, but it sends text to Microsoft. It may be used **only** if Piper's Greek quality is not good enough, and only under these rules:
  - only by the coach, to pre-generate audio for content text;
  - never with learner data: no writing, no captured documents, nothing from `learner/`;
  - off by default for every install, with each learner asked once before it is switched on.

  This is the one documented exception to the local-only guardrail.

**Official listening audio.** The 2022, 2024 and 2026A A2-LTR listening recordings are published as MP3s. The coach can download them into `content/private/` (after asking) for mock exams.

**Speaking.**
- In the app: record (`MediaRecorder`, saved locally), play back, compare with a model answer and useful phrases, and mark the card done.
- Feedback from the coach: it transcribes recordings locally with **faster-whisper**, which supports Greek. This is an optional dependency group, installed after the learner agrees to a model download of roughly 0.5–1.5 GB, depending on the model size chosen in phase 4.
  - Accuracy on beginner speech is uncertain. Feedback is framed as "this is what I heard", never as a pronunciation score.
- Live conversation is the tutor's job, in text, and the course's.
- The course is where live speaking practice happens.

---

## 10. The earlier project (`Greek_Helper`)

Reviewed read-only on 2026-11-15; nothing was copied. The data is UTF-8 JSON with CRLF line endings.

| Material | What it really is | Verdict |
|---|---|---|
| Vocabulary, 3,195 entries | Greek–English with part of speech. It comes from **four generic word-list PDFs** (Beginner → Intermediate, apparently from an English-language coursebook series), **not from the textbook**, and has no lesson links. Only 2 of 2,020 nouns have an article, so gender is missing. No Turkish. | **Import after cleaning.** 547 duplicate rows (435 forms repeat), 94 entries with "PAGE 19"-style header junk, 14 mixed-script entries, about 35 truncated words. What is left is fairly clean. |
| Lessons, 25 | Lesson skeleton: themes, page ranges, communicative functions, grammar and vocabulary focus. | **Import as-is** (without absolute paths). It is the course outline the coach builds around. |
| Practice items, 281 | **No answers in any of them.** OCR noise: 196 contain polytonic misreads, 97 have glued words, and blanks, pictures and tables are lost. | **Not exercises.** Import as `raw/` source prompts (page, exercise number, instruction) for the coach to rebuild. |
| Review items, 1,877 | Unclassified pages, answer keys, and **A2 exam-format tests with solutions**. | Raw material. The A2 tests are the most exam-relevant part. |
| Audio, 46 MP3s (85 MB) and 131 transcripts | **85 of the files the transcripts refer to are missing.** Transcripts are noisy speech-to-text. Nothing links audio to lessons. | Import the 46 files that exist with their transcripts, flagged for review. Listening exercises come later, via the coach. |

What the phase-3 importer must do:
1. Read UTF-8, normalise to NFC, and fold polytonic characters to monotonic (ἄ→ά).
2. Flag `latin_mixed`, `header_junk` and `truncated` entries.
3. Dedupe on lemma + part of speech, merging senses and sources.
4. Enrich gender and article, either generated by the coach and marked `needs_review`, or, better, from an openly licensed dictionary dump (Wiktionary via kaikki.org, CC BY-SA). The download needs the learner's OK.
5. Write `tr` as coach-generated and unverified.
6. Map lessons to pack units.
7. Write everything else to `raw/`.
8. Print an import report with counts.

Output goes only to `content/private/greek-helper/` with `licence: "private, commercial source"`.

---

## 11. Technical decisions (made for the maintainer, one line each; all approved 2026-11-15)

Also approved on that date, so later phases need not ask the maintainer again:
- the faster-whisper model download;
- the scheduled agent runs;
- the home Wi-Fi switch;
- the edge-tts fallback (§9).

Each is still shown to him when it is set up, and a non-maintainer learner is still asked.

- **Stack as designed:** Python with uv, FastAPI and uvicorn, SQLite through the stdlib `sqlite3`, and plain HTML/CSS/JS modules with no build step. The pack schema is defined with pydantic (it comes with FastAPI) and exported as JSON Schema to `schemas/` for agents.
- **Repo layout:** `src/greek_coach/` (server, db, packs, checking, scheduler, session, cli), `web/` (static, with `i18n/en.json` and `i18n/tr.json`), `content/`, `exams/`, `schemas/`, `scripts/`, `tests/`, `.agents/skills/`, `.claude/skills/`.
- **CLI:** `greek-coach start | health | report | validate | backup`.
- **Optional dependency groups** for things only the coach needs, installed on demand: `audio` (piper-tts) and `speech` (faster-whisper). The base install stays small.
- **Port:** 8642 on 127.0.0.1, falling back to the next free port. The chosen port is written to `learner/.port` so the shortcut and the agent can find it. A second start opens the browser on the running instance instead of failing.
- **i18n:** UI strings live in JSON files. Content translations are per item. Turkish is a first-class language, not an afterthought.
- **On-screen Greek keyboard** in the app, because the friend will not have a Greek keyboard layout, and adding one is a system setting the agent should not touch.
- **Licences:** **MIT** for the code; **CC BY-SA 4.0** for original content packs. BY-SA was chosen so the packs can legally incorporate Wiktionary-derived data. The `LICENSE` files are added in phase 2.
- **Harness support:** Claude Code and Codex, both tested in phase 6. Copilot reads `AGENTS.md` and may work, but it is not tested.

## 12. Challenges to the design, and what changed

1. **Exam: one fixed B1 target → two blueprints, B1 and A2-LTR, and the data decides.** A2 + history is legally enough for long-term residence. B1's pass rule (60% in every skill) is stricter. From the learner's starting point, A2 comes first on either path. The history and culture content (20% of A2-LTR) is only needed if A2-LTR gets booked, so it is scheduled late.
2. **App/agent split: kept.** It holds up even better than expected, because most exam tasks (about 60% of A2-LTR, and the reading and listening papers of B1) are deterministic selection or short-answer tasks.
3. **Content packs: kept**, with two additions. Private packs can hold `raw/` material that is never shown as exercises, and an exam blueprint is separate data from the packs.
4. **Browser speech alone is not enough for listening.** Pre-generated audio is added, made by the coach with a local engine.
5. **Selection-first exercise design and an on-screen keyboard**, because typing Greek is a barrier the design did not mention.
6. **The old vocabulary is not the textbook's.** The design assumed it mirrored the lessons. It is still useful, but it needs gender enrichment and does not follow the course order.
7. **More agent, same independence.** The design treated the agent as an occasional coach. The maintainer wants to use the subscription fully, so the tutor, daily prep, speaking feedback and watch are added. The rule that the app works without an agent running is unchanged.
