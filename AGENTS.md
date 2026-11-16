# Agent Instructions

Greek Coach is an open-source, local-first Greek learning app that is installed, operated and extended by a coding agent (Claude Code, Codex, or similar). This file is the canonical instruction file for every agent harness; `CLAUDE.md` only imports it.

## Read first

1. `docs/DESIGN.md` — what we are building, for whom, and the decisions already made.
2. `docs/prompts/README.md` — the phased build plan. Check which phase is current before starting work.
3. `docs/SPEC.md` — once it exists (it is produced in phase 1), it overrides `DESIGN.md` where they differ.

## Current state

Phases 1–4 are built and committed; phase 4 is the coach. `docs/SPEC.md` is agreed. Its exam strategy is to track Ελληνομάθεια B1 and the A2 + history exam side by side and let readiness decide.

What works now:
- **Stack:** uv, FastAPI and SQLite (`learner/greek-coach.db`, migrations `0001`–`0003`), with a no-build front end in `web/`. UI in English and Turkish.
- **Content.**
  - Three open packs (CC BY-SA 4.0):
    - `open-shared-words-tr`;
    - `open-verbs-a1a2`: 253 verb forms, built by `scripts/build_verb_pack.py`;
    - `open-everyday-a1a2`: 23 exam-format tasks, 6 of them listening, plus 2 writing prompts and 2 speaking cards.
  - A private import of the maintainer's earlier material in `content/private/greek-helper` (gitignored): 2,648 words, 25 units, and 1,697 raw exercise prompts for the coach to rebuild.
  - Coach-written packs go in `learner/generated/` (gitignored).
- **Exercise types:**
  - `vocab`, `form`, `mcq`, `true_false`, `match`, `gap_bank` and `categorise`, plus listening variants. These are checked by the app: accent-tolerant, with an on-screen Greek keyboard.
  - `write` and `speak`. These are saved as submissions and marked by the coach; speaking is recorded in the browser.
- **Study loop.**
  - SM-2 spaced repetition.
  - A daily session sized to the profile's minutes. Coach items come first in every segment.
  - Once a week the session holds a writing prompt, and on another day a speaking card.
  - Flagged items are held back until the coach rules on them.
  - After 3 or more days away, the first session back is lighter.
  - The home screen shows the coach's note, ready feedback, the next exam dates, and failed scheduled runs.
- **The coach** (the agent) works only through files:
  - it reads `greek-coach report`;
  - it writes packs, `feedback/<id>.json`, `coach/*.json` and notes;
  - the app takes them in.

  The shared rules are in `docs/COACHING.md`. Skills: `coach`, `capture`, `mark`, `tutor`, `daily-prep`, `watch` and `rebuild-imported`, plus `setup` and `import-material`.
- **CLI:** `start`, `stop`, `health`, `report`, `validate` (packs, Greek lint, learner folder), `reload`, `import`, `raw`, `schema`, `shortcut`, `transcribe`, `run` and `schedule`.
- **Audio and speech.**
  - Browser voice for words.
  - Listening passages pre-generated with `scripts/make_audio.py`: edge-tts with the learner's yes, for content outside `learner/` only.
  - Speaking recordings transcribed locally with faster-whisper `small` (the `speech` group).
- **Tests:** `uv run pytest`, which includes a scripted two weeks of use and the phase 4 contracts (`tests/test_coach.py`).

Not built yet:
- `table_fill` (phase 5);
- exam blueprints, readiness bars, `plan` and `mock-exam` (phase 5).

The macOS and Linux shortcuts and schedulers are written but untested.

Not yet done on the maintainer's machine:
- No scheduled runs are set up.
- The `claude` command-line program is not signed in, so `greek-coach run` fails with "Not logged in" until `claude` is run once in a terminal and signed in.

Next: phase 5 in `docs/prompts/`.

## Two kinds of people use this repo

- **The maintainer** develops the app with an agent. Normal engineering conversation.
- **A learner** may have no technical background at all. They installed an agent, cloned this repo and said "set this up for me". With a learner: never ask them to edit a file, read a stack trace or choose between technical options. Do it yourself, verify it worked, and tell them in plain language what to click.

If it is unclear which one you are talking to, ask once.

## Skills

The canonical copy of each skill is in `.agents/skills/<name>/SKILL.md`. `.claude/skills/<name>/SKILL.md` only points to it, and `tests/test_skills.py` keeps the two in step. The coach skills share `docs/COACHING.md`.

- `setup`: "set this up for me". Installs uv, starts the app, checks health and makes the desktop shortcut. See `.agents/skills/setup/SKILL.md`.
- `import-material`: "import my old project / this book". Writes a mapping, runs `greek-coach import` into `content/private/`, and checks the report. See `.agents/skills/import-material/SKILL.md`.
- `coach`: "coach", "how am I doing?". The check-in: profile on first run, report, marking, flags, 10–30 new items, the home-screen note. See `.agents/skills/coach/SKILL.md`.
- `capture`: "today in class we did…", or a letter or photo in `learner/inbox/`. Turns it into practice, with personal data replaced. See `.agents/skills/capture/SKILL.md`.
- `mark`: marks writing and speaking against the exam criteria into `learner/feedback/<id>.json`. See `.agents/skills/mark/SKILL.md`.
- `tutor`: "tutor", "role-play the landlord", "correct this". Live chat practice, also from a phone, ending in a log and review items. See `.agents/skills/tutor/SKILL.md`.
- `daily-prep`: tomorrow's content, run on a schedule or on request. Also sets up the schedule, after a yes. See `.agents/skills/daily-prep/SKILL.md`.
- `watch`: exam and course dates from the official pages into `coach/watch.json`. See `.agents/skills/watch/SKILL.md`.
- `rebuild-imported`: "turn lesson 5 into exercises". Rebuilds raw OCR exercises into private items. See `.agents/skills/rebuild-imported/SKILL.md`.

## Commands

- `uv run greek-coach start`: runs the app in the background on `127.0.0.1:8642` (or the next free port) and opens the browser.
- `uv run greek-coach stop`: stops it.
- `uv run greek-coach health [--server] [--json]`: checks the install.
- `uv run greek-coach validate <pack>`: checks a content pack and explains any problems.
- `uv run greek-coach import <mapping> --source <folder>`: imports someone's own material as a private pack (`docs/IMPORTING.md`).
- `uv run greek-coach schema`: writes the pack JSON Schemas to `schemas/`.
- `uv run greek-coach report [--since 14d] [--words]`: the learner's record as one JSON document. This is the coach's only view of the database.
- `uv run greek-coach validate learner`: checks coach-written packs (including the Greek lint) and the coach's files.
- `uv run greek-coach reload`: makes the running app load new content and coach files.
- `uv run greek-coach raw <pack> --unit <id>`: shows the raw imported exercises of one lesson.
- `uv run --group speech greek-coach transcribe`: transcribes speaking recordings locally.
- `uv run greek-coach run <daily-prep|watch>` and `uv run greek-coach schedule list|add|remove`: scheduled coach runs. Set them up only after the learner says yes.
- `uv run python scripts/simulate.py`: simulates two weeks of use in a throwaway learner folder and prints the scheduler and home numbers.
- `uv run greek-coach shortcut`: creates the desktop launcher.
- `uv run pytest`: runs the tests.
- `uv run greek-coach start --foreground`: runs the server in the terminal, for development.

## Guardrails

- **Local only.** No accounts, no telemetry, no cloud services. The app runs on `localhost` and all learner data stays on the machine. The one exception is the opt-in edge-tts fallback in `docs/SPEC.md` §9. It handles content text only, never learner data.
- **The coach writes files, never the database.** It reads `greek-coach report`; the app takes in what it writes (`docs/COACHING.md` §7).
- **Never commit learner data or private content.** `learner/` and `content/private/` are gitignored and must stay that way. Do not move anything out of them into tracked paths.
- **Copyright.** Tracked content must be original to this project or openly licensed, with the licence recorded in the pack manifest. Textbook scans, OCR of commercial books, publisher audio and past exam papers belong in `content/private/` only.
- **The app must work without an agent running.** The agent prepares content and feedback ahead of time; the daily study session is the web app alone.
- **Few dependencies.** Every dependency is one more thing that can fail on a stranger's laptop. Add one only when it clearly earns its place.
- **Greek text is UTF-8 everywhere**, including on Windows consoles and in SQLite.
