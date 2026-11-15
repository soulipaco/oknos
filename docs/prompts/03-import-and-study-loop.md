# Phase 3 — Import my material and make the daily session worth opening

Read `AGENTS.md` and `docs/SPEC.md`. The skeleton from phase 2 works. This session gives it real content and a real study loop.

## Part A — Private import

My earlier project is at `C:\Users\you\Desktop\Greek_Helper`. Its app-ready data is in `data/app/` and its documents explain how it was produced. It is OCR of a commercial textbook, so it stays on my machine: the importer code belongs in this repo, its output goes to `content/private/`, and nothing from that folder may end up in a tracked file, a test fixture or an example.

Build an importer that turns that data into a private content pack in our format.

- The vocabulary (around 3,200 entries) is the most valuable part. Bring it in with lesson and page provenance, and flag entries that look like OCR damage instead of importing them silently.
- The practice items came out of OCR heuristics and many are not usable as they are. Do not pass them through. Import only what can be checked automatically and reads cleanly; put the rest aside as raw material for the coach to rebuild in phase 4. Show me the numbers: how many imported, how many set aside, and a sample of each so I can judge the cut.
- Audio and transcripts: import them if the spec includes listening in the first version; otherwise leave a clear note on what would be needed.

Make the importer general enough that someone else can point it at their own material with a small mapping, and document that in a short guide. Other people will have other books.

## Part B — The daily session

Now that there are thousands of items, the app has to decide what to show. Build:

- **Spaced repetition** for vocabulary and for any item answered wrongly, with scheduling state stored per item. Use an established algorithm and say which one and why.
- **A daily session** assembled automatically: reviews that are due, a small amount of new material, and a varied mix of exercise types, sized to the time budget in my profile. One click to start. Stopping halfway loses nothing.
- **A home screen** that answers three questions at a glance: what should I do now, how consistent have I been, and what am I weakest at. I work with dashboards for a living, so honest numbers about my own learning are a motivator for me; make them accurate and avoid decorative gamification.
- **Lookup while studying**: any Greek word in an exercise can be tapped to see its meaning if we have it, and tapping counts as a signal that I did not know it.
- **Hearing the Greek**, using the approach the spec settled on.

## Verify

Run the importer against the real folder and check the result in the app yourself. Simulate a couple of weeks of use by scripting attempts with shifted dates, and confirm the scheduler and the home-screen numbers behave sensibly. Confirm with `git status` that nothing private is tracked.

## Done when

I open the app in the morning, press one button, and get ten minutes of sensible practice drawn from my own book, and the next day's session reflects what I got wrong.
