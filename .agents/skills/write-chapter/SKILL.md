---
name: write-chapter
description: Write the chapters a learner reads before practising each lesson (the app's digital book), from an approved outline, with drafts by smaller subagents and an independent review. Use when someone says "write the chapters for lessons 10-15", "write the next chapter", "make the outline for the book", "fix the chapter I flagged", "10-15. derslerin bölümlerini yaz", "sıradaki bölümü yaz", "bölüm taslağını hazırla".
---

# Write chapters

A chapter is the lesson the learner reads before a stage's practice: a dialogue, the grammar explained, the words, tips, and a few checks. The app takes chapters in from files. The learner reads one with `?lesson=<stage>`, and new words of that stage reach daily sessions only after it is finished.

**First read `docs/LESSONS.md`:**
- §2 the format;
- §3 voice;
- §4 the rules;
- §5 the reviewer's checklist.

**Then read `docs/COACHING.md`:**
- §5 writing items and the quality rule;
- §9 personal data.

Run every command from the repository root.

## 0. Where you are

1. Find the curriculum:
   - `uv run greek-coach report` → `curriculum.curriculum` and `chapters`, which shows which stages have a chapter and which are read;
   - the book's curriculum is `content/private/<pack>/curriculum.json`, the open one `curricula/open-a1-b1.json`.
2. Find the folder (LESSONS §1): a book's chapters are private, the open course's are tracked.
3. If `lessons/outline.json` is missing, start at step 1. If it exists, check that the stages you are asked for are in it.
4. If the request is a flagged section: `report.open_flags` entries with a `chapter` field give the file and the section. Fix that, run step 4 and step 6, and add the flag to `coach/resolved-flags.json` (COACHING §7.4). Then stop.

## 1. The outline (once per curriculum; write it yourself, do not delegate)

Write `lessons/outline.json` (LESSONS §6), one entry per stage, from:
- the stage's `can_do`, `theme` and `include` rules in the curriculum;
- for a book, `content/private/<pack>/units.json` (functions, grammar, vocabulary per lesson);
- for a book, the printed curriculum map, if the earlier project is on this machine (`Greek_Helper/data/processed/lessons/curriculum_map.json`);
- `uv run greek-coach raw <pack> --unit <id>`, for what the lesson actually practises.

Then check the whole outline at once:
- **The order of grammar.** No stage relies on a structure that a later stage teaches. Where a dialogue needs one early, the entry says "set phrase".
- **Words.** 15–25 per stage. Look them up in the pack first (`uv run greek-coach report --words`, or search the items files). Only what is missing goes under `new_words`.
- **Review stages** consolidate; they introduce nothing new.

Show the learner or maintainer a short table (stage, focus, scenario) and **wait for their yes** before any chapter is written.

## 2. Golden chapters (the first two only)

If the curriculum has fewer than two approved chapters, write two of different kinds yourself, before any delegation:
- one built around communication (a dialogue-heavy lesson);
- one built around grammar (a table-heavy lesson).

For the book these are `lesson-01` and `lesson-02`. Validate them (step 4) and ask the maintainer to read them in the app. Do not draft more until they say the golden chapters are right. Every drafter gets the two golden chapters as its examples.

## 3. Drafts (delegate: Sonnet subagents, a few stages at a time)

Give each drafter one stage, through the Agent tool with `model: "sonnet"`, running 3–5 drafters in parallel. It gets only what it needs, in the prompt:

1. `docs/LESSONS.md`, to read itself.
2. The stage's outline entry, and the outline entries of the earlier stages (what it may assume).
3. The two golden chapters, as paths to read.
4. The allowed vocabulary, as a list of `key | Greek | meaning`:
   - the stage's existing words;
   - the words of earlier stages, from `uv run greek-coach report --words` or the items files.
5. For a book: the lesson's OCR page text, from `Greek_Helper/data/app/lesson_details.json` → `items[].source_pages` for that unit, or `uv run greek-coach raw <pack> --unit <id>`. Say in the prompt: **reference only, to see what the lesson covers; do not copy any sentence, dialogue or exercise.**
6. **What to write:**
   - `lessons/<stage>.json`;
   - `items/chapter-<stage>.json`: new words, plus 10–20 practice items including the checks (LESSONS §4).

   It ends by running `uv run greek-coach validate <pack folder>` and fixing every problem and every untaught-word note it can.
7. **What to report back:**
   - the files written;
   - the validate output;
   - anything it was unsure of, with each Greek form it was unsure of.

The drafter does not run `reload` and does not touch other stages' files.

## 4. Validate

```
uv run greek-coach validate content/private/<pack>
```

Use the open pack folder for the open course. Every problem must be fixed. Read the notes:
- untaught words;
- reading time;
- unaccented words.

Fix them, or say in the review note why they stay.

## 5. Review (you, Opus, independently of the drafter)

Review each drafted chapter against LESSONS §5:
- Read it as a file, and then in the app (`?lesson=<stage>`, after `uv run greek-coach reload`).
- Correct the files directly.
- Pay most attention to the Greek: articles, cases, verb endings, accents, and natural word order.
- Write `lessons/review/<stage>.md` (LESSONS §5): what changed, what is unsure, and the correction count.

If a chapter needed more than about ten Greek corrections, say so in the report: the drafter's instructions or examples need improving before the next batch.

## 6. Load and report

1. `uv run greek-coach reload`.
2. Tell the learner in two or three plain lines:
   - which chapters are now in the app;
   - a link to the first one (`<app_url>?lesson=<stage>`);
   - anything left out.
3. **The pilot batch** (the first batch after the golden chapters, 3 chapters): also report the subagents' token use (from the Agent results) and the correction rate. Ask for a yes before generating the rest.
4. Add one line per chapter to `coach/notes.md` (COACHING §7.2).

Running many stages at once as a Workflow needs the user's explicit yes.
