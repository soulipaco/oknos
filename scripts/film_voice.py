"""Make the films' narration: one clip per shot, from its Greek caption (phase 10, step 4).

    uv run python scripts/film_voice.py                   # the published clips (Google), the missing ones
    uv run python scripts/film_voice.py --provider azure  # this computer's own clips (Athina, Nestoras)
    uv run python scripts/film_voice.py --redo            # make all of them again
    uv run python scripts/film_voice.py --list            # print what each clip says, make nothing

Each film page in docs/brand/animations/ holds its shots in an `OknosFilm.film({... shots: [...] ...})`
call. A shot's clip says its caption's Greek (`cap.el`) in the narrator's voice (Athina), unless the
shot has `say`: a list of [role, text] parts, "m" for Oknos and "f" for the narrator, put one after
the other into one clip. The end card's clip is its `say`, if it has one.

Two sets of clips, named after the shot's picture (f1-01, f3-06, f1-end), as decided with the
maintainer on 2026-11-22 (Google for the repo, Athina and Nestoras for their own use):

  voice/<shot>.mp3        Google Cloud Text-to-Speech, Chirp 3 HD Kore (narrator) and Orus (Oknos).
                          Tracked and published: Google lets the audio files be used "in your
                          applications or media" under its Cloud terms, on any tier.
  voice-local/<shot>.mp3  Azure Speech, Athina and Nestoras, for this computer only and not tracked:
                          Microsoft's Product Terms give the use of the output to the paid tier
                          only, and the maintainer's resource is the free tier (F0).

film.js plays voice-local/ when it is there, else voice/, else the film plays silently. The services
are src/oknos/voice.py's, with the keys in learner/secrets.env.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILMS = ROOT / "docs" / "brand" / "animations"
OUT = {"google": FILMS / "voice", "azure": FILMS / "voice-local"}


def film_data(page: Path) -> dict:
    """The shots (and the end card, if any) of one film page."""
    html = page.read_text(encoding="utf-8")
    dec = json.JSONDecoder()
    m = re.search(r"\bshots:\s*", html)
    if not m:
        raise ValueError(f"{page.name}: no shots")
    shots, after = dec.raw_decode(html, m.end())
    end = None
    m = re.compile(r"\bend:\s*").search(html, after)
    if m and not html.startswith("null", m.end()):
        end, _ = dec.raw_decode(html, m.end())
    return {"shots": shots, "end": end}


def frames(mp3: bytes) -> bytes:
    """The audio frames of an mp3: without an ID3 tag or a Xing/Info header, which would give a clip
    made of two parts the length of the first part only."""
    if mp3[:3] == b"ID3":
        size = (mp3[6] << 21) | (mp3[7] << 14) | (mp3[8] << 7) | mp3[9]
        mp3 = mp3[10 + size:]
    head = mp3[:200]
    if b"Xing" in head or b"Info" in head:
        b1, b2 = mp3[1], mp3[2]
        version = (b1 >> 3) & 3          # 3: MPEG-1, 2: MPEG-2, 0: MPEG-2.5
        bitrate_i, rate_i, pad = b2 >> 4, (b2 >> 2) & 3, (b2 >> 1) & 1
        mpeg1 = version == 3
        rates = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}[version]
        kbps = ((0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320) if mpeg1 else
                (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160))[bitrate_i]
        length = (144 if mpeg1 else 72) * kbps * 1000 // rates[rate_i] + pad
        mp3 = mp3[length:]
    return mp3


def clip_name(src: str) -> str:
    return Path(src).stem  # frames/f3-06.webp -> f3-06


def parts_of(shot: dict) -> list[tuple[str, str]]:
    say = shot.get("say")
    if say is None:
        return [("f", shot["cap"]["el"])]
    if isinstance(say, str):
        return [("f", say)]
    return [(role, text) for role, text in say]


def clips() -> list[tuple[str, list[tuple[str, str]]]]:
    """(clip name, parts) for every shot of every film, in order."""
    out = []
    for page in sorted(FILMS.glob("*.html")):
        data = film_data(page)
        for s in data["shots"]:
            out.append((clip_name(s["src"]), parts_of(s)))
        end = data["end"]
        if end and end.get("say"):
            stem = clip_name(data["shots"][0]["src"]).split("-")[0]
            out.append((f"{stem}-end", parts_of(end)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--provider", choices=sorted(OUT), default="google",
                    help="google: the published clips (voice/); azure: this computer's own (voice-local/)")
    ap.add_argument("--redo", action="store_true", help="make every clip again")
    ap.add_argument("--list", action="store_true", help="print the clips' texts, make nothing")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    todo = clips()
    if args.list:
        for name, parts in todo:
            print(name, " + ".join(f"[{r}] {t}" for r, t in parts))
        return 0

    sys.path.insert(0, str(ROOT / "src"))
    from oknos import voice

    tts = voice.providers()[args.provider]
    out = OUT[args.provider]
    keys = voice.secrets()
    why = tts.ready(keys, {})
    if why:
        print(f"{tts.label} is not set up: {why} (learner/secrets.env).")
        return 1
    out.mkdir(parents=True, exist_ok=True)
    made = failed = 0
    for name, parts in todo:
        target = out / f"{name}.mp3"
        if target.exists() and not args.redo:
            continue
        audio = b""
        for role, text in parts:
            for attempt in range(5):
                left = tts.min_interval - (time.monotonic() - tts._last)
                if left > 0:
                    time.sleep(left)
                tts._last = time.monotonic()
                try:
                    audio += frames(tts.make(text, role, keys))  # mp3 frames of one format join into one clip
                    voice._add_usage(tts.name, len(text))
                    break
                except voice.Refused as e:
                    print(f"  {name}: {e}; again in {5 * (attempt + 1)} s")
                    time.sleep(5 * (attempt + 1))
            else:
                audio = b""
                break
        if not audio:
            failed += 1
            print(f"{name}: not made")
            continue
        target.write_bytes(audio)
        made += 1
        print(f"{name}: {len(audio) // 1024} KB  " + " + ".join(t for _, t in parts))
    print(f"made {made}, failed {failed}, in {out.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
