# Phase 5 — Exam mode

Read `AGENTS.md` and `docs/SPEC.md`, in particular the verified description of the exam and how its sections map to exercise types. The app and the coach work for daily study. This session points them at the exam.

Before building, check the official sources again for the current format, dates and sample papers, since these change, and update the spec if anything differs.

## Build

- **An exam blueprint** in the repo: the sections, task types, timings, marking and pass conditions, as structured data with links to the official sources. This is fact about a public exam and can be tracked. Official sample papers themselves are linked, or imported privately by the learner; do not redistribute them.
- **Coverage tagging.** Every exercise type and content item is tagged with the exam skill and task type it trains, so the app can say what has and has not been practised.
- **Readiness view.** For each exam section: an honest estimate of where I stand, the evidence behind it, and how much practice it rests on. Where there is too little data to say, show that instead of a number. I will be making decisions about when to book the exam from this screen, so false confidence is worse than no estimate.
- **Mock exams.** A timed run in the real format, section by section, assembled by the coach from generated and private material. Automatically checkable sections are scored at once; writing waits for the coach; speaking is handled in whatever way the spec decided. Results feed the readiness view.
- **A plan to the exam date.** The coach works backwards from the date and my weekly time budget to a week-by-week plan, shows whether the target is realistic, and re-plans at each check-in from what actually happened. If I am behind, it says so plainly and tells me what to drop.
- **Exam technique.** Short, practical guidance per section: how the task works, how to spend the time, typical traps.

The spec tracks two exams, and the data decides which to book. Build both blueprints:
- `exams/b1-keg.json` (Ελληνομάθεια B1). Pass rule: at least 60% in each of the four skills.
- `exams/a2ltr.json` (A2 plus history and culture for long-term residence). Pass rule: at least 50/100 and half marks in four of the five units. Read its speaking format from the 2026A oral paper and record it in the spec.

Readiness must apply each real pass rule, side by side. The coach can download the official past papers and listening MP3s into `content/private/` for mock exams, after asking me.

Cover the level gap to B1. Use the ΚΕΓ structure table and level descriptors to list what B1 adds over A2 in grammar, vocabulary domains, text length (150-word writing tasks) and task types (`table_fill`, note-taking), and have the coach schedule that material through the plan. Build a history and culture pack from the official syllabus text only when the plan points at an A2-LTR session. Keep the downloaded syllabus in `content/private/` and write the items in your own words.

The plan must use the real dates in `learner/coach/watch.json` and say plainly which session is realistic.

## Verify

Run a complete mock exam yourself in the browser, including the timing behaviour and an interrupted section. Check the readiness numbers against the simulated history by hand for at least one section.

## Done when

I can look at one screen and know whether I would pass today, per section, and what the next four weeks should contain.
