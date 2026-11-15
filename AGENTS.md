# Agent Instructions

Greek Coach is an open-source, local-first Greek learning app that is installed, operated and extended by a coding agent (Claude Code, Codex, or similar). This file is the canonical instruction file for every agent harness; `CLAUDE.md` only imports it.

## Read first

1. `docs/DESIGN.md` — what we are building, for whom, and the decisions already made.
2. `docs/prompts/README.md` — the phased build plan. Check which phase is current before starting work.
3. `docs/SPEC.md` — once it exists (it is produced in phase 1), it overrides `DESIGN.md` where they differ.

## Current state

Phase 3 (import and study loop) is built, verified on Windows, and not yet committed. `docs/SPEC.md` is agreed. Its exam strategy is to track Ελληνομάθεια B1 and the A2 + history exam side by side and let readiness decide.

What works now:
- **Stack:** uv, FastAPI and SQLite (`learner/greek-coach.db`, migrations `0001`–`0002`), with a no-build front end in `web/`. UI in English and Turkish.
- **Content.**
  - Three open packs (CC BY-SA 4.0):
    - `open-shared-words-tr`;
    - `open-verbs-a1a2`: 253 verb-form items for 44 verbs, built by `scripts/build_verb_pack.py`;
    - `open-everyday-a1a2`: 19 tasks in exam format, 6 of them listening.
  - A private pack imported from the maintainer's earlier project, `content/private/greek-helper`, which is gitignored: 2,648 words, 25 units, and exercises kept as raw prompts. Its report is `IMPORT_REPORT.md`.
- **Exercise types:** `vocab` (choice, audio and typed), `form`, `mcq`, `true_false`, `match`, `gap_bank`, `categorise`, and listening variants of all of them.
  - There is an on-screen Greek keyboard, and Latin input is converted to Greek.
  - Checking is accent-tolerant and adds a note when the accent is wrong.
- **Study loop.**
  - SM-2 spaced repetition (`scheduler.py`).
  - A daily session of reviews, verbs, one exam task and new words, sized to the profile's minutes. It can be resumed, and finished days offer "5 more minutes".
  - Tap any Greek word to see its meaning; the tap counts as "not known".
  - Flags on items.
  - A home dashboard: what to do now, a 28-day grid, and accuracy per area with sample sizes.
- **CLI:** `start`, `stop`, `health`, `validate`, `import`, `schema`, `shortcut`.
- **Audio.** Browser voice for words. Listening passages can be pre-generated into `learner/audio/` with `scripts/make_audio.py`:
  - Piper failed the quality test (SPEC §9);
  - edge-tts is the generator once the learner says yes (`edge_tts_ok` in the profile). The maintainer has said yes;
  - the offline Windows voice is the fallback.
- **Tests:** `uv run pytest`, which includes a scripted two weeks of use. `scripts/simulate.py` prints the same simulation day by day.

Not built yet:
- `table_fill`, `write` and `speak` (phases 4–5);
- `report` and the coach skills (phase 4);
- exam blueprints and readiness bars (phase 5).

The macOS and Linux shortcuts are written but untested.

Next: phase 4 in `docs/prompts/`.

## Two kinds of people use this repo

- **The maintainer** develops the app with an agent. Normal engineering conversation.
- **A learner** may have no technical background at all. They installed an agent, cloned this repo and said "set this up for me". With a learner: never ask them to edit a file, read a stack trace or choose between technical options. Do it yourself, verify it worked, and tell them in plain language what to click.

If it is unclear which one you are talking to, ask once.

## Skills

The canonical copy of each skill is in `.agents/skills/<name>/SKILL.md`. `.claude/skills/<name>/SKILL.md` only points to it, and `tests/test_skills.py` keeps the two in step.

- `setup`: "set this up for me". Installs uv, starts the app, checks health and makes the desktop shortcut. See `.agents/skills/setup/SKILL.md`.
- `import-material`: "import my old project / this book". Writes a mapping, runs `greek-coach import` into `content/private/`, and checks the report. See `.agents/skills/import-material/SKILL.md`.

## Commands

- `uv run greek-coach start`: runs the app in the background on `127.0.0.1:8642` (or the next free port) and opens the browser.
- `uv run greek-coach stop`: stops it.
- `uv run greek-coach health [--server] [--json]`: checks the install.
- `uv run greek-coach validate <pack>`: checks a content pack and explains any problems.
- `uv run greek-coach import <mapping> --source <folder>`: imports someone's own material as a private pack (`docs/IMPORTING.md`).
- `uv run greek-coach schema`: writes the pack JSON Schemas to `schemas/`.
- `uv run python scripts/simulate.py`: simulates two weeks of use in a throwaway learner folder and prints the scheduler and home numbers.
- `uv run greek-coach shortcut`: creates the desktop launcher.
- `uv run pytest`: runs the tests.
- `uv run greek-coach start --foreground`: runs the server in the terminal, for development.

## Guardrails

- **Local only.** No accounts, no telemetry, no cloud services. The app runs on `localhost` and all learner data stays on the machine. The one exception is the opt-in edge-tts fallback in `docs/SPEC.md` §9. It handles content text only, never learner data.
- **Never commit learner data or private content.** `learner/` and `content/private/` are gitignored and must stay that way. Do not move anything out of them into tracked paths.
- **Copyright.** Tracked content must be original to this project or openly licensed, with the licence recorded in the pack manifest. Textbook scans, OCR of commercial books, publisher audio and past exam papers belong in `content/private/` only.
- **The app must work without an agent running.** The agent prepares content and feedback ahead of time; the daily study session is the web app alone.
- **Few dependencies.** Every dependency is one more thing that can fail on a stranger's laptop. Add one only when it clearly earns its place.
- **Greek text is UTF-8 everywhere**, including on Windows consoles and in SQLite.
