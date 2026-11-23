# Phase 11 (optional): podcast lessons

Status: started 2026-11-23. The plan agreed with the maintainer and how it works are in `docs/PODCASTS.md`; the pilot (one book chapter as an episode, the renderer and the Podcast page) is built. Added to the roadmap 2026-11-23 from a conversation with the maintainer; this brief is kept as the record.

Read `AGENTS.md`, `docs/SPEC.md` (§9, audio and speech), `docs/VOICE.md`, `docs/LESSONS.md` and `docs/COACHING.md` first.

## The idea

Short audio lessons to listen to hands-free, e.g. while starting work in the morning: a daily episode of 10–20 minutes and a weekly lesson of 20–30 minutes. Every episode is written as **text first** (a script), then made into audio with the voice services the app already uses (`docs/VOICE.md`). Because the script comes first, adding another explanation language later, or turning a Turkish episode into an English one, is a new script and a new render, not a new system.

## Decisions already made by the maintainer

- **Optional.** Built only when the maintainer says so; nothing in the app depends on it.
- **Explanation language is the learner's choice.** The maintainer's own episodes are Greek with Turkish explanations. A learner who uses the app in English gets Greek with English explanations. Not every episode in both; the learner picks. The design must allow other languages later.
- **A default set from the content we have.** One podcast lesson per book chapter (the private book's 26 stages and the open book's 12), made from the chapter's dialogues, examples, words and tips.
- **Personal daily and weekly episodes** from the learner's record (`oknos report`): today's due and weak words, recent mistakes, the current chapter, a short story at their level. Written by the scheduled `daily-prep` run so the episode is ready the next morning.
- **Enrichment beyond our own content.** The book will not be enough at some point. A loop should draw on existing Greek-teaching material elsewhere (podcasts, YouTube videos, social media accounts aimed at Greek learners, Spotify and other platforms) to enrich the episodes, see the copyright rules below.

## Findings from the first look (2026-11-23, estimates)

- Characters: about 400 spoken characters per minute of episode (slow Greek, explanations, pauses cost nothing). Daily 15 min on weekdays ≈ 130,000 a month; weekly 25 min ≈ 45,000 a month. That fits Azure's free 500,000 and Google's free 1,000,000 a month; paid prices (from memory, to check) would make it a few dollars a month.
- Time: an episode is about 150–200 clips, about 10 minutes on Azure's free tier (20 clips a minute); made overnight.
- edge-tts is out for personal episodes: SPEC §9 keeps the coach's per-learner texts off edge.
- Gaps to build: Turkish and English voices for the explanations (today only Greek clips are made); a renderer that joins clips, pauses and speeds into one file (ffmpeg is already used for the films); a Podcast page in the app (reached from the phone through Tailscale Serve, so the laptop must be on); a script format with segments (language, speaker, text, pause, speed).
- Risks: the book's A2/B1 Turkish meanings are AI-drafted and unchecked, and an episode would speak them aloud. Listening is not answering, so it is not exam evidence and does not move the review schedule (at most a "heard" mark).

## Copyright and terms (must hold)

- Other people's podcasts, videos and posts are copyrighted. The loop may use them as **sources of ideas**: topics, words and phrases that come up, what learners ask, which episode to listen to next (with a link). It must not re-voice, translate or reproduce their content, and must not download their audio or video without the maintainer's yes for each source and a check of the platform's terms.
- Anything taken from such sources (notes, transcripts, word lists) is private: it goes in `content/private/` or `learner/`, never in tracked content.
- Episodes that ship with the repository (if any) come only from original or openly licensed content and a voice whose terms allow publishing (today: Google, as for the shipped clips).

## Open questions for the plan (settled 2026-11-23, `docs/PODCASTS.md`)

- Where the episodes are played: the app's page, a file synced to the phone, or a private feed over the tailnet. **Settled:** the app's Podcast page, with a download link.
- How the enrichment loop finds and records sources (the learner names them, or the agent proposes them), and how often it runs. **Settled:** the agent proposes, the maintainer says yes or no per source, a private list in `learner/podcasts/sources.json`; while writing, the agent may also search the web for ideas when the book and the open book are thin, recorded in the script's `sources`. Not built in the pilot.
- Format details: how many pauses for shadowing, slow then normal speed, where the answers to listening questions go. **Settled for the pilot:** dialogue at normal speed, then line by line slower with a gap to repeat, words with a gap, the explanation, a question with a thinking gap and its answer, the dialogue once more; tuned after the maintainer listens.
- Also settled: the agent writes the scripts (spoken style); the explanation voice follows the learner's voice settings (Azure Emel for the maintainer); episodes come from the book's chapter, then the open book's, then web ideas.
