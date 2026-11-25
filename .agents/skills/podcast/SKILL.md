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

## 3. The shape of a chapter episode: a show with a cast (12–15 minutes)

This is format v2, agreed with the maintainer on 2026-11-25 (`docs/PODCASTS.md`). An episode is not a lesson read aloud but a short show: two Turkish hosts talk about a scene, and the grammar nuances come out of their talk. The 24 episodes made before (v1: one narrator, a drill after every line) stay until they are redone.

**The cast** (`cast` in the script; every speech line's `who` names a cast id). The show's people keep their ids in every episode, so they keep their voices:
- `ada`: host, `lang` `["tr", "el"]`, f, 35. The teacher: warm and curious, she explains with Turkish bridges ("Türkçedeki -de ekinin işini…").
- `mert`: cohost, `["tr", "el"]`, m, 32. The learner: easy-going and a bit lazy. He asks the listener's question, guesses after the listener's pause, and makes the typical mistake. He is not a comedian: little banter, and only about the content.
- `katerina`: guest, `["el"]`, f, 45. A native speaker, warm and patient. She says the model sentences and leads the repeat corner.
- The chapter's people: each a `character`, `["el"]`, with gender, a rough age and a manner ("Υπάλληλος, m, 50, polite, formal, brisk"). Ids are lower-case ASCII (`ayse`, `nikos`); the `name` may be Greek. Keep a recurring character's id and gender the same in every episode, so they keep their voice.

Casting voices to people is the program's job (`src/oknos/casting.json`); you never name a voice.

**The parts** (named in the learner's language, as a show would):
1. *Açılış* (30–40 s): a short Greek scene from the chapter, with no explanation, then one hook question ("Neden her yerin önünde başka bir küçük kelime var?").
2. *Hoş geldin* (≈1 min): a few lines between Ada and Mert on what you will be able to say today. No list.
3. *The scene(s)* (≈2–3 min): the chapter's dialogue, played by its people at normal speed. Then the scene once more at `speed` 0.85, or only its key lines, with a "sen de söyle" question.
4. *Unpacking* (≈4–5 min, one part per point): 2–3 nuances, each a "why this and not that?". Mert guesses, Ada explains with a Turkish bridge, and Katerina or Ada says the Greek. Tables become patterns said aloud.
5. *Sıra sende* (≈2 min): 4–5 prompts. For each one Ada asks "nasıl dersin…?", a `pause` of 4–5 s leaves time for the listener, Mert answers (sometimes wrong, then corrected), and the right Greek follows with an `echo`.
6. *Mert'in hatası* (≈1 min): the typical mistake of a Turkish speaker, said once as Mert's slip and put right at once.
7. *A game* (≈1–2 min): a quick quiz between the hosts.
8. *Sahne yeniden* (≈1 min): the scene again at normal speed; by now the listener understands all of it.
9. *A corner* (≈1 min): culture or etymology, told as a story. Check every fact, and leave out what you cannot check.
10. *Gelecek bölüm* (30 s): a teaser of the next chapter's scene, and goodbye.
11. *Tekrar köşesi* (optional, last): Ada says a short drill follows; Katerina says 5–6 key lines at `speed` 0.8, each with an `echo`; then one line of goodbye.

**The Turkish falls from lesson to lesson.** From about lesson 8, end with 2–3 minutes of easy Greek only, just to listen to: Katerina tells the scene as a little story. From lesson 13 (A2) on, do this in every episode, and let the hosts use more Greek between them.

## 3b. A personal episode: daily (10–20 minutes) and weekly (20–30 minutes)

Written by `daily-prep` (its step 5b) for a learner who said yes to them (`podcast.personal` in `profile.json`), or when the learner asks ("make me today's podcast"). It is the learner's own review to listen to: the words due that day and the weak ones, a mistake or two put right, a short story at their level, a look at the current lesson.

1. **The material:** `uv run oknos podcast material daily` (or `weekly`; `--date` for another day than tomorrow). It prints the id (`daily.2026-11-25.tr`, `weekly.2026-w48.tr`), the date, the language, whether a script already exists, and: `due` and `weak` words with their meanings and an example, `mistakes` (what was asked and the right answer), `new` (words met in the last days), `current` (the lesson), `met_words` and `met_verbs` (what the story may use), and `previous` (the last personal episodes and their `focus`, so you do not repeat them). If `exists` is true, stop: never make the same episode twice.
2. **Pick:** a daily episode drills 8–12 words (the due ones first, then weak ones not drilled in the last two `previous` episodes) and one or two mistakes; a weekly one 15–20 words, the week's mistakes grouped by what they have in common, and the current lesson's main point. Skip words whose meaning in `due` is a fragment or a reading card.
3. **The shape of a daily episode** (each a `part`, named in the learner's language). It uses the show's cast (§3): Ada and Mert talk, Katerina says the Greek and tells the story, and the story's people are `character`s. Keep it within about 30–35 requests (§4): Ada and Mert go through the words in one run per few words, rather than a word, a pause, a meaning and an echo for each.
   1. *Giriş* (≈30 s): what today holds, in two sentences. No date, no numbers about the learner.
   2. *Bugünün kelimeleri* (≈5 min): each word: the Greek, a `pause` of 1.5 s to guess, the meaning, the Greek slowly, an `echo`; then a short sentence with it (the example, or one you write with `met_words`), its meaning, an `echo`.
   3. *Düzeltelim* (≈2 min): one or two of `mistakes`, taught as a point ("üçüncü çoğul kişide …"), the right form in two or three Greek sentences with `echo`. Say the wrong form only as the common mistake, never as theirs.
   4. *Kısa hikâye* (≈4 min): an original story of 8–12 short sentences at the learner's level, about everyday life (the open book's people, Zeynep, Katerina, Giorgos, are good company), using today's words and `met_words`; a new word only with its meaning said. Katerina tells it once at normal speed, and its people may speak their own lines. Then Ada and Mert go through it, saying some sentences at speed 0.8 with an `echo`.
   5. *Sorular* (≈2 min): three questions about the story or the words, a `pause` of 4–5 s, the answer in Greek, an `echo`.
   6. *Kapanış* (≈30 s): the story once more at normal speed, or one line of encouragement and today's next step in the app.
4. **A weekly episode** has the same parts, longer: the week's words in two groups (with a short review question between them), the week's mistakes, the current lesson's point (as in a chapter episode's "point", from its chapter), a longer story (15–25 sentences) told in two halves with a true/false question after each half, and five questions at the end. Its date is the first day it is for: the Saturday when `daily-prep` makes it on Friday for the weekend.
5. **The script:** as a chapter's, with `"kind": "daily"` (or `"weekly"`), `"curriculum"` and `"stage"` of the current lesson, `"date"` from the material, `"focus"`: the Greek words and points it drilled, and `"sources": [{"what": "report", "note": "due and weak words, mistakes"}]` (plus `{"what": "chapter", "ref": …}` when you used the chapter), and the `cast` of §3 (Ada, Mert, Katerina and the story's people). Then check and render as in §5. In a scheduled run there is nobody to tell the cost to. With a free-tier service, render only under 80% of its quota. With Gemini (prepaid credit, a few cents an episode), render, and say in the run's summary what it spent.
6. **Privacy:** the text goes to the learner's keyed voice service. It holds learning content only: words, sentences, the right forms. Never the learner's name, their answers quoted as theirs, scores, counts, how long or when they studied, or anything from a captured document or a tutor chat about their life. Never edge-tts (the program refuses it).
7. **Keep the folder small:** after a render, `uv run oknos podcast prune` keeps the newest 14 daily and 8 weekly episodes and deletes the Turkish or English clips no remaining script speaks (Greek clips and chapter episodes stay).

## 4. Writing for the ear

- **Write in exchanges.** The voice service acts the people of a run of lines together in one request, and that is where the natural sound comes from: ElevenLabs v4 (the maintainer's first service) up to ten people, Gemini (the fallback) two. A run between Ada and Mert, with Katerina saying the Greek between them, or a whole scene, sounds like talk. Still bring Katerina in at deliberate points (a model sentence, the repeat corner), not after every host line: with Gemini a third voice starts a new request, and the flow resets a little.
- **Greek inside a Turkish line**, only for a cast member whose `lang` includes `el` (Ada, Mert): "Pire'de demek için şunu dersin: στον Πειραιά."
  - Keep it to a few words; a whole Greek sentence goes in its own `el` line.
  - `check` notes such lines. The render refuses them when no ready service speaks mixed lines.
  - With the old services (Azure, line by line), split them as before: `{"lang": "tr", "say": "Günaydın demek için:"}`, `{"lang": "el", "say": "Καλημέρα."}`.
  - Nobody else, neither a character nor Katerina, ever gets Greek inside a Turkish line.
- Latin transliterations ("ston, stin, sto") only when you name an ending as a sound; otherwise say the Greek itself.
- Short sentences, spoken style, *sen* in Turkish, "you" in English. No "as you see in the table", no bold, no brackets, no lists: say it.
- Say what is coming before it comes ("Şimdi her satırı yavaşça dinle ve arkasından tekrar et.").
- Greek segments: one sentence or one word each, with the `who` of the person saying it.
- **Gaps:**
  - an `echo` after a Greek line the learner should repeat;
  - a `pause` of 4–5 s after a question to the listener;
  - nothing between ordinary lines: the program puts natural gaps between turns.

  Not every line needs a gap; a gap after every sentence is tiring.
- **A slowed line** (`speed` below 1) is said slowly by an audio tag (ElevenLabs) or a style (Gemini), inside its exchange. Use it for the repeat moments only.
- **Few, long runs.** Every `pause`, `echo` and `part` ends a request, and the acting starts afresh after it.
  - So merge consecutive lines of one speaker, put no `pause` between ordinary turns, and save `echo` for the 5–8 lines that matter most (and for the repeat corner).
  - With ElevenLabs the budget is the month's credits, not requests (`check` prints the credits left; about 0.4 a character). A chapter episode is about 8,500 characters, a daily one 4,000–5,000, a weekly one about 9,000.
  - With Gemini it is 100 requests a day. A request is one exchange or one person's run of up to 24 lines or 2,400 characters. `check` prints the requests a render needs: aim at about 45 for a chapter episode, 30–35 for a daily one and about 50 for a weekly one, so the episode can still go to Gemini when ElevenLabs' credits run out.
- Numbers, dates and abbreviations in the learner's language are written as words ("üç", not "3"), so the voice reads them right.
- No personal data, ever: a chapter episode is about the chapter, not about the learner.

## 5. Check, say the cost, make it

```
uv run oknos podcast check <id>        # problems, length, the cast and its voices, and what is still to voice, per service
```

Fix every PROBLEM, and look at the notes. Then, before rendering, **tell the learner the length and what it will spend**:
- with ElevenLabs (first in `podcast.providers` in `profile.json`): the characters, against the credits left this month (about 0.4 credits a character, so about 3,500 for a chapter episode);
- with Gemini: the audio tokens, about $0.20 for a chapter episode of 14 minutes ($0.40 from 2027);
- with a free-tier service: the characters, against this month's quota.

Then:

```
uv run oknos podcast render <id> --wait
```

With ElevenLabs, an episode whose characters do not fit the credits left goes whole to the next service (`check` says so). With Gemini, render only when the requests `check` prints fit what is left today (the day resets at 10:00 in Greece). A render that reaches the day's limit stops, keeps its clips, and resumes the next day with the same command.

`--wait` waits out a service's pace instead of handing lines to the next service. An episode takes a few minutes the first time; a second render spends nothing. When it is done, tell the learner in one or two sentences where to find it: the Podcast page (the headphones link on the home screen's coach tile, or "Listen" on the Book screen and in the chapter), also from the phone. Ask how it sounded; their remarks (too fast, gaps too short, too much Turkish) go into the next script, and into `docs/PODCASTS.md` if they change the default shape.

## 6. Never

- Never track or ship an episode, a script or a source note: they live in `learner/podcasts/`.
- Never re-voice, translate or reproduce someone else's podcast, video or post; never download one without the learner's yes for that source and a check of the platform's terms.
- Never use edge-tts for a script (the program refuses it anyway).
