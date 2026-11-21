# Phase 8 — Discovery: using the app away from home (optional)

Read `AGENTS.md`, `docs/DESIGN.md` and `docs/SPEC.md`. The app runs on `127.0.0.1` on my laptop. I would like to study from my phone or another computer when I am not at home, ideally for free. **This phase is research only: no code, no accounts, no sign-ups.** It ends in a written recommendation I decide on.

The guardrail "Local only. No accounts, no telemetry, no cloud services" (`AGENTS.md`) is a design decision. Any option that moves the app or my data off my machine changes it, so say plainly which options keep it and which break it.

## Compare at least these

1. **Keep it at home and reach it privately:** a private network such as Tailscale (free personal plan) or WireGuard, so my phone reaches the laptop as if on the same Wi-Fi. Nothing is hosted; the laptop must be on.
2. **A small always-on machine at home:** an old laptop or a Raspberry Pi, with option 1 for access.
3. **A free virtual server:** for example Oracle Cloud's Always Free tier or Google Cloud's free e2-micro. Check what is really free today, and what a credit card on file means.
4. **Free app hosting:** for example Render, Fly.io, Koyeb, Railway or Hugging Face Spaces. Check sleeping, the free hours, and whether the disk survives a restart, because the app keeps everything in SQLite (`learner/oknos.db`).

## For each, answer

- **Cost:** is it really free, and for how long? Is a credit card needed?
- **My data:** where `learner/` and the database live, who can read them, and how they are backed up.
- **Copyright:** my private book material (`content/private/`) must never be reachable by anyone else. Can the option guarantee that?
- **Access control:** the app has no login. What stops a stranger from opening it, and what would have to be added?
- **The browser features:** speech recording and some audio need HTTPS outside `localhost`. Does the option give HTTPS?
- **The coach:** the agent works on the files (`learner/`, packs, `coach/`). Where does it run in this option, and do the scheduled runs (`oknos schedule`) still work?
- **Effort:** setup steps, and what breaks when I am not watching it.

## Deliver

`docs/HOSTING.md`: a short table of the options against those questions, the facts checked on the providers' own pages (with the date), and one recommendation with its trade-offs. If the recommendation changes the guardrail, include the exact wording `AGENTS.md`, `DESIGN.md` and `SPEC.md` would need. Do not change them yet.

## Done when

I can read `docs/HOSTING.md` and choose an option, or decide to stay local, without needing anything else explained.
