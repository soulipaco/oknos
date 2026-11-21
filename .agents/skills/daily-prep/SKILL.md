---
name: daily-prep
description: Prepare tomorrow's Greek practice ahead of time. Writes fresh exercises (a short news-style text at the learner's level, verbs they need, leftovers from captured material), marks pending writing, and can be set up to run by itself every day. Use when it runs on a schedule, or when the learner says "prepare tomorrow", "get tomorrow ready", "set this up to run every morning", "yarını hazırla", "her sabah kendiliğinden hazırlasın".
---

# Daily prep

Fresh content every day, without the learner having to open you. This skill runs in one of two ways:

- **Scheduled.** `oknos run daily-prep` starts you headless, and the environment variable `OKNOS_SCHEDULED_RUN` is set. **Nobody is watching.** Never ask a question and never wait for an answer. Anything that needs the learner's yes (a download, a profile change) goes into `coach/notes.md` under "to ask at the next check-in". The wrapper writes the line in `coach/runs.log`, so do not write it yourself. Finish with a short plain summary of what you wrote: it goes into the run's log.
- **On request** ("prepare tomorrow"). The same steps, and you can talk to them.

**First read `docs/COACHING.md`.**

## Steps

1. Run `uv run oknos report`. Read `coach/notes.md`.
2. **Mark pending writing** with `.agents/skills/mark/SKILL.md`.
   - In a scheduled run, transcribe speaking only if `profile.whisper_ok` is true and the model is already downloaded (no `--download`). Otherwise leave it for the check-in.
3. **Decide how much to write:**
   - `generated_stock` shows more than about 40 unseen items in coach packs: write nothing new today. It would only pile up. Note it and stop after step 2.
   - The learner has not practised for 3 days or more (`activity.days_since_last_practice`): write at most 5 items. A big pile is the last thing they need.
   - Otherwise write **8–15 items**.
4. **What to write**, in `<learner_dir>/generated/coach-practice/items/<tomorrow's date>-prep.json`. Write for the curriculum's current stage (`curriculum.current` in the report) and tag each item `"stage:<id>"` (COACHING §5.3). If `coach/plan.json` exists, also aim at the current week's `focus` units and its `beyond_a2` points, and tag exam-format items with their `exam_task` (COACHING §5.1):
   - **One news-style reading text at their level** (`true_false` or `gap_bank`, 60–120 words), about something from their life or their city. You may look at today's real Greek news headlines for a topic if you have web access, but **write the text yourself**: original, simple and at their level. Never copy an article.
   - **Verbs** for the weakest `accuracy.grammar` tags or `verbs.*` areas: 3–6 `form` items, in new sentences.
   - **Leftovers**: anything noted in `coach/notes.md` as "to practise" (a class topic, words from a capture or tutor log).
   - About once a week (no `write` item unseen, and none submitted in 7 days): one `write` prompt in exam format.
5. Self-check every item (COACHING §5.2), then:
   - `uv run oknos validate <learner_dir>/generated/coach-practice`;
   - `uv run oknos validate <learner_dir>`;
   - `uv run oknos reload`.
6. **Update `coach/notes.md`** with one line: the date, what you prepared, and anything left for the check-in.
7. **The home-screen message.** Leave `coach/message.json` alone if it is less than 3 days old (the check-in wrote it). Otherwise, if you marked something, write a one-line message, e.g. "Your writing feedback is ready."

## Setting up the schedule

Do this only when the learner asks, or says yes to an offer from a check-in. It is standing configuration on their computer, so:

1. **Explain in two sentences**, in their language: every day at a time they choose, the computer starts the agent in the background, which prepares the next day's exercises. It uses their subscription a little, and it runs only while the computer is on.
2. **Ask when their computer is usually on and awake.** 05:00 is useless on a laptop that sleeps at night; lunchtime or early evening often works better.
3. **On a clear yes**, run:
   ```
   uv run oknos schedule add daily-prep --at HH:MM
   ```
   Add `--agent codex` if they use Codex rather than Claude Code.
4. Run `uv run oknos schedule list` and **show them what was created**, in plain words: "a Windows scheduled task called 'Oknos daily-prep', every day at 18:30".
5. Tell them how to stop it: "just tell me 'stop the daily prep'", and you run `uv run oknos schedule remove daily-prep`.
6. **Do a test run right away** with `uv run oknos run daily-prep`. Tell them it takes a few minutes, then check the `ok`/`failed` line it prints.
   - The scheduled run uses the agent's **command-line** program (`claude` or `codex`). The desktop app's sign-in does not always carry over to it.
   - If the line says `last=Not logged in` (or similar), the command-line program needs signing in once. Open a terminal for them if your harness can, or ask them to open one. Have them type `claude` (or `codex`) and follow the sign-in it shows, then run the test again.
   - Until a test run says `ok`, tell them plainly that the schedule exists but cannot work yet.

**If a run fails,** the home screen says so: the app reads `coach/runs.log` and `coach/schedule.json`. At the next check-in:

- read the log named in the failed line;
- fix what you can (a missing agent on PATH, an expired login: tell them in plain words what to do);
- if the computer is just off at that time, offer to move it.
