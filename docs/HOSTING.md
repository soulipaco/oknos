# Using Oknos away from home (phase 8, research)

Research only, done 2026-11-22. Nothing was installed, no account was made and the app was not changed. The facts below come from the providers' own pages, read on 2026-11-22 (§4). Options are judged against the guardrails in `AGENTS.md`: local only, learner data stays on the machine, few dependencies, the app works without an agent.

## 1. In short

**Recommendation: option 1 with Tailscale.** Install Tailscale on the laptop and the phone, and let `tailscale serve` pass `https://<laptop>.<tailnet>.ts.net` to the app on `127.0.0.1:8642`.
- The app does not change. It still listens on `127.0.0.1` only, `learner/` and `content/private/` never leave the laptop, and the coach and the scheduled runs work as today.
- The phone gets real HTTPS, so speaking recording works on it too.
- Only your own signed-in devices can open it; strangers on the internet cannot reach it at all.

**What it costs you:**
- one free Tailscale account (signed in with Google, Microsoft, GitHub or Apple), and the Tailscale app on each device;
- the laptop has to be on and awake at home;
- the laptop's name and the tailnet's name appear in a public certificate log (pick a laptop name that says nothing about you).

**Your decisions:**
1. **Tailscale, or stay local.** Tailscale is an outside service with an account, so it bends "no accounts, no cloud services". It never holds the data and cannot read the traffic, but it is one more company in the picture. If that is not acceptable, the honest answer is to stay as you are (§3).
2. **If yes: does the laptop stay on at home?** That means "never sleep when plugged in" in Windows' power settings. If the laptop is often off or travels with you, option 1 does not help. The next step is then a second machine that stays on: a box at home (option 2) or Google's free e2-micro (§3.3a: about $3.65 a month for its IPv4 address, plus new sync code, because the coach cannot run on it). Both cost real effort, and both reuse the Tailscale setup.

## 2. What exists today (the baseline)

- **The app on the laptop.** Opened at `http://127.0.0.1:8642`. Everything works, including recording (`localhost` counts as a secure context).
- **The tutor and the coach from the phone.** Claude Code Remote Control already continues the laptop's session from the Claude app on the phone. The agent and its file access stay on the laptop, but the laptop must stay on and `claude` must keep running. So for chat practice, capture, "how am I doing?" and marking, **the phone is already covered**, and nothing below improves on that.
- **What is missing is the web app itself on the phone:** daily sessions, the book, mock exams, recordings.
- **The "home Wi-Fi mode" in SPEC §3 is not built.** `src/oknos/paths.py` hard-codes `HOST = "127.0.0.1"`. As specified (bind to the LAN address, plain HTTP, a PIN), it would also have a flaw: `http://192.168.x.x` is not a secure context, so the phone's browser would give **no microphone**, and speaking recording would not work. Option 1 covers home Wi-Fi as well, with HTTPS, so it can replace that mode.

## 3. The options

| | 1. Private network to the laptop (Tailscale) | 2. Always-on machine at home + option 1 | 3. Free virtual server (Oracle, Google) | 4. Free app hosting (Render, Fly, Koyeb, Railway, HF) |
|---|---|---|---|---|
| **Really free?** | Yes. Personal plan $0, "free forever" for non-commercial use, up to 6 users, unlimited devices. No card mentioned. | Old laptop: yes (plus power). Raspberry Pi 5: no, it is bought (the 16 GB model is $305; the page shows no price for the smaller ones). | Oracle: free "for the life of the account", but a **credit card is needed** at sign-up (not charged unless you upgrade). Google: a **billing account with a card is required**; usage above the free limit is **billed**, and the public IPv4 address costs about $3.65 a month (§3.3a). | Mostly no for this app (see §3.4). Fly: $5/month of usage with a card on file, then automatic pay-as-you-go. |
| **Where your data lives** | On the laptop, as today. | On the home machine. Two copies (laptop and box) would have to be avoided. | On the provider's disk (Oracle: home region you pick; Google: US regions only). You back it up. | On the provider's disk, where there is one at all. |
| **Private book material** | Never leaves the laptop. | Never leaves home. | A copy of `content/private/` (348 MB today) sits on a third party's server. Unreachable to others only if access control is added and kept right. | Same as 3, and the provider runs the container. |
| **Who can open it** | Only devices signed in to your tailnet. Nothing listens on the internet. Nothing to add to the app. | Same as 1. | Anyone, unless a login is added to the app or the server is put behind Tailscale too. | Anyone with the URL: the services give a public address. A login would have to be built. |
| **HTTPS (recording)** | Yes: Let's Encrypt certificate on a `*.ts.net` name, through `tailscale serve`. | Yes, as 1. | Only if added (a certificate and a domain, or Tailscale as in 1). | Yes, by the platform. |
| **The coach, scheduled runs** | Unchanged: on the laptop. | The agent and `oknos schedule` would have to run on the home machine. The macOS/Linux schedulers are untested. | The agent would have to run on the server (signed in there), or files be copied back and forth. Linux scheduler untested. | The agent cannot run there. Files would have to be shipped in and out. |
| **Effort, and what breaks unseen** | Small: install twice, sign in, one `serve` command. Breaks if the laptop sleeps or is off, or the app starts on another port than 8642. | Large: a second install, moving `learner/`, the agent there. Breaks if the box or its disk fails. | Large: server admin, updates, backups, firewall. Oracle may **reclaim an idle instance**, and a study app is idle most of the week. | Medium to large, and most of them **lose the database** (§3.4). |
| **Guardrail "local only"** | **Kept** for the app and the data. Bent: one outside account for the network. | Kept, as 1. | **Broken**: the app and data move to the cloud. | **Broken**, as 3. |
| **Better than today?** | Yes: the web app on the phone, with recording. | Only if the laptop being off is the real problem. | No, for one person: more work and risk for what option 1 gives. | No: most cannot keep a SQLite file at all. |

### 3.1 Option 1: reach the laptop privately

- **Tailscale** is a WireGuard network run by a coordination service. All three connection types (direct, through a Tailscale relay, through a peer) are end-to-end encrypted; Tailscale says its relays cannot decrypt the traffic. The account exists to sign devices in to your private network; the app's data never passes through Tailscale in readable form.
- **`tailscale serve 8642`** passes HTTPS from your tailnet to a local port and is tailnet-only. Its sibling **Funnel** publishes to the whole internet: **never use Funnel for this app.**
- Practical points:
  - On Windows, `serve` needs an Administrator console.
  - The app falls back to the next free port if 8642 is taken; Serve points at one port. Keep 8642 free, or start with `--port 8642`.
  - Whether the Serve setting survives a reboot was not checked; confirm it at setup.
  - HTTPS certificates last 90 days and are renewed automatically. Each certificate goes into the public Certificate Transparency log with the machine's full name, so the machine and tailnet names must hold nothing personal.
  - On the phone, the pre-made voice clips play as on the laptop. Words without a clip use the phone browser's own Greek voice, which differs from Windows'.
- **Plain WireGuard** (free, GPLv2/MIT, apps for Windows, iOS, Android) avoids the Tailscale account, but needs a port opened on the home router, a way to find the home address when it changes, and its own HTTPS certificate for recording. More work and more exposure than Tailscale, for one person.
- **Headscale** is an open-source, self-hosted replacement for Tailscale's coordination server. It removes the account, but it has to run on a machine reachable from outside, which brings back the problems of options 2 and 3.
- **Cloudflare Tunnel** was also looked at and is **not recommended**. A named tunnel needs a domain on Cloudflare (not free). The free "quick tunnel" gives a random public `trycloudflare.com` address that anyone with the link can open, "for testing and development", and the address changes on every start. Traffic is handled at Cloudflare's edge (caching and filtering imply it is decrypted there; the page does not say so outright). Cloudflare's Zero Trust login has a free plan, but its pages do not give the user limit.

### 3.2 Option 2: a small always-on machine at home

Useful only if the laptop cannot stay on. The app and `learner/` would move to the box, and so would the coach: Claude Code (signed in) and the scheduled runs, which are untested on Linux. Running the app on the box and the coach on the laptop means two copies of the files and the database, which the design avoids (the coach reads `oknos report` from the one database). A Raspberry Pi 5 has to be bought, with a 5 V / 5 A power supply. An old laptop costs nothing, but it is a second Windows install to maintain.

### 3.3 Option 3: a free virtual server

- **Oracle Always Free:** up to 2 Arm OCPUs and 12 GB of memory, or two small AMD machines with 1 GB each; 200 GB of disk; 10 TB of traffic a month. A credit card and a phone number are needed for most sign-ups (the card is not charged unless you upgrade). The machines must be in the home region chosen at sign-up, and "out of host capacity" errors happen. **Oracle may reclaim an Always Free instance that is idle for 7 days** (95th-percentile CPU, network and, on Arm, memory all under 20%). A personal study app is exactly that.
- **Google Cloud free tier:** one e2-micro (1 GB) in us-west1, us-central1 or us-east1 only, 30 GB of standard disk, 1 GB of outbound traffic a month from North America. A billing account is required; usage beyond the limits is billed. The free tier "has no end date", but Google may change it on 30 days' notice. The page does not mention any charge for a public IPv4 address (not checked further).
- Either way the app and all of `learner/` (25 MB today, more as voice clips are built) and `content/private/` sit on someone else's computer, behind a login that would have to be built or a VPN that would have to be added, with server upkeep on top. For one learner this is no better than option 1, and it breaks the guardrail.

### 3.3a Google Cloud in detail (asked 2026-11-22: "the card is already there for text-to-speech, so why not?")

The card is no longer the obstacle: the free tier is counted per billing account, so the account made for Cloud Text-to-Speech can also run the free e2-micro. What is left:

- **It is not quite $0.** The free tier covers the machine (one e2-micro for the whole month), 30 GB of *standard* disk and 1 GB of outbound traffic. It does **not** mention the public IPv4 address, and the VPC price list charges **$0.005 an hour for an IPv4 address in use on a standard VM**, about **$3.65 a month**, with no free-tier exemption. External IPv6 addresses on VMs are free, so an IPv6-only machine could be $0. That is untested: everything the machine must reach (Tailscale, the package index, Anthropic) and the phone's own network would need to work over IPv6.
- **The disk must be picked by hand.** The console's default disk type is *balanced*, which is not in the free tier. Only *standard* is free (the gcloud command-line default).
- **Traffic is enough.** A study session is small: the voice clips average 11 KB (1,959 clips, 21.9 MB), the pictures are WebP. A month of daily sessions is tens of MB, well inside the free 1 GB. Uploading the book material (348 MB) is inbound traffic, which is free.
- **Overruns are billed, and nothing stops them.** On a Paid billing account usage above the free limits is charged automatically, and a budget only sends an e-mail: it "doesn't automatically cap" usage. A wrong click (a balanced disk, a second machine, a region outside the three US ones) costs money quietly.
- **Check which kind of account it is.** If the Text-to-Speech account is still a *Free Trial* account (the $300 credit), it closes after 90 days unless it is upgraded to Paid, and its machines are then stopped and, after a 30-day grace period, deleted. The Billing overview page says "Free trial account" or "Paid account".
- **The machine is small, but big enough for the app.** e2-micro: 2 shared vCPUs at 25% in total, short bursts, 1 GB of memory. The running Oknos server uses about 70–85 MB on this laptop, so the app fits.
- **The coach cannot move there.** Claude Code needs **4 GB of RAM** or more; the e2-micro has 1 GB. Local transcription (faster-whisper) and the voice build need more than that too. So the agent stays on the laptop, and the app and its database would live on the server. That is the real cost:
  - today the coach reads `oknos report` from the database next to it and writes its files into the same `learner/` folder. With the database in the US, every check-in, daily prep and marking run would have to fetch the report from the server, push its packs, feedback, coach files and voice clips up, and ask the server to reload; recordings would have to come down to be transcribed;
  - none of that exists. It is new code (a sync step or remote commands) and changes to every coach skill, against "few dependencies";
  - the scheduled runs stay on the laptop, so the laptop still has to be on at 18:30 for the daily prep. Only the studying itself becomes independent of the laptop.
- **It still needs option 1 on top.** The app has no login. The safe way is to give the server no open ports at all and reach it through Tailscale, exactly as in option 1 (Tailscale Serve gives the HTTPS). Opening it to the internet would need a login to be built, and the private book material would then sit behind it.
- **Where the data goes.** The database, the recordings, anything captured from real life (letters, which can hold personal details) and a copy of the private book would be on a Google machine in the US. Nobody else can open it if it is reachable only through Tailscale, but it is a copy on someone else's computer: the guardrail "local only" no longer holds, and backups become your job (for example, copying the database to the laptop every day).

**Verdict.** It can be done, but it is not free (about $3.65 a month for the IPv4 address), it needs new sync code and skill changes, and it still needs Tailscale. What it buys over option 1 is one thing: studying from the phone while the laptop is off. Starting with option 1 loses nothing: if the laptop being off turns out to be the real problem, the Google machine is the next step and reuses the same Tailscale setup.

### 3.4 Option 4: free app hosting

The app keeps everything in one SQLite file, so the question that decides is whether the disk survives.

- **Render (free):** **no persistent disk**: local SQLite files are lost on every redeploy, restart or spin-down. It spins down after 15 minutes without traffic (about a minute to wake), 750 free hours a month. **Ruled out.**
- **Koyeb (free instance):** 512 MB of RAM, 0.1 vCPU, 2 GB of disk, scales to zero after 1 hour, and **cannot use volumes**. **Ruled out.**
- **Hugging Face Spaces:** a Docker Space (which this app would need) requires a paid PRO plan to create; the free disk is ephemeral (lost on restart). **Ruled out.**
- **Railway (free plan):** $1 of usage a month, no card; one volume of at most 0.5 GB (too small for `content/private/` at 348 MB plus `learner/`); services sleep after 5–10 minutes. When the dollar runs out the service stops (the volume is kept). **Not workable.**
- **Fly.io:** without a card, $1 of credit for 7 days; with a card, $5 of usage a month, volumes up to 5 GB ($0.15/GB a month). Above $5 the organisation moves to pay-as-you-go **automatically**. The pages contradict each other on whether a card is always required. The only one that could hold the database, but with a card on file, a public URL that needs a login, and the coach left out.

## 4. Sources (all read 2026-11-22)

- Tailscale pricing (Personal plan): https://tailscale.com/pricing
- Tailscale HTTPS certificates, Certificate Transparency warning: https://tailscale.com/kb/1153/enabling-https
- Tailscale Serve (tailnet-only; Funnel is public; Windows needs Administrator): https://tailscale.com/kb/1312/serve
- Tailscale connection types (all end-to-end encrypted): https://tailscale.com/kb/1257/connection-types
- Tailscale DERP relays (cannot decrypt traffic): https://tailscale.com/kb/1232/derp-servers
- Tailscale clients (Windows, iOS, Android): https://tailscale.com/kb/1347/installation
- WireGuard (licence, platforms): https://www.wireguard.com/ and https://www.wireguard.com/install/
- Headscale: https://headscale.net/stable/
- Oracle Always Free resources (limits, idle reclamation, capacity): https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- Oracle Free Tier (card, trial end, home region): https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm (the marketing page and FAQ at oracle.com/cloud/free refused automated reading)
- Google Cloud free tier and Free Trial (per billing account, 90-day trial, what happens at its end): https://docs.cloud.google.com/free/docs/free-cloud-features
- Google VPC pricing (external IPv4 $0.005/hour in use, IPv6 on VMs free, outbound traffic): https://cloud.google.com/vpc/pricing (read in a browser; automated reading got only the title)
- Google persistent disks (console default `pd-balanced`, gcloud default `pd-standard`): https://docs.cloud.google.com/compute/docs/disks/persistent-disks
- Google budgets (alerts do not cap spending): https://docs.cloud.google.com/billing/docs/how-to/budgets
- e2-micro machine type: https://docs.cloud.google.com/compute/docs/general-purpose-machines
- Claude Code system requirements (4 GB+ RAM): https://code.claude.com/docs/en/setup
- Raspberry Pi 5: https://www.raspberrypi.com/products/raspberry-pi-5/
- Render free: https://render.com/docs/free
- Fly.io: https://docs.fly.io/about/pricing and https://docs.fly.io/about/free-trial
- Koyeb: https://www.koyeb.com/pricing and https://www.koyeb.com/docs/reference/instances
- Railway: https://railway.com/pricing and https://docs.railway.com/reference/pricing/free-trial
- Hugging Face Spaces: https://huggingface.co/docs/hub/spaces-overview and https://huggingface.co/docs/hub/spaces-storage
- Cloudflare Tunnel and quick tunnels: https://developers.cloudflare.com/tunnel/, https://developers.cloudflare.com/tunnel/get-started/, https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
- Cloudflare Zero Trust plans: https://www.cloudflare.com/plans/zero-trust-services/
- Secure contexts, getUserMedia (microphone needs HTTPS or localhost): https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts and https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia
- Claude Code Remote Control: https://code.claude.com/docs/en/remote-control

Free tiers change. Re-read these pages before setting anything up.

## 5. If option 1 is chosen: the wording to change (not changed yet)

`docs/DESIGN.md` needs no change: it says only that the server runs on `localhost`, which stays true.

**`AGENTS.md`, Guardrails**, the first bullet becomes:

> - **Local only.** No accounts in the app, no telemetry, no cloud services that hold learner data or content. The app runs on `localhost` and all learner data stays on the machine. The learner may opt in to opening it from their own devices through a private network (Tailscale Serve, `docs/HOSTING.md`): the app still listens on `127.0.0.1` only, nothing is hosted, and the network's provider cannot read the traffic. Never publish the app to the internet (no Tailscale Funnel, no public tunnel, no port forwarding). The one exception is the opt-in edge-tts fallback in `docs/SPEC.md` §9. It handles content text only, never learner data.

**`docs/SPEC.md` §3, "In"**, the home Wi-Fi bullet and its two sub-bullets become:

> - Opt-in **access from the learner's own devices** (phone, another computer), at home or away, through a private network: Tailscale Serve passes `https://<machine>.<tailnet>.ts.net` to `127.0.0.1:8642` (`docs/HOSTING.md`).
>   - Off by default; set up only with the learner's yes, as it needs a Tailscale account.
>   - The app is unchanged and listens on `127.0.0.1` only; only the learner's signed-in devices can reach it, over HTTPS, so recording works on the phone.
>   - The laptop must be on and awake.

**`docs/SPEC.md` §3, "Out"**, the line "Access from outside the home network: no tunnels, no port forwarding." becomes:

> - Publishing the app to the internet: no public tunnels (Tailscale Funnel, Cloudflare quick tunnels), no port forwarding, no hosting on a server or app platform (`docs/HOSTING.md`).

**`docs/SPEC.md` §2, "Phone"**, the second sub-bullet becomes:

> - The web app opens on the phone through the private network in §3 (`docs/HOSTING.md`).

If you decide to stay local instead, the one change worth making is to SPEC §3: drop or rethink the home Wi-Fi mode, since over plain HTTP the phone would get no microphone (§2 above).
