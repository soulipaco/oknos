# Oknos by hand

Use this guide if you are happy in a terminal and want to run Oknos yourself, with no AI agent. The app never calls an agent. In the usual setup an agent does the coaching, and that coaching is only files in a documented format, so you can do most of it by hand too. This page says how, and is honest about the parts that are not worth doing by hand.

Run every command from the repository folder. All you need installed is [uv](https://docs.astral.sh/uv/), which brings Python. You need git only to clone and update, and [ffmpeg](https://ffmpeg.org/) only to make podcast episodes. Your own data lives in `learner/`, which git never tracks: back up that folder and you have backed up everything.

## 1. Install, run, update

```
git clone https://github.com/soulipaco/oknos
cd oknos
uv run oknos start        # starts in the background, opens http://127.0.0.1:8642 (or the next free port)
uv run oknos stop
uv run oknos health       # checks the install; add --server while the app runs
uv run oknos shortcut     # a desktop icon that starts it
```

The first `start` downloads Python and the packages, which takes a minute or two. To update, run `git pull`, then `uv run oknos stop; uv run oknos start`. A restart is needed after any change to the code. New or edited content only needs `uv run oknos reload`.

## 2. Your settings: `learner/profile.json`

The app creates the `learner/` folder on its first start. The language switch and the session length are in the app itself. Everything else lives in this file (UTF-8 JSON). Keep any keys you find there that you do not know:

```json
{
  "ui_lang": "tr",
  "minutes": 15,
  "days_per_week": 5,
  "target_exam": "b1-keg",
  "level": "A1",
  "curriculum": "oknos-book",
  "voice": {"providers": ["google"]},
  "podcast": {"providers": ["google"]}
}
```

| Key | What it does |
|---|---|
| `ui_lang` | `"en"` or `"tr"`, the language of the app and of the explanations |
| `minutes` | the length of the daily session, 1–120 |
| `target_exam` | `"a2ltr"` (A2 + history), `"b1-keg"` (Ελληνομάθεια B1) or `"undecided"` |
| `level` | `A1`, `A2` or `B1`: daily sessions never serve an item above it (default A1); raise it as you progress |
| `curriculum` | `"oknos-book"` (26 lessons, the default) or `"open-a1-b1"` (the shorter 12-chapter course) |
| `voice.providers` | the order of the voice services that make your clips (also on the Voice screen) |
| `podcast.providers` | the same, for podcast episodes |
| `edge_tts_ok` | `true` lets edge-tts, Microsoft's unofficial read-aloud service, voice the content (your own use only) |

Run `uv run oknos reload` after editing it. [COACHING.md §7.6](COACHING.md) lists the rest.

## 3. The voice

Every Greek text of the open content already comes with a recorded clip (Google Chirp 3 HD), so you don't have to do anything. To voice your own exercises too, or to use other voices, put a key for one service in `learner/secrets.env`, for example `GOOGLE_TTS_API_KEY=…` ([VOICE.md, "Setting a service up"](VOICE.md#setting-a-service-up) shows where each key comes from), then:

```
uv run oknos voice status     # which keys are there, characters used this month, clips made
uv run oknos voice sample google
uv run oknos voice build      # makes every missing clip; resumable
```

A key is only ever sent to its own service, and only the Greek text goes with it.

## 4. Your own exercises

Make a pack folder in `learner/generated/` with a `pack.json`:

```json
{"id": "my-practice", "title": {"en": "My own practice", "tr": "Kendi alıştırmalarım"},
 "version": 1, "levels": ["A1", "A2"], "visibility": "generated", "licence": "private",
 "source": "Written by me"}
```

Then add `items/<anything>.json`, a JSON array of items. A word and a multiple-choice question look like this:

```json
[
  {"id": "v-farmakeio", "type": "vocab", "skill": "vocab", "level": "A1", "topics": ["health"],
   "el": "το φαρμακείο", "lemma": "φαρμακείο", "pos": "noun", "gender": "n", "en": "pharmacy", "tr": "eczane",
   "example": {"el": "Το φαρμακείο είναι κλειστό.", "en": "The pharmacy is closed.", "tr": "Eczane kapalı."}},

  {"id": "q-farmakeio", "type": "mcq", "skill": "vocab", "level": "A1", "topics": ["health"],
   "rubric": {"el": "Διαλέξτε τη σωστή απάντηση.", "en": "Choose the correct answer.", "tr": "Doğru cevabı seçin."},
   "prompt": {"el": "Πού αγοράζουμε φάρμακα;", "en": "Where do we buy medicine?", "tr": "İlacı nereden alırız?"},
   "options": ["Στο φαρμακείο.", "Στον φούρνο.", "Στο σχολείο."],
   "answer": 0}
]
```

Check the pack and bring it into the running app:

```
uv run oknos validate learner    # explains every problem, Greek spelling checks included
uv run oknos words learner        # lists any Greek word you show that has no meaning when tapped
uv run oknos reload
```

A word that `words` lists gets a row in your pack's `glossary.json`; the open packs' `glossary.json` files show the format.

The other exercise types are `form`, `true_false`, `match`, `gap_bank`, `categorise`, `table_fill`, listening variants, `write` and `speak`. `uv run oknos schema` writes a JSON Schema for each of them to `schemas/`, and the open packs in `content/open/` are full examples.

## 5. Your own book or word list

`uv run oknos import <mapping> --source <folder>` turns material you own (word lists, a scanned coursebook, handouts) into a private pack in `content/private/`, which git never tracks. [IMPORTING.md](IMPORTING.md) shows how to write the mapping.

## 6. Writing and speaking

What you write or record in the app is kept as a submission, waiting to be marked. `uv run oknos report` lists the submissions with their text. `uv run --group speech oknos transcribe` turns your recordings into text on your computer, the first time after a model download. A teacher or a fluent friend can mark one by writing `learner/feedback/<submission_id>.json` in the format of [COACHING.md §7.3](COACHING.md); the app then shows it next to the original. A mark only counts towards the exam screen when it has a score.

## 7. Podcasts

The 26 book episodes come with the repository and play on the Podcast page. To make your own, write `learner/podcasts/<id>/script.json` in the format of [PODCASTS.md, "The script"](PODCASTS.md#the-script), then:

```
uv run oknos podcast check <id>    # checks the script and says how many characters it will spend
uv run oknos podcast render <id>   # makes episode.mp3 with your voice service; needs ffmpeg
```

## 8. Your record

`uv run oknos report` prints everything the app knows about your progress as one JSON document. That covers the readiness per exam part, what is due, your weak words and recent mistakes. It is the same view a coach would read.

## 9. On your phone

Through your own private network (Tailscale Serve), never the open internet: [HOSTING.md](HOSTING.md).

## 10. What is not worth doing by hand

These are files too, but writing them means doing the coach's thinking yourself:

- **a plan** to an exam date (`learner/coach/plan.json`, [COACHING.md §11](COACHING.md));
- **a mock exam** (`learner/coach/mocks/<id>.json`, [§12](COACHING.md)), which also needs a set of unseen exam-format items;
- **the home screen's note** (`learner/coach/message.json`, [§7.1](COACHING.md));
- **exam dates** (`learner/coach/watch.json`): the official pages are linked in `exams/*.json`.

`oknos run` and `oknos schedule` start an agent, so leave them out. If you later want the coaching done for you, open an agent in this folder and say "coach". It reads the same files and carries on from where you are.
