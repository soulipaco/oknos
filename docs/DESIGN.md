# Design

This is the starting point, written before any code. Phase 1 turns it into `docs/SPEC.md` after interviewing the maintainer and verifying the open questions at the bottom. Where a decision here turns out to be wrong, change it there and say why.

## Who it is for

**Primary user: the maintainer.** A BI analyst who has lived in Greece for eight years, has never managed to learn Greek, and says plainly that it feels hard and that he does not want to do it. He needs to pass a B1-level exam to change his residence status and plans to enrol in a language course alongside the app. He is interested in AI and in data. He has existing A1–A2 material from an earlier project.

**Secondary user: a non-technical friend.** Installs an agent, says "set this up", and expects it to work. Cannot debug anything.

Two consequences shape everything else:

1. **Motivation is the real problem, not content.** A complete curriculum that he opens twice is a failure. A thin app he opens for ten minutes every day is a success. Sessions are short, start with one click, and are built from things in his actual life: work, bureaucracy, the neighbourhood, his own interests.
2. **The exam is the product goal.** Every feature should be explainable as "this moves an exam skill". The app should always be able to answer: how ready am I, per skill, and what should I do today?

## The core architectural idea: the agent is the AI

Every user of this app already has a capable agent on their machine, because that is how they install it. So the app itself contains **no LLM calls and needs no API key**. Work is split in two:

| | Web app | Agent (coach) |
|---|---|---|
| When | Daily, on its own | Occasionally, when the learner opens the agent |
| Does | Presents exercises, checks answers deterministically, schedules reviews, records every attempt, shows progress | Reads the learner's records, generates new content, marks free writing, plans the week, runs mock exams, imports material |
| Needs | A browser | A Claude Code / Codex session |

They communicate only through files on disk. The app writes what the learner did; the agent reads it and writes new content and feedback that the app then shows. This keeps the app simple, free to run, and usable when the agent is closed. It also means the coach improves automatically as agents improve.

The coach's behaviour lives in the repo as agent skills and commands (for example: set up, daily check-in, after-class, mark my writing, mock exam, import material), described in `AGENTS.md` terms so that more than one harness can follow them.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Runtime | Python, managed by `uv` | `uv` installs the right Python by itself, so setup is one tool and one command on Windows, macOS and Linux. The maintainer reads Python. |
| Server | FastAPI on `localhost` | Small, well known to every agent, serves both the API and the static front end. |
| Storage | SQLite file in `learner/` plus plain Markdown/JSON files for coach notes and feedback | SQLite ships with Python. Files are what agents read best. Backup is copying one folder. |
| Front end | Plain HTML, CSS and JavaScript modules, no build step | No Node, no bundler, nothing to compile on the friend's laptop. Any small library is vendored into the repo. |
| Audio | Browser speech synthesis for Greek to begin with | Zero install. Quality and voice availability need checking per OS; see open questions. |

Rejected: a React/Vite front end (build step and Node for no benefit at this size), Electron or a desktop wrapper (heavy, installer problems), calling an LLM API from the app (needs keys and money, and duplicates the agent), browser `localStorage` for progress (the agent cannot read it).

## Content

Content comes in **packs**: a folder with a manifest (title, level, licence, source) and items in one documented JSON schema. Exercise types should map onto exam tasks, not onto whatever a textbook happened to contain.

- `content/open/` — tracked. Original or openly licensed material only. The public repo must be useful with this alone.
- `content/private/` — gitignored. The learner's own textbook, course handouts, past papers.
- `learner/generated/` — gitignored. Written by the coach for this learner, in the same pack format.

**The earlier project.** `Greek_Helper` (a folder on the maintainer's machine, outside this repo) holds OCR of a commercial A1–A2 textbook, word lists, audio and transcripts, already processed into `data/app/` (25 lessons, about 3,200 vocabulary items, 281 practice items). It is copyrighted and cannot be published. It is imported as a private pack by an importer script that lives in this repo; the data itself does not. Its vocabulary list is the most immediately valuable part. Its practice items are OCR-derived and noisy, so treat them as raw material for the coach to rebuild, not as finished exercises.

**The B1 gap.** Existing material stops at A2. B1 content has to come from the exam specification, openly available sample papers (linked or imported privately, not redistributed), the course he enrols in, and coach-generated exercises checked against the specification.

## Learner data

Everything about the learner lives in `learner/` and is gitignored: the SQLite database (attempts, review schedule, session history), a profile the coach maintains (goal, exam date, interests, known weak points), writing submissions with feedback, and coach notes from one session to the next. The folder must be safe to copy to another machine and keep working.

## Open questions for phase 1

1. **Which exam exactly?** "B1 for changing residence status" could mean the Certificate of Attainment in Greek (Ελληνομάθεια) at B1 from the Centre for the Greek Language, the citizenship knowledge certificate (ΠΕΓΠ), or the language-and-history requirement for long-term residence, which may be set at a different level. They differ in format, sections, pass marks and dates. Confirm from official sources and with the maintainer's lawyer or the relevant office before designing the exam mode.
2. **Exam date and weekly time budget.** These set the pace of the plan.
3. **Course details.** Which course, which textbook, how often. The "after class" flow should fit it.
4. **Speaking and listening.** How far can local, free tooling go? Check Greek voice availability for browser speech synthesis on Windows and macOS, and whether speaking practice is realistic in the first version or should be left to the course.
5. **Interface language.** English, Turkish, or both? The friend may need Turkish.
6. **Licence** for the code, and the licence for original content packs.
7. **Which harnesses are supported on day one.** Claude Code certainly; verify what Codex needs to follow the same setup and coach instructions.
