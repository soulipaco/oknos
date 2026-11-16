---
name: plan
description: Make or update the learner's week-by-week plan to a real exam session, working backwards from the announced dates and their actual weekly time. Says plainly whether the target is realistic and, if they are behind, what to drop. Use when the learner says "make me a plan", "am I on track?", "when can I take the exam?", "which exam should I book?", "bana bir plan yap", "sınava yetişir miyim?", "hangi sınava gireyim?", and at every check-in (the coach skill calls it).
---

# Plan to the exam

The learner will decide which session to book, and when, from this plan and the readiness screen. **An optimistic plan is worse than none.** It wastes a fee, a sitting and their confidence. Your job is arithmetic and honesty, then a concrete four weeks.

**First read `docs/COACHING.md`** (§2 tone, §7 files, §11 the plan file).

## 1. Get the facts

1. Run `uv run greek-coach report`. You need:
   - `plan_inputs`: candidate sessions from `watch.json` (date, registration window, `weeks_left`, `hours_at_pace`, `hours_needed`, `hint`), the real pace, the budget and `exams_without_announced_date`;
   - `readiness`: the state of each unit of each exam, and the verdict;
   - `coverage`: what has and has not been practised per exam task, and B1's `beyond_a2` list;
   - `plan_progress`: the previous plan's weeks, planned against done (null on a first plan).
2. If `plan_inputs.watch_checked_at` is missing or more than 7 days old and you have web access, run the `watch` skill first. **A plan uses only dates from `watch.json`.** Never use a date from memory or from this file.
3. Read `exams/a2ltr.json` and `exams/b1-keg.json` for each unit's points, minutes and tasks.
4. If `profile.minutes` or `profile.days_per_week` is missing, ask once ("How many minutes a day, and on how many days a week, can you really give the app?"), and write both into `profile.json`. For the maintainer, `docs/SPEC.md` §2 has the answer: about 20 minutes on weekdays.

## 2. Decide what is realistic

Do it session by session, earliest first:

- **The hours.**
  - `hours_needed` is ΚΕΓ's rough teaching-hour guide minus the hours practised so far.
  - `hours_at_pace` is what the remaining weeks give at the pace of the **last 4 weeks**, not the budget. Use the pace.
  - If there is no pace yet (`pace_measured` is false, a new learner), use `hours_at_budget` and `hint_at_budget`, and say that the budget is an assumption until a few weeks of practice show the real pace.
- **The hint.** `yes` / `tight` / `only_at_budget` / `no` is the app's crude check. You may be more pessimistic than the hint, never more optimistic, unless readiness already says `pass`.
- **Readiness.** A unit `below` with few weeks left is a red flag even when the hours add up. For B1, one weak skill fails the exam. For A2-LTR, one weak unit is survivable.
- **Registration.** If the registration window closes before the learner could reasonably decide (say in under 2 weeks) and the verdict is not `yes`, the session is not realistic.
- **No announced date** (`exams_without_announced_date`). Say so plainly: "No A2 + history session has been announced; the last two were in late 2024 and May 2026." Plan towards the level instead, and re-plan when `watch` finds a call.

Then write the verdict in one or two plain sentences, in both languages:

- "May 2027 B1 is not realistic: at your recent pace that is about 25 hours of practice, and the rough guide says 180 or more. The first session your numbers could make is …".
- When the arithmetic rules everything out for a year or more, say that too, and say what would change it (a course, more minutes).

**Never tell them to book.** That is their decision, and the legal question is for their lawyer (SPEC §1.1). You can say which session their numbers make realistic.

**Which exam the weeks aim at** (`exam` in the file):

1. The exam of the realistic target session, if there is one.
2. Otherwise, the one the learner has said they lean towards (profile, notes; the maintainer leans towards B1, SPEC §1.4).
3. Otherwise `b1-keg`: its four skills include everything A2-LTR's language units need.

History and culture is added only when an A2-LTR session becomes the target. Say in the verdict which exam the weeks aim at, and that A2 comes first either way.

**Sessions with no date yet** (B1 in October, any A2-LTR session) go into `options` with `session: null` and `realistic: "unknown"`, with a `why` such as "B1 October 2027: not announced; last year it was 23 October."

## 3. Write the weeks

Write `<learner_dir>/coach/plan.json` (COACHING §11). Weeks start on Monday; cover at least the next 8 weeks, or up to the session if that is sooner. Each week has:

- `minutes`: the real pace, rising gently to the budget at most. Not the budget if they have not been keeping it.
- `focus`: 1–2 unit ids of the target exam (or `foundations` for words and verbs). Choose units by readiness (the `below` and weakest `no_evidence` ones first) and by points per hour:
  - **A2-LTR history and culture** is 20 memorisable points. Schedule it in the last 6–8 weeks before an A2-LTR session, once a date exists (see §5).
  - **B1** needs all four skills at 60%. Do not let one skill wait until the end.
- `content`: one plain sentence (en, tr) of what that week's sessions hold, e.g. "Past tense of the 20 commonest verbs; two notice-reading tasks; one formal e-mail."
- `beyond_a2`: for a B1 target, the ids from `exams/b1-keg.json` `beyond_a2` that the week introduces. Spread them: the passive, conditionals and the 150-word texts are months of work, not a week.
- `checkpoint`, `mock`: put a mock exam (the `mock-exam` skill) every 4–6 weeks once the units have some evidence, and always one 2–3 weeks before a session.

The first four weeks must be concrete, because the exam screen shows them. Later weeks can be broader.

## 4. Re-plan at every check-in

When `plan_progress` exists:

1. Compare each past week's `done_minutes` with `minutes`, and the `missed_focus` units.
2. **If they are behind** (two or more `short` weeks, or the pace is under 70% of the plan):
   - say it plainly in `behind`: "You did about 40 of the planned 100 minutes a week for three weeks.";
   - **say what to drop** in `drop`, concretely. For example:
     - "Leave B1 writing until February";
     - "Skip the history unit until a date is announced";
     - "Move the target to the October session".

     Dropping scope is better than a plan they cannot follow.
   - lower `minutes` to what they actually do, and move the target if the verdict changes.
3. No guilt and no cheerleading (COACHING §2). Numbers, and what changes.
4. Rewrite the whole file. Keep `made_at` as today.

## 5. The history and culture pack (A2-LTR only)

Build it **only when the plan targets an A2-LTR session with an announced date**. Before that, it is wasted effort.

1. Ask once: "For the history part I need the official history and culture text, a free PDF from the Ministry (about 17 pages). Shall I download it?" On a yes, save it in `content/private/official-a2ltr/syllabus/`. The URL is in `exams/a2ltr.json` `sources`.
2. Write the items **in your own words**, from the facts in the text, into `content/private/a2ltr-history/` (a private pack). Use A2-level Greek: `match` (sentence halves), `mcq` and `categorise` (the four eras: ancient, Byzantine, 1800–1900, 1900–2000), tagged `a2ltr.history.*`. Never copy sentences from the PDF.
3. Self-check every fact against the text. A wrong history fact is a lost point on the day.

## 6. Tell them

At most about 6 lines in their language:

- the verdict, with the one number behind it;
- the target session (or "no realistic announced session yet") and the registration deadline;
- if behind: what to drop;
- the next two weeks in one line each;
- "the plan is on the exam screen": `<app_url>?exam`.

Then `uv run greek-coach validate <learner_dir>` and `uv run greek-coach reload`.
