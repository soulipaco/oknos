# Podcast lessons of the Oknos book

One audio episode per chapter of the Oknos book (`content/open/oknos-book/`), Greek with Turkish explanations, so a fresh clone can listen on the app's Podcast page before anyone sets up a voice service. See `docs/PODCASTS.md`, "Shipped episodes".

- **Made with** Google's voices only: Cloud Text-to-Speech, Chirp 3 HD, for now, then Gemini TTS as its daily quota allows. `index.json` says which service voiced each episode (`p`). Google's terms let its audio be used in applications and media; ElevenLabs', Azure's free tier and edge-tts do not, so they never make audio for this folder, and `oknos guard` checks it.
- **Licence:** CC BY-SA 4.0, like the book they teach (`content/open/LICENSE.md`). Attribution: "Oknos contributors", voices by Google.
- **Layout:** `<id>/script.json` (what is said, by whom, at what pace), `<id>/episode.json` (parts and lines in time) and `<id>/episode.mp3` (mono, 32 kb/s).
- **Waiting for audio:** a folder with only `script.json` is an episode whose audio is not made yet; the app leaves it out until `episode.mp3` is there.
- **The app** plays the learner's own rendering of an episode (`learner/podcasts/<id>/`) first, then the one here.
- **Remaking:** `uv run python scripts/ship_podcasts.py --check` says what is missing or out of date; without `--check` it makes it.

Never put personal episodes (daily, weekly) or episodes voiced by another service here.
