# Writing chapters

A **chapter** is the lesson a learner reads before practising a stage of the curriculum. Practice comes after it and covers exactly what it taught. New words of a stage with a chapter come into daily sessions only once the chapter has been read. Each word is shown on a learn card before it is tested (SPEC §4.8, §5.4).

This file is for whoever writes chapters: the maintainer, the coach, or a drafting subagent. The procedure, including who drafts and who reviews, is the `write-chapter` skill (`.agents/skills/write-chapter/SKILL.md`).

## 1. Where chapters live

| Curriculum | Chapters | Practice items | Visibility |
|---|---|---|---|
| A book's curriculum (`content/private/<pack>/curriculum.json`) | `content/private/<pack>/lessons/<stage>.json` | `content/private/<pack>/items/chapter-<stage>.json` | private, gitignored |
| The open course (`curricula/open-a1-b1.json`) | `content/open/open-book/lessons/<stage>.json` | `content/open/open-book/items/chapter-<stage>.json` | tracked, CC BY-SA 4.0, original |
| Coach-written for one learner | `learner/generated/<pack>/lessons/<stage>.json` | the same pack's `items/` | gitignored |

- The file name is the stage id.
- A later content root replaces an earlier one for the same curriculum and stage: the coach's version wins over the pack's.
- `lessons/outline.json` is the writer's plan for the whole curriculum (§6), not a chapter.
- `lessons/review/<stage>.md` holds the reviewer's notes.

**Copyright.**
- A chapter for a book's curriculum follows that book's syllabus and may use its OCR pages as reference, so it stays private.
- Its text is still written new. Never copy a sentence, a dialogue or an exercise from the book.
- Names, situations and examples are your own.
- A chapter for the open course must be original throughout.

## 2. The format

The JSON Schema is `schemas/chapter.schema.json` (written by `uv run greek-coach schema`). The model is in `src/greek_coach/chapters.py`.

```json
{
  "id": "<curriculum>.<stage>",
  "curriculum": "greek-helper-book",
  "stage": "lesson-01",
  "level": "A1",
  "title": {"tr": "…", "en": "…"},
  "minutes": 10,
  "version": 1,
  "sections": [{"kind": "intro", "title": {"tr": "…", "en": "…"}, "blocks": [ … ]}, …]
}
```

**Sections** come in this order. Kinds may repeat, for example two `grammar` sections, one focus each.

| Kind | Required | What it holds |
|---|---|---|
| `intro` | yes | what the learner will be able to do, in 2–3 sentences, and the one key point |
| `warmup` | | a question that connects to their life before the text |
| `text` | yes | the dialogue(s) or text that carries the lesson |
| `comprehension` | | 1–3 questions on the text (`check`) |
| `grammar` | yes | one focus: explanation, table, examples |
| `words` | yes | a `words` block with this stage's words |
| `tips` | | Turkish bridge, typical mistakes, the exam |
| `try` | yes | a `check` block with 3–5 items that test what was taught |

**Blocks.** Every explanation has both `tr` and `en`. The Greek is the same for both.

| Block | Fields | Notes |
|---|---|---|
| `prose` | `tr`, `en` | Paragraphs split on newlines. Inline: `**bold**`, `*italic*`, `[[Greek]]` (tappable, and it counts as glossed). Nothing else. |
| `dialogue` | `setting {tr,en}?`, `lines [{who, el, tr, en}]` | At least two lines. `who` is a Greek name or role. Each line can be played; all of them with "Play all". |
| `table` | `caption {tr,en}?`, `head []`, `rows [[]]`, `note {tr,en}?` | Each row has as many cells as `head`. Cells are Greek, or short labels. |
| `examples` | `items [{el, tr, en, note {tr,en}?}]` | Short sentences that show the grammar point. |
| `words` | `items ["<pack>/<id>"]` | Vocab items. **They belong to this stage**: listing a word here places it in the stage, after an explicit `stage:` tag. |
| `tip` | `kind`, `tr`, `en`, `exam_task?` | `tr_bridge` (what Turkish shares), `mistake` (a typical error), `exam` (how it appears in the exam; name the blueprint task). |
| `check` | `items ["<pack>/<id>"]` (1–5) | Checkable items (not `write` or `speak`), answered inside the chapter. They train the review schedule but never count as exam evidence. Items named here also belong to the stage. |

## 3. Voice and style

**Turkish (`tr`):**
- Talk to the learner as *sen*: short sentences, everyday words.
- Natural Turkish: write the way a good Turkish teacher would explain, not a translation of the English.
- Use Turkish grammar terms only when they help (*artikel*, *fiil*, *çoğul*). Explain each one the first time.

**English (`en`):**
- The same content, written for an English reader.
- Do not translate the Turkish bridges word for word. Where a Turkish comparison does not help an English reader, give the English one (French *tu/vous*, English *the*).

**Greek:**
- Monotonic, NFC, final ς.
- Modern standard spoken Greek, of the kind a clerk, a neighbour or a teacher in Athens actually says.
- Names and places should be ones the learner meets in Greece: Ελένη, Νίκος, Αθήνα, a δήμος office, a λαϊκή. The learner's own world is welcome too (a Turkish name, Σμύρνη).

**Teaching:**
- One focus at a time: a grammar section explains one thing, with one table and 3–5 examples.
- Show before telling: the dialogue uses the point first, then the grammar section names it.
- Say what is a set phrase for now, and when the rule comes ("the rule comes in Lesson 3").
- Every rule has an example of the learner's own kind of sentence.

## 4. Rules a chapter must keep

1. **Words.** Dialogues and examples use only:
   - the words of this and earlier stages;
   - the words in this chapter's `words` block;
   - names;
   - the function words listed in `lint.FUNCTION_WORDS`.

   Anything else must be glossed with `[[…]]` in the text or added to `words`. `validate` lists the words it cannot place as a note.
2. **Grammar.** Never use a structure a later chapter teaches without calling it a set phrase. The outline (§6) says what each stage teaches and what it may assume.
3. **Length.**
   - A1: 8–12 minutes of reading.
   - A2: 12–15 minutes.
   - B1: up to 20 minutes.

   `minutes` states it, and `validate` checks the estimate.
4. **Size.**
   - **Words:** 15–25 per stage.
   - **Items:** 10–20 practice items in `items/chapter-<stage>.json`, besides the words.
   - **Checks:** 2 comprehension checks and 3–5 "try it" checks among them.
5. **Items.**
   - Item ids are `ch<NN>-…`, for example `ch01-try-formal-greet`.
   - Every item has the topic `stage:<stage id>`, a `rubric` in Greek with `en` and `tr`, and a `source` of `{"doc": "chapter", "stage": "<id>", "by": "<who>"}`.
   - Every item has one answer you can defend (COACHING §5.2). An `explain` that says why is worth more than another item.
   - Exam-format items carry `exam_task` only at the exam's level (`lint_tags`).
6. **Words already in a pack** are referenced, never duplicated. A missing word becomes a new vocab item in `items/chapter-<stage>.json`, with `en`, `tr`, `pos`, a gender for nouns, and an `example`.

## 5. The reviewer's checklist

Read the chapter as the learner would see it: `?lesson=<stage>` in the app.

- [ ] **Greek.** Every accent, article, case ending and verb form is right. Sentences are natural, not textbook-stiff. Read each dialogue aloud.
- [ ] **Teaching.**
  - [ ] Is there one focus per grammar section?
  - [ ] Is nothing used before it is taught, except as a named set phrase?
  - [ ] Does the table match the examples?
- [ ] **Turkish.** It reads as natural Turkish. Suffixes after Greek words are written so a reader can say them (*«Χαίρω πολύ» diyene…*, not *«Χαίρω πολύ»ye*).
- [ ] **English.** It is complete and natural.
- [ ] **Checks.**
  - [ ] Is every answer the only right one?
  - [ ] Is no distractor also correct?
  - [ ] Does each check test what the chapter taught?
- [ ] **Copyright.** Nothing is copied from the book.
- [ ] **Validation.** `uv run greek-coach validate <pack>` reports no problems. Its notes are read and either fixed or answered in the review note.

The review note (`lessons/review/<stage>.md`) lists, in a few lines:
- what was corrected;
- anything still unsure;
- the correction count: how many Greek fixes and how many teaching fixes.

## 6. The outline (`lessons/outline.json`)

Written once per curriculum, before any chapter, and approved by the learner or maintainer. It has one entry per stage:

```json
{"stage": "lesson-02", "objectives": ["…"], "grammar": ["the present of είμαι, all persons"],
 "assumes": ["lesson-01: greetings, με λένε, είμαι από as a set phrase"],
 "words": ["greek-helper/…"], "new_words": ["…"], "scenario": {"tr": "…", "en": "…"},
 "exam_task": "b1keg.speaking.warmup", "notes": "…"}
```

The outline is where the order of grammar is checked across the whole book. A chapter is drafted from its entry, and must not drift from it without the outline being changed too.
