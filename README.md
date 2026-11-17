# Greek Coach

A local-first Greek learning companion that your coding agent installs, runs and personalises for you. It is for people living in Greece who need to pass a language certification exam and have struggled to stay interested in studying.

> **Status: exam mode (phase 5).** The app runs a daily session on its own, tells you honestly whether you would pass today, and runs timed mock exams; your agent is the coach.
> - **The app:**
>   - you move through a course in order, simple before hard: reading the alphabet first, then lesson by lesson (your own coursebook's lessons if you imported it), and a lesson opens when the one before it is learned, or when you pass its "test me" check;
>   - one button starts a session sized to your time: reviews, verbs, one exam-format task and new words from your current lesson;
>   - or choose yourself: words, verbs, reading, listening, writing, speaking or your mistakes, from any lesson you have reached; see all your words and verb tables;
>   - once a week the session includes a writing prompt or a speaking card in exam format;
>   - spaced repetition (SM-2), tap any Greek word for its meaning, flag an item that looks wrong;
>   - an on-screen Greek keyboard;
>   - honest numbers on the home screen, with no streaks or badges;
>   - **"would you pass today?"** per exam section, for Ελληνομάθεια B1 and for the A2 + history exam for long-term residence, each against its real pass rule. Where there is too little evidence it says so instead of guessing;
>   - **timed mock exams** in the real format, section by section, and a plan to the exam date with the next four weeks.
> - **The coach** (open your agent and say one word):
>   - **"coach"**: how it is going, your 2–3 weakest areas, feedback on your writing, and next week's exercises already in the app;
>   - **"tutor"**: a short chat in Greek, a role-play or "correct this";
>   - **"today in class we did…"**, or a photo of a letter in `learner/inbox/`: practice built from it;
>   - **"any exam dates?"**: the official pages are checked and the next dates go on the home screen;
>   - **"make me a plan"**: a week-by-week plan to a real, announced session, which says plainly whether it is realistic and what to drop if you fall behind;
>   - **"give me a mock exam"**: a full mock in the exam's format, marked afterwards.
> - **Content:** five open packs (including learning to read Greek, and B1 practice), plus your own material if you import it privately.
>
> Next: phase 6, a test on a stranger's machine (see `docs/prompts/`).

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
uv run python scripts/simulate.py        # simulated weeks of use: scheduler, home and readiness numbers
GREEK_COACH_MOCK_SPEED=30 uv run greek-coach start --foreground   # development: mock-exam time runs 30x faster
uv run pytest
```

How the code is laid out:
- `src/greek_coach/`: the FastAPI server, SQLite, pack loading, answer checking, the scheduler (`scheduler.py`), sessions, word lookup, the importer (`importer/`) and the CLI.
  - The coach's side: `report.py` (what the coach reads), `coachfiles.py` (the files it writes), `lint.py` (Greek and exam-tag checks), `scheduling.py` and `transcribe.py`.
  - Exam mode: `exams.py` (blueprints and pass rules), `readiness.py`, `mock.py` and `plan.py`.
  - Progression: `curriculum.py`, with the open course in `curricula/`.
- `exams/`: the exam blueprints, facts about the two public exams with links to the official sources.
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
