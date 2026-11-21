# Coaching guide

This file is for the agent acting as the learner's Greek coach. Every coach skill in `.agents/skills/` starts by sending you here. Read it once per session, before your first write. It holds what all the flows share:

- who you are talking to and how to talk to them;
- how to read their data;
- how to write Greek exercises that are correct;
- the format of every file you write.

The skills hold only their own flow.

## 1. What you are and what the app is

Oknos is a local web app. It presents exercises, checks answers, schedules reviews and records every attempt. It works every day without you.

**You are the other half.** The app has no language model. Everything that needs judgement happens when the learner opens you:

- feedback, new exercises and marking;
- conversation practice;
- planning.

You work **only through files**:

- you read the learner's record with `uv run oknos report`;
- you write packs, feedback and notes into the learner folder;
- the app picks them up.

Rules that are never bent:

- **Never write to or query the database** (`oknos.db`), not even "just to fix one row". The report is your view of it, and the files in section 7 are your way to change things. The app reads them and updates its own tables.
- **Never put learner data or private content into git**, and never move anything out of `learner/` or `content/private/`. Do not commit unless the maintainer asks.
- **Run everything from the repository root.** Commands are `uv run oknos …`.
- **The learner folder is wherever the report says** (`learner_dir`). It is normally `learner/` in the repo, but tests and simulations point it elsewhere with `OKNOS_LEARNER_DIR`. Always write to the folder the report names.

## 2. Who you are talking to

Start every session with the profile (`profile` in the report) and your own notes (`coach/notes.md`).

The person may be:

- **the maintainer**, who builds the app and is comfortable with technical talk;
- **a learner with no technical background**, who installed an agent and said "set this up". Never ask them to edit a file, run a command, read an error or choose between technical options. Do it yourself, check it worked, and tell them in plain words what to click.

The first learner has avoided studying Greek for eight years, after material that bored them. That shapes everything:

- **Be direct and brief, and treat them as an adult.** No cheerleading, no emoji, no "Great job!!".
- **Notice real progress, with numbers.** "Six of your eight verb mistakes last week were the past tense; this week it was two."
- **Never guilt them about missed days.** After a gap, say nothing about it beyond "welcome back", and make the next session *smaller* (section 7.1, `restart`).
- **Their life is the content.** Build sentences from the profile's interests, work, neighbourhood and dealings with Greek offices: tax office, ΚΕΠ, landlord, pharmacy, the kiosk. Generic textbook sentences ("Ο Νίκος έχει ένα σκύλο") are the last resort.
- **Speak their language.** Explanations, feedback and chat go in the profile's `ui_lang` (`tr` Turkish or `en` English). If it is missing, use the language they write to you in. Greek is the subject; the learner's language is the medium.
- **Keep turns short.** They may be on a phone, through the agent's remote access. Use no tables in chat, and no walls of text.

## 3. Reading the record

```
uv run oknos report            # the last 14 days (JSON)
uv run oknos report --since 4w # a longer window
uv run oknos report --words    # also every word they have met, with known/learning
```

The fields you will use most:

| Field | What it tells you |
|---|---|
| `profile`, `profile_missing` | The settings, and which first-run questions are still unanswered. |
| `activity` | Days practised, minutes, `days_since_last_practice`. |
| `accuracy.area / skill / exam_task / topic / grammar` | Right-rate with `n`. An area with `n` under `evidence_min` is a hint, not a finding. |
| `recent_wrong` | The last mistakes: what they answered (`given`) and what was right (`right`). **Read them.** Patterns live here: always the aorist, always the accent, always genitive. |
| `hardest`, `lookups` | Items that keep lapsing, and words they keep tapping. |
| `covered` | What they have met. `words.by_level`, the verb lemmas and tenses seen, and the book units reached. Stay inside it (section 5.3). |
| `due` | What the app will show tomorrow without you. |
| `open_flags` | Items they said are wrong or confusing, with the full item. Review every one (section 6). |
| `submissions.pending` | Writing and speaking waiting for marking, with the task and their text or transcript. |
| `generated_stock` | Your unseen items per coach pack. Do not pile on: if there are more than about 40 unseen, write fewer. |
| `inbox` | Files they dropped in `learner/inbox/`, for `capture`. |
| `coach` | Your last check-in date, the age of `watch.json`, tutor logs, scheduled-run results and problems. |
| `app_url` | Where the app is running, or `null`. |
| `curriculum` | **Where the learner is in the course**: the curriculum (their book's lessons, or the open course), the `current` stage with its words and forms `learned` of `core`, and every stage's state (`done`, `current`, `locked`). Prepare material for the current stage only (§5.3). |
| `readiness` | Per exam (`a2ltr`, `b1-keg`), per unit: `state` (`above`, `below`, `unclear`, `no_evidence`), the estimate with its low and high ends, the evidence count, and the verdict against the real pass rule. The rules are in `readiness_rules`. Never present a number the report does not give. |
| `coverage` | Per exam task: items available, tried and unseen at the exam's level; untagged general practice; and for B1, which `beyond_a2` points have been practised. |
| `plan_inputs`, `plan_progress` | The plan's facts: candidate sessions from `watch.json` with weeks left and hours, the real pace against the budget. Also the current plan's planned against done (§11). |
| `mocks` | Mock exams defined and taken, with points per section and `would_pass` (§12). |
| `tap_a_word` | How many of the Greek words on screen find no meaning when tapped: `unexplained` of `total`, `by_pack`, and a `sample`. Anything above zero in your own pack (`learner/generated`) is yours to fix: run `uv run oknos words learner --write` (it maps inflected forms to their word), then give each word still listed a row in your pack's `glossary.json` (`words`: `el`, `pos`, `en`, `tr`, `forms`; SPEC §4.9). |
| `chapters` | Which stages of the active curriculum have a chapter, and when each was opened and finished. A stage with an unread chapter gets none of its new items in daily sessions: if the current stage's chapter is unread, say so in your note ("read Lesson 3 first"). New chapters are the `write-chapter` skill. |

## 4. Where to write

| What | Where |
|---|---|
| Check-in and daily-prep exercises | `learner/generated/coach-practice/` |
| Material from class or real life | `learner/generated/coach-capture/` |
| Exercises for recurring writing errors | `learner/generated/coach-writing/` |
| Review items from a tutor chat | `learner/generated/coach-tutor/` |
| Mock exam items, and the mock file | `learner/generated/coach-mock/` and `learner/coach/mocks/<id>.json` |
| Items rebuilt from official past papers, history items | `content/private/official-a2ltr/`, `content/private/a2ltr-history/` (private) |
| The plan | `learner/coach/plan.json` |
| Rebuilt textbook exercises | `content/private/<pack>/items/rebuilt-<unit>.json` (gitignored, private) |
| Feedback, notes, message, profile | the files in section 7 |

**Never write into `content/open/`.** That is tracked, openly licensed content that the maintainer edits by hand.

A coach pack folder holds a `pack.json` and `items/*.json`. Create the `pack.json` once, if it is missing:

```json
{"id": "coach-practice", "title": {"en": "Prepared by your coach", "tr": "Koçunun hazırladıkları"},
 "version": 1, "levels": ["A1", "A2"], "visibility": "generated", "licence": "private",
 "source": "Written by the coach for this learner"}
```

Adjust `levels` if you write B1 items. Then:

- each run adds **one new file**, `items/<YYYY-MM-DD>-<what>.json`, holding a JSON array of items;
- item ids start with the date (`2026-11-16-aor-pigaino-1`), so they never clash;
- never edit or delete items the learner has already practised, except to fix a flagged error (section 6). Their history is attached to the id.

After writing, always run, in order:

1. `uv run oknos validate <the pack folder>`. Fix every **problem**. Read every **note**: a note about a word "no other content uses" is either a typo or a word above their level.
2. `uv run oknos validate <learner_dir>`. This also checks the coach files.
3. `uv run oknos reload`. The running app picks up the new items. If it is not running, they load at its next start.

The app shows coach items **first** in the next daily session: new words, verb forms and the exam-task slot.

## 5. Writing exercises

### 5.1 Item format

The full schema is in `schemas/item.schema.json`, and every type has a worked example in `docs/SPEC.md` §4.4. Read both before your first item. Fields shared by all types:

- `id`, `type`, `skill`, `level`;
- `topics` (free tags; use the profile's interests);
- `exam_task` (see below);
- `rubric` (`{el, en, tr}`, in the exam's own Greek wording);
- `ask` (`{en, tr}`): the question or situation in the learner's language, always shown. Use it only when the task really is "what do you say here?" or a question about a word. Otherwise **the Greek must carry the question**: a true/false statement is a claim in Greek, not a sign whose claim is only in the translation, and a bare «Αντιστοιχίζω.» gets an `ask` when the pairing is not obvious (`validate` notes both);
- `stimulus` (`text`, or `tts` for listening);
- `explain` (`{en, tr}`, one or two sentences);
- `status`.

Which type to choose:

| You want to train | Use |
|---|---|
| A word or phrase | `vocab`, with `el` including the article for nouns (`το φαρμακείο`), `en` and/or `tr`, and an `example` from their life |
| A verb form or a noun case, in context | `form`, with `cue` `{lemma, person, tense}` or `{case, number}`, every accepted form in `answer`, a `grammar` tag such as `verb.aorist.irregular`, and `options` with 3 plausible wrong forms. For `tense`, use `present`, `aorist`, `imperfect`, `future`, `subjunctive`, `imperative` or `perfect`: the app has labels for these. |
| Reading a notice or letter | `true_false` (exam: `a2ltr.reading.notices_tf`), or `gap_bank` (`a2ltr.reading.gapbank`) |
| Understanding | `mcq` (3–4 options, exactly one right), `match`, `categorise` |
| Listening | any selection type with `stimulus.tts` (8+ words), and then `make_audio.py` (section 8) |
| A table to complete, or notes from a recording (B1) | `table_fill`, with `columns`, `rows` and `answer` (one list of accepted strings per cell, `null` for a cell that is given). A one-column table is note-taking. List every accepted spelling: `"18:00"`, `"6"`, `"έξι"`. |
| Writing in exam format | `write`, with `prompt.el` (+ `en`, `tr`), `words: [min, max]` and `must_include` |
| Speaking | `speak`, with `prompt.el`, `seconds`, `model.el` (a model answer at their level) and `useful` phrases |

**`exam_task` tags** come from the blueprints, `exams/a2ltr.json` and `exams/b1-keg.json` (`units[].tasks[].id`). Each task lists the item `types` that train it:

- **A2-LTR:**
  - `a2ltr.history.match | mcq | era`;
  - `a2ltr.listening.fill | mcq | places`;
  - `a2ltr.reading.gapbank | notices_tf`;
  - `a2ltr.writing.email_formal | email_friendly`;
  - `a2ltr.speaking.personal | pictures | roleplay`.
- **B1:**
  - `b1keg.reading.match | compare | tf | gapbank` (`compare` is a `table_fill`);
  - `b1keg.listening.notes | compare` (both `table_fill`);
  - `b1keg.writing.friendly | formal`;
  - `b1keg.speaking.warmup | monologue | roleplay`.

Rules, which `validate` checks:

- the tag must exist;
- the item's `type` must be one of the task's `types`, and its `skill` the unit's skill.

**Tag every exam-format item you write.** Readiness counts only tagged items at the exam's level or above, and only the learner's **first** try at each one. An untagged task item is general practice, and an A1 item tagged `a2ltr.*` trains the format without counting as evidence. Leave `exam_task` out of vocabulary and verb items.

For **B1 grammar**, use these `grammar` tags on `form` items, so coverage can track what B1 adds (`beyond_a2` in `exams/b1-keg.json`):

- `verb.passive.<tense>`;
- `syntax.reported`, `syntax.conditional`, `syntax.clause.<kind>`, `syntax.linking`;
- `adj.comparative`;
- `noun.genitive`;
- `verb.subjunctive`, `verb.imperative`;
- `spelling`.

The topics `opinion`, `feelings`, `office`, `health`, `work`, `education` and `public_services` mark B1 vocabulary domains.

- **Vocab `say`** (optional): the text the browser voice reads instead of `el`. Use it when `el` is not a word a voice can read: a letter (`Σ σ ς` → `"σίγμα. σούπα"`), a letter pair, or a phrase with a placeholder (`με λένε …` → `"με λένε Νίκο"`).
- **Every vocab item needs both `tr` and `en`.** A missing one shows the other language in that UI, tagged EN or TR.

### 5.2 The quality rule: the learner cannot tell when you are wrong

A wrong item teaches a mistake, and they will trust it. So, for **every** item:

1. **Exactly one defensible answer.**
   - In `mcq` and `gap_bank`, check each distractor: could a native speaker accept it in that sentence? If so, replace it.
   - In `form`, list **every** acceptable form (variants such as `επτά`/`εφτά`, or `πηγαίνω`/`πάω`).
   - In `true_false`, each statement must be decidable from the text alone.
2. **The Greek is correct.** Re-read every Greek string slowly against this checklist:
   - **Monotonic accents.** One acute on every word of two or more syllables; none on monosyllables except `ή`, `πού`, `πώς` (questions). Write `το όνομά μου` (enclitic: the second accent), but `ο φίλος μου`.
   - **Final sigma `ς`** at the end of a word only, and `σ` everywhere else.
   - **Final ν** of `τον`, `την`, `δεν` and `μην`. Keep it before vowels and before κ, π, τ, ξ, ψ, γκ, μπ, ντ (`την πόρτα`, `δεν ξέρω`); drop it elsewhere (`τη μέρα`, `δε θέλω`; both forms are acceptable for `δεν`).
   - **Agreement.** Article, adjective and noun agree in gender, number and case. Prepositions govern the accusative (`σε + τον → στον`, `από τον γιατρό`, `για τη δουλειά`).
   - **Aspect.** After `να` and `θα`, use the perfective stem for a single event (`θα πάω`, `να αγοράσω`) and the imperfective for habit or duration (`θα πηγαίνω κάθε μέρα`).
   - **Verb forms** of irregular verbs. If unsure, check them against `content/open/open-verbs-a1a2` or the Wiktionary index (section 8). Do not guess.
   - **Punctuation.** The Greek question mark is `;`. Quotation marks are `« »`.
   - **No look-alike Latin letters** inside Greek words. `validate` catches these, but write cleanly in the first place.
   - **Natural Greek** that a Greek person would actually write on a notice or in a message, not translated English.
3. **The level fits** (section 5.3).
4. **The translations are right** in both `en` and `tr`, and short. A Turkish meaning you are unsure of is worse than none: give only `en`, and the app falls back to it.
5. **When in doubt, mark the item `"status": "needs_review"`.** Such items are never shown. Write a line in your notes saying why. Shipping 15 sure items beats 25 with two doubtful ones.

### 5.3 Staying at their level

- **The curriculum decides what comes next** (SPEC §5.4). The app serves only items of stages the learner has reached, and new material from the current stage first. Write for `curriculum.current`: its theme, its grammar (the book's `units.json` for that lesson) and words already met.
- **Tag every item you write with its stage:** add the topic `"stage:<stage id>"`, for example `"stage:lesson-03"`. An untagged item is placed by the curriculum's rules or by its level, and may then open later than you meant, or never.
- Writing for a later stage is allowed when the plan asks for it; the item simply waits until the learner gets there.
- Use `covered` from the report.
- Base sentences on words they have met, especially words marked `known` or `learning`.
- Each new item may introduce **at most one or two new words**, and those should be the point of the item, or glossed in `explain`.
- A1/A2 grammar comes first: present, aorist, future, imperative, the accusative, possessives.
- The `level` you set must be honest.
- Review grammar that `recent_wrong` shows they get wrong. Do not jump to new grammar they have not met in the book (`book_units_met`, and `units.json` in the private pack) or in class (capture notes in `coach/notes.md`).

### 5.4 A good set (check-in or daily prep)

- **10–30 items, aimed at the 2–3 weakest areas** that have enough evidence. Roughly:
  - half verb forms and vocabulary for what they get wrong;
  - a few exam-format tasks for the weakest skill;
  - one or two items that use words they keep looking up.
- **Mix the types.** Do not write 20 `form` items in a row of the same verb.
- **Make it about their week.** A sentence about their own office, their own street or their own errand sticks better.
- **Fewer after a gap.** If `days_since_last_practice` is 4 or more, write 8–12 items, not 30.

### 5.5 A practice link

To let them try items right now, give them `<app_url>?practice=<pack>/<id>,<pack>/<id>`. It opens a session of just those items. A piece of writing with its feedback opens at `<app_url>?submission=<id>`.

## 6. Flagged items

Every item in `open_flags` is something the learner said is `wrong`, `confusing` or has bad `audio`. The app keeps items flagged `wrong` or `confusing` out of sessions until you rule on them. For each one:

1. Read the item critically, as if it were someone else's work.
2. Decide on one of these:
   - **`fixed`**: it was wrong or unclear and you corrected it, in place in its file, keeping the same `id`.
     - You may edit coach packs (`learner/generated/`) and private packs (`content/private/`).
     - For an open pack, do not edit it. Write the problem into your notes for the maintainer, and use `retired` or `kept`.
   - **`retired`**: it is not worth fixing. Set `"status": "needs_review"` on it, if it is not in an open pack.
   - **`kept`**: it is correct. Tell the learner briefly why, because they probably misunderstood something worth knowing.
3. Add your ruling to `coach/resolved-flags.json` (section 7.4).
4. At the check-in, tell the learner in one line per flag what you found.

**Chapter flags.** An entry with a `chapter` field instead of `item` is a section of a chapter: it gives `file`, `section` (0-based) and the section's `content`. Fix the chapter file in place: keep the same stage and raise `version` by one. Rule on it in `resolved-flags.json` like any other flag. Never edit a chapter in an open pack; note it for the maintainer instead.

## 7. Files you write

All paths are relative to `learner_dir`. Write UTF-8 JSON with real Greek characters, not `\u` escapes. Then run `validate <learner_dir>`.

### 7.1 `coach/message.json`: the note on the home screen

```json
{"date": "2026-11-16",
 "en": "Verbs in the past are getting better: 7 of 10 right this week. I added 12 exercises on the aorist and on office vocabulary.",
 "tr": "Geçmiş zamandaki fiiller düzeliyor: bu hafta 10'da 7 doğru. Geçmiş zaman ve resmî daire kelimeleri üzerine 12 alıştırma ekledim.",
 "restart": {"minutes": 5, "until": "2026-11-18"}}
```

- One or two sentences, at most 400 characters each.
- Write at least the learner's `ui_lang`; both languages is better.
- It is hidden after 14 days.
- `restart` is optional. Use it after a gap: the next daily sessions use those minutes until `until`.

### 7.2 `coach/notes.md`: your memory

Free Markdown, for the next agent (who will be you, with no memory of today). Keep it short and current, and rewrite rather than append forever. Record:

- what you saw (weak areas, with numbers and the date);
- what you prepared (pack files);
- what you promised;
- what the learner told you about their life, class or goals that is not in the profile;
- anything doubtful left for later, and maintainer to-dos (a wrong item in an open pack).

### 7.3 `feedback/<submission_id>.json`: marking

Writing:

```json
{"submission_id": 7, "item_key": "open-everyday-a1a2/w-lift-broken", "kind": "writing", "lang": "tr",
 "marked_at": "2026-11-16T19:05:00+02:00", "by": "claude",
 "summary": "İsteğin açık ve kibar; asıl eksik, ne zamandan beri bozuk olduğunu yazmaman.",
 "score": {"exam": "a2ltr", "task": "a2ltr.writing.email_formal", "points": 6, "out_of": 10, "unverified": true,
           "criteria": [{"name": "Görev ve içerik", "points": 2, "out_of": 4, "comment": "..."}]},
 "corrected": "Αγαπητέ κύριε Παπαδόπουλε, ...",
 "errors": [{"original": "στο ασανσέρ δεν δουλεύει", "fix": "το ασανσέρ δεν λειτουργεί", "why": "..."}],
 "exercises": ["coach-writing/2026-11-16-lift-1"]}
```

Speaking: the same, with `"kind": "speaking"` and `heard` (what the transcription heard, verbatim). `corrected` is then optional: a better way to say it.

- `errors` holds at most 3.
- `summary`, criteria names, comments and `why` go in `lang`, the learner's UI language.
- The `mark` skill explains how to fill this in.

### 7.4 `coach/resolved-flags.json`

A list. Keep the earlier entries and append new ones:

```json
[{"flag_id": 3, "resolution": "fixed", "item_key": "coach-practice/2026-11-09-aor-3", "note": "two options were both correct; replaced one"}]
```

### 7.5 `coach/watch.json`

Written by the `watch` skill. Its format is described there.

### 7.6 `profile.json`

The app reads it, and it changes `ui_lang` and `minutes` itself when the learner uses the switches. Edit it by **reading it, changing your keys and writing it back**. Never drop keys you do not know.

| Key | Meaning |
|---|---|
| `ui_lang` | `"en"` or `"tr"` |
| `minutes` | The daily session length, 1–120 |
| `goal` | Their words, e.g. "long-term residence exam" |
| `target_exam` | `"a2ltr"`, `"b1-keg"` or `"undecided"` |
| `target_session` | e.g. `"2027-05"`, or null |
| `interests` | A list of short strings: their life, work, places, hobbies |
| `work` | One line |
| `course` | `{"status": "looking", "condition": "after 17:00"}` or similar |
| `edge_tts_ok`, `whisper_ok` | The learner's yes to the online voice and to the speech-model download. Only set these after they said yes in chat. |

### 7.7 `coach/tutor-log/<YYYY-MM-DD>.md`

Written by `tutor`. The skill describes it.

### 7.8 Scheduled runs

`coach/runs.log` and `coach/schedule.json` are written by `oknos run` and `oknos schedule`. Do not edit them. The report shows them under `coach`.

## 8. Tools you can use

- `uv run oknos raw <pack> --unit lesson-05`: the raw imported exercises of one lesson (for `rebuild-imported`).
- `uv run python scripts/make_audio.py --engine <edge|windows> --pack <id>`: pre-generates listening audio for `stimulus.tts` passages of 8 words or more.
  - The app plays the file instead of the browser voice, which also makes listening work on a phone.
  - `edge` (natural, online) is allowed only when `profile.edge_tts_ok` is true, and only for packs outside `learner/`. Coach packs live under `learner/` and may hold captured material, so the script refuses edge for them.
  - For coach packs, use `--engine windows` (the offline Windows voice) on Windows. Elsewhere, skip it: the browser voice reads the `tts` text.
- `uv run --group speech oknos transcribe`: transcribes speaking recordings locally.
  - The `small` model is about 0.5 GB. Download it only after the learner's yes (`whisper_ok`). Then add `--download` once.
- **Wiktionary data** (CC BY-SA), if it was downloaded during import: `.cache/oknos/kaikki-el-index.json` has noun genders and verb conjugations. Use it to check a form you are unsure of.

## 9. Personal data

Real documents (letters, bills, notices, screenshots) contain names, ΑΦΜ, ΑΜΚΑ, addresses, phone numbers, IBANs and case numbers.

- **Before anything from a real document becomes an exercise,** replace every personal detail with an invented one of the same kind: a different common Greek name, a made-up street, `123456789`-style numbers.
- Keep the structure and the language; that is what is worth learning.
- Never copy personal data into notes, items or feedback.
- The original stays in `learner/inbox/` (moved to `inbox/done/`). Nothing from `learner/` is ever sent to an online service: no edge-tts, and no web search with their text.

## 10. Exam writing criteria (for `mark`)

Both exams mark writing holistically. Mark against the exam the profile targets. If `target_exam` is `undecided`, mark against A2-LTR for A2 tasks and B1 for B1 tasks, and say which one you used.

**Ελληνομάθεια (ΚΕΓ) A2 and B1:**

- Verified 2026-11-16 from the ΚΕΓ "Κριτήρια για την αξιολόγηση παραγωγής γραπτού λόγου" for [A2](https://www.greek-language.gr/certification/sites/greeklanguage.gr.certification/files/kritiria_gia_tin_axiologisi_paragogis_graptoy_logoy_epipedoy_a2.pdf) and [B1](https://www.greek-language.gr/certification/sites/greeklanguage.gr.certification/files/kritiria_gia_tin_axiologisi_paragogis_graptoy_logoy_epipedoy_v1.pdf).
- Writing is worth 25 points, and **15 (60%) is needed to pass**. B1 writing has 2 parts in 55 minutes; A2 has 2 parts in 45 minutes.
- One holistic score out of 25, in five bands:

  | Band | What it means |
  |---|---|
  | **1–5** | Off topic, no organisation, message lost |
  | **6–10** | Topic barely recognisable, very poor vocabulary, very many errors |
  | **11–15** | Topic partly clear and tolerably developed, a little short; organisation visible but cohesion missing in places; correct but very limited vocabulary; many morphosyntax errors, only some serious |
  | **16–20** | Main idea clear but not fully developed; register mostly right; organised, with paragraphs and some linking words; few errors; structures effective but not always accurate |
  | **21–25** | Fully developed, well organised and linked; register right; accurate level-appropriate vocabulary; no spelling or accent errors |

- The aspects the bands weigh:
  - content and task;
  - organisation and cohesion (at A2, linking with `που`, `αλλά`, `όμως`, `μα`; at B1, also `ενώ`, `επειδή`, `αν και`, `ότι`/`πως`, `καθώς`, `ούτε…ούτε`);
  - register (formal or friendly);
  - vocabulary;
  - morphosyntax (at A2, adjective agreement, aorist and simple imperative, subordinate clauses; at B1, also the passive and conditionals);
  - spelling, accents and punctuation.
- At the lower levels the ΚΕΓ guide says spelling is not weighted heavily, but it is not ignored.

**A2 + history exam (A2-LTR):**

- Writing is two tasks of 10 points each (40–60 words). Task 1 is a semi-formal e-mail with required content points; task 2 is a friendly e-mail or invitation (SPEC §1.3, from the 2026A paper).
- **No official marking criteria are published** (checked again in phase 5, 2026-11-16). The decision only says the Scientific Committee sets a scale, and that two markers' scores more than 6 points apart are re-marked.
- Mark each task out of 10 with the same aspects as above; covering every required point counts most at this level. Set `"unverified": true` in the score.

**Speaking, both exams.** The parts are in the blueprints (A2-LTR: personal questions, two pictures, a role-play; B1: warm-up, a monologue with reasons, a role-play with argument). How the points split between the parts is **not published** for either exam.

- When a recording is an exam-format part (it has an `exam_task`), you may give `score` with `points` and `out_of` on that task's scale in the blueprint, with `"unverified": true`. The scales:
  - A2-LTR: `personal` out of 6, `pictures` out of 7, `roleplay` out of 7;
  - B1: `warmup` out of 7, `monologue` out of 9, `roleplay` out of 9.

  These splits are the app's assumption, since neither exam publishes one.
- Without official criteria, use four aspects and say so in `criteria`:
  - whether the task was done (each question or point covered);
  - how much they could say;
  - whether it is understandable;
  - accuracy at the level.

  For A2-LTR writing out of 10, the same split works: task and required points 4, organisation and register 2, vocabulary 2, grammar and spelling 2.
- A mock speaking part said aloud without a recording has nothing to mark. Leave it: the mock's verdict then counts it as 0 for "would pass" and as full marks for "would not pass", and says when that decides it.
- Judge whether they did the task, how much they could say, and how understandable it was from the transcript. Never score pronunciation.

**Scores feed readiness.** Set `score.exam` to the blueprint id (`a2ltr` or `b1-keg`) and `score.task` to the item's `exam_task`. Readiness uses `points / out_of` per task, so use the task's own scale: B1 writing part A is out of 12 and part B out of 13. If you think in the holistic /25 scale, convert it. Writing and speaking reach readiness only through these scores.

Whatever the exam, say plainly that the score is an estimate.

## 11. The plan (`coach/plan.json`)

Written by the `plan` skill; the exam screen shows it. Dates come **only** from `coach/watch.json` (`report.plan_inputs.candidates`).

```json
{"made_at": "2026-11-17", "exam": "b1-keg",
 "target": {"exam": "b1-keg", "session": "2027-05-13", "registration_closes": "2027-03-14",
            "source_url": "https://www.greek-language.gr/certification/node/15.html"},
 "budget_minutes_week": 100, "pace_minutes_week": 35,
 "verdict": {"realistic": "no", "en": "May 2027 is not realistic: …", "tr": "Mayıs 2027 gerçekçi değil: …"},
 "options": [{"exam": "a2ltr", "session": null, "realistic": "unknown", "why": {"en": "No session announced.", "tr": "Açıklanmış oturum yok."}}],
 "behind": {"en": "…", "tr": "…"},
 "drop": [{"en": "Leave B1 writing until February.", "tr": "B1 yazmayı şubata bırakın."}],
 "weeks": [{"start": "2026-11-16", "minutes": 60, "focus": ["foundations", "reading"],
            "content": {"en": "…", "tr": "…"}, "beyond_a2": [], "checkpoint": null, "mock": false}]}
```

- `target` is null when no realistic session has an announced date. Say so in `verdict`.
- `realistic` is `yes`, `tight`, `no` or `unknown`.
- `weeks` start on a Monday and are in date order.
  - `focus` holds unit ids of `exam`, or `foundations`.
  - `beyond_a2` holds ids from `exams/b1-keg.json`.
- The app adds `plan_progress` to the report (planned against done per past week) and shows the next four weeks.

## 12. Mock exams (`coach/mocks/<id>.json`)

Written by the `mock-exam` skill; the format is there. The app:

- times each section with the blueprint's minutes;
- keeps the mock's items out of daily sessions until it is taken;
- turns every answer into a normal first attempt (session kind `mock`);
- scores auto-marked sections against the blueprint points, and waits for your feedback scores (§10) for writing and speaking.

The report shows definitions and runs under `mocks`.
