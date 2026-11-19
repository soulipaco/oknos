# Build prompts

Each file is one prompt for one fresh agent session, run from the repo root. Paste the whole file. Run them in order; each phase ends with something you can check yourself before moving on.

| Phase | File | Ends with |
|---|---|---|
| 1 | `01-spec.md` | `docs/SPEC.md`, agreed with you. No code. |
| 2 | `02-walking-skeleton.md` | A fresh clone installs with one sentence and runs one real exercise end to end. |
| 3 | `03-import-and-study-loop.md` | Your old A1–A2 material imported privately; a daily session worth opening. |
| 4 | `04-coach.md` | The agent acts as coach: check-in, after-class, writing feedback. |
| 5 | `05-exam-mode.md` | Readiness per exam skill, mock exams, a plan to the exam date. |
| 5c | `05c-book.md` | A chapter to read before each stage's practice; new words taught before they are tested; the chapter-writing procedure. |
| 5d | `05d-every-word.md` | Every Greek word you can tap has a meaning (forms, rubric words, names); no question hidden behind "Translate"; plus the day's other adjustments. |
| 6 | `06-friend-test.md` | Proof that a stranger's machine can install it. Optional: deferred by the maintainer on 2026-11-19. |

How to use them:

- Start every phase in a **new session**, so the agent works from the repo's documents and not from a long chat history. If a phase needs something the documents do not say, the fix is to update the documents.
- Use plan mode for phases 2 to 5 and read the plan before approving it.
- Commit at the end of each phase. A phase that went badly is then one `git reset` away from a clean retry.
- After each phase, use the app for a few days before starting the next. What annoys you is better input than anything planned in advance; add it to the next prompt.
