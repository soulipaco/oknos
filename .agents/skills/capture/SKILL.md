---
name: capture
description: Turn something from the learner's class or real life into Greek practice. A photo or file of a letter, notice, bill, menu or handout dropped in the inbox, or a description such as "today we covered the past tense and words about the doctor", becomes vocabulary, a reading task and verb forms in the next sessions. Use when the learner says "today in class we did…", "what does this letter say?", "I put a photo in the inbox", "how do I say X to my landlord?", "bugün derste … gördük", "bu mektup ne diyor?", or when the report shows files in the inbox.
---

# Capture: class and real life

Real life matters more than class to this learner. A notice on their building, a letter from the tax office or the pharmacy's opening hours are the Greek they actually need, and practising them *is* exam practice: the A2 reading paper is public notices, and B1 writing is requests and complaints.

**First read `docs/COACHING.md`**, especially §5 (writing items) and §9 (personal data).

## 1. What did they bring?

- **A file**:
  - in `<learner_dir>/inbox/` (the report lists them under `inbox`), or attached in chat (a photo, PDF or text);
  - read it yourself: images and PDFs with your own file-reading or vision tools;
  - if a photo is unreadable, say so and ask for a sharper one. Do not guess at text you cannot see.
- **A class**: "today we covered…". Ask at most one question if it is too vague to build on ("which verbs?"), or work from their course notes in `coach/notes.md` and `units.json`.
- **A real-life question**: "how do I tell my landlord the heating is broken?". Answer it first: give them the sentence they need, in Greek with a translation. Then capture it.

## 2. Help first

Before building any exercise, give them what they came for, in their language and briefly:

- **A document**: what it says and whether they need to do anything (a deadline, an amount, where to go). Note that they can ask someone they trust if it looks official and important. You are a language coach, not a lawyer or an accountant.
- **A class**: one line confirming what you understood was covered.
- **A question**: the Greek they need.

## 3. Make it safe: personal data

Before anything from a real document becomes an exercise, replace every personal detail with an invented one of the same kind:

- names: use a different common Greek name;
- ΑΦΜ, ΑΜΚΑ, IBAN, phone numbers, case and contract numbers;
- street addresses, e-mails, dates of birth, amounts tied to their accounts.

Keep the document's structure, language and register: that is what is worth learning. Nothing of the original goes into items, notes or feedback.

## 4. Build the practice

Write to `<learner_dir>/generated/coach-capture/items/<today>-<short-name>.json`. Create the pack's `pack.json` if it is missing (COACHING §4, with id `coach-capture`). A good capture is **8–20 items**:

- **Vocabulary** (5–12 `vocab` items): the words they need from the source, with the article for nouns. Each gets an `example` sentence from the same situation and `topics` naming it (`landlord`, `tax-office`, `pharmacy`, `class`…).
- **A reading task** (one `true_false` or `gap_bank`): the anonymised document itself, simplified if needed to stay near their level, with 4–6 statements or gaps about what matters in it (dates, what to bring, what is forbidden). For a class, write a short text at their level that uses what was covered.
- **Verb forms** (`form` items) for the verbs met, in the forms that appeared or that the class covered, in sentences from the same situation.
- For a class, also a `write` prompt in exam format if writing was part of the lesson, or a `speak` card if a dialogue was.

Set `level` honestly. A real notice may be B1 in places; simplify the reading text or mark the item B1. Then:

- self-check every item (COACHING §5.2);
- `uv run greek-coach validate <learner_dir>/generated/coach-capture`, then `uv run greek-coach validate <learner_dir>`;
- `uv run greek-coach reload`.

## 5. Tidy up and tell them

- Move processed inbox files to `<learner_dir>/inbox/done/`, adding today's date in front of the name. Never delete them.
- In `coach/notes.md`, add one line: the date, what was captured (with no personal data), and the item file. For a class, also what the class covered: the next check-in uses it to stay at the right level.
- Tell them in one or two lines: "14 exercises from the tax-office letter are in your next sessions. If you want to try them now: <app_url>?practice=…". Build the link from 3–5 of the new item keys (COACHING §5.5).

## Class handouts and copyright

A handout or a textbook page is the course's or the publisher's material. It stays private: the original in `inbox/done/`, and the derived items in `learner/generated/`, which is gitignored. Never copy it into `content/open/` or anywhere tracked.
