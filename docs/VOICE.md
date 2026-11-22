# The Greek voice

Oknos reads Greek aloud from **clips made ahead of time**. The app knows what it will say (words, example sentences, dialogue lines, listening passages, every word you can tap), so each text is made once, by the first voice service in your list that works, and kept in `learner/voice/`. Anything without a clip (a word the coach added today) is read by your browser's own voice, as before. In the app, the speaker icon at the top opens **Voice**, where you can hear each service, see what it costs and change the order.

Nothing here is shipped with the repository: every learner makes their own clips on their own computer. Only the Greek text goes to a voice service, never your answers, your writing or your progress.

## The services

From the listening test of 2026-11-22 (ten sentences from the open book, the same eight voices for each; ranked by the maintainer's ear):

| Service | Voices | Sound | Cost and terms |
|---|---|---|---|
| **Azure Speech** (Microsoft, official) | Athina, Nestoras | best | Your own key. Free tier F0: 500,000 characters a month; the whole book is about 150,000 the first time. The free tier makes 20 clips a minute. |
| **edge-tts** (Microsoft, unofficial) | Athina, Nestoras | best (the same voices) | Free, no account. The Edge browser's read-aloud service, used from outside the browser: Microsoft can slow it or close it, and the clips are for your own computer only. Only with your yes (`"edge_tts_ok": true` in `learner/profile.json`), and never for the coach's own texts (SPEC §9). |
| **Google Cloud Text-to-Speech** | Chirp 3 HD Kore, Orus | very good, just behind Microsoft | Your own key; 1 million characters free a month (billing must be on; the free trial covers it). **The default for a new learner.** |
| **OpenAI** | gpt-4o-mini-tts (coral, ash) | good, a slight accent | Your own key; pay as you go, about one or two dollars for the whole book. |
| Your browser's voice | on Windows, Stefanos | robotic | Always there; it reads whatever has no clip. |

Tested and not offered: OpenAI tts-1-hd (unclear Greek), Chatterbox Multilingual and F5-TTS-Greek (local models, no better than the browser's voice here).

Each character in the book's dialogues gets a voice of their kind (Zeynep and Katerina the female voice, Giorgos and Stelios the male one; `src/oknos/speakers.json`), so a dialogue sounds like two people.

## Setting a service up

Keys go in `learner/secrets.env` (git never tracks `learner/`), one per line. They are only ever sent to their own service.

- **Google:** console.cloud.google.com → start the free trial → create a project → enable *Cloud Text-to-Speech API* → Credentials → Create credentials → API key, restricted to *Cloud Text-to-Speech API* → `GOOGLE_TTS_API_KEY=…`
- **Azure:** azure.microsoft.com/free with a Microsoft account → create a *Speech* resource, region West Europe, pricing tier *Free F0* → Keys and Endpoint → `AZURE_SPEECH_KEY=…` and `AZURE_SPEECH_REGION=westeurope`
- **OpenAI:** platform.openai.com/api-keys → new secret key, Restricted with *Audio* on → `OPENAI_API_KEY=…`
- **edge-tts:** nothing to set up; your agent asks for your yes once.

The order is `voice.providers` in `learner/profile.json` (the Voice screen changes it). A new learner starts with `["google"]`.

## Making the clips

```
uv run oknos voice status          # the services, the keys present (yes/no), this month's characters, clips made
uv run oknos voice build           # make every missing clip (resumable; the first time takes a few hours)
uv run oknos voice build --limit 50
uv run oknos voice build --redo edge   # make again, with the other services, what one service made
uv run oknos voice sample google   # the Voice screen's two test sentences, with one service
```

The build lets the first service's family (Azure and edge are one family: the same voices) make everything it can over a few rounds, because a refusal is often only throttling; the next service in the list fills in only what is left, so one speaker does not change voice halfway through a dialogue. Free quotas are left at 90%. `daily-prep` runs `oknos voice build` after it writes new items, so tomorrow's words are already spoken well.

The code is `src/oknos/voice.py` (services, chain, cache, quota) and the `/voice` route in `src/oknos/server.py`; the app's `speak()` in `web/app.js` tries the clip first.
