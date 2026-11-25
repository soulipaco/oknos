"""Keep private things private: what git would publish must hold no learner data, no private
content and no local user paths (phase 7).

Run by the tests, by CI, and by the pre-push hook in `.githooks/` (`git config core.hooksPath
.githooks`, which the `setup` skill sets). It reads what git tracks (the index, or a commit), not
the working tree, so an ignored file never trips it and a force-added one always does.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

PRIVATE_DIRS = ("learner/", "content/private/")

# A local user folder: C:\Users\<name>, C:/Users/<name>, /Users/<name>, /home/<name>, or an
# agent's temp folder. Placeholders used in docs and tests (someone, you, <name>, …) are fine.
_SEP = r"[\\/]+"
USER_PATH = re.compile(
    r"(?:\b[A-Za-z]:" + _SEP + r"Users" + _SEP + r"|(?<![\w.])/Users/|(?<![\w.])/home/)"
    r"(?!(?:someone|you|user|username|name|me|runner|example)\b)([A-Za-z0-9][\w.-]*)"
    r"|AppData" + _SEP + r"Local" + _SEP + r"Temp" + _SEP + r"claude",
    re.IGNORECASE,
)


def _git(args: list[str], cwd: Path) -> str:
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    if out.returncode not in (0, 1):  # git grep exits 1 when nothing matches
        raise RuntimeError(out.stderr.decode("utf-8", "replace").strip() or f"git {args[0]} failed")
    return out.stdout.decode("utf-8", "replace")


# Published audio (the open content's clips, the films' voice) may come only from a service whose
# terms let it be published under CC BY-SA: Google's (voice.Provider.publishable). Never ElevenLabs
# (its use policy forbids passing its audio on under more permissive terms), Azure's free tier or
# edge-tts. Each manifest names who made each clip.
PUBLISHABLE = ("google", "gemini")
AUDIO_MANIFESTS = {"content/open-voice/index.json": "clips", "docs/brand/animations/voice/made_with.json": None}


def _audio_makers(repo: Path, rev: str | None, files: list[str]) -> list[str]:
    import json

    problems = []
    for path, field in AUDIO_MANIFESTS.items():
        if path not in files:
            continue
        try:
            data = json.loads(_git(["show", f"{rev}:{path}" if rev else f":{path}"], repo))
        except (json.JSONDecodeError, RuntimeError):
            problems.append(f"{path}: not readable JSON")
            continue
        makers = ([c.get("p", "google") for c in data.get(field, {}).values()] if field else list(data.values()))
        bad = sorted({m for m in makers if m not in PUBLISHABLE})
        if bad:
            problems.append(f"{path}: published audio made by {', '.join(bad)}, whose terms do not let it be "
                            f"published; only {' or '.join(PUBLISHABLE)} may make it")
    return problems


def check(repo: Path | str = ".", rev: str | None = None) -> list[str]:
    """Problems in what git tracks: the index, or the commit `rev`. Empty when all is well."""
    repo = Path(repo)
    where = [rev] if rev else ["--cached"]
    files = _git(["ls-tree", "-r", "--name-only", rev] if rev else ["ls-files"], repo).splitlines()
    problems = [f"{f}: tracked, but everything under {d} must stay on this machine (it is gitignored)"
                for f in files for d in PRIVATE_DIRS if f.replace("\\", "/").startswith(d)]
    problems += _audio_makers(repo, rev, files)
    # git grep finds the candidate lines fast; USER_PATH then decides (placeholders are fine)
    lines = _git(["grep", "-I", "-n", "-i", "-E", "-e", BROAD, *where], repo).splitlines()
    for line in lines:
        name, _, rest = (line.split(":", 1)[1] if rev else line).partition(":")
        number, _, text = rest.partition(":")
        if USER_PATH.search(text):
            problems.append(f"{name}:{number}: a local user path: {text.strip()[:120]}")
    return problems


BROAD = r"[a-z]:[\/]+users[\/]|/users/|/home/|appdata[\/]+local[\/]+temp"


def main(rev: str | None = None) -> int:
    problems = check(".", rev)
    for p in problems:
        print(p)
    if problems:
        print(f"\n{len(problems)} problem(s): fix them before pushing. Untrack a private file with "
              "`git rm --cached <file>`; replace a user path with a placeholder such as C:\\Users\\you.")
        return 1
    print("guard: nothing private is tracked")
    return 0
