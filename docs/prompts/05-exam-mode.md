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

Also cover the level gap: my imported material ends at A2. Use the exam's published syllabus or level descriptors to list what B1 adds in grammar, vocabulary domains and task difficulty, and have the coach schedule that material through the plan.

## Verify

Run a complete mock exam yourself in the browser, including the timing behaviour and an interrupted section. Check the readiness numbers against the simulated history by hand for at least one section.

## Done when

I can look at one screen and know whether I would pass today, per section, and what the next four weeks should contain.
