# Phase 1 — Specification

Read `AGENTS.md` and `docs/DESIGN.md` first. They describe an app that does not exist yet. Your job in this session is to turn that design into a specification I agree with. Do not write application code in this session.

I am the maintainer and the primary learner described in the design. I am not a software engineer by trade: I work with data and Python, and I have no strong opinions on web stacks. So when a technical choice does not affect what I experience as a learner, make it yourself and record it in a sentence. Bring me only the choices that change the product.

## What I need from you

1. **Settle the open questions** at the bottom of `docs/DESIGN.md`.
   - The exam question comes first, because the exam mode, the exercise types and the readiness tracking all depend on it. Research the candidate exams from official sources (the Centre for the Greek Language, the relevant Greek ministries) and show me what you found: for each, who requires it, the level, the sections, timings, pass marks, how often it is held, and where official sample papers are. Give links. Say clearly what you could verify and what you could not. I will confirm which one applies to my case.
   - For the rest, interview me. Ask a few questions at a time, not one long form. Ask about my week, what I have tried before and why it failed, what I find interesting, and what would make me open this app on a tired evening. The motivation problem in the design is real and is the main risk to the project.
   - Check the technical unknowns yourself instead of asking me: Greek speech-synthesis voices in browsers on Windows and macOS, and what Codex needs in order to follow the same setup and coach instructions as Claude Code.

2. **Look at the earlier project** at `C:\Users\you\Desktop\Greek_Helper` (start with its `README.md` and `docs/AGENT_HANDOFF.md`, then sample `data/app/`). Tell me honestly what is worth importing, what is too noisy to use as it stands, and what the importer in phase 3 will have to do. That material is copyrighted and must never be copied into this repo.

3. **Challenge the design.** If the stack, the split between app and agent, or the content-pack idea looks wrong to you after the research, say so and propose the alternative. I would rather change it now.

4. **Write `docs/SPEC.md`**, covering:
   - the exam, as verified, and how each section maps to exercise types in the app;
   - the first-version scope, and an explicit list of what is left out;
   - the content-pack format, with one small worked example per exercise type;
   - the learner-data layout in `learner/`: the database tables and the files the coach reads and writes;
   - the coach commands: what each one does, what it reads, what it writes;
   - what a ten-minute daily session looks like, screen by screen, in words;
   - the install flow for a non-technical person, step by step, per operating system;
   - anything in phases 2 to 6 of `docs/prompts/` that should change as a result, and update those prompt files to match.

Then update the "Current state" section of `AGENTS.md`.

## Done when

I have read `docs/SPEC.md`, the exam is confirmed by me, and there is nothing in it I would be surprised by in phase 2. Finish by listing the decisions you made on my behalf, so I can object to any of them.
