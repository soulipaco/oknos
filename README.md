# Greek Coach

A local-first Greek learning companion that your coding agent installs, runs and personalises for you. It is for people living in Greece who need to pass a language certification exam and have struggled to stay interested in studying.

> **Status: study loop (phase 3).** One button starts a daily session sized to your time: the reviews that are due, a verb slot, one task in exam format, and a few new words.
> - Spaced repetition (SM-2) brings back what you got wrong the next day.
> - Exercise types: word cards (choice, listening and typed, with an on-screen Greek keyboard), verb forms, multiple choice, true/false, matching, word bank, sorting into categories, and listening.
> - Tap any Greek word to see its meaning.
> - The home screen shows what to do now, how consistent you have been, and what you are weakest at, with real numbers and no streaks or badges.
> - Content: three open packs (*"Words you already know"*, everyday verbs, everyday tasks in exam format), plus your own material if you import it privately.
>
> The coach comes in phase 4 (see `docs/prompts/`).

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
  - it builds new exercises around your weak spots;
  - it gives feedback on your writing;
  - it turns what you covered in class into practice;
  - it tracks how ready you are for the exam.
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
uv run python scripts/simulate.py        # two simulated weeks: scheduler and home numbers
uv run pytest
```

How the code is laid out:
- `src/greek_coach/`: the FastAPI server, SQLite, pack loading, answer checking, the scheduler (`scheduler.py`), sessions, word lookup, the importer (`importer/`) and the CLI.
- `web/`: plain HTML/CSS/JS with no build step, plus `i18n/` for the English and Turkish UI strings.
- `content/open/`: the tracked content packs. `content/private/` (gitignored) holds imported material.
- `scripts/`: the verb-pack builder, the listening-audio generator and the simulation.

## Licences

- Code: MIT (`LICENSE`).
- Content in `content/open/`: CC BY-SA 4.0 (`content/open/LICENSE.md`).

## Documents

- `AGENTS.md`: instructions for any coding agent working in this repo.
- `docs/SPEC.md`: the agreed specification. It overrides `docs/DESIGN.md`.
- `docs/DESIGN.md`: the original product and architecture decisions.
- `docs/prompts/`: the phased prompts used to build the app.
