---
name: podcast
description: Write and make a podcast lesson, an audio episode to listen to hands-free, from a book chapter (one episode per chapter, Greek with Turkish or English explanations), or a personal daily or weekly review episode from the learner's record. Writes the script as text, checks it, says what it will cost, then makes one mp3 that plays on the app's Podcast page. Use when the learner says "make the podcast for this lesson", "a podcast for lesson 3", "I want to listen to the chapter", "make me today's podcast", "bu dersin podcast'ini yap", "dersi dinlemek istiyorum", "podcast hazırla", "bugünün podcast'ini yap", or when daily-prep keeps the episodes going.
---

# Podcast lessons

A chapter episode is a lesson to listen to on the way to work: the chapter's dialogue at normal speed and then slowly with gaps to repeat, its words, what to know, a question or two, all explained in the learner's language like a good teacher on the radio. You write the **script** (text); the program checks it and makes the audio. Read `docs/PODCASTS.md` first (the format, the voices, the copyright rules) and `docs/COACHING.md` §2 (tone).

## 1. Which episode

- Default: the learner's **current lesson** (`uv run oknos report` → `curriculum.current`), or the one they name.
- **Language:** `podcast.lang` in `profile.json`, else the app's language (`ui_lang`). The maintainer's: Turkish.
- **Id:** `<source>.<stage>.<lang>`: `book.lesson-03.tr` for the private book, `open.shopping.en` for the open book. The folder is `<learner_dir>/podcasts/<id>/`, the script `script.json` in it.
- If a script already exists, improve it (raise `version`) rather than starting over, unless asked.
- Once a learner has episodes, `daily-prep` (step 5a) keeps them a lesson ahead with this skill: one episode a run, for the current stage, then the next.

## 2. What to make it from

In this order, and only as much as the episode needs:

1. **The chapter** of that stage: `content/private/<pack>/lessons/<stage>.json` for the book, `content/open/open-book/lessons/<stage>.json` for the open course. Its dialogues, examples, words (with their meanings in the pack), tables and tips. A coach-written chapter in `learner/generated/` wins over the pack's.
2. **The open book's chapter** that the book curriculum's `follows` maps to the same stage, or that covers the same theme, where the book's chapter is thin (few examples, one short dialogue). For a learner without the book: the open book, plus their own imported material when it covers the theme.
3. **Ideas from the web**, only if the episode is still thin: search for how others teach this point to learners (common mistakes, useful set phrases, cultural notes). Take ideas, never text: no sentence, dialogue or explanation copied, translated or re-voiced. Record each source in the script's `sources` (`{"what": "idea", "url": …, "note": what you took}`). Never download audio or video.

The Greek you put in the script is the chapter's own, or new sentences you write at the stage's level with words the learner has met by this stage (this stage and earlier). Use the pack's meanings for words; where the book's meaning is an unchecked AI draft (A2/B1 Turkish), keep to the plain, common meaning.

## 3. The shape of a chapter episode (12–15 minutes)

Each `part` is a mark the player lists, so keep them few and named in the learner's language.

1. **Giriş / Intro** (≈1 min): what the lesson is about and what you will be able to say at the end; one sentence on how to listen ("repeat aloud in the gaps").
2. **Dialogue** (≈3 min): set the scene in a sentence; the whole dialogue at normal speed, each line with its `who`; then line by line: the line at `speed` 0.8, an `echo` gap (1.3–1.6), and its meaning in the learner's language. Long lines are split in two for the repeat.
3. **Words** (≈3 min): each new word: the Greek, a short `pause` (1–1.5 s, so the listener can guess), the meaning, the Greek once more slowly, an `echo` gap. 8–15 words; skip ones the dialogue made obvious.
4. **The point** (≈3 min): the grammar or usage the chapter teaches, said simply, with 3–5 short Greek examples (each: Greek, meaning, sometimes an echo). Tables become patterns said aloud ("εγώ είμαι, εσύ είσαι…"), never a list of cells.
5. **Tips** (≈1 min): the Turkish bridge or the typical mistake, and the exam tip if the chapter has one.
6. **Quick questions** (≈2 min): 3–4 questions in the learner's language ("how do you say … ?"), a `pause` of 4–5 s, the Greek answer, an `echo` gap.
7. **Once more** (≈1 min): the dialogue again at normal speed, and a goodbye that names the next step (read the chapter in the app, practise).

## 3b. A personal episode: daily (10–20 minutes) and weekly (20–30 minutes)

Written by `daily-prep` (its step 5b) for a learner who said yes to them (`podcast.personal` in `profile.json`), or when the learner asks ("make me today's podcast"). It is the learner's own review to listen to: the words due that day and the weak ones, a mistake or two put right, a short story at their level, a look at the current lesson.

1. **The material:** `uv run oknos podcast material daily` (or `weekly`; `--date` for another day than tomorrow). It prints the id (`daily.2026-11-25.tr`, `weekly.2026-w48.tr`), the date, the language, whether a script already exists, and: `due` and `weak` words with their meanings and an example, `mistakes` (what was asked and the right answer), `new` (words met in the last days), `current` (the lesson), `met_words` and `met_verbs` (what the story may use), and `previous` (the last personal episodes and their `focus`, so you do not repeat them). If `exists` is true, stop: never make the same episode twice.
2. **Pick:** a daily episode drills 8–12 words (the due ones first, then weak ones not drilled in the last two `previous` episodes) and one or two mistakes; a weekly one 15–20 words, the week's mistakes grouped by what they have in common, and the current lesson's main point. Skip words whose meaning in `due` is a fragment or a reading card.
3. **The shape of a daily episode** (each a `part`, named in the learner's language):
   1. *Giriş* (≈30 s): what today holds, in two sentences. No date, no numbers about the learner.
   2. *Bugünün kelimeleri* (≈5 min): each word: the Greek, a `pause` of 1.5 s to guess, the meaning, the Greek slowly, an `echo`; then a short sentence with it (the example, or one you write with `met_words`), its meaning, an `echo`.
   3. *Düzeltelim* (≈2 min): one or two of `mistakes`, taught as a point ("üçüncü çoğul kişide …"), the right form in two or three Greek sentences with `echo`. Say the wrong form only as the common mistake, never as theirs.
   4. *Kısa hikâye* (≈4 min): an original story of 8–12 short sentences at the learner's level, about everyday life (the open book's people, Zeynep, Katerina, Giorgos, are good company), using today's words and `met_words`; a new word only with its meaning said. Once at normal speed (role `f` for the narrator), then sentence by sentence at speed 0.8 with its meaning and an `echo` for some.
   5. *Sorular* (≈2 min): three questions about the story or the words, a `pause` of 4–5 s, the answer in Greek, an `echo`.
   6. *Kapanış* (≈30 s): the story once more at normal speed, or one line of encouragement and today's next step in the app.
4. **A weekly episode** has the same parts, longer: the week's words in two groups (with a short review question between them), the week's mistakes, the current lesson's point (as in a chapter episode's "point", from its chapter), a longer story (15–25 sentences) told in two halves with a true/false question after each half, and five questions at the end. Its date is the first day it is for: the Saturday when `daily-prep` makes it on Friday for the weekend.
5. **The script:** as a chapter's, with `"kind": "daily"` (or `"weekly"`), `"curriculum"` and `"stage"` of the current lesson, `"date"` from the material, `"focus"`: the Greek words and points it drilled, and `"sources": [{"what": "report", "note": "due and weak words, mistakes"}]` (plus `{"what": "chapter", "ref": …}` when you used the chapter). Then check and render as in §5. In a scheduled run there is nobody to tell the cost to: render only under 80% of the service's free quota.
6. **Privacy:** the text goes to the learner's keyed voice service. It holds learning content only: words, sentences, the right forms. Never the learner's name, their answers quoted as theirs, scores, counts, how long or when they studied, or anything from a captured document or a tutor chat about their life. Never edge-tts (the program refuses it).
7. **Keep the folder small:** after a render, `uv run oknos podcast prune` keeps the newest 14 daily and 8 weekly episodes and deletes the Turkish or English clips no remaining script speaks (Greek clips and chapter episodes stay).

## 4. Writing for the ear

- **Never put Greek inside a Turkish or English segment.** The Turkish voice cannot say Greek. Split: `{"lang": "tr", "say": "Günaydın demek için:"}`, `{"lang": "el", "say": "Καλημέρα."}`. Transliteration in Latin letters is not needed either; just play the Greek.
- Short sentences, spoken style, *sen* in Turkish, "you" in English. No "as you see in the table", no bold, no brackets, no lists: say it.
- Say what is coming before it comes ("Şimdi her satırı yavaşça dinle ve arkasından tekrar et.").
- Greek segments: one sentence or one word each; give a dialogue line its `who` (the speaker's voice: `src/oknos/speakers.json`), else `role` `f` or `m`. Words and examples in the narrator's voice need no `who`.
- Gaps: `echo` after a Greek line the learner should repeat; `pause` 1–2 s between sections and 4–5 s after a question. Not every line needs a gap; a gap after every sentence is tiring.
- Numbers, dates and abbreviations in the learner's language are written as words ("üç", not "3"), so the voice reads them right.
- No personal data, ever: a chapter episode is about the chapter, not about the learner.

## 5. Check, say the cost, make it

```
uv run oknos podcast check <id>        # problems, length, and the characters still to voice, per service
```

Fix every PROBLEM; look at the notes. Then **tell the learner the length and the characters it will spend** (and this month's use against the free quota, from the output) before rendering; a first episode in a new language makes every explanation line new, later ones reuse the Greek clips. Then:

```
uv run oknos podcast render <id> --wait
```

`--wait` waits out Azure's free-tier pace (20 clips a minute) instead of handing clips to the next service. An episode of 150–200 lines takes a few minutes the first time. When it is done, tell the learner in one or two sentences where to find it: the Podcast page (the headphones link on the home screen's coach tile, or "Listen" on the Book screen and in the chapter), also from the phone. Ask how it sounded; their remarks (too fast, gaps too short, too much Turkish) go into the next script, and into `docs/PODCASTS.md` if they change the default shape.

## 6. Never

- Never track or ship an episode, a script or a source note: they live in `learner/podcasts/`.
- Never re-voice, translate or reproduce someone else's podcast, video or post; never download one without the learner's yes for that source and a check of the platform's terms.
- Never use edge-tts for a script (the program refuses it anyway).
