"""Make the podcast episodes shipped with the open book (docs/PODCASTS.md, "Shipped episodes").

    uv run python scripts/ship_podcasts.py --check                    # what is missing or out of date
    uv run python scripts/ship_podcasts.py                            # make them with Chirp 3 HD (the default)
    uv run python scripts/ship_podcasts.py --provider gemini book.lesson-02.tr   # one, with Gemini TTS

The chapter episodes of the Oknos book (`book.<stage>.<lang>`, written with the podcast skill into
learner/podcasts/) are rendered again with a voice whose terms let its audio be published (Google's:
Chirp 3 HD, no daily limit, or Gemini TTS, 100 requests a day on Tier 1; never ElevenLabs, Azure's free
tier or edge-tts), and copied into content/open-podcasts/<id>/: the script, episode.json and
episode.mp3 (mono, --bitrate, 32 kb/s by default). index.json says which service made each episode;
`oknos guard` fails if one is not publishable. The app plays the learner's own rendering first, then
the shipped one (src/oknos/podcast.py).

The learner's own episodes are never touched: the render runs in learner/podcasts-ship/, sharing the
learner's clip cache (learner/voice/podcast/), so a line the learner's own render already made with
the same service and voice costs nothing. Keys come from learner/secrets.env (or --secrets, or the
environment) and go to Google only. Personal episodes (daily, weekly) are never shipped.

A shipped episode is made again when its script changed or another service made it; --force makes
it again anyway. With Gemini, a day's requests running out stops the run; the clips made are kept, and
the same command goes on the next day.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from oknos import paths, podcast, voice  # noqa: E402

LICENCE = "CC-BY-SA-4.0"
SERVICES = {"google": "Google Cloud Text-to-Speech, Chirp 3 HD", "gemini": "Google Gemini TTS"}


def public_script(raw: dict) -> dict:
    """The script as shipped: the open book's curriculum and refs, no pointers into learner/."""
    out = dict(raw)
    if out.get("curriculum") == "greek-helper-book":
        out["curriculum"] = "oknos-book"
    sources = []
    for s in raw.get("sources") or []:
        s = dict(s)
        ref = s.get("ref", "")
        if ref.startswith("greek-helper/"):
            s["ref"] = "oknos-book/" + ref.split("/", 1)[1]
        if "script.v1" in ref or ref.startswith("learner/"):
            continue
        if "v1" in (s.get("note") or "") or "learner/" in (s.get("note") or ""):
            s.pop("note", None)
        sources.append(s)
    out["sources"] = sources
    return out


def text(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ids", nargs="*", help="episode ids (default: every book chapter episode)")
    ap.add_argument("--provider", choices=sorted(SERVICES), default="google")
    ap.add_argument("--bitrate", type=int, default=32, help="kb/s of the shipped mp3 (mono)")
    ap.add_argument("--secrets", type=Path, help="a secrets.env with GOOGLE_TTS_API_KEY or GEMINI_API_KEY")
    ap.add_argument("--check", action="store_true", help="say what is missing or out of date, make nothing")
    ap.add_argument("--force", action="store_true", help="make the episodes again even if up to date")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    p = voice.providers()[args.provider]
    assert p.publishable, f"{p.name}'s audio may not be published"
    if args.secrets:
        for line in args.secrets.read_text(encoding="utf-8-sig").splitlines():
            k, sep, v = line.partition("=")
            if sep and k.strip() in ("GOOGLE_TTS_API_KEY", "GEMINI_API_KEY"):
                os.environ[k.strip()] = v.strip()

    source = podcast.podcasts_dir()
    build = paths.learner_dir() / "podcasts-ship"
    ship = podcast.shipped_dir()
    index_file = ship / "index.json"
    try:
        index = json.loads(index_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        index = {}
    episodes = index.get("episodes", {})

    ids = args.ids or sorted(d.name for d in source.iterdir()
                             if d.name.startswith("book.") and (d / "script.json").is_file())
    todo = []
    for pid in ids:
        raw = json.loads((source / pid / "script.json").read_text(encoding="utf-8-sig"))
        if raw.get("kind") != "chapter":
            print(f"{pid}: a {raw.get('kind')} episode, never shipped")
            continue
        body = text(public_script(raw))
        have = ship / pid / "script.json"
        current = (have.is_file() and have.read_text(encoding="utf-8") == body and (ship / pid / "episode.mp3").is_file()
                   and episodes.get(pid, {}).get("p") == p.name)
        if current and not args.force:
            continue
        todo.append((pid, body))
        print(f"{pid}: {'out of date' if have.is_file() else 'missing'}")
    if args.check or not todo:
        print(f"{len(todo)} to make with {p.name}" if todo else "every shipped episode is up to date")
        return 0

    # Render in learner/podcasts-ship/ with this one service; the learner's clip cache is shared.
    podcast.episode_dir = lambda pid: build / pid
    podcast._chain = lambda profile, keys: [p]
    exe = podcast.ffmpeg()
    for pid, body in todo:
        (build / pid).mkdir(parents=True, exist_ok=True)
        (build / pid / "script.json").write_text(body, encoding="utf-8")
        try:
            meta = podcast.render(pid, wait=True)
        except podcast.PodcastError as e:
            print(f"{pid}: stopped: {str(e)[:300]}")
            break
        if set(meta.get("made") or {}) - {p.name}:
            print(f"{pid}: made by {meta['made']}, not only {p.name}; not shipped")
            continue
        out = ship / pid
        out.mkdir(parents=True, exist_ok=True)
        podcast._run([exe, "-v", "error", "-y", "-i", str(build / pid / "episode.mp3"), "-ac", "1",
                      "-c:a", "libmp3lame", "-b:a", f"{args.bitrate}k", "-map_metadata", "0",
                      str(out / "episode.part.mp3")])
        (out / "episode.part.mp3").replace(out / "episode.mp3")
        (out / "script.json").write_text(body, encoding="utf-8")
        shipped = {k: v for k, v in meta.items() if k not in ("clips", "chars", "tokens", "made")}
        shipped["script"] = podcast.script_hash(pid, out)
        (out / "episode.json").write_text(text(shipped), encoding="utf-8")
        try:  # read again: another run may have shipped other episodes meanwhile
            episodes = json.loads(index_file.read_text(encoding="utf-8")).get("episodes", {})
        except FileNotFoundError:
            pass
        episodes[pid] = {"p": p.name, "rendered": meta["rendered"][:10], "seconds": meta["seconds"],
                         "version": meta.get("version")}
        write_index(index_file, episodes, args.bitrate)
        print(f"{pid}: shipped, {meta['seconds'] / 60:.1f} min, {(out / 'episode.mp3').stat().st_size / 1e6:.1f} MB")
    return 0


def write_index(f: Path, episodes: dict, bitrate: int) -> None:
    counts: dict[str, int] = {}
    for e in episodes.values():
        counts[e["p"]] = counts.get(e["p"], 0) + 1
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text({
        "about": "Podcast lessons of the Oknos book, shipped with the open content (docs/PODCASTS.md). "
                 "Each is <id>/episode.mp3 with its script.json and episode.json; p is the service that voiced it.",
        "licence": LICENCE,
        "made_with": "; ".join(f"{SERVICES[k]}: {n} episodes" for k, n in sorted(counts.items())),
        "mp3": f"mono, {bitrate} kb/s",
        "updated": date.today().isoformat(),
        "episodes": dict(sorted(episodes.items())),
    }), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
