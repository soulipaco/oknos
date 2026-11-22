# Voice clips for the open content

Spoken Greek for every text of the open packs in `content/open/` (words, example sentences, the open book's dialogue lines and examples, listening passages, every word you can tap), so a fresh clone sounds good before anyone sets up a voice service. See `docs/VOICE.md`.

- **Made with** Google Cloud Text-to-Speech, Chirp 3 HD: **Kore** for the narrator and female speakers, **Orus** for male ones. Google's Cloud terms let its audio be used in applications. Azure's free tier and edge-tts do not, so they never make clips for this folder.
- **Licence:** CC BY-SA 4.0, like the texts they read (`content/open/LICENSE.md`). Attribution: "Oknos contributors", voices by Google Cloud Text-to-Speech.
- **Layout:** `<role>/<key[:2]>/<key>.mp3`, the same names as a learner's own clips in `learner/voice/`. `key` is the SHA-1 of `<role>|<text>`, the text normalised (NFC, single spaces, case-folded; `src/oknos/voice.py`). `index.json` lists every clip with its role and text. Chirp 3 HD sometimes sends back silence for a short word; the script checks every clip (its loudness with ffmpeg, else its length) and asks again, then as `word.` or `«word»`, which sound the same. Such a clip's `said` records what was sent.
- **The app** plays the learner's own clip first, then the one here, then lets the browser's voice read the text.
- **Remaking:** after a change to the open content's Greek, `uv run python scripts/ship_voice.py --secrets <path to a secrets.env with GOOGLE_TTS_API_KEY>` makes only what is missing; `--prune` deletes clips no text uses any more; `--check` makes nothing. A test (`tests/test_voice.py`) fails while a text has no clip.

Never put clips of the private book (`content/private/`) or of the coach's per-learner packs (`learner/generated/`) here.
