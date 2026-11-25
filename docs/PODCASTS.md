# Podcast lessons

Audio lessons to listen to hands-free: on the way to work, while cooking. Each episode is written as **text first** (a script), checked, and then made into one audio file with the voice services the app already uses (`docs/VOICE.md`). The brief and its history are in `docs/prompts/11-podcasts.md`; this file is how it works.

Status (2026-11-23): the pilot. The first episode is the book's Lesson 1 in Turkish: 9 parts, 12.8 minutes, 4,833 Azure characters (76 Turkish and 17 new Greek clips; the dialogue's Greek clips were already there). The maintainer listened and said carry on; Lessons 2 and 3 followed the same day. From then on `daily-prep` keeps the podcast a lesson ahead (step 5a: for a learner who has episodes, one new chapter episode a run, for the current stage and then the next, while the service stays under 80% of its free quota). One episode per book chapter, written by the agent with the `podcast` skill, played on the app's Podcast page. On 2026-11-24 a long-running session made the episodes of lessons 4–24, so every chapter up to the end of A2 has one (drafted by Opus subagents from the chapters, three lessons each, checked, rendered one at a time: 12.2–14.6 minutes and 3,800–5,500 Azure characters each, about 101,000 in all), and the **personal daily and weekly episodes** were built (below); `daily-prep` makes them only for a learner who has said yes (`podcast.personal`). The enrichment loop comes later.

## Decisions (agreed with the maintainer, 2026-11-23)

- **Where:** a Podcast page in the app (`?podcast`), reached from the phone through the tailnet (`docs/HOSTING.md`). It plays with the screen off, remembers where you stopped, and has a download link for the mp3. The laptop must be on.
- **Who writes:** the agent writes each script in spoken style, like a teacher on the radio, from the chapter (`podcast` skill). The program checks it (`oknos podcast check`) and makes the audio (`oknos podcast render`).
- **Explanation language:** the learner's choice, Turkish or English (`podcast.lang` in `profile.json`, else the app's language). The maintainer's episodes are Greek with Turkish explanations. Another language later is a new set of voices and new scripts, not a new system.
- **Voices follow the learner's voice settings** (`voice.providers`, the Voice screen): the Greek is spoken as everywhere else in the app (the same clips are reused), the explanations by the same service's Turkish or English voice. The maintainer's order makes that Azure: Athina and Nestoras for the Greek, Emel for Turkish.
- **What an episode is made from:**
  - for a learner: the open book's chapter, plus their own material when it is enough;
  - for the maintainer: the private book's chapter, then the open book's chapter where the book is thin;
  - if the agent still finds it thin, it may search the web **for ideas only** (Copyright, below).
- **Listening is not answering.** An episode is never exam evidence and does not move the review schedule.

## The script

`learner/podcasts/<id>/script.json`, written by the agent. The id is `<source>.<stage>.<lang>`, e.g. `book.lesson-01.tr` or `open.first-words.en`.

```json
{
  "id": "book.lesson-01.tr",
  "kind": "chapter",
  "curriculum": "greek-helper-book",
  "stage": "lesson-01",
  "lang": "tr",
  "title": {"tr": "Ders 1: Merhaba, ben …", "en": "Lesson 1: Hello, I'm …"},
  "version": 1,
  "written": "2026-11-23",
  "sources": [{"what": "chapter", "ref": "greek-helper/lessons/lesson-01"}],
  "segments": [
    {"part": "Giriş"},
    {"lang": "tr", "say": "Merhaba! Bugün selamlaşmayı öğreniyoruz."},
    {"lang": "el", "say": "Καλημέρα!", "who": "Κατερίνα"},
    {"lang": "el", "say": "Καλημέρα!", "who": "Κατερίνα", "speed": 0.8},
    {"echo": 1.5},
    {"pause": 2}
  ]
}
```

| Segment | Fields | What it does |
|---|---|---|
| `part` | `part` | a chapter mark: the player lists them and jumps to them |
| speech | `lang` (`el`, `tr`, `en`), `say`, `who?` or `role?` (`f`, `m`), `speed?` (0.6–1.0) | one clip. A Greek line with `who` gets that speaker's voice (`src/oknos/speakers.json`); slower speed is made from the same clip (the pitch stays) |
| `pause` | seconds (0.2–20) | silence |
| `echo` | a factor (0.5–3) | a gap to repeat after the speaker: the last clip's length × the factor, plus one second |

`oknos podcast check <id>` refuses a script with:
- Greek letters inside a Turkish or English segment (the Turkish voice would mangle them: split the sentence, Greek in its own segment);
- a Greek segment the Greek lint rejects (`src/oknos/lint.py`);
- an unknown language, speaker role or speed, or a first segment that is not a `part`.

It prints the estimated length and the **characters that still need a clip, per service**: that is what rendering will spend.

## Format v2: a show with a cast (in progress, 2026-11-25)

After listening to the first episodes, the maintainer found them a mechanical lesson rather than a podcast. The voices were flat and few, and the delivery was one narrator. The grammar nuances are what they like; the delivery is what has to change. Agreed direction:

- **Two Turkish hosts.** Ada (f, mid-30s, the teacher, warm, explains with Turkish bridges) and Mert (m, early 30s, the learner: he asks the listener's questions, guesses after a "sen de söyle" pause, makes the typical mistake). There is little banter, and only about the content.
- **A native Greek guest**, Katerina (f, 40s), who says the Greek. The chapter's characters act out the scenes, each with their own voice.
- The hosts and Katerina sound the same in every episode.
- **The shape:**
  - a cold open with a short Greek scene;
  - the scene, then its nuances raised as "why this and not that?";
  - 4–6 key lines to answer;
  - the scene again;
  - a teaser for the next episode.
- **The drill and the Turkish:** the line-by-line drill moves to an optional last part. The Turkish share falls from lesson to lesson, and an episode ends with a few minutes of easy Greek only.
- **Sound:** a short sting between parts and a jingle; never noise under speech.

The voices and the engine are below ("The voices"). The sources this direction draws on are Greek-teaching podcasts and channels (Easy Greek, Language Transfer, Let's Talk Greek, Easy Greek Stories), as ideas only. No podcast teaches Greek in Turkish.

**The cast** is a list in the script; a speech segment's `who` names a cast id:

```json
"cast": [
  {"id": "ada", "name": "Ada", "role": "host", "lang": ["tr"], "gender": "f", "age": "35", "manner": "warm, curious"},
  {"id": "mert", "name": "Mert", "role": "cohost", "lang": ["tr", "el"], "gender": "m"},
  {"id": "katerina", "name": "Κατερίνα", "role": "guest", "lang": ["el"], "gender": "f"}
]
```

`role` is `host`, `cohost`, `guest`, `character` or `narrator`. Each member gets their own voice ("The voices", below). `check` refuses a `who` that is not in the cast, and a line in a language its speaker does not speak. Greek inside a Turkish line is allowed for a member who speaks Greek (a note, not a problem). Scripts without a cast work as before; the 24 chapter episodes stay as they are until v2 is agreed after a pilot.

## The voices (built 2026-11-25)

The maintainer found the first episodes mechanical: two Greek voices for everyone, each line made alone and glued with the same short gap, one narrator. A blind test settled what to change. Four podcast excerpts (two women at a door; a story told in Turkish with two men's Greek lines; two hosts chatting with Greek words in between; the v2 format), each made with seven setups and scored by ear from 1 to 5:

| Setup | Score of 20 |
|---|---|
| **Gemini 3.8 Flash TTS**: two speakers acted in one request, a described style per person | **17** |
| Google Chirp 3 HD, a voice per person | 14–14.5 |
| Azure for the main Greek pair, Chirp for the rest | 14 |
| OpenAI gpt-4o-mini-tts, a described style per person | 13.5 |
| Azure as before (Athina, Nestoras, Emel), line by line | 12.5 |
| Azure in one SSML document, with multilingual voices for the second woman and man | 12.5 |

A voice per person alone gained little; acting the exchange together gained most. So podcasts are voiced by **Gemini TTS**, with **Chirp 3 HD** as the fallback (the same 30 voice names, so people keep roughly their sound). The app's own clips (words, sentences) are not affected: they keep `voice.providers`.

**Setting it up.** `podcast.providers` in `profile.json` is the podcast's own list, e.g. `["gemini", "google"]` (without it the podcast uses the Voice screen's list, as before). Gemini needs its own key from AI Studio (aistudio.google.com/apikey, in a project with billing, which makes it the paid tier: the text is not used to train models) in `learner/secrets.env` as `GEMINI_API_KEY`, and prepaid credit on that project. The Cloud Text-to-Speech key does not reach Gemini: that route needs a signed-in account, not a key.

**Casting** (`src/oknos/casting.py`, `src/oknos/casting.json`). The show's people keep one voice in every episode: Ada Sulafat (warm), Mert Umbriel (easy-going), Katerina Gacrux (mature). A character gets a voice of their gender from the other 27, in an order fixed by their name, so the same character sounds the same in every episode and two people of one episode never share a voice (only with more people of one gender than voices). A cast member may name a voice itself (`"voice": {"google": "Leda"}`). Older scripts are cast too: a Turkish line with no speaker is Ada, a Greek line with no speaker Katerina, a Greek line with a name that character. `oknos podcast check` prints the cast.

**How an episode is made.** When the first ready service in the podcast's list has named voices (gemini, google), the episode is cast:
- Consecutive lines between at most two people (up to 10 lines, 1,000 characters) are one request, acted together, each line with its speaker's style: the setting, then the person's name, age, role and manner from the cast. A slowed line, or a line followed by an echo gap, is made on its own (the gap is measured on it).
- A host may say Greek inside a Turkish sentence ("…şuydu: Ναι."), in her own voice. `check` makes this a note for a cast member whose `lang` includes `el`, and a problem for anyone else; only a service that speaks mixed lines (gemini) makes it, and the render stops if none is ready.
- Between requests, gaps follow the turn-taking: 0.3 s between two people in Greek, 0.35 s in Turkish, 0.25 s for the same person, 0.6 s where the language changes.
- A short jingle opens and closes the episode and a soft sting marks each new part: a plucked motif in D, made from numbers by ffmpeg (original, like the films' ambience). No music runs under speech.
- Chirp, which reads one line at a time, now and then answers a short word with silence: such a clip is asked again in quotation marks.
- Clips are kept in `learner/voice/podcast/` and listed in `episode.json` (`clips`), with `cast`, the services and, for Gemini, the audio tokens; a second render spends nothing. `prune` deletes cast clips no episode lists, once they are three days old.

When the first ready service is Azure or OpenAI, an episode is made line by line with the female or male voice as before, and a line with Greek inside Turkish is refused.

**Cost.** Gemini bills audio by tokens, about 25 a second of speech. The 3.8 Flash TTS price until 2026-12-31 is $9 per million audio tokens (then $18), so a chapter episode of 14 minutes costs about $0.20 ($0.40 from 2027), and 300,000 characters a month about $5 ($10). The credit is prepaid, so it cannot run over; a budget alert in the Google Cloud console is still worth setting. Chirp 3 HD is free up to 1 million characters a month.

**What else was tried.** Azure has only Athina and Nestoras for Greek; its new Turkish HD voices (Elif, Aydın, Grant, Harper on MAI-Voice-2.1, with styles) are refused on the free tier. OpenAI's TTS models shut down on 2027-01-06. ElevenLabs speaks Greek and Turkish with a dialogue API, but costs four to ten times as much at this volume and was not tested. No open model that runs on a laptop speaks Greek well enough (Chatterbox Multilingual was tested in phase 10). Gemini 3.8 is about the best that a low cost buys today.

## Making the audio

```
uv run oknos podcast list                 # the scripts and episodes in learner/podcasts/
uv run oknos podcast check book.lesson-01.tr
uv run oknos podcast render book.lesson-01.tr --wait
uv run oknos podcast material daily       # what a personal episode is written from (below)
uv run oknos podcast prune                # old personal episodes and the clips only they used
```

`render` casts the episode when the podcast's first service has named voices ("The voices"). Otherwise it makes the missing clips through the voice chain (`voice.make`; a Greek clip the app already has is reused), then joins them with ffmpeg: each clip with the services' silence at both ends trimmed and at its speed (`atempo`), a short breath after each line, the script's pauses and gaps, one loudness pass (−16 LUFS), one mp3 (`episode.mp3`, 64 kb/s mono, about 6 MB for 13 minutes). `episode.json` beside it holds the length, the time of each part, the characters used and the services that spoke. ffmpeg must be installed (it is for the films).

Turkish and English clips are kept in `learner/voice/<lang>/` beside the Greek ones. edge-tts never makes them: the scripts are the agent's own texts (SPEC §9).

| Service | Turkish | English |
|---|---|---|
| Azure | Emel (f), Ahmet (m) | Ava (f), Andrew (m) |
| Google Chirp 3 HD | Kore (f), Orus (m) | Kore (f), Orus (m) |
| OpenAI gpt-4o-mini-tts | coral (f), ash (m) | coral (f), ash (m) |

**Cost.** About 400 spoken characters a minute; a chapter episode of 12–15 minutes is about 5,000–8,000 new characters (most Greek lines already have a clip). Azure's free tier is 500,000 a month, Google's 1,000,000. The 26 book chapters together fit in one month of Azure's free tier, next to the daily voice builds.

## The page

`?podcast` lists the episodes, newest first; `?podcast=<id>` plays one: the parts to jump to, the speed (0.8×, 1×, 1.25×), the position kept on that device, the title on the phone's lock screen, a download link and the script as text. The Book screen and a chapter's reader show "Listen" when the chapter has an episode. The server serves only `learner/podcasts/<id>/episode.mp3` (`/podcasts/<id>.mp3`, with range requests so the phone can seek).

## Personal episodes (built 2026-11-24)

A learner's own review to listen to: a **daily** episode of 10–20 minutes (the words due that day and the weak ones, a mistake or two put right, a short original story at their level, three questions) and a **weekly** one of 20–30 minutes (the week's words and mistakes, the current lesson's main point, a longer story in two halves). The agent writes them with the `podcast` skill (§3b) from:

```
uv run oknos podcast material daily     # tomorrow's (or --date YYYY-MM-DD); weekly for the weekly one
```

`material` (`src/oknos/podcast_material.py`) reads the database and writes nothing. It prints the episode's id (`daily.2026-11-25.tr`, `weekly.2026-w48.tr`), its date, whether a script already exists, and the words due (on that day, or in that week) and weak (lapses, low ease), with their meanings and an example sentence (the item's own, else one from a chapter); the recent mistakes with the right answer; the words met in the last days; the current lesson; the words and verbs the learner has met (the story keeps to them); and the last personal episodes with what they drilled (`focus`), so the next one does not repeat them. Reading cards (`open-alphabet`) are left out.

A personal script is a chapter script with `kind` `daily` or `weekly`, the `date` it is for, `focus` (the Greek words and points it drilled) and the report among its `sources`; `check` refuses one without a date or whose id does not start with its kind.

- **When:** `daily-prep` (step 5b) writes tomorrow's, only when `podcast.personal` in `profile.json` says yes (`{"daily": true, "weekly": true}`): a daily episode for Monday to Friday, the weekly one on Friday evening for the weekend. With only `daily`, one every day. It renders only under 80% of the service's free quota; Gemini has no free quota, and a daily episode costs it a few cents.
- **Where:** the home screen's coach tile links "Today's episode" (the daily one for today, else this week's weekly one: `/api/home` → `podcast_today`); the Podcast page lists it with the others.
- **Privacy:** the text goes to the learner's keyed voice service (never edge-tts), so it holds learning content only: words, sentences, right forms. Never the learner's name, their answers quoted as theirs, scores, counts, when or how long they studied, or anything from a capture or a tutor chat about their life.
- **Keeping it small:** `uv run oknos podcast prune` (run by `daily-prep` after a render) keeps the newest 14 daily and 8 weekly episodes and deletes the Turkish and English clips no remaining script speaks. Greek clips stay (the app uses them), and chapter episodes are never deleted.
- **Cost:** a daily episode of about 14 minutes spends about 4,000–5,500 new characters (nearly all the Turkish is new each day; many Greek words already have a clip), a weekly one about 8,000–10,000. Weekdays plus a weekly: about 110,000–150,000 characters a month, inside Azure's free 500,000 next to the chapter episodes and the daily voice builds.

## Copyright and privacy (must hold)

- Other people's podcasts, videos and posts are **sources of ideas only**: topics, which words and phrases come up, what learners ask, an episode worth listening to next (with a link). An episode never re-voices, translates or reproduces their content, and nothing is downloaded without the maintainer's yes for that source and a check of the platform's terms.
- Each idea source is recorded in the script's `sources` (`{"what": "idea", "url": …, "note": what was taken}`). Scripts, notes and episodes live in `learner/` and are never tracked.
- Episodes of the private book or of a learner's record stay in `learner/podcasts/`; they are never shipped.
- A chapter episode carries no personal data. Personal episodes are spoken only by a keyed service on the learner's own account, never by edge-tts, and hold learning content only (above).
- Episodes that might ship with the repository one day come only from the open content, voiced by Google (as the shipped clips).

## Later (not built)

- **The enrichment loop:** the agent proposes Greek-teaching podcasts, channels and accounts, the maintainer says yes or no to each, and the agent keeps a private list (`learner/podcasts/sources.json`: link, what it is, the date, the yes) to draw ideas from when writing.
- Episodes for every book chapter and the open book; a private podcast feed if the page is not enough.
