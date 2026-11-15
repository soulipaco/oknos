# Phase 6 — The friend test

Read `AGENTS.md` and `docs/SPEC.md`. The app works on my machine. Before I tell anyone else about it, I want evidence that it works for a person who cannot fix anything, on a machine that has nothing installed.

## Do

1. **Fresh-install rehearsal.** In a clean environment (a new clone in a temporary directory, with the project's prerequisite hidden from `PATH` if you can arrange it), start an agent session that knows nothing but the repo and give it only the sentence "set this up for me". Watch where it hesitates, asks a technical question, or reports success without checking. Each of those is a defect in our instructions; fix the instructions and run it again until it goes through cleanly. Do this for the Windows path at least, and reason carefully through macOS and Linux where you cannot run them.
2. **First-run experience without private content, in Turkish.** Run the first-run flow with the UI in Turkish, and again in English. My friend has no textbook import. With only `content/open/`, is there enough to start, and does the coach's first conversation get them to a useful first session? Extend the original open pack if it is too thin.
3. **Failure paths.** The port is taken. The app is already running. The laptop was restarted and they do not remember how to open it. They updated the repo and the database is from an older version. Each should end in the app working or in one plain sentence about what to do, never a stack trace.
4. **Updating and backing up.** "Update the app" and "back up my progress" should both work as plain requests to the agent, and updating must never touch `learner/`.
5. **Public-repo check.** Search the full git history for anything from `learner/` or `content/private/`, for my name, email or local paths, and for content whose licence is not recorded. Check that the licence files from phase 2 are present (MIT for code, CC BY-SA 4.0 for open packs) and that every open pack manifest records one. Repeat step 1 with Codex as well as Claude Code. Rewrite the README for a visitor: what this is, a screenshot, and the three steps to start.

## Done when

You can show me a transcript of a from-scratch install driven by one sentence, and the repo is safe to make public. List anything you could not test, so I know what to watch when my friend tries it.
