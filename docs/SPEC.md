# Specification

Status: **agreed (2026-11-15).** The maintainer accepted the exam strategy in §1.4. Where this file and `docs/DESIGN.md` disagree, this file wins.

Exam facts were checked against official sources on **2026-11-15** and again in phase 5 on **2026-11-16**. Each claim below is marked as **verified** (seen in an official source) or **unverified** (taken from a secondary source or from memory, and still to be checked). The structured, machine-readable version of §1.2–§1.3 is in the blueprints `exams/a2ltr.json` and `exams/b1-keg.json` (§4.5); when they disagree with this text, fix both.

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
| Timings | History 25 min, listening 25 min, reading 30 min, writing 40 min, then a separate speaking test of 12 min per pair | Reading 40 min, listening 25 min, writing 55 min (2 h written in total), speaking about 12 min per pair | About 150 min written. Listening and speaking about 15 min each (unverified). |
| Pass mark | At least 50/100 **and** at least 50% in 4 of the 5 units, so one weak unit is survivable. History-only candidates: 10/20. (Verified, [ΚΥΑ 140304/Κ1, art. 12](https://gsvetlly.minedu.gov.gr/publications/docs2023/KYA_ELLINOMATHIAS_2021.pdf).) | **At least 60% in each of the four skills.** Failing one skill fails the whole exam. There is no overall-total rule; the certificate shows Καλώς / Λίαν καλώς / Άριστα. (Verified in the [ΚΕΓ exam guide](https://www.greek-language.gr/certification/sites/greeklanguage.gr.certification/files/odigos_ell_2022.pdf), p. 22.) | At least 20 on knowledge, at least 40 on language, at least 70 overall |
| Teaching hours, ΚΕΓ estimate | A2 needs about 120–180 h | B1 needs about 180–250 h (verified, guide p. 26) | — |
| How often | The ΚΥΑ says twice a year, April and October (art. 9 §3), but in practice sessions are irregular: the last two were the second half of 2024 and **23 May 2026** (applications 9–20 Apr 2026). **No 2026B or 2027 call as of 2026-11-16.** | May every year for all levels, plus an October session for B1 in Greece only (the last one was Fri 23 Oct 2026). **May 2027: registration 1 Feb – 14 Mar 2027, B1 written exam Thu 13 May 2027** (verified, [ΚΕΓ node/15](https://www.greek-language.gr/certification/node/15.html)). Nothing later is announced. | Twice a year, about May and November. Procurement for Nov 2026 and Apr 2027 is published. |
| Fee | €50, or €20 for history only (verified, ΚΥΑ art. 9 §4 and the 2026 call). Places are capped (**1,000** in 2026A) and allocated by order of application. | Unverified (the fee table could not be read reliably) | A fee applies; the amount is unverified |
| Past papers | Official papers, answer keys and audio for 2022, 2024 and 2026A in the current format (older ones in earlier formats), plus the history syllabus | Two undated sample series on the ΚΕΓ site, with one MP3 and no answer keys | Official published question bank (the language part alone is 400+ pages) |

Verified: the A2-LTR structure and points, from the [2026A written paper](https://www.gsvetlly.minedu.gov.gr/ellinomatheia) and the exam page. The B1 structure, from the [ΚΕΓ B1 structure table](https://www.greek-language.gr/certification/node/119.html). The [May 2027 registration dates](https://www.greek-language.gr/certification/news/show.html?id=94). The ΠΕΓΠ sections and pass marks, from [mitos.gov.gr](https://mitos.gov.gr/index.php/%CE%94%CE%94:%CE%95%CE%BE%CE%B5%CF%84%CE%AC%CF%83%CE%B5%CE%B9%CF%82_%CE%B1%CF%80%CF%8C%CE%BA%CF%84%CE%B7%CF%83%CE%B7%CF%82_%CE%A0%CE%B9%CF%83%CF%84%CE%BF%CF%80%CE%BF%CE%B9%CE%B7%CF%84%CE%B9%CE%BA%CE%BF%CF%8D_%CE%95%CF%80%CE%AC%CF%81%CE%BA%CE%B5%CE%B9%CE%B1%CF%82_%CE%93%CE%BD%CF%8E%CF%83%CE%B5%CF%89%CE%BD_%CE%B3%CE%B9%CE%B1_%CE%A0%CE%BF%CE%BB%CE%B9%CF%84%CE%BF%CE%B3%CF%81%CE%AC%CF%86%CE%B7%CF%83%CE%B7).

Re-checked on 2026-11-16 (phase 5):
- The B1 date of 13 May 2027 and the registration window are now verified on ΚΕΓ's own page.
- The A2-LTR fee is verified; the cap of 2,300 from a 2024 news report was wrong for 2026A, which had 1,000 places.
- A2-LTR speaking is read from the 2026A oral paper (§1.3).
- From October 2026, ΚΕΓ marks B1 reading and listening by machine from a shaded answer sheet; only the answer sheet counts ([news id=97](https://www.greek-language.gr/certification/news/show.html?id=97)).

Still unverified:
- The 2024 amendment of the A2-LTR decision (ΚΥΑ 25047/Κ1/2024, Β' 1776): its link on the official site returns 404, so any change it made is unread.
- The split of the speaking points into parts, for both exams. No marking criteria are published for A2-LTR writing or speaking.

### 1.3 The A2-LTR exam in detail (from the 2026A paper)

| Unit | Points | Time | Part 1 | Part 2 | Part 3 |
|---|---|---|---|---|---|
| History & culture | 20 | 25 min | Match sentence halves, 10 × 0.5 (5 pts) | Multiple choice, 10 × 1 (10 pts) | Put people or events in their era, 10 × 0.5 (5 pts) |
| Listening | 20 | 25 min | Voice message: fill in the missing information from options, with distractors (5 pts) | Dialogue heard twice: multiple choice (10 pts) | Six short dialogues: pick the place where each happens, with distractors (5 pts) |
| Reading | 20 | 30 min | Gapped text with a word bank and distractors (6 pts) | Ten public notices (pharmacy hours, offices…): 14 true/false statements (14 pts) | — |
| Writing | 20 | 40 min | Semi-formal e-mail, 40–60 words, with required content points (10 pts) | Friendly e-mail or invitation, 40–60 words (10 pts) | — |
| Speaking | 20 | 12 min per pair | Personal questions from the examiner (name, origin, how long in Greece, home, free time, family, languages) | A pair of photos on one theme: 1 minute to look, then describe them and answer comparison and opinion questions | Role-play between the two candidates, from A and B cards (a phone call, advice, an office, a shop, a family disagreement) |

Speaking is held by two assessors and recorded (ΚΥΑ art. 8, 12). The 2026A oral paper has one question set, 5 picture sets and 5 role-plays. **How the 20 points split between the parts, and the criteria, are not published** (verified absent, 2026-11-16). The writing criteria are not published either; when the two markers differ by more than 6 points, the Scientific Committee re-marks.

### 1.3b The B1 exam in detail (ΚΕΓ structure table and guide, verified 2026-11-16)

| Skill | Points | Time | Tasks |
|---|---|---|---|
| Reading | 25 | 40 min | 1. Matching, 6 items (6 pts) · 2. **Table comparison**, 12 × 0.5 (6 pts) · 3. True/false, 6 (6 pts) · 4. Gap fill from a bank with 6 distractors, 7 (7 pts). Texts of 150–200 words, authentic and fairly formal, including a literary extract. |
| Listening | 25 | 25 min | 1. **Notes** from a 300-word monologue or interview, 12 (12 pts) · 2. **Table comparison** from a 2–3-person discussion of 350–400 words, 13 (13 pts). Each recording is heard twice; notes are written in lower case. |
| Writing | 25 | 55 min | A. A friendly letter, notice or advert, **150 words** (12 pts) · B. A formal text (information, a request for permission with reasons, a complaint with reasons), **150 words** (13 pts). Marked holistically out of 25 (`docs/COACHING.md` §10). |
| Speaking | 25 | about 12 min per pair | A. Warm-up questions · B. A monologue (for a photo: the feelings it shows, with reasons) · C. A role-play between the candidates "with a fair amount of argument". No preparation time except about 2 minutes for the role card. Per-part points unverified. |

**What B1 adds over A2.** Sources: the ΚΕΓ A2 and B1 structure tables, the level descriptors ([A2](https://www.greek-language.gr/certification/node/98.html), [B1](https://www.greek-language.gr/certification/node/99.html)) and the B1 writing criteria footnotes.

- **Texts.** Reading texts grow from 120–140 to 150–200 words. Writing grows from 2 × 80–100 words in 45 min to **2 × 150 words in 55 min**.
- **Task types.** Table comparison and note-taking (`table_fill`) are new. Listening becomes two long recordings instead of four short ones.
- **Grammar:**
  - the passive voice in present, imperfect, future and aorist;
  - reported speech;
  - first-type conditionals;
  - concessive, relative and adverbial clauses;
  - periphrastic comparatives;
  - the genitive;
  - the subjunctive and the perfective imperative;
  - impersonal verbs.
- **Linking words:** ενώ, επειδή, αν και, καθώς, ότι/πως, δηλαδή, ίσως, ή…ή, είτε…είτε, ούτε…ούτε.
- **Vocabulary and functions:**
  - verbs of opinion and feeling (νομίζω, πιστεύω, χαίρομαι, λυπάμαι);
  - giving and asking for advice and permission, justifying an opinion;
  - formal letters: a job application, a complaint, the landlord, a hotel;
  - domains: public services, health, work, education, shopping, leisure.
- **Spelling:** final ‑ν, the άνω τελεία, ‑γ‑ in έλεγα/έτρωγα, and the φτ/φθ and χτ/χθ variants.

The B1 blueprint lists these as `beyond_a2` entries, so coverage and the plan can track them.

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
- **The starting point matters most.** The learner currently reads Greek letters slowly and plans 20 minutes a day. That is about 2.3 hours a week, or 10 a month, if every day; on weekdays only it is about 1.7 hours a week. ΚΕΓ's rough estimate is 120–180 teaching hours for A2 and 180–250 for B1. On the app alone, that puts A2 about 12–18 months away and B1 about 18–24 months away. An evening course at 6 h/week roughly triples the pace. That would make A2 by mid-2027 and B1 by late 2027 plausible.
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
  - **Correction from the research (2026-11-15):** registration seemed open for the **6-month course, 1 Dec 2026 – 14 May 2027**, at 8 h/week or 15 h/week. A **3-month course** runs **22 Feb – 14 May 2027** at 15 h/week. The online A1/A2 courses also take a second-semester intake in March 2027.
  - **Re-checked in phase 5 (2026-11-16):** the 8 h/week 6-month course does meet in the evening, 17:00–21:00, but its registration closed on 11 Nov 2026. The online A1 and A2 courses start on 1 Mar 2027, with registration 15–23 Feb 2027 and evening slots after 20:30 (in `learner/coach/watch.json`).
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
  units.json                   optional: the course outline (lessons with theme, functions, grammar, vocabulary)
  overlays/tr.json             optional, imported packs: Turkish meanings written by the coach, applied on (re-)import
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

`answer` lists every accepted form, so variants such as επτά/εφτά both count. `options` (optional) is an object of choices per gap, e.g. `{"1": ["πήγα", "πάω", "θα πάω", "πήγες"]}`. The app offers the choices while the form is new and asks for it typed once it has been answered right. `translation` (optional, also on `gap_bank`) is the whole sentence in `en`/`tr`, shown on request and after answering.

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

Phase 5, as built (`src/greek_coach/exams.py`, validated on load and exported by `greek-coach schema`):

- **Top level:** `id`, `title`, `short` ("A2+", "B1"), `level`, `task_prefix` (`a2ltr`, `b1keg`), `checked_at`, `total_points`, `hours_estimate` (ΚΕΓ teaching hours, cumulative), `sessions_note`, `sources`, `watch` and, for B1, `beyond_a2`.
- **`pass_rule`:** `{min_total, unit_min_share, units_needed, text}`.
  - B1: `{null, 0.6, 4}`.
  - A2-LTR: `{50, 0.5, 4}` (4 of 5 units).
  - `exams.passes()` applies it.
- **`units[]`:** `id`, `skill`, `points`, `minutes`, `marked_by` (`app` or `coach`), `technique` (short practical advice, en/tr), `note` and `tasks[]`.
  - Each task has `id`, `title`, `types` (the item types that train it), `questions`, `points`, `points_verified` (false for the unpublished speaking split) and `words`.
  - The loader checks that task points add up to the unit and units to the total.
- **`beyond_a2[]`:** what B1 adds over A2 (§1.3b), each with a `match` rule (grammar tag prefixes, topics, exam tasks) so coverage can count it.
- **Tagging** (§1.5): `validate` checks that an item's `exam_task` exists, that its `type` is one the task uses and that its `skill` is the unit's. An item below the exam's level trains the format but is not readiness evidence.
- **`exams/watch-sources.json`** now holds only the course page; the exam pages moved into the blueprints.

### 4.7 `table_fill` (phase 5, as built)

- **Format:** `columns`, `rows`, an `answer` grid where each cell is a list of accepted strings (or one string), or `null` for a cell that is not asked, plus an optional `given` grid shown in those cells.
- **Checking:** each asked cell is typed and checked like `form`, accent-tolerant, with a leading article optional. The response is `{"answers": [...]}`, one string per asked cell, in reading order.
- **Note-taking** (B1 listening 1) is a one-column table.
- **Audio:** `stimulus` gained `start`/`end` (seconds), so one official recording can serve the separate parts of a rebuilt paper. The browser plays only that range.

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
    resolved-flags.json   the coach's ruling on flagged items (fixed / retired / kept); the app applies it
    schedule.json         written by `greek-coach schedule`: which skills run when, with which agent
    runs.log              one line per scheduled run (time, skill, ok/failed), so a silent failure shows up
  feedback/<submission-id>.json   writing or speaking feedback the app shows next to the original
  generated/<pack-id>/    coach-written packs (coach-practice, coach-capture, coach-writing, coach-tutor)
  inbox/                  learner drops handouts, photos, letters, notes; anything to "capture" (processed: inbox/done/)
  recordings/<id>.webm    speaking recordings; <id>.json is the local transcript
  logs/runs/              the output of each scheduled run
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
| `submissions` | id, item_key, session_id, attempt_id, ts, kind (`writing`, `speaking`), text, recording_path, word_count, status (`new`, `marked`), feedback_path, feedback_seen_at | app; the coach marks by writing `feedback/<id>.json`, and the app sets `marked` when it sees the file |
| `mock_runs` | id, blueprint, mock_id, started_at, finished_at, status (`running`, `finished`, `abandoned`), unit_scores_json | app (phase 5, migration 0004) |
| `mock_sections` | id, run_id, unit, session_id (kind `mock`), started_at, ends_at, closed_at, closed_by (`learner`, `time`, `time_away`), answers_json (drafts), last_saved_at, result_json | app (phase 5) |

Migrations are numbered SQL files applied at start-up, so an older database upgrades itself (phase 6 tests this).

**Scheduler:** SM-2-style spaced repetition (Anki's lineage), implemented in about 50 lines in the repo with no dependency. It was chosen because it is well understood and explainable on a dashboard. The state columns are generic enough to move to FSRS later.

Phase 3, as built (`src/greek_coach/scheduler.py`). SM-2 was kept; nothing seen so far argues for FSRS.
- **What is scheduled.** Every `vocab` and `form` item enters the schedule the first time it is seen. Verbs are the learner's stated gap, so they are scheduled like words. Any other item enters the first time it is answered wrongly.
- **Quality** comes from the attempt, never from self-grading:
  - wrong, or any part wrong: 1, a lapse, so it is due tomorrow;
  - right after a word lookup, or right with an accent note: 3;
  - right: 4;
  - right in under half the expected time: 5.
- **Intervals:** 1 day, 6 days, then the interval times the ease. An item with an interval of 21 days or more counts as "known" on the home screen.
- **Lookups.** Tapping a word that a vocab item explains makes that item due today, with its ease lowered by 0.15. An unseen word joins today's reviews.
- **The daily session** has four segments, sized with the learner's own median seconds per card type (defaults: 20 s for a card, 30 s for a form, 90 s for a task):
  1. due reviews, most overdue first, at most 25;
  2. a verb slot of 4 forms, due ones first;
  3. one task in exam format, wrong-and-due first, weakest skill first;
  4. 5–12 new words.
  New words come from coach-generated packs first. After that, open packs and the learner's own book take turns: A1 first, then words that appear in the earliest unit of the book.
- **Stopping and resuming.** A daily session left early is resumed by the same button. Once it is finished, the button offers five more minutes.
- **Practice sessions.** `?practice=<pack/item>,…` (or `POST /api/session` with `kind: "practice"`) opens a session with chosen items, for the coach and for checking content.

### 5.2 How the coach reads the data

The coach does not parse SQLite by hand. `uv run greek-coach report [--since 14d]` prints one JSON document covering:
- sessions and minutes per day;
- accuracy per skill, `exam_task` and topic;
- the items that are hardest (most lapses) and most looked up;
- open flags and unmarked submissions;
- the current readiness estimate.

This is the stable contract between app and agent. The coach writes only files (packs, feedback, notes, message, plan, profile), never the database.

### 5.4 Progression along a curriculum (phase 5b, as built: `src/greek_coach/curriculum.py`)

**The problem it fixes.** The daily session drew from every pack at once, so the maintainer's first session held B1 passives and a 150-word letter before they could read the alphabet. Items now come in course order, simple before hard.

**A curriculum** is an ordered list of stages: `curricula/open-a1-b1.json` (tracked, for a learner without a book) or a book's own `curriculum.json` in its private pack folder. The maintainer's is `content/private/greek-helper/curriculum.json`, built from the book's `units.json`: an intro (reading) stage, then lessons 1–24, then a B1 stage.

- **Which curriculum:** `profile.curriculum` if set; else a book curriculum whose pack is loaded; else the open one. `"curriculum": "off"` turns it off (an advanced learner); `profile.level` then limits the level.
- **Where an item belongs:**
  1. a topic `stage:<id>` (what the coach writes);
  2. the first stage whose `include` rules match it (`units`, `packs`, `items`, a verb's lemma, tense and person, `grammar` tags, `pos`, `types`, `levels`, `topics`);
  3. otherwise a level pool (unplaced A1 words open from lesson 3, A2 from lesson 13, B1 at the B1 stage);
  4. otherwise nowhere.

  Generic verb rules apply up to A2 only, so B1 forms wait for the B1 stage.
- **Done:** a stage is done when 80% of its own words and verb forms are *learned* (answered right the last time), or when the learner passes its *check*. Pool words never count. A review stage counts the stages it reviews.
  - Done is recorded (`stage_checks`, migration 0005) and stays done. A later mistake brings the item back as a review, not the learner back a lesson.
  - The current stage is the first one not done.
- **The check** ("I know this: test me"): up to 20 of the stage's items, 80% to pass, unanswered items counted as wrong. It is open for the current stage and the next one.
- **The daily session** serves only items of reached stages. New words and forms come from the current stage first, then what is left of earlier stages, then pool extras. Exam tasks, writing and speaking appear only in the stages that hold them. Items placed nowhere never appear in a daily session. A plan of today's that holds cards of a stage not reached is stale: it is closed and today is planned afresh; the answers already given stay.
- **The alphabet:** `content/open/open-alphabet` has 24 letters, 13 letter pairs and the accent, and 30 syllables, as vocab cards: the sound in Turkish and English, the letter's name, an example word. Letters with the same sound are told apart by their name, so there is never a second right answer.
- **The learner's own screens:**
  - the **course map**, and a page per stage (its words with status, forms, tasks, "Practise this lesson", the check);
  - **Choose practice**: a bit of everything, words, verbs, reading, listening, writing, speaking, or my mistakes; from all reached lessons or one; 5, 10 or 20 minutes;
  - **My words**: search in Greek or the UI language, status and lesson filters, later lessons on request, "practise selected";
  - **My verbs**: per-verb tables, with forms of later lessons locked.
- **The report** gains `curriculum`. The coach writes for the current stage and tags items `stage:<id>` (COACHING §5.3).

Simulated first five weeks of a beginner on the book curriculum (`scripts/simulate.py`, 20 min/day, 15% wrong):

| When | Where |
|---|---|
| days 1–20 (17 practice days) | Intro (reading): 129 letters, sounds and words |
| day 21 | Lesson 1 |
| day 23 | Lesson 2 |
| days 24–35 | Lesson 3, which holds the present tense of all A-group verbs: 92 words and forms, about 40% learned by day 35 |

The intro is slow on purpose (about 5–12 new cards a day); a learner who already reads can pass its check on day one.

Nothing came from a later stage before an earlier one was done, and no stage reopened.

### 5.3 Readiness (phase 5, as built: `src/greek_coach/readiness.py`)

The maintainer books an exam from this, so false confidence is worse than no estimate. Per exam, per unit:

- **Evidence is the first attempt at each item tagged for that exam, at its level or above**, in the last 90 days, at most the 20 most recent per task.
  - A repeat of an item measures memory of it, so it never counts.
  - A2 practice is not B1 evidence.
  - Mock answers are first attempts too, and are counted as timed.
- **Writing and speaking** count only the coach's feedback scores (`score.exam`, `score.task`, `points/out_of`). The app never scores them.
- **Per task:** the mean item score (share of sub-answers right) with a Wilson 80% interval, where n is the number of items, not sub-answers.
  - Unit points are Σ task points × share.
  - The low and high ends add the task ends, which is conservative.
  - A task with no evidence spans its whole range, and its share in the point estimate is assumed from the unit's other tasks (shown as assumed).
- **No number** is shown when a unit has fewer than 6 first attempts (2 coach marks for writing and speaking), or a task worth ≥25% of the unit has none.
- **States:** `above` (low end ≥ pass line), `below` (high end < pass line), `unclear`, `no_evidence`.
- **The exam verdict** applies the real rule to every unit's low end (`pass`) and high end (`fail`); otherwise `unclear`. A unit with no evidence counts as 0 for the low end and full marks for the high end.
- **Coverage** per task: items available, tried, and unseen at level. It also covers untagged general practice and B1's `beyond_a2`.

The report gains `readiness`, `readiness_rules`, `coverage`, `plan_inputs`, `plan_progress` and `mocks` (`report_version: 2`).

Phase 4, as built (`src/greek_coach/report.py`, `report_version: 1`):
- **More fields:**
  - `recent_wrong`: what was answered against what was right;
  - `covered`: words by level, verb lemmas and tenses, book units met; with `--words`, every word met;
  - accuracy per `grammar` tag;
  - `generated_stock`: unseen coach items per pack;
  - `inbox`;
  - `coach`: last check-in, watch age, tutor logs, scheduled runs and problems;
  - `profile_missing`, `learner_dir` and `app_url`.
- **Readiness is `null` until phase 5.**
- **The coach files** (message, watch, feedback, flag resolutions, schedule, profile) are pydantic models in `coachfiles.py`. `greek-coach validate <learner folder>` checks them. The app reads them leniently: a broken file is skipped and logged, never fatal.
- **Their formats** are documented for agents in `docs/COACHING.md` §7.

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
| `plan` | inside check-in, or "make me a plan" | profile (minutes, days_per_week), `report` (`plan_inputs`, `plan_progress`, readiness), blueprints, `watch.json` | `coach/plan.json`, plus an honest one-line verdict on whether the target is realistic; re-plans each check-in and says what to drop when behind | 5 |
| `mock-exam` | "give me a mock exam" | blueprint, generated and private items (official papers in `content/private/official-a2ltr/`) | items in `generated/coach-mock/` (or a private pack for official papers) and `coach/mocks/<id>.json`; after the run, marks the writing and speaking | 5 |
| `update`, `backup` | "update the app", "back up my progress" | git, `learner/` | `git pull` + `uv sync` + migration check; a zip in `learner/backups/` | 6 |

**Scheduling** is set up by `setup` or on request, and only after the learner says yes, because it is standing configuration on their machine.
- The harness-neutral way is the OS scheduler running the agent headless: Task Scheduler on Windows, launchd on macOS, cron on Linux, calling `claude -p "<skill>"` or `codex exec "<skill>"` in the repo folder.
- The harness's own scheduled tasks are used where available.
- Scheduled runs use the learner's subscription. A run that fails leaves yesterday's content in place and a line in `runs.log`, which the next check-in reports.

Quality rule for everything the coach generates: validate against the schema, re-read each item for exactly one defensible answer, stay within the learner's level and covered material, and mark anything doubtful as `needs_review` instead of shipping it.

Phase 4, as built:
- **Profile.** The `profile` row of the table is part of `coach`: on a first run it asks the profile questions.
- **Speaking feedback** is part of `mark`.
- **The shared rules** live in `docs/COACHING.md`, which every coach skill reads first:
  - who the learner is and the tone;
  - how to read the report and where to write;
  - the Greek-correctness checklist;
  - personal data;
  - the file formats;
  - the exam writing criteria.
- **`validate` adds a Greek lint** for every pack:
  - **problems:** Latin look-alike letters inside Greek words, polytonic characters, non-NFC text, final-sigma errors;
  - **notes:** missing accents and, for coach packs, words that no other content uses.
- **Flagged items.** Items flagged `wrong` or `confusing` stay out of sessions until the coach rules on them in `coach/resolved-flags.json`.

---

## 7. A ten-minute daily session, screen by screen

> **Changed in phase 5b (2026-11-17).** "One large button, nothing else competes" was wrong for this learner. They could not see their words or choose what to practise, and the session ignored the course order, so B1 forms came before the alphabet. The home screen now also shows the current lesson, and links to "Choose practice", "My words", "My verbs" and the course map; see §5.4 and §12 item 8. The daily button stays the main way in.

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

**Phase-3 listening test (2026-11-16).** Eight A2 sentences were rendered by each voice, transcribed locally with faster-whisper `small`, and compared with the text by character error rate (CER). The digits and the word "ασανσέρ" inflate every voice's score equally.

| Voice | Licence | Mean CER | Notes |
|---|---|---|---|
| edge-tts `el-GR-AthinaNeural` (online, Microsoft) | Microsoft service | 0.08 | Natural. Nearly all of its error is the digits in sentences 2 and 4; without them it is about 0.02. Tested 2026-11-16, after the maintainer switched it on. |
| Microsoft Stefanos (Windows, offline) | Windows voice | 0.06 | Robotic but correct. This is the baseline for what whisper can hear. |
| Piper `el_GR-joy-medium` | **CC BY-NC 4.0** (non-commercial) | 0.14 | Usable, but the licence does not fit CC BY-SA packs. |
| Piper `el_GR-rapunzelina-low` | CC0 | 0.30 | One sentence fully garbled ("Καλημέρα" became babble); others with wrong consonants. |

**Verdict: Piper is not good enough for listening passages.** Its only openly licensed Greek voice garbles sentences, which confirms the reported risk. So, per the rules above, **edge-tts is the approved generator.** It stays off until the learner says yes, recorded as `"edge_tts_ok": true` in `profile.json`; the coach asks once, then sets it. The maintainer said yes on 2026-11-16. The open pack's six listening passages were then generated with it, with retries, because the free service sometimes answers with no audio.
- Until then the coach uses the local Stefanos voice. It is offline and robotic, but whisper understood it best of all.
- `scripts/make_audio.py --engine edge|windows|piper --pack <id>` writes `learner/audio/<pack>/<item>.<ext>` for every `stimulus.tts` passage of eight words or more.
- The app plays that file instead of the browser voice. It works on a phone, which has no Greek voice.
- Generated audio is never tracked: it is derived content, and the licences of TTS output are not CC BY-SA. Open packs carry `tts` text, not audio files.
- The edge engine refuses packs under `learner/`.

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

**Phase-3 re-measurement and result (2026-11-16)**, from `uv run greek-coach import greek-helper --source …`:
- **Vocabulary:** 3,289 rows (3,195 plus 94 that Greek_Helper had already set aside).
  - 56 OCR-split words were joined again with the dictionary (υπογ ράφω → υπογράφω).
  - 113 entries were flagged and kept out (99 header junk, 14 mixed script, 5 truncated; some carry two flags).
  - 528 duplicates were merged.
  - The result is **2,648 vocab items**: A1 1,053, A2 809, B1 786.
  - 1,250 nouns have an article from Wiktionary; 173 do not.
  - 407 words are linked to the first unit of the book that uses them.
  - 1,053 A1 words have a Turkish meaning from the coach overlay, marked unverified (60 are listed as doubtful).
- **Exercises:** the full texts come from `data/processed/exercises/exercise_items.json`; the app file only holds previews.
  - Of 2,158 items, 1,697 were kept in `raw/` as source prompts, all folded to monotonic.
  - 461 were dropped: 448 exact duplicates and 13 too short.
  - Kept by kind: 1,256 exercises, 328 answer keys, 69 tests, 38 revision items, 6 listening tests.
- **Audio:** 46 MP3s were copied and flagged `needs_review`; 85 transcripts have no audio file, all listed in the report.
- **Course outline:** the 25 lessons are in `units.json`, without paths.
- The importer is general: a small mapping file per source (`docs/IMPORTING.md`).

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
- **CLI:** `greek-coach start | stop | health | report | validate | backup | shortcut`.
  - Phase 2 added `stop` and `shortcut`. With `shortcut` the agent never hand-writes OS launcher files.
  - `start` runs the server as a background process with no window, waits for `/health`, opens the browser and returns. A desktop double-click therefore behaves the same on every OS. `start --foreground` is for development.
  - `stop` finds the process through the pid that `/health` reports.
- **Optional dependency groups** for things only the coach needs, installed on demand: `audio` (piper-tts) and `speech` (faster-whisper). The base install stays small.
- **Port:** 8642 on 127.0.0.1, falling back to the next free port. The chosen port is written to `learner/.port` so the shortcut and the agent can find it. A second start opens the browser on the running instance instead of failing.
- **i18n:** UI strings live in JSON files. Content translations are per item. Turkish is a first-class language, not an afterthought.
- **On-screen Greek keyboard** in the app, because the friend will not have a Greek keyboard layout, and adding one is a system setting the agent should not touch.
- **Licences:** **MIT** for the code; **CC BY-SA 4.0** for original content packs. BY-SA was chosen so the packs can legally incorporate Wiktionary-derived data. The `LICENSE` files are added in phase 2.
- **Harness support:** Claude Code and Codex, both tested in phase 6. Copilot reads `AGENTS.md` and may work, but it is not tested.

Phase 3 additions (2026-11-16):
- **Importer:** `greek-coach import <mapping> --source <folder>`, with mappings in `src/greek_coach/importer/mappings/`. It refuses any output folder outside `content/private/` and `learner/generated/`.
- **Dictionary enrichment:** the kaikki.org Greek JSONL (Wiktionary, CC BY-SA) is downloaded once, with the learner's OK, into `.cache/greek-coach/` (gitignored). The importer reads a small index built from it; the app never needs it.
- **Verb pack:** `content/open/open-verbs-a1a2` is generated by `scripts/build_verb_pack.py`. The sentences are original; the forms come from Wiktionary's conjugation tables.
- **Answer typing:** the on-screen keyboard follows the standard Greek layout. Latin letters typed on a physical keyboard, pasted, or typed on a phone become Greek as they arrive, and `;` before a vowel adds the accent.
- **Tests never see private content:** the test fixture limits content to `content/open/`.
- **New endpoints:**
  - `POST /api/lookup`, `POST /api/flag` and `POST /api/reload`, the last for the coach after writing a pack;
  - `GET /packs/<id>/audio/<file>` and `GET /audio-cache/<pack>/<item>`, both with path traversal blocked.
- **JSON Schemas** for agents: `greek-coach schema` writes them to `schemas/`.
- **`table_fill` waited for phase 5**, as the phase-3 prompt allows (built in phase 5, §4.7).

Phase 4 additions (2026-11-16):
- **The coach changes things through files.** The app takes them in on start, on `/api/reload` and on `/api/home`:
  - a feedback file marks a submission as done;
  - `resolved-flags.json` closes flags.

  `report` stays read-only.
- **Coach packs.** One long-lived pack per purpose in `learner/generated/` (`coach-practice`, `coach-capture`, `coach-writing`, `coach-tutor`). Each run adds `items/<date>-<what>.json`, with item ids that start with the date.
- **Rebuilt textbook items** go into the private pack as `items/rebuilt-<unit>.json`. The importer only replaces `vocab-*.json`, so a re-import keeps them.
- **Writing and speaking in the session.**
  - Once a week (no submission in 7 days, a budget of at least 10 minutes, not on a day back after a gap), the exam-task slot holds a `write` card, counted as 6 minutes.
  - On another day it holds a `speak` card, counted as 2 minutes.
  - Both can be skipped; a skipped card comes back the next day.
- **Coach items first.** They come first in the verb and task segments as well as in new words, so a check-in shows in the next session.
- **After 3 or more days away,** the first session back caps reviews at 15 and new words at 3. The coach can also shrink the next sessions with `restart` in `message.json`.
- **Recordings.** They are uploaded as the raw request body (`POST /api/recording`), so no multipart dependency is needed. They are saved as `recordings/<submission-id>.<ext>` and served from `/recordings/<file>`, with path traversal blocked.
- **Transcription:** faster-whisper `small` (about 0.5 GB, int8 on CPU), in the optional `speech` group, with the model cached in `.cache/greek-coach/whisper/`. Transcripts go to `recordings/<id>.json`.
  - The group pins `av>=16,<17`: faster-whisper 1.2 crashes with av 17 and later (`metadata_errors`).
  - Tested on a 17-second recording made with the offline Greek voice. The transcript kept the learner's errors (`σε το πάρκο`, `Χθες πηγαίνω`) and misheard only a place name.
- **Scheduled runs:**
  - `greek-coach run <skill>` runs `claude -p` with a fixed tool allow-list (or `codex exec --full-auto`), writes its output to `learner/logs/runs/`, and always appends to `coach/runs.log`;
  - `greek-coach schedule add|list|remove` writes the OS entry (Windows `schtasks` with `pythonw`, launchd, cron) and `coach/schedule.json`;
  - the home screen shows a failed run, or one missing for two periods;
  - the agent is found on PATH or in its installer's default folder (`~/.local/bin`, the npm folder), because a scheduled task's PATH often lacks them;
  - **the command-line agent must be signed in.** On the maintainer's machine `claude -p` answered "Not logged in" although the desktop app is signed in. The run records that line, the home screen shows the failure, and the `daily-prep` skill tells the learner how to sign in once.
- **Exam watch sources** lived in `exams/watch-sources.json` until phase 5 moved them into the blueprints.
- **Writing criteria:** the ΚΕΓ A2 and B1 holistic writing scales, out of 25 with 15 to pass, were verified on 2026-11-16 and summarised in `docs/COACHING.md` §10. The A2-LTR writing criteria were not found; the coach marks those tasks out of 10 and labels the score unverified.
- **New commands:** `greek-coach reload`, so the coach can refresh the running app on any OS, and `greek-coach raw`.
- **Open content:** `open-everyday-a1a2` gained 2 `write` prompts and 2 `speak` cards, so the weekly slot works without a coach.

## 12. Challenges to the design, and what changed

1. **Exam: one fixed B1 target → two blueprints, B1 and A2-LTR, and the data decides.** A2 + history is legally enough for long-term residence. B1's pass rule (60% in every skill) is stricter. From the learner's starting point, A2 comes first on either path. The history and culture content (20% of A2-LTR) is only needed if A2-LTR gets booked, so it is scheduled late.
2. **App/agent split: kept.** It holds up even better than expected, because most exam tasks (about 60% of A2-LTR, and the reading and listening papers of B1) are deterministic selection or short-answer tasks.
3. **Content packs: kept**, with two additions. Private packs can hold `raw/` material that is never shown as exercises, and an exam blueprint is separate data from the packs.
4. **Browser speech alone is not enough for listening.** Pre-generated audio is added, made by the coach with a local engine.
5. **Selection-first exercise design and an on-screen keyboard**, because typing Greek is a barrier the design did not mention.
6. **The old vocabulary is not the textbook's.** The design assumed it mirrored the lessons. It is still useful, but it needs gender enrichment and does not follow the course order.
8. **One button → a course the learner can see and steer (phase 5b).** The single "start" button and pack-order sessions gave no agency and no progression. Learning now follows a curriculum, simple before hard (§5.4), and the learner can see their words, verbs and lessons and choose what to practise.
7. **More agent, same independence.** The design treated the agent as an occasional coach. The maintainer wants to use the subscription fully, so the tutor, daily prep, speaking feedback and watch are added. The rule that the app works without an agent running is unchanged.

## 13. Phase 5 additions (2026-11-16)

- **Mock exams** (`src/greek_coach/mock.py`, migration 0004):
  - The coach defines a mock as `learner/coach/mocks/<id>.json`: a blueprint and, per unit, the items in paper order.
  - The app times each section with the blueprint's minutes, on the server's clock. Answers are saved as drafts, and there is no feedback until hand-in. The learner can go back and change answers within a section.
  - **An interrupted section keeps its clock running, as in the exam** (the maintainer's choice, 2026-11-16). Coming back in time resumes with the time left and the saved answers. Coming back late finds the section closed with what was saved (`time_away`), and the readiness screen says so.
  - On closing, each answered item becomes a normal attempt in a `mock` session, so it feeds readiness and the review schedule.
  - Points follow the blueprint: task points × the share of its questions right; an unanswered item counts as wrong.
  - Items of a mock not yet taken stay out of daily sessions, so the mock is a first sight.
  - `GREEK_COACH_MOCK_SPEED` (development only) makes mock time pass faster, for checking the timing.
- **Speaking in a mock:** one `speak` card per exam part, recorded in the browser. The coach marks each recording with an estimated score on that part's scale, labelled unverified because neither exam publishes its speaking criteria. Without a recording the part is not scored.
- **The plan** (`coach/plan.json`, `src/greek_coach/plan.py`):
  - The report's `plan_inputs` gives the candidate sessions from `watch.json`, the weeks left, the real pace (minutes per week over 4 weeks) against the budget (`profile.minutes × profile.days_per_week`), the hours practised, ΚΕΓ's hour guide and a crude realism hint.
  - `plan_progress` checks planned against done for each past week.
  - The exam screen shows the verdict, the current week and the next four weeks.
  - The daily session's exam-task slot prefers the current plan week's focus units.
- **The exam screen** (`?exam`): both exams side by side, each unit's estimate as a range against the pass line or "not enough evidence", the evidence behind it, coverage, the B1 additions, technique, the plan, the dates and the mocks. The home screen shows one bar per unit of the selected exam.
- **Official A2-LTR papers** (approved 2026-11-16): downloaded into `content/private/official-a2ltr/`, never tracked. They are rebuilt into private items by the `mock-exam` skill.
- **Open content:** `open-b1-bridge` (B1 tasks including `table_fill`, two 150-word writing prompts, two speaking cards and B1 grammar forms). Mis-tagged open items were retagged to the blueprint task ids.

