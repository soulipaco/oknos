"""Make the films' narration: one clip per shot, from its Greek caption (phase 10, step 4).

    uv run python scripts/film_voice.py            # make the clips that are missing
    uv run python scripts/film_voice.py --redo     # make all of them again
    uv run python scripts/film_voice.py --list     # print what each clip says, make nothing

Each film page in docs/brand/animations/ holds its shots in an `OknosFilm.film({... shots: [...] ...})`
call. A shot's clip says its caption's Greek (`cap.el`) in the narrator's voice (Athina), unless the
shot has `say`: a list of [role, text] parts, "m" for Oknos (Nestoras) and "f" for the narrator, put
one after the other into one clip. The end card's clip is its `say`, if it has one.

The clips go to docs/brand/animations/voice/<shot>.mp3 (the shot's picture name: f1-01, f3-06, f1-end),
which git does not track: Microsoft's Product Terms give the right to use prebuilt neural voices'
output to customers of the paid tier only, and the maintainer's Azure resource is the free tier (F0).
film.js plays a clip when it finds one and plays silently when it does not.

The voice is Azure Speech through src/oknos/voice.py, with the key in learner/secrets.env; the free
tier makes 20 clips a minute, so the provider's pacing is waited out.
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
OUT = FILMS / "voice"


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

    azure = voice.providers()["azure"]
    keys = voice.secrets()
    why = azure.ready(keys, {})
    if why:
        print(f"Azure Speech is not set up: {why} (learner/secrets.env).")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    made = failed = 0
    for name, parts in todo:
        target = OUT / f"{name}.mp3"
        if target.exists() and not args.redo:
            continue
        audio = b""
        for role, text in parts:
            for attempt in range(5):
                left = azure.min_interval - (time.monotonic() - azure._last)
                if left > 0:
                    time.sleep(left)
                azure._last = time.monotonic()
                try:
                    audio += azure.make(text, role, keys)  # mp3 frames of one format join into one clip
                    voice._add_usage("azure", len(text))
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
    print(f"made {made}, failed {failed}, in {OUT.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
