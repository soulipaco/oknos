# Phase 5c — The book: read first, then practise

Read `AGENTS.md`, `docs/SPEC.md` (especially §4, §5.4 and §7) and `docs/COACHING.md`. Use plan mode, and show me the plan before writing code.

## Why

The app tests me on things it never taught me. A new word reaches me first as a test card, and a new stage starts with exercises. I learn by reading. Before I practise a topic, I want to read a lesson that explains it: a short text or dialogue, the grammar laid out and explained, the words, and a few examples. Then I want the practice to be about exactly what I just read.

So every curriculum stage gets a **chapter**, and the app becomes a digital book: **read the chapter, then practise it**. The daily session and spaced repetition stay. They now come after the teaching, not instead of it.

Decisions already made (2026-11-18):
- Explanations are written in **Turkish and English**. The UI language picks which one is shown. Greek text (dialogues, examples, tables) is the same in both.
- The work is about **80% flow (UX) and 20% look (UI)**. The reader screen and the home flow matter most. Visual polish is limited to what the reader needs and to tidying the home screen.
- Chapters are drafted by **Sonnet subagents** and reviewed and corrected by **Opus**, with automatic validation in between.

## 1. The chapter format

Design a chapter format, write a JSON Schema for it (`greek-coach schema`), and document it in a new `docs/LESSONS.md`. Use structured blocks, not free Markdown. Blocks can be validated, linted for Greek, linked to items, and filled in reliably by a smaller model. Allow only minimal inline formatting (bold, italic, a Greek span), rendered by our own small renderer. Do not add a Markdown dependency.

A chapter belongs to one stage (`stage` = the stage id) and lives in its pack at `lessons/<stage-id>.json`. Suggested blocks; adjust them if the plan finds a better shape:
- `prose`: explanation text `{tr, en}`.
- `dialogue`: a setting, then lines of `{who, el, tr, en}`. It can be played line by line or all at once with the browser voice.
- `table`: grammar paradigms, with a caption, a header and rows (Greek cells, optional notes).
- `examples`: `{el, tr, en, note?}`.
- `words`: references to vocab item ids. The app renders them with audio, meaning and the learner's status.
- `tip`: `kind` is one of `tr_bridge` (a word or structure Turkish shares), `mistake` (a typical error for a Turkish or English speaker) or `exam` (how this appears in the exam, citing the blueprint task).
- `check`: an inline item reference (`<pack>/<id>`) or a small inline question, checked by the existing renderers.

Every chapter follows the same order. It comes from the coursebook's own recommended lesson flow (`Greek_Helper/data/processed/exercises/activity_taxonomy.json`):
1. "In this chapter": the stage's `can_do`, in two or three lines.
2. A warm-up question.
3. The dialogue or text.
4. Comprehension (true/false or questions).
5. Grammar: table, explanation and examples. One focus at a time.
6. Words.
7. Tips: Turkish bridge, common mistakes, the exam.
8. "Try it": 3–5 checks.
9. The button "Practise this chapter".

Length: an A1 chapter takes about 8–12 minutes to read, A2 about 12–15. Show the estimate on the chapter.

## 2. Where chapters live (copyright)

- **The book curriculum** (`content/private/greek-helper/curriculum.json`, 26 stages) gets its chapters in `content/private/greek-helper/lessons/`. They are private and gitignored. The text is newly written and never copied from the OCR pages. It follows the book's syllabus closely and uses those pages as reference, so it stays private.
- **The open curriculum** (`curricula/open-a1-b1.json`, 12 stages) gets its chapters in a new open pack, `content/open/open-book/` (CC BY-SA 4.0, original). This is needed before phase 6, so that the friend has something to read.
- Coach-written chapters (for example one written after a class) go in `learner/generated/`.

## 3. The app

**Reader screen** (`?lesson=<stage-id>`):
- One readable column (about 65 characters), generous line height, and a serif face for Greek.
- A small progress line or contents list for the chapter's sections.
- The existing tap-a-word popover and Greek keyboard keep working here.
- Dialogue lines can be played, and inline checks are checked as you read.
- At the end, a single button: "Done reading — practise this chapter". It starts a session of exactly this stage's items.
- It works without an agent running, like everything else.

**Reading progress:**
- New migration `0006` records when a chapter is opened and finished, and which sections were seen.
- `report` (`report_version` 3) includes this, so the coach knows what has been read.
- Inline checks are recorded as attempts of kind `lesson`. They are **excluded from readiness** (readiness stays first attempts at exam level only, SPEC §5.3) but count toward SM-2.

**Teach before testing.**
- New items of a stage (words, forms, exam tasks) enter daily sessions only once its chapter is finished.
- A stage with no chapter keeps today's behaviour.
- Reviews of already-introduced items are never blocked.
- When a word is introduced in a session for the first time, show an ungraded **learn card** first: the word, audio, meaning and an example sentence (from the chapter where possible). Only after that does it become a test card. This applies to all words, not only those of the book.

**Home rebuilt around one next action.** The first thing on the home screen is the one thing to do now:
- "Read: Lesson 3 — Origin and residence (10 min)";
- or, once it is read, "Practise Lesson 3";
- or "Today's review (12 min)" when reviews are due.

Readiness, the coach's note and the links (Choose practice, My words, My verbs) stay, but below it and quieter. The course map shows each stage as a chapter with three states: read ✓, practised %, test ✓.

**Look (the 20%).**
- Typography and spacing for the reader.
- A less crowded home screen.
- A light theme next to the current dark one, following the system setting with a switch.

No broad restyle beyond that.

## 4. The generation procedure (a new skill, `write-chapter`)

Write it as a skill (`.agents/skills/write-chapter/SKILL.md`, and the pointer in `.claude/skills/`). It must be repeatable by any agent, not only in this session. The steps:

1. **Outline (Opus, once per curriculum).** Write `lessons/outline.json` with one entry per stage. Each entry has:
   - the objectives (`can_do`);
   - the grammar points, with exact scope;
   - 15–25 core word ids;
   - the dialogue scenario;
   - what is assumed from earlier stages;
   - which exam task it feeds.

   **Rule: a chapter never uses grammar that a later chapter teaches.** Check this across the whole outline before any chapter is written. I approve the outline, which is short to read.
2. **Two golden chapters (Opus, by hand).** Write two chapters of different kinds (for example lesson-02 and lesson-09), and I read them in the app. Mass generation does not start until I have said they are right. They become the examples every drafter is given.
3. **Drafts (Sonnet subagents, in parallel, a few at a time).** Each drafter receives:
   - `docs/LESSONS.md`;
   - its outline entry;
   - the two golden chapters;
   - the allowed vocabulary (this stage and the earlier ones);
   - the stage's item ids;
   - for the book curriculum, the OCR text of that lesson's pages (`Greek_Helper/data/app/lesson_details.json` → source pages), **as reference only, with the instruction not to copy sentences**.

   It writes the chapter in Turkish and English, plus 10–20 practice items tagged `stage:<id>` that test what the chapter taught. For the book this replaces most of the `rebuild-imported` work for that lesson; reuse that skill's rules.
4. **Validate (`greek-coach validate`, extended):**
   - the schema;
   - the Greek lint;
   - every Greek word in dialogues and examples is in the allowed vocabulary or glossed in the chapter;
   - every reference resolves;
   - both `tr` and `en` are present;
   - the length is within limits.

   A drafter fixes its own validation errors before handing back.
5. **Review (Opus, independently of the drafter):**
   - Greek correctness: accents, agreement, cases, verb forms;
   - the teaching: only grammar already taught, one focus at a time;
   - natural Turkish, and the English.

   The reviewer corrects the chapter directly and writes a short review note per chapter (what changed, what was unsure).
6. **In the app:** a "something is wrong here" flag on each section of the reader, which the coach's next check-in picks up and fixes (`docs/COACHING.md`).

Run a pilot batch of 3 chapters first. Report its token use and the review's correction rate before generating the rest. Then generate the book curriculum in stage order, current stage first, then the open curriculum. Running the generation as a workflow needs my explicit yes at that point.

## Tests

- The chapter schema and validator, with a good chapter and a broken one.
- Teach-before-test gating:
  - new items wait until the chapter is finished;
  - reviews are never blocked;
  - a stage with no chapter behaves as before.
- Lesson-kind attempts are excluded from readiness.
- The learn card appears once per new word, then the test card.
- Migration `0006` on an existing database.
- `scripts/simulate.py` still runs, with reading added to the simulated days.
- `tests/test_skills.py` covers the new skill.

## Done when

- I can open the app, see "Read Lesson N" as the first thing, read the chapter comfortably in Turkish or English, and press one button to practise exactly what it taught.
- New words are shown to me before I am tested on them.
- The two golden chapters and the pilot batch are in, and I have read them.
- The procedure is written down well enough that "write the chapters for lessons 10–15" works in a fresh session.
- `AGENTS.md` and `docs/SPEC.md` are updated, and the tests pass.
