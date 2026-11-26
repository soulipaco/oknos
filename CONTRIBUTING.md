# Contributing to Oknos

Thank you for wanting to make Oknos better. Fixes to the Greek are as welcome as fixes to the code, and you do not need to be a programmer to send one.

There are three ways to help:

- **Tell us about an error.** Open an issue: [a bug in the app](https://github.com/soulipaco/oknos/issues/new?template=bug.yml), [an error in the Greek or the teaching](https://github.com/soulipaco/oknos/issues/new?template=content.yml), or [an idea](https://github.com/soulipaco/oknos/issues/new?template=idea.yml).
- **Fix the content:** the Greek, the exercises, the chapters, the meanings.
- **Fix or extend the code.**

Questions and longer talks go to [Discussions](https://github.com/soulipaco/oknos/discussions). A security problem goes through [SECURITY.md](SECURITY.md), not an issue.

## Found an error in the Greek?

Inside the app, the ⚑ flag on an exercise or a chapter section sends the problem to the learner's own coach (their agent on their computer). It never reaches us. So if you found the error in the open content, please also open a [content issue](https://github.com/soulipaco/oknos/issues/new?template=content.yml): say where it is (the lesson and the Greek text, or the file and the item id), what is wrong, the correction, and a source if you have one. A native speaker's "this sounds wrong" is useful too.

## Content

The open content lives in `content/open/`. Each folder is a pack with a `pack.json` that names its licence.

- **Exercises and words:** `content/open/<pack>/items/*.json`. Each item has an `id`; keep it when you fix an item, because learners' progress is tied to it. The formats are in `schemas/item.schema.json` and `docs/SPEC.md`.
- **Chapters of the books:** `content/open/oknos-book/lessons/<stage>.json` (the 26-lesson book) and `content/open/open-book/lessons/<stage>.json` (the shorter open course). How a chapter is built and reviewed is in `docs/LESSONS.md`; the format is `schemas/chapter.schema.json`.
- **Meanings of tappable words:** a pack's `glossary.json` (`words`, `forms`, `names`, and `leave` for words left unexplained on purpose, with a reason). Every Greek word shown in the app must have a meaning in Turkish and English.

Check your change before you send it:

```
uv run oknos validate content/open
```

This checks each pack and chapter against its schema, runs the Greek lint (Latin look-alike letters inside a Greek word, polytonic accents, text not in Unicode NFC, a final σ or an inner ς; as a note, a longer word with no accent), checks the exam-task tags, finds tappable words with no meaning, and finds translations that ask something the Greek does not. Problems must be fixed. Notes are worth reading but do not fail the check. `uv run oknos words content/open/<pack>` lists the words of a pack that have no meaning yet.

To see your change in the app, run `uv run oknos start` (or `uv run oknos reload` if it is already running) and open the lesson.

Two things to know:

- **The voice.** The open texts come with recorded clips in `content/open-voice/`. If you change a Greek text, its old clip no longer matches; `validate` notes this, and the browser voice reads the new text until the maintainer remakes the clips. You do not need a voice service to contribute.
- **Who checks the Greek.** Much of the content was written by AI models and reviewed by other models, not by a person (see `docs/BUILT-WITH-AGENTS.md`). A fix from someone who knows Greek well is exactly what it needs.

## Code

You need [uv](https://docs.astral.sh/uv/) and nothing else, not even Python.

```
uv sync
uv run pytest
uv run oknos guard
```

`docs/DEVELOPING.md` has all the commands and how the code is laid out. The server is FastAPI with SQLite (`src/oknos/`); the front end is plain HTML, CSS and JavaScript with no build step (`web/`), with the English and Turkish strings in `web/i18n/`. After a change to `src/` or `web/`, restart the app: `uv run oknos stop; uv run oknos start`.

Add a test for what you change where you can. The tests use only the open content and a throwaway learner folder; they need no keys, no agent and nothing from `content/private/`.

## Rules that must hold

These are checked in review, and some of them by CI:

- **Nothing from `learner/` or `content/private/`.** Both are gitignored: they hold a learner's own record and their private material. `uv run oknos guard` fails if git tracks anything there.
- **No local user paths.** Write `C:\Users\you` or `/home/you`, never your own user name. The guard checks this too.
- **Original or openly licensed content only.** Code is under MIT (`LICENSE`); content is under CC BY-SA 4.0 (`content/open/LICENSE.md`). Never copy from a textbook, a course, a past exam paper or a word list's own glosses, even a short passage. Write your own example sentences. If you add something under another open licence, record the source and licence in the pack's `pack.json`. By sending a pull request you agree that your work is shared under these licences.
- **Few dependencies.** Every dependency is one more thing that can fail on a stranger's laptop. Add one only when it clearly earns its place, and say why in the pull request.
- **The app works without an agent.** The daily study must run with the web app alone. An agent may prepare content ahead of time, but no screen may need one.
- **Local only.** No accounts, no telemetry, no service that holds learner data. The app listens on `127.0.0.1`.
- **Greek is UTF-8 everywhere**, including on Windows consoles and in SQLite. Use the Greek letters themselves, never look-alike Latin ones, and monotonic accents only (`validate` catches both).

## Working with an agent

Oknos is built and run by coding agents, and you are welcome to use one too. Start it in the repository: it reads `AGENTS.md`, the instructions every agent here follows, and the skills in `.agents/skills/` (for example `write-chapter` for the book's chapters). A pull request made with an agent is fine, as long as you have run the checks yourself and read the whole diff. You are the one sending it.

## Sending a pull request

1. Fork the repository on GitHub and clone your fork.
2. Make a branch for your change: `git switch -c fix-lesson-5-dative`.
3. Make the change, then run the checks:
   ```
   uv run oknos guard
   uv run pytest
   uv run oknos validate content/open
   ```
4. Push the branch to your fork and open a pull request to `main`. The template asks a few short questions.
5. CI runs the same three checks on Ubuntu and Windows. It must pass before the change is merged.

Keep a pull request to one change: one fixed chapter, one new exercise set, one bug. Small ones are reviewed faster.

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
