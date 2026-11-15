# Phase 2 — Walking skeleton

Read `AGENTS.md`, `docs/SPEC.md` and `docs/DESIGN.md`. The specification is agreed; this session builds the thinnest version of the app that works from end to end.

The point of this phase is to prove the risky parts early: that installation really is one sentence, that the app and the agent can exchange information through files, and that Greek text survives every layer on Windows. Breadth comes later. Resist adding exercise types, pages or polish that the list below does not ask for.

## Build

- The project scaffold as specified: the local server, the SQLite database created on first run inside `learner/`, and the no-build front end served by the same process.
- One small **original** content pack in `content/open/`, written by you, at beginner level, using two or three exercise types from the spec (`vocab`, `mcq`, `true_false`). Twenty to thirty items is enough. Make it the "Words you already know" pack from the spec (Greek–Turkish shared words, with English translations too). Record its licence (CC BY-SA 4.0) in the manifest.
- UI strings in English and Turkish from the start (`web/i18n/`), switchable on the home screen.
- `LICENSE` (MIT) for the code and a licence note for `content/open/` (CC BY-SA 4.0).
- One study session in the browser: the learner starts it with a single click, answers items, gets immediate right/wrong feedback, and sees a short summary at the end. Every attempt is recorded.
- One start command that launches the server and opens the browser, working the same way on Windows, macOS and Linux.
- The `setup` skill, as the spec lays out: canonical in `.agents/skills/setup/SKILL.md`, plus the Claude Code pointer in `.claude/skills/setup/SKILL.md` and a test that the two agree. Also a one-line entry in `AGENTS.md`. It covers the "set this up for me" case, including the desktop shortcut: check for the one prerequisite, install it if missing, start the app, confirm it responds, and tell the learner in plain words how to open it next time. Write it for a learner who cannot read an error message, so the agent must verify each step itself.
- A minimal health check the agent can run to confirm an install is good, and a few tests around answer checking and attempt recording.

The interface should already feel calm and pleasant, with Greek text large and well set. It is a place I am supposed to want to return to, so do not ship a developer-looking page even at this stage.

## Verify, do not assume

Before you report back, clone the repo into a fresh temporary directory and follow your own setup instructions exactly as written, as if you had never seen the project. Then drive the session in a browser and confirm that an attempt lands in the database with its Greek text intact. Fix whatever that exposes. Tell me what you ran and what you saw, including anything that failed along the way.

## Done when

I can delete the folder, clone it again, tell a new agent session "set this up for me", and be answering a Greek question in the browser a few minutes later without having typed a command myself.

Update "Current state" in `AGENTS.md` and the README, and leave the work ready for me to commit.
