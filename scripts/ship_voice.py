"""Make the voice clips shipped with the open content (docs/VOICE.md, "Clips shipped with the open content").

    uv run python scripts/ship_voice.py --check                  # what is missing or stale, make nothing
    uv run python scripts/ship_voice.py --secrets <secrets.env>  # make the missing clips (Google), resumable
    uv run python scripts/ship_voice.py --secrets <...> --prune  # also delete clips no open text uses any more

Every Greek text of the tracked open packs (content/open/open-*, the open book's chapters
included) that the app can speak gets one clip, made with Google Cloud Text-to-Speech, Chirp 3 HD:
Kore for the narrator and female speakers, Orus for male ones (src/oknos/voice.py's role_of). Never
the private book (content/private/) or the coach's per-learner packs (learner/generated/).

The clips sit in content/open-voice/ with the same names as learner/voice/ (role/xx/<key>.mp3, the
key made from the role and the text), so the app finds either with one lookup. index.json lists
every clip with its text and role. Google lets its audio be used in applications under its Cloud
terms; Azure's free tier and edge-tts do not, so those never make shipped clips.

Chirp 3 HD now and then sends back near-silence for a short word (92 of the first 2,206 clips,
all single words or fragments). Every clip is checked: with ffmpeg on the PATH by its loudness,
else by its length. A silent one is asked for again, then as "word.", «word» and "word…", which
read the same; index.json records under "said" what was sent when it is not the text itself.
`--recheck` checks the clips already made and remakes the silent ones.

The key is GOOGLE_TTS_API_KEY from the given secrets file (or the environment); it is sent to
Google only and never printed. Every request has a 60-second timeout, every ffmpeg call one too.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from oknos import packs, paths, voice  # noqa: E402

LICENCE = "CC-BY-SA-4.0"
PACE = 0.25  # seconds between requests
QUIET_DB = -35.0  # a clip's mean loudness below this is silence (the good ones are -15 to -25 dB)
SHORT_S = 0.47    # without ffmpeg: a clip shorter than this is silence (32 kb/s mp3: 4,000 bytes a second)


def silent(data: bytes) -> bool:
    """Google sent near-silence instead of speech."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return len(data) / 4000 < SHORT_S
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(data)
    try:
        err = subprocess.run([ffmpeg, "-hide_banner", "-i", f.name, "-af", "volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True, timeout=60).stderr
    finally:
        os.unlink(f.name)
    mean = [float(line.split(":")[-1].split()[0]) for line in err.splitlines() if "mean_volume" in line]
    return not mean or mean[0] < QUIET_DB


def variants(text: str) -> list[str]:
    """What is sent: the text (twice), then forms that read the same and that Chirp does not drop."""
    bare = text.rstrip(".;!…")
    cap = bare[:1].upper() + bare[1:]
    return [text, text, f"{bare}.", f"«{text}»", f"{bare}…", f"{bare}!", f"{cap}.", f"{cap}!"]


def open_texts() -> list[tuple[str, str]]:
    """Every (text, role) the open content can speak, read with no private pack and no learner folder."""
    os.environ["OKNOS_LEARNER_DIR"] = tempfile.mkdtemp(prefix="oknos-ship-voice-")
    paths.content_roots = lambda: [("open", paths.CONTENT_DIR / "open")]
    catalog = packs.load_all()
    return voice.texts(catalog)


def read_manifest(out: Path) -> dict:
    try:
        return json.loads((out / "index.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def write_manifest(out: Path, clips: dict, browser: dict) -> None:
    google = voice.providers()["google"]
    data = {
        "about": "Greek voice clips for the open content of Oknos (docs/VOICE.md). Each clip is "
                 "<role>/<key[:2]>/<key>.mp3, key = sha1('<role>|<normalised text>') (src/oknos/voice.py).",
        "licence": LICENCE,
        "made_with": "Google Cloud Text-to-Speech, Chirp 3 HD",
        "voices": google.voices,
        "characters": sum(len(c.get("said", c["t"])) for c in clips.values()),
        "clips": dict(sorted(clips.items())),
        "browser": dict(sorted(browser.items())),  # texts Chirp gave only silence for: the browser's voice reads them
    }
    tmp = out / "index.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(out / "index.json")


def load_key(path: str | None) -> str | None:
    if os.environ.get("GOOGLE_TTS_API_KEY"):
        return os.environ["GOOGLE_TTS_API_KEY"]
    if path and Path(path).is_file():
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "GOOGLE_TTS_API_KEY" and value.strip():
                return value.strip()
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--secrets", help="a secrets.env holding GOOGLE_TTS_API_KEY (e.g. the main checkout's learner/secrets.env)")
    ap.add_argument("--check", action="store_true", help="report what is missing or stale, make nothing")
    ap.add_argument("--prune", action="store_true", help="delete clips no open text uses any more")
    ap.add_argument("--recheck", action="store_true", help="find silent clips among those made and make them again")
    ap.add_argument("--limit", type=int, default=None, help="make at most this many clips")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    out = voice.shipped_dir()
    pairs = open_texts()
    wanted = {voice.key(t, r): (t, r) for t, r in pairs}
    manifest = read_manifest(out)
    clips = manifest.get("clips", {})
    browser = {} if args.recheck else {k: v for k, v in manifest.get("browser", {}).items() if k in wanted}
    clips = {k: v for k, v in clips.items() if voice.file_for(v["t"], v["r"], out).is_file()}
    if args.recheck:
        quiet = [k for k, c in clips.items() if silent(voice.file_for(c["t"], c["r"], out).read_bytes())]
        print(f"{len(quiet):,} of {len(clips):,} clips are silent; they are made again")
        clips = {k: v for k, v in clips.items() if k not in quiet}
    todo = [(k, t, r) for k, (t, r) in wanted.items() if k not in clips and k not in browser]
    stale = sorted(set(clips) - set(wanted))
    print(f"{len(wanted):,} open texts; {len(set(clips) & set(wanted)):,} have a clip, {len(todo):,} missing, "
          f"{len(stale):,} stale, {len(browser):,} left to the browser voice; {sum(len(t) for _, t, _ in todo):,} characters to make.")
    if args.check:
        return 1 if todo else 0

    if args.prune and stale:
        for k in stale:
            voice.file_for(clips[k]["t"], clips[k]["r"], out).unlink(missing_ok=True)
            del clips[k]
        out.mkdir(parents=True, exist_ok=True)
        write_manifest(out, clips, browser)
        print(f"deleted {len(stale):,} stale clips")

    if not todo:
        return 0
    api_key = load_key(args.secrets)
    if not api_key:
        print("No GOOGLE_TTS_API_KEY (pass --secrets <path to secrets.env>).")
        return 1
    keys = {"GOOGLE_TTS_API_KEY": api_key}
    google = voice.providers()["google"]
    if args.limit is not None:
        todo = todo[:args.limit]
    made = failed = chars = 0
    started = time.monotonic()
    for n, (k, text, role) in enumerate(todo, 1):
        data = said = None
        for sent in variants(text):
            for attempt in range(5):
                time.sleep(PACE)
                try:
                    data = google.make(sent, role, keys)  # voice._post: a 60-second timeout
                    chars += len(sent)
                    break
                except voice.Refused as e:
                    print(f"  {k[:8]}: {e}; again in {10 * (attempt + 1)} s", flush=True)
                    time.sleep(10 * (attempt + 1))
            if data and not silent(data):
                said = sent
                break
            data = None
        if not data:
            failed += 1
            print(f"  only silence, left to the browser voice: {text}", flush=True)
            voice.file_for(text, role, out).unlink(missing_ok=True)  # never play a silent clip
            browser[k] = {"r": role, "t": text, "why": "Chirp 3 HD sent only silence"}
            continue
        target = voice.file_for(text, role, out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        clips[k] = {"r": role, "t": text, **({"said": said} if said != text else {})}
        made += 1
        if made % 50 == 0:
            write_manifest(out, clips, browser)
        if n % 100 == 0 or n == len(todo):
            rate = n / max(time.monotonic() - started, 1e-6)
            print(f"  {n:,}/{len(todo):,}, about {(len(todo) - n) / rate / 60:.0f} min left", flush=True)
    out.mkdir(parents=True, exist_ok=True)
    write_manifest(out, clips, browser)
    print(f"made {made:,} ({chars:,} characters), failed {failed:,}; {len(clips):,} clips in {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
