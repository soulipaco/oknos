---
name: mock-exam
description: Put together a timed mock exam in the real format of the learner's exam (Ελληνομάθεια B1 or A2 + history), section by section, from fresh coach-written items and their private official papers; after the run, mark the writing and speaking so the result reaches the readiness screen. Use when the learner says "give me a mock exam", "a practice test", "test me like the real exam", "deneme sınavı", "beni gerçek sınav gibi dene", or when the plan schedules a mock.
---

# Mock exam

A mock exam is the only evidence the app has that the learner can do the exam **in the time**, without feedback, all at once. It is also the strongest evidence for readiness, because every item in it is a first sight. So it must look and feel like the real paper, and every answer must be beyond doubt.

**First read `docs/COACHING.md`** (§5 the quality rules, §12 the mock files).

## 1. Choose the exam and the sections

1. Run `uv run oknos report`. Note `profile.target_exam`, `readiness`, `coverage` and `mocks` (mocks already defined, and past runs).
2. **Which exam.** Use the plan's target (`coach/plan.json` `exam`) or `profile.target_exam`. If it is `undecided`, ask which one, in one line.
3. **Which units.**
   - A full mock has every unit of the blueprint.
   - A partial mock (for example only reading and listening) is fine when the plan asks for it, or when a unit cannot be made yet (say why).
   - The app takes the time for each section from `exams/<id>.json`. You do not set it.
4. **If a mock of the same exam is already defined and not taken** (`mocks.defined` without a finished run), do not write another one. Point the learner to it.

## 2. Write the items: the real format, one fresh set

Write all items into `<learner_dir>/generated/coach-mock/items/<today>-<exam>.json`, with ids starting `<today>-mock-`. Create the pack's `pack.json` once (COACHING §4), with `"id": "coach-mock"`.

**Match the blueprint task by task** (`exams/<id>.json` → `units[].tasks[]`):

- the same item `type` as the task's `types`, the `exam_task` tag of that task, and `level` equal to the exam's level;
- **the same number of questions** as `questions`. For example, A2-LTR reading part 2 is 14 true/false statements over ten notices. Write it as several `true_false` items whose statements add up to 14. B1 reading part 2 is one table of 12 cells.
- **The real lengths:**
  - A2-LTR writing is 40–60 words;
  - B1 reading texts are 150–200 words and B1 writing is 150 words;
  - B1 listening is about 300 words (notes) and 350–400 words (a discussion between two or three people).
- **Rubrics** in the exam's own Greek wording, with `en`/`tr`. During a mock the app shows only the rubric's translation, never the translation of a text or statement.
- **Listening:** `stimulus.tts`, `plays: 2`.
- **Speaking:** one `speak` card per part, with the part's `exam_task`:
  - A2-LTR: questions about yourself; two pictures, described in words because the app shows no pictures; a role-play card;
  - B1: warm-up; a monologue with reasons; a role-play with argument.
  - `seconds` should be realistic: 60–120 per part.
- **Topics from the learner's life** (COACHING §2), at exam difficulty. A mock that is easier than the exam gives false confidence.
- **Everything new.** Do not reuse items the learner has seen (`covered`, `recent_wrong`).

**Official papers.** If `content/private/official-a2ltr/` holds downloaded A2-LTR papers, an A2-LTR mock may be rebuilt from one of them instead:

- the real texts and questions go into a **private** pack, `content/private/official-a2ltr/items/<year>.json`, never into `learner/generated/` or anything tracked;
- give every item a `source` (`{"doc": "ΓΡΑΠΤΗ ΕΞΕΤΑΣΗ 2024.pdf", "page": 3}`), and take the answers from that year's answer key (ΛΥΣΕΙΣ);
- listening uses the official MP3. Copy it into the pack's `audio/` and set `stimulus.audio` with `start` and `end` (seconds) for each part. Listen to or skim the transcript in the key to find the boundaries;
- keep at least one year unused, for a later mock;
- **older papers differ from the blueprint**, which follows the 2026A paper (the latest). The 2024 paper, for example:
  - has photo ordering in listening;
  - uses true / false / not in the text, and "which advert" questions;
  - asks for longer e-mails.

  Prefer the 2026A paper for format. When rebuilding an older one, convert each part to the blueprint task with the same skill (for example, photo descriptions become a word bank), keep the blueprint's question counts, and note each change in the item's `source`;
- **one recording, several questions:** give every item of that part the same `audio`, `start` and `end`. In a mock they share the plays, as in the exam;
- a mock may mix packs: official items from the private pack and your own items from `coach-mock` in one file are fine;
- ask before downloading anything (SPEC §9). The maintainer said yes on 2026-11-16 for the 2022, 2024 and 2026A papers.

**Self-check every item twice** (COACHING §5.2). In a mock the learner gets no feedback until the end, so a wrong key silently costs points and misleads readiness. Mark anything doubtful `needs_review` and replace it.

## 3. Write the mock file

Write `<learner_dir>/coach/mocks/<id>.json`, where `<id>` is `<today>-<exam>` and equals the file name:

```json
{"id": "2026-11-20-a2ltr", "blueprint": "a2ltr", "created": "2026-11-20",
 "title": {"en": "Mock exam 1 (A2 + history)", "tr": "Deneme sınavı 1 (A2 + tarih)"},
 "sections": [
   {"unit": "listening", "items": ["coach-mock/2026-11-20-mock-l1", "coach-mock/2026-11-20-mock-l2"]},
   {"unit": "reading", "items": ["coach-mock/2026-11-20-mock-r1"]}
 ]}
```

- `sections` follow the paper's order. Each `items` list is in paper order, with full item keys (`<pack>/<id>`).
- Every item's `exam_task` must belong to that section's unit.

Then:

- `uv run oknos validate <learner_dir>/generated/coach-mock` (and the private pack if you used one);
- `uv run oknos validate <learner_dir>`;
- `uv run oknos reload`.

The exam screen now shows the mock. Until it is taken, its items stay out of daily sessions.

## 4. Tell them how it works

In their language, in a few lines:

- it is in the app, on the exam screen (`<app_url>?exam`);
- each section has the real time, and **the clock keeps running if they leave**, as in the exam. Coming back in time continues; coming back late closes the section with what was saved;
- there is no feedback until they hand in a section. They can go back and change answers within it;
- writing and speaking are marked by you afterwards: "tell me 'mark my mock' when you're done".

## 5. After the run

When `mocks.runs` shows a finished run (or the learner says they are done):

1. Mark its writing and speaking submissions with the `mark` skill. In each feedback file set `score.exam` to the blueprint id and `score.task` to the item's `exam_task`, with `points` and `out_of` on that task's scale (for example A2-LTR e-mail: out of 10; B1 writing part B: out of 13). The app scales them into the unit.
2. Run `uv run oknos reload`, then the report again. Read `mocks.runs[0]`: the points per section, `would_pass`, unanswered items, and any `time_away` section.
3. **Tell them the result honestly**, per section, against the pass line:
   - what cost the most points;
   - whether time was the problem (unanswered items) or knowledge (wrong answers);
   - one change for the next weeks.

   Then update the plan (the `plan` skill, §4), since this is the best evidence there is.
