---
name: rebuild-imported
description: Turn one lesson of the learner's imported textbook (the raw OCR exercises kept aside at import) into clean, checkable exercises in their private pack. Use when the learner says "turn lesson 5 into exercises", "rebuild lesson 3", "use the exercises from my book", "5. dersi alıştırmaya çevir", "kitabımdaki alıştırmaları kullan".
---

# Rebuild imported exercises

At import, the learner's earlier material was kept as **raw** prompts, because OCR left them noisy:

- glued words, wrong letters;
- tables and pictures lost;
- no answers attached.

They are in `content/private/<pack>/raw/exercises.json`, which is private and gitignored. This skill rebuilds one lesson at a time into exercises the app can check.

**First read `docs/COACHING.md`**, especially §5 (writing items and the quality rule).

#<!-- phase 5b: rebuilt items carry their lesson's stage tag -->
# 1. Choose the lesson

- `uv run oknos raw <pack> --list-units` lists the lessons with how many raw entries each has. The pack is usually `greek-helper`; `ls content/private` shows the others.
- If they did not say which lesson, suggest the earliest one they have not rebuilt yet:
  - look for `items/rebuilt-*.json` in the pack;
  - check `covered.book_units_met` in `uv run oknos report`.
- `uv run oknos raw <pack> --unit lesson-05` prints:
  - the lesson outline (theme, functions, grammar, vocabulary);
  - its raw entries (page, exercise marker, instruction, text).

  Use `--limit` and `--pages` for long lessons.
- **Answer keys** are separate entries (`kind: answer_key`), mostly not linked to a lesson. Search them with words from the exercise: `uv run oknos raw <pack> --kind answer_key --search "<a distinctive word>"`. Use one only if it clearly belongs to this exercise.

#<!-- phase 5b: rebuilt items carry their lesson's stage tag -->
# 2. Understand each raw exercise

For every entry, work out what the original exercise was:

- a reading text with questions;
- a fill-in of verb forms or articles;
- matching;
- a dialogue.

Repair the OCR in your head: `μετάτο` → `μετά το`, `καιμαθαίνω` → `και μαθαίνω`, `[0:45` → `10:45`. If an exercise depended on a picture or a table that is lost, skip it and say so.

#<!-- phase 5b: rebuilt items carry their lesson's stage tag -->
# 3. Rebuild

Write clean items of the supported types (SPEC §4.4) to `content/private/<pack>/items/rebuilt-<unit>.json`. If the file exists, add to it, and never change ids that already exist.

- **Keep the book's intent and level.** These items are for this learner only, privately, so you may stay close to the book's sentences. Fix the Greek; do not modernise or extend it.
- **Every item gets a definite answer** you can defend. Derive it from the text, the grammar or a matched answer key. If you cannot be sure, the item gets `"status": "needs_review"` and is not shown.
- **Ids:** `rb-<unit>-p<page>-<n>`, for example `rb-lesson-05-p70-1`.
- **`source`:** `{"doc": "<doc>", "page": <page>, "raw": "<raw id>"}`. It is required for private packs.
- **`topics`:** include `unit:<unit id>`, so the app knows which lesson the item belongs to.
- **`rubric`:** use the book's instruction, repaired and in Greek, with `en` and `tr` translations.
- **Types:**
  - a reading text becomes `true_false` or `mcq`;
  - a verb or article fill-in becomes `form` (one gap per item, or a short text with a few gaps), with `options` when the book gave choices;
  - word lists become `vocab` only if the private pack's vocabulary does not have the word already.
- **Size:** about 15–40 items per lesson. Quality over coverage.

#<!-- phase 5b: rebuilt items carry their lesson's stage tag -->
# 4. Check and load

1. Self-check every item (COACHING §5.2).
2. Run `uv run oknos validate content/private/<pack>` and fix every problem.
3. Run `uv run oknos reload`.
4. Give them a link to try a few right away: `<app_url>?practice=<pack>/<id>,…` with 4–6 ids.

#<!-- phase 5b: rebuilt items carry their lesson's stage tag -->
# 5. Report

Tell them in two lines:

- how many exercises are now in the app from that lesson;
- how many you skipped (pictures, unclear OCR), or marked `needs_review` and why.

Add one line to `coach/notes.md`: the unit, the file, the counts, and what was left out.

## Stages (phase 5b)

Rebuilt items follow the book's curriculum. Give every item the topic `"stage:<lesson id>"` of the lesson it came from, for example `"stage:lesson-05"`, as well as `"unit:<lesson id>"`. The app then serves it only when the learner reaches that lesson. Rebuild lessons in course order, starting with the learner's current stage (`curriculum.current` in the report).

