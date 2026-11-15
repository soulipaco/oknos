# Greek Coach

A local-first Greek learning companion that your coding agent installs, runs and personalises for you. It is aimed at people living in Greece who need to pass a language certification exam and have struggled to stay interested in studying.

> Status: design phase. There is no app yet. See `docs/DESIGN.md` and `docs/prompts/`.

## The idea

- You install an agent such as Claude Code or Codex, clone this repo, and say **"set this up for me"**. The agent does the rest.
- You study in a web app that runs only on your own computer.
- Your progress, mistakes and writing stay in a local folder. Nothing is uploaded.
- When you open the agent again, it reads how you have been doing and acts as your coach: it builds new exercises around your weak spots, gives feedback on your writing, turns what you covered in class into practice, and tracks your readiness for the exam.
- You can import your own material (a textbook you own, course handouts) as a private content pack that never leaves your machine.

## Documents

- `AGENTS.md` — instructions for any coding agent working in this repo.
- `docs/DESIGN.md` — product and architecture decisions.
- `docs/prompts/` — the phased prompts used to build the app.
