---
name: setup
description: Install and start Oknos on this computer and put a shortcut on the desktop. Use when someone says "set this up for me", "install this", "get it running", "bunu benim için kur", or has just downloaded or cloned this repository and wants to use it.
---

# Set up Oknos

You are installing Oknos for someone who may have no technical background. Read this whole file before you start.

## Rules for this whole skill

- **Do every step yourself and check it worked before you move on.** The person cannot read an error message and must never be asked to. Do not show them commands, logs or stack traces, and do not ask them to choose between technical options.
- **Talk to them in their language.** If they write in Turkish, answer in Turkish and use `"tr"` as the app language. Otherwise use English and `"en"`.
- Keep them informed in short plain sentences, e.g. "Installing the tools the app needs. This takes a minute or two."
- Before installing anything on their computer (git or uv), say in one sentence what it is and get a yes: "I need to install two free tools, Git and uv, that the app runs on. Is that OK?" Ask once, for both.
- **Never touch system or security settings.** Do not change voices, firewall, PATH settings or execution policies permanently. Do not create scheduled tasks here.
- **Never put anything from `learner/` into git**, and never commit.
- If this is the maintainer (a developer working on the app), follow the same steps but you can talk normally and show output. Also run `uv run pytest` at the end. If you can't tell who it is, ask once: "Are you setting this up to study, or to work on the app's code?"

Commands below are for the shell your harness gives you. Commands that differ by system are shown for **Windows (PowerShell)** and for **macOS/Linux (bash)**. If you are in Git Bash on Windows, the macOS/Linux form of a command usually works too, except where noted.

## Step 1: get the code (skip if you are already inside the repository)

You are inside the repository if this file is at `.agents/skills/setup/SKILL.md` below your working folder. Skip to step 2.

Otherwise the person gave you a link. Check for git with `git --version`.

If git is missing:
- **Windows:** tell them "A Windows window may pop up asking for permission; please click Yes." Then run:
  ```
  winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
  ```
  Then call git by its full path for the rest of this session, `"C:\Program Files\Git\cmd\git.exe"`, because the current shell does not see the new PATH yet.
- **macOS:** run `xcode-select --install` and tell them "A window will appear; click Install and wait until it finishes, then tell me." Wait for them, then check `git --version` again.
- **Linux:** install the `git` package with the system package manager (`sudo apt install -y git`, `sudo dnf install -y git`…). If it asks for a password, tell them it is their computer password.

Clone into the folder they are in (or their Documents folder if they have no preference), then work inside the new `oknos` folder for every step below:
```
git clone <the link they gave you> oknos
```

**Check:** the folder `oknos` exists and contains `pyproject.toml`.

## Step 2: make sure uv is installed (the one prerequisite)

uv installs Python and everything else the app needs. Check with `uv --version`.

If it is missing, install it with the official per-user installer. It needs no admin rights:
- **Windows:**
  ```
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **macOS/Linux:**
  ```
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

The current shell does not see the new PATH. For the rest of this session, call uv by its full path:
- Windows: `& "$env:USERPROFILE\.local\bin\uv.exe"` in PowerShell, or `"$USERPROFILE/.local/bin/uv.exe"` in Git Bash.
- macOS/Linux: `"$HOME/.local/bin/uv"`.

Wherever this file says `uv`, use that full path.

**Check:** `uv --version` (with the full path if needed) prints a version.

## Step 3: install the app's dependencies

Run this in the repository folder:
```
uv sync
```
The first run downloads Python and a few packages. That can take a minute or two, so tell the person.

**Check:** it ends without an error. If it fails with a network error, check the internet connection, wait a moment and run it again.

If the folder is a git clone, also turn on the check that stops private files from ever being pushed. It changes nothing else:
```
git config core.hooksPath .githooks
```

## Step 4: check the install

```
uv run oknos health
```

**Check:** the last line is `All good.` and these lines say `ok`:
- the database line;
- "Greek text survives the database";
- the content line.

If any line says `FAIL`, use the table at the end of this file and fix it before going on.

## Step 5: write the learner profile (only if it does not exist yet)

If `learner/profile.json` does not exist, create it as UTF-8 with exactly this content, using `"tr"` or `"en"` as decided above:
```json
{"ui_lang": "en", "minutes": 10}
```
If the file already exists, leave it alone. It holds their settings.

## Step 6: start the app

```
uv run oknos start
```
This starts the app in the background and opens it in the browser. The command returns by itself after a few seconds; the app keeps running without a window.

**Check:**
- The command prints `Oknos is running at http://127.0.0.1:<port>/`.
- Then run:
  ```
  uv run oknos health --server
  ```
  It must end with `All good.`, and include both "App running at …" and "Greek text survives the web layer too" as `ok`. That proves that Greek text goes through the database and the web server unharmed.

## Step 7: put the shortcut on the desktop

```
uv run oknos shortcut
```

**Check:** it prints `Created <path>`, and that file exists:
- Windows: `Oknos.lnk` on the Desktop.
- macOS: `Oknos.command` on the Desktop.
- Linux: `oknos.desktop` in `~/.local/share/applications` (and on the Desktop if there is one).

## Step 8: the Greek voice

The app reads Greek from clips made ahead of time (`docs/VOICE.md`). Offer the choice in plain words, and do only what they pick:
- **Google (the default):** "Google's voices sound very good and are free within a monthly allowance, but you need a Google Cloud key. I can walk you through it, about ten minutes." Guide them screen by screen (`docs/VOICE.md`), ask them to paste the key into `learner/secrets.env` themselves, never in the chat.
- **Microsoft's voices, free, on this computer only:** the best sound in our test, no account; it sends the Greek text to Microsoft's read-aloud service. Ask for their yes, then set `"edge_tts_ok": true` and `"voice": {"providers": ["edge"]}` in `learner/profile.json`.
- **Azure or OpenAI:** for someone who already has an account; the same key steps.
- **Keep the browser's voice:** nothing to do.

With a service chosen, run `uv run oknos voice build` in the background and tell them the voice gets better over the next hour or two as clips are made. Then the browser voice below is only the fallback.

## Step 8b: the browser's Greek voice (optional, the person does it)

The health output from step 4 has a "Greek voice" line. If it says a Greek voice is installed, there is nothing to do.

If there is no Greek voice, the app still works, but the speaker buttons stay hidden. Tell the person how to add one, and say it is optional. Never change this setting yourself.
- **Windows:** Settings → Time & language → Speech → Add voices → Greek.
- **macOS:** System Settings → Accessibility → Spoken Content → System voice → Manage Voices → Greek.
- **Linux:** say that Greek voices on Linux are limited and the app will use recorded audio where it has it.

## Step 9: tell them how to use it

Say something like this, in their language:

> Oknos is ready, and it is open in your browser now. Whenever you want to study, double-click **Oknos** on your desktop. You don't need me open for that. When you want new exercises or feedback, open me again and say "coach".

On macOS, add: "The first time, your Mac may ask whether you are sure you want to open it. Click Open."

Do not set up scheduled runs here. If they ask for exercises to be prepared automatically every day, follow "Setting up the schedule" in `.agents/skills/daily-prep/SKILL.md`, which asks first.

## If a check fails

| What you see | What to do |
|---|---|
| `uv sync` fails with a network or download error | Check the internet connection and run it again. A company network may block downloads; if so, say so plainly. |
| `uv sync` says the Python version is not supported | Run `uv python install 3.12`, then `uv sync` again. |
| Health: "Database could not be opened" | The folder is not writable. This often happens inside a OneDrive- or iCloud-synced folder, or a folder protected by "Controlled folder access". Clone the repository again into a normal local folder (e.g. `C:\Users\<name>\oknos` or `~/oknos`) and start again from step 3. |
| Health: "Greek text survives the database" is FAIL | This is a bug in the app, not something the person can fix. Tell them the app could not be set up correctly and that the maintainer needs to look at it. Keep the health output for the maintainer. |
| Health: content line says 0 exercises | The `content/open/` folder is missing or damaged. Run `git status` and restore it with `git checkout -- content/open`. |
| `start` says "Oknos did not start" | It prints the end of `learner/logs/server.log`; read it. If another program is using the port, `start` already picks the next free one. Run `uv run oknos stop`, then `start` again. |
| `health --server` says the app is not running right after `start` | Run `uv run oknos start` again and re-check. If it still fails, read `learner/logs/server.log`. |
| `shortcut` fails | Run it again once. If it still fails, tell them they can always ask you "start Oknos", and you will run `uv run oknos start` in this folder. |
| The browser did not open | Give them the address `start` printed, as a link. |
