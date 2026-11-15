# Phase 3 — Import my material and make the daily session worth opening

Read `AGENTS.md` and `docs/SPEC.md`. The skeleton from phase 2 works. This session gives it real content and a real study loop.

## Part A — Private import

My earlier project is at `C:\Users\you\Desktop\Greek_Helper`. Its app-ready data is in `data/app/` and its documents explain how it was produced. It is OCR of a commercial textbook, so it stays on my machine: the importer code belongs in this repo, its output goes to `content/private/`, and nothing from that folder may end up in a tracked file, a test fixture or an example.

Build an importer that turns that data into a private content pack in our format.

`docs/SPEC.md` §10 records what phase 1 found in that folder. Start from it, and re-measure rather than trust it.

- The vocabulary (about 3,200 entries) is the most valuable part. It comes from four generic word-list PDFs, not from the textbook lessons. Bring it in with document and page provenance. Fold polytonic OCR characters to monotonic, dedupe, and flag entries that look like OCR damage instead of importing them silently. Gender and articles are missing. Enrich them as the spec says, and ask me before downloading any dictionary data.
- The lesson skeleton (themes, grammar, vocabulary and functions per lesson) imports as-is, without the absolute paths.
- The practice and review items have no answers and are OCR-noisy. Do not pass any of them through as exercises. Put them in the pack's `raw/` folder as source prompts for the coach to rebuild in phase 4. Show me the numbers: how many are kept as raw, how many are dropped, and a sample of each.
- Audio: import the MP3s that actually exist, linked to their transcripts and flagged for review. The transcripts refer to many files that are missing; list them in the import report.
- Listen to a few Piper `el_GR` samples of A2 sentences and tell me whether the quality is good enough for listening passages (spec §9). If Piper is not good enough, use the edge-tts fallback, following exactly the rules in spec §9.

Make the importer general enough that someone else can point it at their own material with a small mapping, and document that in a short guide. Other people will have other books.

## Part B — The daily session

Now that there are thousands of items, the app has to decide what to show. Build:

- **Spaced repetition** for vocabulary and for any item answered wrongly, with scheduling state stored per item. The spec chose SM-2; change that only with a reason.
- **The remaining v1 exercise types** from the spec (`match`, `gap_bank`, `categorise`, listening variants), the on-screen Greek keyboard, and accent-tolerant checking.
- **A verb track.** Verbs are my own stated gap. Build `form` items for the most common A1–A2 verbs (present, aorist, future; the main irregulars) and give them a daily slot in the session. Write them yourself as an open pack.
- `table_fill` (needed for B1) can wait until phase 5 if time runs short.
- **A daily session** assembled automatically: reviews that are due, a small amount of new material, and a varied mix of exercise types, sized to the time budget in my profile. One click to start. Stopping halfway loses nothing.
- **A home screen** that answers three questions at a glance: what should I do now, how consistent have I been, and what am I weakest at. I work with dashboards for a living, so honest numbers about my own learning are a motivator for me; make them accurate and avoid decorative gamification.
- **Lookup while studying**: any Greek word in an exercise can be tapped to see its meaning if we have it, and tapping counts as a signal that I did not know it.
- **Hearing the Greek**, using the approach the spec settled on.

## Verify

Run the importer against the real folder and check the result in the app yourself. Simulate a couple of weeks of use by scripting attempts with shifted dates, and confirm the scheduler and the home-screen numbers behave sensibly. Confirm with `git status` that nothing private is tracked.

## Done when

I open the app in the morning, press one button, and get ten minutes of sensible practice drawn from my own book, and the next day's session reflects what I got wrong.
