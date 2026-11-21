# Phase 4 — The coach

Read `AGENTS.md`, `docs/SPEC.md` and the "agent is the AI" section of `docs/DESIGN.md`. The app now runs a daily session on its own. This session builds the other half: the behaviour of the agent when the learner opens it.

The app contains no language model. Everything that needs judgement (writing feedback, new exercises, planning) is done by whichever agent the learner is running, working from files in `learner/` and writing results back for the app to display. What you are building here is therefore mostly instructions for a future agent, plus the small pieces of app and tooling those instructions rely on. Write those instructions for a capable reader with no memory of this project: explain the learner, the purpose of each flow and what good output looks like, and leave the judgement to them. Put them where both Claude Code and Codex will find them, as the spec decided: canonical in `.agents/skills/<name>/SKILL.md`, with Claude Code pointers in `.claude/skills/`. The coach reads learner data through `oknos report`, never by writing to the database. Explanations and feedback go in the learner's UI language (Turkish or English).

## Flows

- **Check-in.** The learner opens the agent and says something like "how am I doing?" or just "coach". The coach reads recent attempts, the profile and its own previous notes, then tells them in a few plain sentences what is going well, what the two or three weakest areas are, and what it has prepared. It then writes a small set of new exercises aimed at those weak areas into `learner/generated/`, which appear in the next daily session. It ends by updating its notes for next time.
- **Capture (class and real life).** Real-life material matters more than class for me. I drop a photo of a notice, a letter or a menu in `learner/inbox/`, or tell the tutor about it from my phone, and it becomes practice. Replace personal data in real documents with invented details before it becomes an exercise. The class side: I am enrolling in a language course when an evening one opens (see the spec). After a lesson I want to say "today we covered the past tense of these verbs and vocabulary about the doctor", or drop in a photo or handout, and get practice on exactly that in my next sessions. Handouts are private content.
- **Writing.** The app offers a writing prompt of the kind the exam uses and saves what I write. Next time the coach is open, it marks the piece against the exam's criteria, corrects it, explains the two or three most important errors (not all of them), and turns recurring errors into exercises. The feedback is shown in the app next to the original.
- **Tutor.** Live chat practice in the agent: role-plays (landlord, office clerk, doctor), "correct this sentence", grammar explained in Turkish. It stays at my level, keeps turns short, and ends by writing a log and turning new words and errors into review items. It must work when I drive the session from my phone.
- **Daily prep and watch, on a schedule.** `daily-prep` writes tomorrow's fresh content and marks pending work. `watch` checks the official exam pages and the course page for new dates and registration windows and writes `learner/coach/watch.json` for the home screen. Set the schedule up only after I agree, show me what was created, and make a failed run visible rather than silent.
- **Speaking feedback.** Transcribe my recordings locally with faster-whisper (ask before the model download) and give "what I heard" feedback, shown in the app.
- **Rebuilding imported material.** The practice items set aside in phase 3 are raw material. Give the coach a way to turn a lesson's worth of them into clean, checkable exercises, privately.
- **Profile.** On first run the coach asks the learner a few questions (goal, exam date, time per day, interests, interface language) and keeps the profile current afterwards.

## Things that matter

- **Generated Greek must be correct.** A learner cannot tell when the coach is wrong. Have the coach check what it generates: validate against the pack schema, re-read every item for a single unambiguous correct answer, and keep the level within what the learner has covered. Give the app a way for the learner to flag an item as wrong or confusing, and have the coach review flagged items at the next check-in.
- **Tone.** I am someone who has avoided this for eight years. The coach is direct and brief, treats me as an adult, notices real progress, and does not guilt me about missed days. When I have been away, it makes the next session smaller, not larger.
- **My interests are the content.** New material should be built from my life as recorded in the profile: work, data, dealing with Greek offices, the neighbourhood. Generic textbook sentences are the fallback.
- **The learner may be my non-technical friend.** Every flow must work through conversation alone.

## Verify

Play the learner yourself: with a few weeks of simulated attempts in a scratch `learner/` folder, start a fresh agent session that has only the repo's instructions and say "coach". Check that it follows the flow, that the generated items validate and show up in the app, and that a writing submission comes back with feedback visible in the browser. Read the generated Greek critically and tell me how good it was.

## Done when

I can finish a week of sessions, open the agent, say one word, and leave with feedback I believe and next week's practice already in the app.
