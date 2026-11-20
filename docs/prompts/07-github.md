# Phase 7 — The repository on GitHub

Read `AGENTS.md`. The repo lives only on my machine: `git remote -v` is empty, so nothing is backed up and nothing can be pushed. I want it on GitHub, **private** first, with the tests running there on every push. Making it public is a separate decision, after the public-repo check of phase 6 (step 5).

## Do

1. **Safety check before anything leaves the machine.** Search the whole git history, not just the working tree:
   - nothing from `learner/` or `content/private/` was ever committed, and both stay in `.gitignore`;
   - no personal data: my name, e-mail, home or user paths (`C:\Users\…`), tokens, the scratchpad paths that agent sessions write into `.claude/launch.json` (which must stay untracked);
   - no copyrighted material outside `content/private/`: textbook text, exam papers, publisher audio. The open packs record their licence.

   Report what you find. If something must be removed from history, stop and ask me before rewriting anything.
2. **Create the repository.** With the `gh` command-line program, which I sign in to myself (never ask me for a token): a **private** repo named `greek-coach` under my account. Add it as `origin` and push `main`. Ask me before the first push, and show me the list of files it will contain.
3. **A guard that keeps private things private.** A small check, run by the tests and by a git pre-push hook the `setup` skill can install, that fails if any tracked path is under `learner/` or `content/private/`, or if a tracked file contains a local user path. One more dependency is not needed for this.
4. **CI.** A GitHub Actions workflow that runs `uv run pytest` and `uv run greek-coach validate content/open` on every push and pull request, on Windows and Linux (macOS too if the free minutes allow). The tests already see only the open packs; check that nothing in them needs `content/private/` or a signed-in agent.
5. **The agent's workflow.** Update `AGENTS.md`: commits still land on `main` through a short branch, and now `git push` follows **only when I ask**. Say how to see the CI result (`gh run list`, `gh run view`).
6. **The README.** Keep the `<owner>` placeholder until the repo is public; note in `AGENTS.md` that phase 6 step 5 must pass before it is made public.

## Done when

The private repo exists with `main` pushed, CI is green on it, the safety check found nothing (or I decided what to do about what it found), and the guard fails a test commit that adds a file under `content/private/`.
