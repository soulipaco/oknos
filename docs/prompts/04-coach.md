# Phase 4 — The coach

Read `AGENTS.md`, `docs/SPEC.md` and the "agent is the AI" section of `docs/DESIGN.md`. The app now runs a daily session on its own. This session builds the other half: the behaviour of the agent when the learner opens it.

The app contains no language model. Everything that needs judgement (writing feedback, new exercises, planning) is done by whichever agent the learner is running, working from files in `learner/` and writing results back for the app to display. What you are building here is therefore mostly instructions for a future agent, plus the small pieces of app and tooling those instructions rely on. Write those instructions for a capable reader with no memory of this project: explain the learner, the purpose of each flow and what good output looks like, and leave the judgement to them. Put them where both Claude Code and Codex will find them, as the spec decided.

## Flows

- **Check-in.** The learner opens the agent and says something like "how am I doing?" or just "coach". The coach reads recent attempts, the profile and its own previous notes, then tells them in a few plain sentences what is going well, what the two or three weakest areas are, and what it has prepared. It then writes a small set of new exercises aimed at those weak areas into `learner/generated/`, which appear in the next daily session. It ends by updating its notes for next time.
- **After class.** I am enrolling in a language course. After a lesson I want to say "today we covered the past tense of these verbs and vocabulary about the doctor", or drop in a photo or handout, and get practice on exactly that in my next sessions. Handouts are private content.
- **Writing.** The app offers a writing prompt of the kind the exam uses and saves what I write. Next time the coach is open, it marks the piece against the exam's criteria, corrects it, explains the two or three most important errors (not all of them), and turns recurring errors into exercises. The feedback is shown in the app next to the original.
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
