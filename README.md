# Greek Coach

A local-first Greek learning companion that your coding agent installs, runs and personalises for you. It is for people living in Greece who need to pass a language certification exam and have struggled to stay interested in studying.

> **Status: the coach (phase 4).** The app runs a daily session on its own; your agent is the coach.
> - **The app:**
>   - one button starts a session sized to your time: reviews, verbs, one exam-format task and new words;
>   - once a week the session includes a writing prompt or a speaking card in exam format;
>   - spaced repetition (SM-2), tap any Greek word for its meaning, flag an item that looks wrong;
>   - an on-screen Greek keyboard;
>   - honest numbers on the home screen, with no streaks or badges.
> - **The coach** (open your agent and say one word):
>   - **"coach"**: how it is going, your 2–3 weakest areas, feedback on your writing, and next week's exercises already in the app;
>   - **"tutor"**: a short chat in Greek, a role-play or "correct this";
>   - **"today in class we did…"**, or a photo of a letter in `learner/inbox/`: practice built from it;
>   - **"any exam dates?"**: the official pages are checked and the next dates go on the home screen.
> - **Content:** three open packs, plus your own material if you import it privately.
>
> Exam readiness and mock exams come in phase 5 (see `docs/prompts/`).

## Get started

1. Install an agent such as the Claude desktop app (Claude Code) or Codex, and sign in.
2. In a new session, say: **"Download `https://github.com/<owner>/greek-coach` and set it up for me."**
3. The agent installs what is needed, starts the app and puts a **Greek Coach** shortcut on your desktop.

After that, double-click **Greek Coach** whenever you want to study. You don't need the agent open for that.

If you already have the code, open the folder in your agent and say "set this up for me". The steps the agent follows are in `.agents/skills/setup/SKILL.md`.

## The idea

- You study in a web app that runs only on your own computer, at `http://127.0.0.1:8642`.
- Your progress, mistakes and writing stay in a local folder (`learner/`). Nothing is uploaded.
- When you open the agent again, it reads how you have been doing and acts as your coach:
  - it builds new exercises around your weak spots, from your own life (work, neighbourhood, Greek offices);
  - it marks your writing against the exam's criteria and shows the corrections next to what you wrote;
  - it turns what you covered in class, or a letter you received, into practice;
  - it practises conversation with you, also from your phone;
  - it can prepare tomorrow's exercises every day by itself, if you agree.

  Everything the coach knows about the coaching is in `docs/COACHING.md` and `.agents/skills/`.
- You can import your own material (a textbook you own, a word list, course handouts) as a private content pack that never leaves your machine. Ask the agent to "import my material", or see `docs/IMPORTING.md`.

## For developers

You need [uv](https://docs.astral.sh/uv/). Nothing else, not even Python.

```
uv sync
uv run greek-coach start          # background server + browser
uv run greek-coach health         # install check, including a Greek round trip through SQLite
uv run greek-coach stop
uv run greek-coach start --foreground   # server in this terminal, for development
uv run greek-coach import <mapping> --source <folder>   # private pack from your own material
uv run greek-coach report                # the learner's record as JSON, which is what the coach reads
uv run greek-coach validate learner      # check coach-written packs and files
uv run greek-coach reload                # make the running app pick up new content
uv run greek-coach raw greek-helper --unit lesson-05    # raw imported exercises, for rebuilding
uv run --group speech greek-coach transcribe            # local transcription of speaking recordings
uv run greek-coach schedule list|add|remove             # scheduled coach runs (asks the learner first)
uv run python scripts/simulate.py        # simulated weeks of use: scheduler and home numbers
uv run pytest
```

How the code is laid out:
- `src/greek_coach/`: the FastAPI server, SQLite, pack loading, answer checking, the scheduler (`scheduler.py`), sessions, word lookup, the importer (`importer/`) and the CLI.
  - The coach's side: `report.py` (what the coach reads), `coachfiles.py` (the files it writes), `lint.py` (Greek checks), `scheduling.py` and `transcribe.py`.
- `web/`: plain HTML/CSS/JS with no build step, plus `i18n/` for the English and Turkish UI strings.
- `content/open/`: the tracked content packs. `content/private/` (gitignored) holds imported material.
- `scripts/`: the verb-pack builder, the listening-audio generator and the simulation.

## Licences

- Code: MIT (`LICENSE`).
- Content in `content/open/`: CC BY-SA 4.0 (`content/open/LICENSE.md`).

## Documents

- `AGENTS.md`: instructions for any coding agent working in this repo.
- `docs/COACHING.md`: how the agent coaches: the learner, tone, quality rules for generated Greek, and file formats.
- `docs/SPEC.md`: the agreed specification. It overrides `docs/DESIGN.md`.
- `docs/DESIGN.md`: the original product and architecture decisions.
- `docs/prompts/`: the phased prompts used to build the app.
