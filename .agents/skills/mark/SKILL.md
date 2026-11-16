---
name: mark
description: Mark the learner's Greek writing or speaking against the exam's criteria. Corrects the text, explains the two or three errors that matter most, estimates the exam score, and turns recurring errors into exercises; the feedback appears in the app next to the original. Use when the learner says "mark my writing", "check my e-mail", "listen to my recording", "yazımı değerlendir", "kaydımı dinle", or when a check-in or daily prep finds pending submissions.
---

# Marking writing and speaking

The learner wrote or recorded something in the app (a `write` or `speak` card). The app saved it as a submission. Your job is feedback they will believe and use:

- not every error, but the few that matter;
- explained in their language;
- shown in the app next to what they wrote.

**First read `docs/COACHING.md`**, especially §2 (tone), §7.3 (the feedback file) and §10 (the exam criteria).

## 1. Find what is waiting

Run `uv run greek-coach report` and look at `submissions.pending`. Each entry has:

- `submission_id` and `item_key`;
- `task` (the prompt, word range and required points);
- `text` (writing) or `transcript` (speaking);
- `feedback_file`, the path to write.

Also read the earlier files in `<learner_dir>/feedback/`. Recurring errors across pieces are the most useful thing you can point out.

## 2. Writing

For each piece:

1. **Read the task and the text twice.** Work out what they were trying to say before you judge how they said it.
2. **Correct it minimally.** `corrected` is *their* text with the errors fixed: same ideas, same simple structures, Greek a native speaker would accept. Do not rewrite it into your own style. If a sentence cannot be understood, write the closest correct version of what they probably meant.
3. **Choose the 2–3 errors that matter most** for `errors`. In order of priority:
   - errors that block or change the meaning;
   - errors at their level that recur (in this piece, in earlier feedback or in `recent_wrong`);
   - errors the exam's criteria weigh: register (formal "Αγαπητέ κύριε… / Με εκτίμηση" vs friendly), and missing required content.

   Leave small slips out of `errors`. They are fixed silently in `corrected`, and the app highlights every change.
4. **For each error:**
   - `original`: their words, short;
   - `fix`: the corrected words;
   - `why`: one or two sentences in their language, with the rule in plain words and an example if it helps. Example: "σε + το → στο: after σε the article joins it: στο γραφείο, στη δουλειά."
5. **Score it** against the target exam (COACHING §10):
   - which `must_include` points are present;
   - word count against `words`;
   - then the band.

   Put the per-aspect view in `score.criteria`, with short comments in their language. Keep `unverified: true` for A2-LTR. Give a whole or half point, never false precision.

   Set `score.exam` (the blueprint id) and `score.task` (the item's `exam_task`). Score on **that task's scale** in the blueprint: A2-LTR e-mails out of 10, B1 part A out of 12, B1 part B out of 13 (COACHING §10). These scores are the only way writing reaches the readiness screen.
6. **`summary`**: one or two sentences in their language. Start with what worked, then the one thing to do differently next time.
7. **Turn recurring errors into practice.** If an error appears for the second time or more, or is a core A2 point, write 3–8 items in `<learner_dir>/generated/coach-writing/items/<today>-sub<id>.json`:
   - `form` items for the form;
   - a `gap_bank` for the connector or preposition;
   - one `mcq` for register.

   Use sentences close to theirs, about the same topic. Self-check, validate, reload (COACHING §4), and list the new item keys in `exercises`.
8. **Write `<learner_dir>/feedback/<submission_id>.json`** (COACHING §7.3). Then run `uv run greek-coach validate <learner_dir>` and `uv run greek-coach reload`. The app marks the submission as done and shows "Feedback is ready" on the home screen.

## 3. Speaking

1. **Get a transcript.** If `transcribed` is false:
   - If `profile.whisper_ok` is not true, ask once, in their language: "To listen to your recordings I need a free speech-recognition model, about 0.5 GB. It runs only on this computer; nothing is sent anywhere. Shall I download it?" On a yes, set `"whisper_ok": true` in `profile.json`. On a no, give feedback on the task and the model answer only, and say you could not listen.
   - Run `uv run --group speech greek-coach transcribe`. If it says the model is not downloaded and they said yes, run it again with `--download`. The first run also installs the speech package, which takes a few minutes.
2. **Remember what a transcript is.** It is what a machine heard, and beginners' Greek is hard for it. An odd word may be the recogniser's mistake, not theirs. Treat a word as their error only when the transcript makes sense otherwise and the error is a typical learner error (a wrong ending, a wrong article).
3. **Write the feedback** with `kind: "speaking"`:
   - `heard`: the transcript, verbatim;
   - `summary`: did they do the task? How much did they manage to say?
   - `errors`: at most 3 clear grammar or word errors;
   - `corrected`: a better way to say what they said, at their level.
   - No pronunciation score, ever. You may mention one word that was clearly not understood ("I heard 'κάθε' where you probably said 'καφέ'"), framed as what the machine heard.
   - Leave `score` out unless the task is in exam format (it has an `exam_task`). Then score it on that task's scale in the blueprint, with `score.exam`, `score.task` and `"unverified": true`, because neither exam publishes its speaking criteria. Judge whether they did the task and how much they could say, never pronunciation (COACHING §10).
4. Validate and reload as for writing.

## Mock exams

Submissions from a mock (the report's `mocks.runs` lists the sections with `waiting_for_coach`) are marked the same way. The scores matter more there: the mock's result and the readiness screen wait for them. Mark them before anything else in the check-in.

## 4. Tell them

In their language, at most about 4 lines per piece:

- the estimate (for example "about 6 of 10");
- the one thing that worked;
- the main fix;
- the link `<app_url>?submission=<id>`, where they can see the original and the correction side by side.

If you wrote exercises, say they are in the next sessions.

## Quality check before you finish

- Is every Greek word in `corrected` right? Re-read it against COACHING §5.2. A wrong correction is the worst possible feedback.
- Are there at most 3 `errors`, and does each `why` make sense to someone with no grammar terms?
- Is everything the learner reads in their UI language?
