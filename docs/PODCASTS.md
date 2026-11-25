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

The voices and the engine (a larger pool, Google Chirp 3 HD's 30 voices, Gemini's multi-speaker TTS, music) are a separate piece of work. The sources this direction draws on are Greek-teaching podcasts and channels (Easy Greek, Language Transfer, Let's Talk Greek, Easy Greek Stories), as ideas only. No podcast teaches Greek in Turkish.

**The cast** is a list in the script; a speech segment's `who` names a cast id:

```json
"cast": [
  {"id": "ada", "name": "Ada", "role": "host", "lang": ["tr"], "gender": "f", "age": "35", "manner": "warm, curious"},
  {"id": "mert", "name": "Mert", "role": "cohost", "lang": ["tr", "el"], "gender": "m"},
  {"id": "katerina", "name": "Κατερίνα", "role": "guest", "lang": ["el"], "gender": "f"}
]
```

`role` is `host`, `cohost`, `guest`, `character` or `narrator`. Until a cast is mapped to particular voices, a member speaks with the voice of their gender. `check` refuses a `who` that is not in the cast, and a line in a language its speaker does not speak. Scripts without a cast work as before; the 24 chapter episodes stay as they are until v2 is agreed after a pilot.

## Making the audio

```
uv run oknos podcast list                 # the scripts and episodes in learner/podcasts/
uv run oknos podcast check book.lesson-01.tr
uv run oknos podcast render book.lesson-01.tr --wait
uv run oknos podcast material daily       # what a personal episode is written from (below)
uv run oknos podcast prune                # old personal episodes and the clips only they used
```

`render` makes the missing clips through the voice chain (`voice.make`; a Greek clip the app already has is reused), then joins them with ffmpeg: each clip with the services' silence at both ends trimmed and at its speed (`atempo`), a short breath after each line, the script's pauses and gaps, one loudness pass (−16 LUFS), one mp3 (`episode.mp3`, 64 kb/s mono, about 6 MB for 13 minutes). `episode.json` beside it holds the length, the time of each part, the characters used and the services that spoke. ffmpeg must be installed (it is for the films).

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

- **When:** `daily-prep` (step 5b) writes tomorrow's, only when `podcast.personal` in `profile.json` says yes (`{"daily": true, "weekly": true}`): a daily episode for Monday to Friday, the weekly one on Friday evening for the weekend. With only `daily`, one every day. It renders only under 80% of the service's free quota.
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
