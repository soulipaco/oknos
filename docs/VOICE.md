# The Greek voice

Oknos reads Greek aloud from **clips made ahead of time**. The app knows what it will say (words, example sentences, dialogue lines, listening passages, every word you can tap), so each text is made once, by the first voice service in your list that works, and kept in `learner/voice/`. Anything without a clip (a word the coach added today) is read by your browser's own voice, as before. In the app, the speaker icon at the top opens **Voice**, where you can hear each service, see what it costs and change the order.

The open content comes with its clips already made (below), so a fresh clone sounds good with no key at all. The private book and the coach's own items are spoken by your own service, on your own computer. Only the Greek text goes to a voice service, never your answers, your writing or your progress.

## Clips shipped with the open content

Every text of the open packs (`content/open/`, the open book included) has a clip in `content/open-voice/`: 2,206 clips, about 34,000 characters, about 16 MB in the repository (7 KB a clip on average). They are made with **Google Chirp 3 HD**, Kore for the narrator and female speakers and Orus for male ones, the voice of the published films: Google's Cloud terms let its audio be used in applications, while Azure's free tier and edge-tts do not. Licence CC BY-SA 4.0, like the texts (`content/open-voice/README.md`).

The app looks for a clip in this order:

1. `learner/voice/`, your own clips;
2. `content/open-voice/`, the shipped ones (the same file names: role and text);
3. none: your browser's voice reads the text.

`oknos voice status` counts the shipped clips with your own. `oknos voice build` does not remake a shipped clip when your first ready service is Google (it would be the same voice) or when no service is set up. When your first service has other voices (Azure, edge, OpenAI), it makes those texts too, so each speaker keeps one voice across the open content and the book; your clip then wins over the shipped one.

After a change to the open content's Greek, the maintainer remakes what is missing. Until then the browser's voice reads the new text, and `oknos validate content/open` (also in CI) prints a note, not a failure; the tests check only that the shipped clips and `index.json` agree:

```
uv run python scripts/ship_voice.py --check                       # what is missing or stale
uv run python scripts/ship_voice.py --secrets learner/secrets.env # make the missing clips (Google key)
uv run python scripts/ship_voice.py --secrets learner/secrets.env --prune  # and delete unused ones
```

Chirp 3 HD now and then sends back silence for a short word (92 of the first 2,206 clips, all short words or letter pairs). The script checks every clip, by its loudness with ffmpeg or else by its length, and asks again, then as `word.`, `«word»` or `word!`, which sound the same (24 clips; `said` in `index.json`); `--recheck` finds silent clips among those already made. What stays silent is listed under `browser` in `index.json` and read by the browser's voice (none today; κι came out on a later try). A test fails on a clip too short to hold speech.

Never the private book (`content/private/`) or the coach's packs (`learner/generated/`): those are never shipped.

## The services

From the listening test of 2026-11-22 (ten sentences from the open book, the same eight voices for each; ranked by the maintainer's ear):

| Service | Voices | Sound | Cost and terms |
|---|---|---|---|
| **Azure Speech** (Microsoft, official) | Athina, Nestoras | best | Your own key. Free tier F0: 500,000 characters a month; the whole book is about 150,000 the first time. The free tier makes 20 clips a minute. |
| **edge-tts** (Microsoft, unofficial) | Athina, Nestoras | best (the same voices) | Free, no account. The Edge browser's read-aloud service, used from outside the browser: Microsoft can slow it or close it, and the clips are for your own computer only. Only with your yes (`"edge_tts_ok": true` in `learner/profile.json`), and never for the coach's own texts (SPEC §9). |
| **Google Cloud Text-to-Speech** | Chirp 3 HD Kore, Orus | very good, just behind Microsoft | Your own key; 1 million characters free a month (billing must be on; the free trial covers it). **The default for a new learner**, and the voice of the shipped clips. |
| **OpenAI** | gpt-4o-mini-tts (coral, ash) | good, a slight accent | Your own key; pay as you go, about one or two dollars for the whole book. |
| Your browser's voice | on Windows, Stefanos | robotic | Always there; it reads whatever has no clip. |

Tested and not offered: OpenAI tts-1-hd (unclear Greek), Chatterbox Multilingual and F5-TTS-Greek (local models, no better than the browser's voice here). OpenAI's TTS models (gpt-4o-mini-tts, tts-1) shut down on 2027-01-06.

**For the podcasts only: Gemini TTS** (Google's Gemini API, `GEMINI_API_KEY` from aistudio.google.com/apikey in a project with billing and prepaid credit; the paid tier does not use the text for training). It won a second blind test of seven setups on podcast excerpts on 2026-11-25 (17 of 20, against 12.5 for Azure line by line): two speakers acted together, a described style per person, Greek inside a Turkish sentence. About $0.20 a 14-minute episode until 2026-12-31, then about $0.40. It never makes the app's clips (`voice.podcast_providers()`); the podcast's own list is `podcast.providers` in the profile. Google Chirp 3 HD has the same 30 voices (14 female, 16 male) by name in Greek, Turkish and English, and is the fallback. How an episode is cast: `docs/PODCASTS.md`, "The voices".

**For the podcasts only: ElevenLabs v4** (elevenlabs.io, `ELEVENLABS_API_KEY`, a paid plan for its library voices). On 2026-11-25 the maintainer heard it beside Gemini and preferred it (v4 > Gemini > ElevenLabs v3), so their podcast list is ElevenLabs, then Gemini, then Chirp 3 HD. Up to ten people are acted in one request, each in a native Greek or Turkish voice of its library; the plan's monthly credits are a hard cap (about 0.4 a character, measured).

For the podcast lessons (`docs/PODCASTS.md`) each keyed service also speaks Turkish and English: Azure Emel and Ahmet (tr), Ava and Andrew (en); Google Chirp 3 HD Kore and Orus (tr-TR, en-US); OpenAI coral and ash. Those clips are kept in `learner/voice/tr/` and `learner/voice/en/`; edge-tts never makes them, as the scripts are the agent's own texts.

Each character in the book's dialogues gets a voice of their kind (Zeynep and Katerina the female voice, Giorgos and Stelios the male one; `src/oknos/speakers.json`), so a dialogue sounds like two people.

## Setting a service up

Keys go in `learner/secrets.env` (git never tracks `learner/`), one per line. They are only ever sent to their own service.

- **Google:** console.cloud.google.com → start the free trial → create a project → enable *Cloud Text-to-Speech API* → Credentials → Create credentials → API key, restricted to *Cloud Text-to-Speech API* → `GOOGLE_TTS_API_KEY=…`
- **Azure:** azure.microsoft.com/free with a Microsoft account → create a *Speech* resource, region West Europe, pricing tier *Free F0* → Keys and Endpoint → `AZURE_SPEECH_KEY=…` and `AZURE_SPEECH_REGION=westeurope`
- **OpenAI:** platform.openai.com/api-keys → new secret key, Restricted with *Audio* on → `OPENAI_API_KEY=…`
- **Gemini (podcasts):** aistudio.google.com/apikey → Create API key, in a project with billing → add prepaid credit (ai.studio/projects) → `GEMINI_API_KEY=…`; then `"podcast": {"providers": ["gemini", "google"]}` in `learner/profile.json`.
- **ElevenLabs (podcasts):** elevenlabs.io → a paid plan (Starter or higher; the API cannot use library voices on Free) → Profile → API Keys → Create, with Text to Speech, Voices read and User read → `ELEVENLABS_API_KEY=…`; then `"podcast": {"providers": ["elevenlabs", "gemini", "google"]}` in `learner/profile.json`.
- **edge-tts:** nothing to set up; your agent asks for your yes once.

The order is `voice.providers` in `learner/profile.json` (the Voice screen changes it). A new learner starts with `["google"]`.

## Making the clips

```
uv run oknos voice status          # the services, the keys present (yes/no), this month's characters, clips made
uv run oknos voice build           # make every missing clip (resumable; the first time takes a few hours)
uv run oknos voice build --wait    # wait out each service's pace (Azure's free tier: one clip every 3 s)
uv run oknos voice build --limit 50
uv run oknos voice build --redo edge   # make again, with the other services, what one service made
uv run oknos voice sample google   # the Voice screen's two test sentences, with one service
```

The build lets the first service's family (Azure and edge are one family: the same voices) make everything it can over a few rounds, because a refusal is often only throttling; the next service in the list fills in only what is left, so one speaker does not change voice halfway through a dialogue. Free quotas are left at 90%. Without `--wait`, a clip whose service is still pacing itself goes to the next one: with Azure first and edge second, edge then makes most clips. A clip that takes too long fails and goes to the next service: 45 seconds for edge (a connection to it once hung for hours), 60 for the others. Run one build at a time: two at once make the same clips twice and write over each other's `index.json` (which service made what). `daily-prep` runs `oknos voice build` after it writes new items, so tomorrow's words are already spoken well.

The code is `src/oknos/voice.py` (services, chain, cache, quota) and the `/voice` route in `src/oknos/server.py`; the app's `speak()` in `web/app.js` tries the clip first. The shipped clips are made by `scripts/ship_voice.py`.
