# Phase 5d — Every word you can tap has a meaning, no question hidden behind "Translate", and other adjustments

Read `AGENTS.md`, `docs/SPEC.md` §4.8 and `docs/LESSONS.md`. Use plan mode, and show me the plan before writing code.

## Why

Every Greek word on screen can be tapped, but many give "no meaning for … in your packs yet". For example, tapping Διαλέγω in the rubric «Διαλέγω το σωστό.» shows nothing. A learner who taps a word and gets nothing stops tapping.

**Measured on 2026-11-19:**
- 2,527 distinct Greek words can be tapped in items and chapters;
- 1,038 of them (about 41%) find no meaning:
  - 73 in rubrics;
  - 421 in chapters;
  - 852 in item texts.

  The groups overlap. Most are:
  - inflected forms (ακούστε, διαλέξτε, απαντήσεις, βρίσκονται);
  - instruction words (Αντιστοιχίζω, Συμπληρώνω);
  - names (Ελένη, Μεχμέτ).

## Do

1. **Measure it in the app.**
   - `validate` lists, per pack and per chapter, the tappable words the lookup cannot explain, as a note.
   - `report` carries the count, so the coach sees it.
   - Reuse the scan from this measurement: lookup over `greek.words()` of rubrics, prompts, texts, statements, options, dialogue lines, examples and table cells.
2. **Inflected forms find their word.**
   - Use the cached Wiktionary index (`.cache/oknos/kaikki-el-index.json`, already used by the importer and the verb-pack builder) to map a form to its lemma: verbs (ακούστε → ακούω), nouns (απαντήσεις → απάντηση) and adjectives.
   - Then show the lemma's vocab item, labelled "form of …" / "… biçimi".
   - Prefer this to ever-longer ending lists in `lookup._ENDINGS`.
3. **Instruction words.** A small tracked glossary of the rubric vocabulary, the same shape as `src/oknos/function_words.json`. Examples:
   - Διαλέγω, Διαλέξτε, Συμπληρώνω, Αντιστοιχίζω;
   - Σωστό ή λάθος, Διαβάζω/Διαβάστε, Ακούω/Ακούστε, Γράφω/Γράψτε;
   - η απάντηση, η ερώτηση, ο διάλογος, το κείμενο.
4. **Names.** A capitalised word that is a speaker in the chapter, or a known first name or place, shows "name" / "özel isim" (and Greece's cities as places), not "no meaning".
5. **The rest.**
   - The words still unexplained after 2–4 get glossary entries, in Turkish and English, with their lemma.
   - Draft them with Sonnet subagents, as for the Turkish meanings on 2026-11-19, and spot-check them with Opus.
   - Book words go in the private pack's overlay. Open-pack words go in tracked files.
6. **Keep it fixed.** A test asserts that the open packs and the test chapter have no unexplained tappable word. The chapter-writing brief (`write-chapter`, `docs/LESSONS.md` §4) adds: "every Greek word in your chapter and items must be explained by tapping; `validate` lists those that are not".

## Other adjustments

Collect the other small adjustments of the day here before starting. Each one is a line: the screen, what is wrong, and what it should do.

- **A question that can only be answered after pressing "Translate".**
  - **What happens:** in a check, the Greek of a true/false statement is only a sign («ΣΤΑΣΗ», «ΠΑΡΚΟ»), and the claim to judge ("the ΣΤΑΣΗ sign shows a stop") is only in the hidden translation. Some mcq prompts are only a Greek frame («Θα ήθελα …», «Νίκος: «…»»), and the actual question ("order a medium-sweet Greek coffee politely") is only in the hidden translation.
  - **Where:** found on 2026-11-19 in `ch00-q-signs`. A scan of statements with at most 2 Greek words and a much longer translation finds 14 such items, all in the book's chapter items: ch00 ×6, ch01 ×1, ch03 ×1, ch04 ×4, ch07 ×1, ch12 ×1.
  - **What it should do:** never hide the question.
    - (a) **Content.** Rewrite those items so the Greek carries the claim (true/false: «Η ΣΤΑΣΗ είναι για το λεωφορείο.»). Where the task is genuinely "what do you say in this situation", keep the situation in the UI language, but show it.
    - (b) **App.** Give items a field for a situation or question in the UI language that is always visible (for example `ask {tr, en}`, shown above the Greek like the rubric), separate from the translation that stays behind "Translate".
    - (c) **Lint.** `validate` flags a statement or prompt whose Greek has at most 2 words while its translation is much longer, and LESSONS §4 and the review brief say "the Greek must carry the question".

## Done when

- At most 2% of tappable words find nothing. Those that remain are listed in the validate output, with a reason for each.
- Tapping a form shows its word and says it is a form of it. Tapping a rubric word or a name shows something useful.
- The tests pass, and `AGENTS.md` and `docs/SPEC.md` are updated.
