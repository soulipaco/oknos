# Developing Oknos

You need [uv](https://docs.astral.sh/uv/). Nothing else, not even Python. Agents working in this repo also read `AGENTS.md`.

## Commands

```
uv sync
uv run oknos start          # background server + browser (http://127.0.0.1:8642)
uv run oknos stop
uv run oknos stop; uv run oknos start   # restart: needed after changes to code (src/, web/)
uv run oknos reload         # make the running app pick up new content (packs, chapters, coach files)
uv run oknos health         # install check, including a Greek round trip through SQLite
uv run oknos start --foreground   # server in this terminal, for development
uv run oknos import <mapping> --source <folder>   # private pack from your own material
uv run oknos report                # the learner's record as JSON, which is what the coach reads
uv run oknos validate content/open # check content packs, chapters, the Greek lint and tap-a-word gaps
uv run oknos validate learner      # check coach-written packs and files
uv run oknos words <pack> --write  # map inflected forms to their word in the pack's glossary
uv run oknos raw <pack> --unit lesson-05    # raw imported exercises, for rebuilding
uv run --group speech oknos transcribe      # local transcription of speaking recordings
uv run oknos schedule list|add|remove       # scheduled coach runs (asks the learner first)
uv run oknos guard                 # check that git tracks nothing private
uv run python scripts/simulate.py  # simulated weeks of use: scheduler, home and readiness numbers
OKNOS_MOCK_SPEED=30 uv run oknos start --foreground   # mock-exam time runs 30x faster
uv run --with fonttools python scripts/make_brand.py  # remake the brand files and the README's pictures
uv run --no-sync python scripts/make_brand.py developer  # only the developer diagrams, with the counts read from the repo
uv run pytest
```

CI runs the guard, the tests and `validate content/open` on Ubuntu and Windows for every push and pull request.

## How the code is laid out

- `src/oknos/`: the FastAPI server, SQLite, pack loading, answer checking, the scheduler (`scheduler.py`), sessions, word lookup (`lookup.py`), the importer (`importer/`) and the CLI.
  - The coach's side: `report.py` (what the coach reads), `coachfiles.py` (the files it writes), `lint.py` (Greek and exam-tag checks), `scheduling.py` and `transcribe.py`.
  - Exam mode: `exams.py` (blueprints and pass rules), `readiness.py`, `mock.py` and `plan.py`.
  - Progression and the book: `curriculum.py` and `chapters.py`, with the open course in `curricula/`.
- `exams/`: the exam blueprints, facts about the two public exams with links to the official sources.
- `web/`: plain HTML/CSS/JS with no build step, plus `i18n/` for the English and Turkish UI strings.
- `content/open/`: the tracked content packs, including the open course's book (`open-book/`). `content/private/` (gitignored) holds imported material.
- `scripts/`: the verb-pack builder, the listening-audio generator, the shipped voice clips (`ship_voice.py`, `docs/VOICE.md`), the films' voice, the simulation and the brand files.
- `docs/brand/`: the name, the logo, the icon and the donkey; `docs/img/`: the README's pictures.
  - `docs/brand/animations/`: the three films. The app serves this folder itself at `/films/` (`src/oknos/films.py`: only the pages, `film.js`, `anim.css` and the files in `frames/`, `voice/`, `voice-local/` and `ambience/`), so there is one copy. The films page (`?films`, `?films=<n>`) and the first-launch welcome show a film's page in a frame with `?embed`; `film.js` then hides the page's own header and links, takes the app's language and theme, and tells the app its height and when the film has ended.

## Documents

- `AGENTS.md`: instructions for any coding agent working in this repo.
- `docs/SPEC.md`: the agreed specification. It overrides `docs/DESIGN.md`.
- `docs/DESIGN.md`: the original product and architecture decisions.
- `docs/COACHING.md`: how the agent coaches: the learner, tone, quality rules for generated Greek, and file formats.
- `docs/LESSONS.md`: how the book's chapters are written and reviewed.
- `docs/IMPORTING.md`: importing your own material.
- `docs/MANUAL.md`: running Oknos by hand, with no agent.
- `docs/brand/README.md`: the name and the look.
- `docs/BUILT-WITH-AGENTS.md`: how agents build and run Oknos, who made what, and what no person has checked.
- `docs/prompts/`: the phased prompts used to build the app.

## The README's screenshots

The README's pictures (`docs/img/app-*.webp`, `docs/img/hero-{light,dark}.webp`, `docs/img/film-preview.webp`) and the social preview (`docs/brand/social-preview.png`) come from one script, run in a fresh clone (only the open content, no private material):

```
uv run --with playwright --with pillow python scripts/readme_images.py
```

It refuses to run while `content/private/` holds anything, and it never touches `learner/`. It makes a throwaway learner folder with 24 days of simulated practice (`scripts/simulate.py`), an English profile and a coach's note; adds a demo coach pack (copies of the open exam-format items, answered once, about half right) so the exam screen has evidence to show; runs the app on port 8690 with that folder; photographs the screens in light and dark with headless Chrome or Edge; makes film 1's preview from the film's own player; composes the hero and the social preview from the screenshots; then stops the app and deletes the folder (`--keep` keeps it, `--port` picks another port). Playwright and Pillow are used only here, through `uv run --with`. The diagrams (`docs/img/*.svg`) and the brand files come from `scripts/make_brand.py`; its developer diagrams (`by-the-numbers`, `harness`, `who-made-what`, `how-it-is-built`) count chapters, pictures, clips, skills, tests and commits from the checkout itself, so remake them (`make_brand.py developer`) when those change. Never take screenshots from a real learner folder.
