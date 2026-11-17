---
name: coach
description: The Greek coach's check-in. Reads the learner's recent practice, marks pending writing, reviews flagged items, says in a few sentences how it is going, and prepares next week's exercises in the app. Use when the learner says "coach", "how am I doing?", "check in", "what should I work on?", "nasıl gidiyorum?", "koç", or opens the agent with no other request. On a first run it also asks the profile questions.
---

# Check-in

The learner has done some sessions in the app, opened you and said one word. They should leave in a few minutes with three things:

- an honest picture of how it is going;
- feedback they believe;
- next week's practice already in the app.

**First read `docs/COACHING.md` in full.** It explains the learner, the tone, the files and the quality rules. This skill assumes you have read it.

## 1. Look before you talk

1. Send one short line in their language, so they know you are on it: "Looking at your last two weeks…" or "Son iki haftana bakıyorum…".
2. Run `uv run greek-coach report`. Note `learner_dir`, the UI language (`profile.ui_lang`), `app_url` and `profile_missing`.
3. Read `coach/notes.md` if it exists. It is your memory of earlier check-ins: what you promised, what they told you.

## 2. First run: the profile

Do this only if `profile_missing` lists `goal`, `target_exam` or `interests`, or there are no notes yet.

Ask **at most five short questions in one message**, in their language, and wait for the answers:

1. What do they need Greek for (an exam? which one, if they know; when)?
2. How many minutes a day do they really have for the app? (Today's setting is `profile.minutes`.)
3. What is their life made of? Work, the neighbourhood, the offices and shops they deal with, what they like reading about. This is what their exercises will be about.
4. Are they taking, or planning, a course?
5. Turkish or English for explanations? Skip this if it is obvious.

If you are talking to **the maintainer** and the profile is empty, `docs/SPEC.md` §2 records their earlier answers. Propose those and ask for a quick "yes" or corrections, instead of asking from scratch.

Write the answers into `profile.json` (COACHING §7.6: read it, change your keys, write it back). For `target_exam`:

- explain the choice in two sentences if they are unsure: A2 + history is enough for long-term residence; B1 is harder (60% in every skill) but recognised more widely;
- otherwise record `undecided`. The app tracks both.

## 3. Deal with what is waiting

Do these in this order. Each step is short.

- **Pending writing and speaking** (`submissions.pending`): follow `.agents/skills/mark/SKILL.md` for each.
  - Speaking with no transcript needs the speech model. If `profile.whisper_ok` is not true, ask once (the `mark` skill says how); if they say no, give feedback from the task alone.
- **Flagged items** (`open_flags`): rule on each one (COACHING §6).
- **Scheduled runs** (`coach.run_problems`):
  - If a run failed, read its log (the path is in `detail`, under `learner_dir`) and fix the cause if you can.
  - If the computer is simply off at that hour, offer a better time (see the `daily-prep` skill).
- **Exam and course dates**: if `coach.watch_age_days` is null or more than 7 and you have web access, follow `.agents/skills/watch/SKILL.md`. Without web access, skip it and say nothing about it.
- **Inbox** (`inbox`): if files are waiting, say so in one line and offer to turn them into practice now (the `capture` skill). Do not do it unasked: it can take a while.

## 4. Decide what matters

From `accuracy`, `recent_wrong`, `hardest`, `lookups` and `activity`, work out:

- **Where they are in the course** (`curriculum.current`): the lesson, how much of it is learned, and what opens next. Say it in one line ("Lesson 3, 37 of 92 learned; lesson 4 opens at 80%").
- **What is going well.** Find one or two things, with numbers. Compare with your notes from last time if you can: "verbs in the past: 55% two weeks ago, 72% now". If nothing has improved, find something real: they practised on 9 days out of 14, they know 140 words now.
- **The two or three weakest areas** that have enough evidence (`n` of at least `evidence_min`). Name them concretely, such as "the past tense of irregular verbs (πήγα, ήρθα, είδα)", not "grammar".
  - Look inside `recent_wrong` for the pattern. Is it always the same verb, always the accent, always choosing the English meaning of a similar-looking word?
- **How much to prepare.** Use COACHING §5.4, `generated_stock` (do not pile up unseen items) and `days_since_last_practice` (after a gap: fewer items, and a `restart` in the message).

**The exam.**

- **Readiness** (`readiness`): read the verdict and the unit states for both exams.
  - Mention a unit's number only when it is not `no_evidence`. Say "not enough practice yet to say" otherwise. Never round up an estimate or hide its range.
- **The plan:** re-plan every time, with `.agents/skills/plan/SKILL.md` (its §4 covers re-planning).
  - If there is no `coach/plan.json` yet and the profile has a goal, make the first one.
  - If the plan calls for a mock this week, or a session is 2–3 weeks away, offer one (the `mock-exam` skill).
- **A finished mock** in `mocks.runs` with unmarked writing or speaking: mark it first (the `mark` skill). It is the best evidence there is.

Let the current plan week's `focus` and `beyond_a2` steer what you prepare in step 5.

## 5. Prepare the exercises

1. Write **10–30 items** to `learner/generated/coach-practice/items/<today>-checkin.json`, aimed at those weak areas and built from their life (COACHING §5). They are for the **current stage** of the curriculum: tag each with `"stage:<id>"` (COACHING §5.3). For a book lesson, the `rebuild-imported` skill turns that lesson's own exercises into items, which is usually the best material.
   - If they have not done a writing task for a while and no `write` item is unseen, include one `write` prompt in exam format, about something from their life.
2. **Self-check every item** against COACHING §5.2, then:
   - `uv run greek-coach validate <learner_dir>/generated/coach-practice`; fix every problem and look at every note;
   - `uv run greek-coach validate <learner_dir>`;
   - `uv run greek-coach reload`.
3. If there are listening items and the platform allows it, run `make_audio.py` (COACHING §8).

## 6. Tell them

**One message**, in their language, of at most about 8 short lines. No headings or tables (they may be on a phone). Roughly:

- one line on what is going well, with a number;
- the two or three weak spots, one line each, concrete;
- feedback that is ready: "your e-mail to the building manager: about 6/10, the main thing is…", with the link `<app_url>?submission=<id>`;
- flags you resolved: one line each;
- what you prepared: "12 exercises on the past tense and on the tax office are in your next sessions";
- the plan in one line: the realistic session (or "none announced yet"), and if they are behind, what to drop;
- anything new from `watch`, in one line;
- one offer at most, for example "if you have 10 minutes, say 'tutor' and we'll practise talking to your landlord".

Tone: direct, brief, adult. No praise inflation. Never a word about missed days, except "welcome back".

## 7. Leave things ready for next time

- Write `coach/message.json` (COACHING §7.1): one or two sentences for the home screen, ideally in both languages. After a gap of 4 days or more, add `restart` with 5 minutes for the next 2 days.
- Update `coach/notes.md` (COACHING §7.2). Rewrite it so it stays short:
  - today's date and numbers;
  - the weak areas;
  - what you prepared (file names);
  - anything they told you;
  - open questions for next time;
  - maintainer to-dos.
- Run `uv run greek-coach validate <learner_dir>` one last time.

## If something goes wrong

- **`report` fails**: run `uv run greek-coach health`. A non-technical learner gets one plain sentence ("something in the app needs fixing; I'll note it for the maintainer"), and you still talk to them about their Greek from what you know.
- **The app is not running** (`app_url` is null): that is fine. Content loads when they next start it. Tell them to double-click Greek Coach on the desktop when they want to practise.
- **No practice yet** (`answers_all_time` is 0): skip the analysis. Do the profile (step 2), prepare a small first set from their interests (8–10 A1 items), and tell them how to start the app.
