# Agent Instructions

Oknos (Ὄκνος, the figure of sloth in Greek myth: `docs/brand/README.md`; called Greek Coach until 2026-11-21) is an open-source, local-first Greek learning app that is installed, operated and extended by a coding agent (Claude Code, Codex, or similar). This file is the canonical instruction file for every agent harness; `CLAUDE.md` only imports it.

## Read first

1. `docs/DESIGN.md` — what we are building, for whom, and the decisions already made.
2. `docs/prompts/README.md` — the phased build plan. Check which phase is current before starting work.
3. `docs/SPEC.md` — once it exists (it is produced in phase 1), it overrides `DESIGN.md` where they differ.

## Quick start

The commands used most, from the repo root (all of them are listed under **Commands** below):

```
uv run oknos start      # start the app in the background and open the browser (http://127.0.0.1:8642)
uv run oknos stop       # stop it
uv run oknos stop; uv run oknos start   # restart: needed after changes to code (src/, web/)
uv run oknos reload     # take in new or edited content (packs, chapters, coach files) without a restart
uv run oknos health     # check the install
uv run pytest                 # run the tests
```

## Current state

Phases 1–5 and 5b are built and committed. Phase 5b is a curriculum the learner progresses through, plus screens to see and choose what to practise. Phase 5c (the book: a chapter to read before each stage's practice) is built. Phase 5d (every tappable word has a meaning; no question hidden behind "Translate") is built. **All 26 stages of the book curriculum have a chapter**: the intro, lessons 1–24 and the B1 bridge. Each was drafted by Sonnet (lessons 1–2 by Opus), reviewed by Opus, and validated. `docs/SPEC.md` is agreed. Its exam strategy is to track Ελληνομάθεια B1 and the A2 + history exam side by side and let readiness decide. Exam facts were re-checked against the official sources on 2026-11-16.

What works now:
- **Stack:** uv, FastAPI and SQLite (`learner/oknos.db`, migrations `0001`–`0006`), with a no-build front end in `web/`. UI in English and Turkish.
- **Progression (phase 5b, SPEC §5.4).**
  - A curriculum orders everything: the maintainer's book lessons (`content/private/greek-helper/curriculum.json`: intro/reading, lessons 1–24, B1) or the open course (`curricula/open-a1-b1.json`).
  - Daily sessions serve only reached stages, the current one first. A plan of today's that holds cards of a stage not reached (made before the curriculum, or under another one) is replaced, not resumed.
  - A stage is done at 80% learned, or with a passed "test me" check, and stays done.
  - Coach items carry the topic `stage:<id>`.
  - `src/oknos/curriculum.py`.
- **The book: read first, then practise (phase 5c, SPEC §4.8, `docs/LESSONS.md`).**
  - A stage can have a **chapter** (`<pack>/lessons/<stage>.json`, `src/oknos/chapters.py`): typed blocks (prose, dialogue, table, examples, words, tip, check) in a fixed section order, with explanations in Turkish and English.
  - The reader (`?lesson=<stage>`) plays the dialogues, makes every word tappable, and runs the inline "try it" checks. These are a `lesson` session: they train the review schedule but are never exam evidence. It ends with "Done reading — practise this chapter".
  - **Teach before testing:** a stage's new items enter daily sessions only once its chapter is read (or its check passed). Reviews never wait. A stage without a chapter behaves as before.
  - A word never seen gets an ungraded **learn card** (meaning, and an example from a chapter) before its first test.
  - The chapter's `words` block places those words in its stage.
  - The home screen's first button is the one next action: read the current chapter, or today's session. Light, dark and system themes.
  - **The home screen** (2026-11-22): a Today card (the greeting, the one next action, the new words waiting, with their pictures) beside the current lesson (its ring and rope, its words with pictures, read and practise), then small tiles for the coach (the donkey), the coming dates and a short "would you pass today?"; the progress fold stays below. `/api/home` carries `words` (`session.home_words`).
  - **Pictures** (phase 9, started 2026-11-22, `docs/brand/IMAGES.md`): words have pictures made by an image model through Codex, reviewed, and taken in as WebP into `content/open/open-pictures/` (`scripts/pictures.py`). A picture belongs to a word, so any pack's item with that word shows it: on the learn card, after an answer, and in "pick the picture" (`el_picture`). By 2026-11-24: 955 pictures, 102 for open words and 853 for nouns of the maintainer's book (the 2026-11-23 batches took the book's lessons 1–23 and the A1 words that open at lesson 3, then the windows of 2026-11-23 and 24 about 500 more of its nouns: about 1 in 20 was rejected and asked for once more; the last four, the vasilopita, the opal, the beam δοκάρι and the stepping stone, came on 2026-11-24 from prompts that say what the picture must not look like, two variants each; the same day ο/η μηχανικός, drawn as a car mechanic, was redrawn as an engineer, its meaning in the book); 74 more of the book's words reuse a picture of the same thing spelled another way or named by another word (αβγό → αυγό, φρούτο → φρούτα, χαρτονόμισμα → μετρητά); 87 of the open book's 218 words and 1,015 of the book's words have one.
  - **Scenes of the story** (2026-11-22, `docs/brand/CHARACTERS.md`): the open book's recurring people (Zeynep, Katerina, Giorgos) have a fixed look and a reference sheet, and a scene picture can sit above a chapter's dialogue (`picture`) or a task (`stimulus.pictures`, one or two; two are labelled α and β, as in the A2 exam's "describe and compare two photos"). The pilot was the shopping chapter; now all 12 chapters of the open book have scenes (20 pictures in `content/open/open-book/pictures/`), each with one or two picture questions (true/false, multiple choice) and, where a chapter has two scenes, a two-picture speaking card (`a2ltr.speaking.pictures`; the B1 chapter's is a one-picture monologue, `b1keg.speaking.monologue`).
  - **The voice** (phase 10, 2026-11-22, `docs/VOICE.md`): every Greek text the app speaks is made ahead of time as a clip in `learner/voice/` by the first service in the learner's list (Azure Speech, edge-tts, Google Cloud TTS or OpenAI, with the learner's own keys in `learner/secrets.env`), each dialogue speaker in a voice of their kind; the browser voice reads what has no clip. `oknos voice status|build|sample`; the Voice screen (`?voice`, the speaker icon at the top) hears, compares and orders the services. The maintainer's order: Azure → edge (Athina, Nestoras) → Google.
  - **Published audio is Google's, the maintainer's own is ElevenLabs'** (2026-11-26, `docs/VOICE.md`): every service (Gemini and ElevenLabs included) can make a learner's own clips through `voice.providers`; shipped audio (these clips, the films' `voice/`) only a service whose terms allow publishing (`publishable`: Google's Gemini and Chirp), which `oknos guard` checks from the manifests. The maintainer's lists: `voice.providers` and `podcast.providers` start with ElevenLabs; the shipped clips stay Chirp 3 HD (`scripts/ship_voice.py`, no daily limit) and the films' `voice/` is remade with Gemini (`scripts/film_voice.py`, 100 requests a day).
  - **Shipped clips** (2026-11-22): the open content's 2,206 texts come with clips made by Google Chirp 3 HD (Kore, Orus) in `content/open-voice/` (tracked, CC BY-SA 4.0, about 16 MB in the repo; `scripts/ship_voice.py`, `index.json` lists each clip). The app plays the learner's own clip first, then the shipped one, then the browser voice, so a fresh clone sounds good with no key. `voice build` leaves shipped clips alone unless the learner's first service has other voices (Azure, edge, OpenAI). An open text with no shipped clip (or a clip no text uses) is a note from `oknos validate content/open`, not a failing test; the browser voice reads it until `scripts/ship_voice.py` is run with a Google key.
  - **Films** (2026-11-22, `docs/brand/animations/`): three short painted films of the Oknos myth (motion comics: illustrations drawn through Codex with the cast's reference sheets, a camera move, Greek captions with TR/EN). With sound: one clip per shot, made by `scripts/film_voice.py`: Google's Kore and Orus in `voice/` (tracked, published), the maintainer's Athina and Nestoras in `voice-local/` (not tracked: Azure's free tier gives no right to publish its audio). Under the voice, a quiet background of wind, cicadas and goat bells (`ambience/`, one 30-second loop per film, original and CC BY-SA 4.0, made from numbers by `scripts/film_ambience.py`), with its own off switch.
    - **In the app** (2026-11-23): the server serves `docs/brand/animations/` at `/films/` (`src/oknos/films.py`, one copy, no duplicate in `web/`). The films page (`?films`, `?films=<n>`) is reached from the coach's donkey tile on the home screen and from the Book screen. Film 1 plays once as a welcome the first time a new learner opens the app (nothing answered, no chapter opened): Skip or Escape closes it, and ending or skipping it sets `welcome_film_seen` in `profile.json`; with reduced motion it waits for a tap; `?welcome` shows it again. A film plays in a frame (`film.js ?embed`) in the app's language and theme, with the `voice-local/` clips when that folder is there, else `voice/`; the web font is fetched only outside the app. Without the film files the app has no welcome and the page says the films are not there. Film 2 (Oknos and his wife) is archived on 2026-11-24: its files stay in `docs/brand/animations/`, but the app neither lists nor serves it (`ARCHIVED` in `films.py`).
  - **Podcast lessons** (phase 11, pilot 2026-11-23, `docs/PODCASTS.md`): an episode is a script first (`learner/podcasts/<id>/script.json`: parts, lines in Greek, Turkish or English with speaker and speed, pauses, gaps to repeat), written by the agent with the `podcast` skill from the chapter (then the open book's, then web ideas only), checked and rendered by `oknos podcast check|render` (`src/oknos/podcast.py`): the missing clips through the learner's voice chain (each service now has Turkish and English voices too, e.g. Azure Emel; never edge), joined with ffmpeg (slow lines with `atempo`, silences, one loudness pass) into `episode.mp3` with `episode.json` (parts and lines in time). The Podcast page (`?podcast`, `?podcast=<id>`) plays it: parts to jump to, speed, the position kept on the device, the lock-screen title, the script, a download link; "Listen" on the Book screen and in the reader, a link on the home screen's coach tile when there are episodes. Episodes stay in `learner/`; listening is not exam evidence. The book's lessons 1–24 have episodes in Turkish (the pilot, lesson 1: 12.8 minutes, 4,833 Azure characters; lessons 4–24 written by Opus subagents from the chapters and rendered on 2026-11-24, 12–15 minutes and about 4,000–5,500 characters each); `daily-prep` keeps the podcast a lesson ahead (its step 5a). **Personal episodes** (2026-11-24): a daily (10–20 min) and a weekly (20–30 min) review from the learner's record, written with the `podcast` skill (§3b) from `oknos podcast material daily|weekly` (`src/oknos/podcast_material.py`: due and weak words with meanings and examples, recent mistakes, the current lesson, the words met, the last episodes' `focus`), made by `daily-prep` (step 5b) only when `podcast.personal` in `profile.json` says yes; the home screen's coach tile links today's (`podcast_today`); `oknos podcast prune` keeps the newest 14 daily and 8 weekly and drops the Turkish/English clips only they used. They hold learning content only (no name, no answers quoted as the learner's, no scores). **Cast episodes** (2026-11-25, `docs/PODCASTS.md` "The voices"): after a blind test the maintainer chose Gemini TTS for podcasts, and the same evening, by ear, ElevenLabs v4 over it (`podcast.providers` = elevenlabs, then gemini, then Google Chirp 3 HD; keys `ELEVENLABS_API_KEY` on the Creator plan, its monthly credits a hard cap, and `GEMINI_API_KEY`, paid tier, prepaid credit). Each person of a script gets their own voice (`src/oknos/casting.py`, `casting.json`: Ada, Mert and Katerina fixed, characters by name from a pool per service: ElevenLabs' native Greek voices of their gender and age), the lines between the people a service acts together (ElevenLabs up to ten, Gemini two) are one request, a slowed line carries ElevenLabs' `[slowly]` tag, a host may say Greek inside a Turkish line, and a jingle and stings frame the episode. The enrichment loop is not built yet.
  - **The look** (2026-11-21, `docs/brand/README.md`): every progress bar is a plaited rope, a stage's ring closes as it is learned, the donkey (the agent) sits by the coach's note, the end of a session and an empty screen, and the icons are one line style (no emoji). An empty practice choice says why and leads back.
  - Navigation: every screen has its own URL (`?book`, `?lesson=<stage>`, `?stage=<id>`, `?practise`, `?words`, `?verbs`, `?exam`, `?writing`, `?submission=<id>`, `?mock=<run id>`, `?films`, `?films=<n>`), so the browser's back and forward work. An app bar on every screen links Home · Book · Practise · Words · Verbs · Exam.
  - The **Book** screen (formerly the course map) is the table of contents. Any chapter can be read, also ahead of the lesson, and the reader links to the previous and next chapters.
  - Book chapters (private): `content/private/greek-helper/lessons/`. `outline.json` (26 stages) is approved. All 26 chapters exist, each with a review note in `lessons/review/`. The reviews made 170 Greek fixes and 191 teaching fixes in all, about 7 of each per chapter.
  - **Pilot batch, 2026-11-19:**
    - Sonnet drafting took about 150–190k tokens per chapter, and the Opus review about 140–165k.
    - The review made 4–5 Greek fixes and 5–7 teaching fixes per chapter, against 2–3 Greek fixes in each golden chapter (written by Opus).
    - The errors were in rules and descriptions (final -ν, the vocative, how phone numbers are read, the stress of σπίτι) more than in spelling. The review step is essential.
  - A table cell can be Greek or `{tr, en}`.
  - Writing more is the `write-chapter` skill: Sonnet drafts, Opus reviews.
  - **The open course's book** (tracked, CC BY-SA 4.0, original): `content/open/open-book/`, one chapter for each of the 12 stages of `curricula/open-a1-b1.json`, written 2026-11-20. A story runs through it: Zeynep from Izmir moves to Thessaloniki.
    - `first-words` and `everyday-verbs` are the golden chapters (Opus); the other ten were drafted by Sonnet and reviewed by Opus. Each has a review note in `lessons/review/`. The reviews made 14 Greek fixes and 26 teaching fixes in all, about 1 and 2 per chapter.
    - 398 items: 218 vocab, the rest practice and checks. Its `glossary.json` explains every other word it shows (forms, endings in tables, names); a fresh clone has no unexplained open word.
    - A fresh clone's learner now starts by reading the `reading` chapter.
    - Under a book's curriculum the open book supports it (`curriculum.py`, SPEC §5.4): words the book already has are not served twice, and the rest are extras at the lesson the book curriculum's `follows` maps each open stage to. The maintainer's mapping is in `content/private/greek-helper/curriculum.json`.
    - Tests leave the open book out by default (`tests/conftest.py`): its chapters gate every stage. Tests of the book use the `open_book` / `full_catalog` fixtures (`tests/test_open_book.py`).
- **Exam blueprints** (tracked facts): `exams/a2ltr.json` and `exams/b1-keg.json`.
  - Each has units, tasks, points, minutes, the real pass rule, exam technique (en/tr), official sources and the pages `watch` checks.
  - B1 also lists what it adds over A2 (`beyond_a2`).
  - `exams/watch-sources.json` keeps only the course page.
- **Content.**
  - Five open packs (CC BY-SA 4.0):
    - `open-shared-words-tr`;
    - `open-verbs-a1a2`: 253 verb forms, built by `scripts/build_verb_pack.py`. The standard modern form comes first, not an older variant such as θα ιδεί or ηύρες. Each sentence has a Turkish translation (`scripts/verb_pack_tr.json`);
    - `open-everyday-a1a2`: 23 exam-format tasks, plus 2 writing prompts and 2 speaking cards;
    - `open-b1-bridge`: 15 B1 items, including `table_fill`, 150-word writing, speaking and passive/conditional forms;
    - `open-alphabet`: 67 reading cards (letters, letter pairs, the accent, syllables), with sounds in Turkish and English. A letter card's voice reads its `say` text, the letter's name and an example word ("σίγμα. σούπα"), not "Σ σ ς".

    Every exam-format item is tagged with a blueprint task (`exam_task`), and `validate` checks the tags.
  - Private material (gitignored, under `content/private/`):
    - the maintainer's earlier material in `greek-helper`: 2,648 words, 25 units, and 1,697 raw exercise prompts for the coach to rebuild. All but one of the words now have a Turkish meaning. Those for A2/B1 were drafted by Sonnet on 2026-11-19, unverified; they are in `overlays/tr.json`, so they survive a re-import;
    - the official A2-LTR papers, keys and MP3s for 2022, 2024 and 2026A in `official-a2ltr/papers/`.
  - Coach-written packs go in `learner/generated/` (gitignored).
- **Exercise types:**
  - `vocab`, `form`, `mcq`, `true_false`, `match`, `gap_bank`, `categorise` and `table_fill`, plus listening variants (audio ranges with `start`/`end`). These are checked by the app: accent-tolerant, with an on-screen Greek keyboard.
  - `write` and `speak`. These are saved as submissions and marked by the coach; speaking is recorded in the browser.
- **Study loop.**
  - SM-2 spaced repetition.
  - A daily session sized to the profile's minutes. Coach items come first in every segment; the exam-task slot prefers the plan's focus units this week.
  - Once a week the session holds a writing prompt, and on another day a speaking card.
  - Flagged items, and the items of a mock not yet taken, are held back.
  - After 3 or more days away, the first session back is lighter.
  - The home screen shows:
    - the current lesson and its progress;
    - the app bar (Home, Book, Practise, Words, Verbs, Exam) instead of the old link tiles;
    - the coach's note, ready feedback, the next exam dates, failed scheduled runs;
    - one readiness bar per exam unit.
- **Exam mode** (the exam screen, `?exam`).
  - **Readiness per unit, against each exam's real pass rule** (`src/oknos/readiness.py`, SPEC §5.3):
    - evidence is first attempts only, at the exam's level, with a Wilson range;
    - "not enough evidence" replaces a number when there is too little;
    - writing and speaking count only through the coach's scores.
  - Coverage per task.
  - The plan's next four weeks, with planned against done.
  - Timed mock exams (`src/oknos/mock.py`):
    - section by section, with the server's clock;
    - the clock keeps running when interrupted;
    - auto-scored to the blueprint's points.
- **The coach** (the agent) works only through files:
  - it reads `oknos report` (`report_version` 3: readiness, coverage, plan inputs and progress, mocks, chapters read);
  - it writes packs, `feedback/<id>.json`, `coach/*.json` (including `plan.json` and `mocks/<id>.json`) and notes;
  - the app takes them in.

  The shared rules are in `docs/COACHING.md`. Skills: `coach`, `capture`, `mark`, `tutor`, `daily-prep`, `watch`, `rebuild-imported`, `plan`, `mock-exam` and `write-chapter`, plus `setup` and `import-material`.
- **CLI:** `start`, `stop`, `health`, `report`, `validate` (packs, chapters, Greek lint, exam tags, tap-a-word gaps, hidden questions, learner folder), `words`, `reload`, `import`, `raw`, `schema`, `shortcut`, `transcribe`, `voice`, `podcast`, `run` and `schedule`.
- **Audio and speech.**
  - Browser voice for words. A vocab item's optional `say` replaces `el` as what is read.
- **Tap a word (phase 5d, SPEC §4.9):** every Greek word on screen has a meaning.
  - The lookup finds, in this order:
    - exact words and verb forms;
    - accent-free matches;
    - function words (`src/oknos/function_words.json`), instruction words (`rubric_words.json`: Διαλέγω, Συμπληρώστε…) and the packs' glossary words;
    - names and places (`names.json`, chapter speakers, glossary `names`);
    - inflected forms mapped to their word ("“ακούστε” is a form of ακούω");
    - then stems and phrases.
  - A pack's `glossary.json` holds `forms`, `words`, `names`, and `leave` (left unexplained on purpose, with a reason). `uv run oknos words <pack> --write` maps inflected forms from the cached Wiktionary dump.
  - The open packs' meanings are tracked in `content/open/open-shared-words-tr/glossary.json`. They were drafted by Sonnet on 2026-11-20 and spot-checked by Opus. On a fresh clone the open packs explain every word they show.
  - With the book, 15 of 5,169 tappable words (0.3%) are left unexplained, all OCR fragments or endings in grammar tables. `report` carries `tap_a_word`.
  - A meaning shown in the other UI language because the item has none in this one is tagged EN or TR.
- **No question behind "Translate":**
  - items can carry `ask {tr, en}`, the question or situation in the UI language, always shown under the rubric;
  - `validate` notes a rubric, statement or prompt whose translation asks a question the Greek does not, or says much more than the Greek (SPEC §4.9);
  - the 101 items it found (86 in the book, 15 in the open book) are fixed.
  - Listening passages pre-generated with `scripts/make_audio.py`: edge-tts with the learner's yes, for content outside `learner/` only.
  - Speaking recordings transcribed locally with faster-whisper `small` (the `speech` group).
- **Tests:** `uv run pytest`, which includes a scripted two weeks of use, the phase 4 contracts (`tests/test_coach.py`) exam mode (`tests/test_exam.py`), chapters (`tests/test_chapters.py`), the open book (`tests/test_open_book.py`) and tap-a-word coverage (`tests/test_lookup_coverage.py`: no open word without a meaning). `scripts/simulate.py` also prints the readiness per unit.

Known limits:
- The open content alone gives too few A2/B1 exam-format items for readiness to show numbers in the first weeks. The coach's items and mocks are what make them appear.
- The open verb pack has about 2 forms per tense per verb, so the verb tables are sparse.
- The book's lessons have few words linked to them (407 of 2,648). The rest open by level. Each stage's chapter places the words it teaches. A chapter can bring a word forward, never push it to a later lesson. The book's other words still open by level, with no chapter sentence for their learn card.
- A heavy review day can still leave no room for new words in the daily session. After reading, "Practise this chapter" is the way to the new words.
- The A2-LTR history pack waits until the plan targets an A2-LTR session with an announced date; none is announced. The syllabus PDF needs the learner's yes.
- Neither exam publishes its speaking points split, and A2-LTR publishes no writing criteria. Those scores are always labelled estimates.
- Pictures are of single words, so picture-based speaking parts are still described in words.
- The glossary meanings (open and book) and the book's A2/B1 Turkish meanings are AI-drafted and spot-checked, not checked by a person. A wrong one is fixed through the ⚑ flag or by editing `glossary.json`.

The macOS and Linux shortcuts and schedulers are written but untested.

On the maintainer's machine (2026-11-20): the `claude` command-line program is signed in, and two scheduled runs are set up: `daily-prep` every day at 18:30 and `watch` on Mondays at 18:00. A test run of `watch` passed.

Next:
- the maintainer reads the chapters as the lessons come; the ⚑ flag on a section sends a fix to the coach.

Optional, deferred by the maintainer (2026-11-19):
- phase 6 (the friend test).

Phase 7 (the repo on GitHub, private, with CI) is built: see **Git and GitHub** below. Phase 10 (the voice) is built: see **The voice** above.

On the roadmap (2026-11-20, `docs/prompts/`):
- phase 8 (optional) is researched: `docs/HOSTING.md`. On 2026-11-22 the maintainer chose Tailscale Serve to the laptop (the setup is the maintainer's, §6 there), and it is set up on the maintainer's laptop the same day: tailnet only, no Funnel. Serve points at one port. `oknos start` takes the port it ran on last (`learner/.last-port`), so a restart keeps the phone working; if that port is busy and the app lands on another, `oknos start` and `oknos health` print the one command that re-points Serve (`tailscale serve --bg <port>`). A Google Cloud e2-micro is the next step only if the laptop being off becomes the problem.
- phase 11 (optional, `docs/prompts/11-podcasts.md`, added 2026-11-23; started the same day, the pilot is built: `docs/PODCASTS.md`): podcast lessons, written as text first and then voiced. One per book chapter by default, and personal daily (10–20 min) and weekly (20–30 min) episodes made by `daily-prep`. Explanations in Turkish or English, the learner's choice; other languages later are a new script, not a new system. A loop enriches them from other Greek-teaching podcasts, videos and accounts as sources of ideas only, never re-voicing their content.
- the films in the app, and a new GitHub look (added 2026-11-23):
  - the films in the app: done 2026-11-23 (see **Films** above).
  - the new GitHub face: done 2026-11-24. The README has a hero (the home screen with a picture card and a chapter's scene), a gallery of the app in light and dark, a films section with a short animated preview of film 1, and current facts; the social preview matches the hero. All of it is made by `scripts/readme_images.py` from a demo learner with the open content only (`docs/DEVELOPING.md`, "The README's screenshots").

## Git and GitHub

- The repository is on GitHub under the maintainer's account, **private**.
- Commits land on `main` through a short branch: commit there, fast-forward `main`, delete the branch. `git push` follows **only when the maintainer asks**.
- **CI** (`.github/workflows/ci.yml`) runs on every push and pull request, on Ubuntu and Windows: the guard, `uv run pytest` and `uv run oknos validate content/open`. The tests need nothing from `content/private/`, `learner/` or a signed-in agent. See the result with `gh run list`, and a failure with `gh run view <id> --log-failed`.
- **The guard** (`uv run oknos guard`, `src/oknos/guard.py`) fails if git tracks anything under `learner/` or `content/private/`, or a file holding a local user path (`C:\Users\<name>`, `/home/<name>`, an agent's temp folder). Write a placeholder such as `C:\Users\you` instead. The tests and CI run it, and so does the pre-push hook in `.githooks/`, which `git config core.hooksPath .githooks` turns on (the `setup` skill does this).
- **Before the repo is made public** (a separate decision):
  - phase 6 step 5, the public-repo check, must pass;
  - the README's `<owner>` placeholder gets the real account;
  - upload `docs/brand/social-preview.png` in the repo's Settings → General → Social preview (GitHub shows that section only for public repositories);
  - every commit so far carries the maintainer's personal e-mail; switch to the GitHub no-reply address, and decide whether to rewrite the old commits;
  - three old revisions of the docs still hold the maintainer's Windows user name in a path (fixed in the current files); rewriting that history needs the maintainer's yes.

## Two kinds of people use this repo

- **The maintainer** develops the app with an agent. Normal engineering conversation.
- **A learner** may have no technical background at all. They installed an agent, cloned this repo and said "set this up for me". With a learner: never ask them to edit a file, read a stack trace or choose between technical options. Do it yourself, verify it worked, and tell them in plain language what to click.

If it is unclear which one you are talking to, ask once.

## Skills

The canonical copy of each skill is in `.agents/skills/<name>/SKILL.md`. `.claude/skills/<name>/SKILL.md` only points to it, and `tests/test_skills.py` keeps the two in step. The coach skills share `docs/COACHING.md`.

- `setup`: "set this up for me". Installs uv, starts the app, checks health and makes the desktop shortcut. See `.agents/skills/setup/SKILL.md`.
- `import-material`: "import my old project / this book". Writes a mapping, runs `oknos import` into `content/private/`, and checks the report. See `.agents/skills/import-material/SKILL.md`.
- `coach`: "coach", "how am I doing?". The check-in: profile on first run, report, marking, flags, 10–30 new items, the home-screen note. See `.agents/skills/coach/SKILL.md`.
- `capture`: "today in class we did…", or a letter or photo in `learner/inbox/`. Turns it into practice, with personal data replaced. See `.agents/skills/capture/SKILL.md`.
- `mark`: marks writing and speaking against the exam criteria into `learner/feedback/<id>.json`. See `.agents/skills/mark/SKILL.md`.
- `tutor`: "tutor", "role-play the landlord", "correct this". Live chat practice, also from a phone, ending in a log and review items. See `.agents/skills/tutor/SKILL.md`.
- `daily-prep`: tomorrow's content, run on a schedule or on request. Also sets up the schedule, after a yes. See `.agents/skills/daily-prep/SKILL.md`.
- `watch`: exam and course dates from the official pages into `coach/watch.json`. See `.agents/skills/watch/SKILL.md`.
- `rebuild-imported`: "turn lesson 5 into exercises". Rebuilds raw OCR exercises into private items. See `.agents/skills/rebuild-imported/SKILL.md`.
- `plan`: "make me a plan", "when can I take the exam?". A week-by-week plan to a real session from `watch.json` and the real pace, with an honest verdict; re-planned at every check-in. See `.agents/skills/plan/SKILL.md`.
- `mock-exam`: "give me a mock exam". A timed mock in the real format, then marks its writing and speaking. See `.agents/skills/mock-exam/SKILL.md`.
- `write-chapter`: "write the chapters for lessons 10–15", "make the outline". The chapters read before each stage's practice: an outline, golden chapters, Sonnet drafts, Opus review. See `.agents/skills/write-chapter/SKILL.md` and `docs/LESSONS.md`.
- `podcast`: "make the podcast for this lesson", "bu dersin podcast'ini yap". Writes a chapter's podcast lesson as a script, checks it, says the characters it will spend, and renders the mp3 for the Podcast page. See `.agents/skills/podcast/SKILL.md` and `docs/PODCASTS.md`.

## Commands

The full list, with how the code is laid out, is in `docs/DEVELOPING.md`. The README is for learners and visitors; its diagrams come from `scripts/make_brand.py`, and its screenshots, hero, film preview and the social preview from `scripts/readme_images.py`, run in a fresh clone (`docs/DEVELOPING.md`, "The README's screenshots").

- `uv run oknos start`: runs the app in the background on `127.0.0.1:8642` (or the next free port) and opens the browser.
- `uv run oknos stop`: stops it.
- `uv run oknos health [--server] [--json]`: checks the install.
- `uv run oknos validate <pack>`: checks a content pack and explains any problems.
- `uv run oknos import <mapping> --source <folder>`: imports someone's own material as a private pack (`docs/IMPORTING.md`).
- `uv run oknos schema`: writes the pack JSON Schemas to `schemas/`.
- `uv run oknos report [--since 14d] [--words]`: the learner's record as one JSON document. This is the coach's only view of the database.
- `uv run oknos validate learner`: checks coach-written packs (including the Greek lint) and the coach's files.
- `uv run oknos words <pack> [--write] [--json <file>]`: lists the tappable words that find no meaning; `--write` maps inflected forms to their word in the pack's `glossary.json`.
- `uv run oknos reload`: makes the running app load new content and coach files.
- `uv run oknos voice status|build|sample`: the Greek voice made ahead of time (`docs/VOICE.md`).
- `uv run oknos podcast list|check <id>|render <id> [--wait]|material daily|weekly [--date]|prune`: podcast lessons (`docs/PODCASTS.md`); `check` prints the characters a render will spend; `material` what a personal episode is written from; ffmpeg must be installed.
- `uv run oknos raw <pack> --unit <id>`: shows the raw imported exercises of one lesson.
- `uv run --group speech oknos transcribe`: transcribes speaking recordings locally.
- `uv run oknos run <daily-prep|watch>` and `uv run oknos schedule list|add|remove`: scheduled coach runs. Set them up only after the learner says yes.
- `uv run python scripts/simulate.py`: simulates two weeks of use in a throwaway learner folder and prints the scheduler, home and readiness numbers.
- `OKNOS_MOCK_SPEED=30 uv run oknos start --foreground`: development only; mock-exam time passes 30 times faster, to check the timing.
- `uv run oknos shortcut`: creates the desktop launcher.
- `uv run pytest`: runs the tests.
- `uv run oknos start --foreground`: runs the server in the terminal, for development.
- `uv run oknos guard [--rev <commit>]`: checks that git tracks nothing private (learner data, private content, local user paths).

## Guardrails

- **Local only.** No accounts in the app, no telemetry, no cloud services that hold learner data or content. The app runs on `localhost` and all learner data stays on the machine. There are two exceptions, both opt-in and off until the learner says yes:
  - **The learner's own devices**, through a private network (Tailscale Serve, `docs/HOSTING.md`). The app still listens on `127.0.0.1` only, nothing is hosted, and the network's provider cannot read the traffic. Never publish the app to the internet: no Tailscale Funnel, no public tunnel, no port forwarding. `oknos start` and `oknos health` only read `tailscale serve status`, never change it.
  - **The voice services** (`docs/SPEC.md` §9, `docs/VOICE.md`): Azure Speech, Google Cloud Text-to-Speech, Gemini TTS and ElevenLabs (podcasts only, paid) and OpenAI on the learner's own account and key (`learner/secrets.env`, each key sent only to its own service), and edge-tts, which needs no key but also `"edge_tts_ok": true` in the profile. They are sent the Greek content text only, never learner data (answers, writing, recordings, captured documents, progress). edge-tts gets nothing from `learner/`, not even the coach's own packs; a keyed service may voice those, as the coach writes them without personal data. The clips made for a learner stay in `learner/voice/`; only the open content's clips are shipped (`content/open-voice/`, made by the maintainer from open text).
- **The coach writes files, never the database.** It reads `oknos report`; the app takes in what it writes (`docs/COACHING.md` §7).
- **Never commit learner data or private content.** `learner/` and `content/private/` are gitignored and must stay that way. Do not move anything out of them into tracked paths.
- **Copyright.** Tracked content must be original to this project or openly licensed, with the licence recorded in the pack manifest. Textbook scans, OCR of commercial books, publisher audio and past exam papers belong in `content/private/` only.
- **The app must work without an agent running.** The agent prepares content and feedback ahead of time; the daily study session is the web app alone.
- **Few dependencies.** Every dependency is one more thing that can fail on a stranger's laptop. Add one only when it clearly earns its place.
- **Greek text is UTF-8 everywhere**, including on Windows consoles and in SQLite.
