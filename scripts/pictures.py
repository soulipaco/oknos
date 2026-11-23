"""Take accepted pictures into the open pictures pack (phase 9: pictures).

    uv run --with pillow python scripts/pictures.py <requests.json> [<requests.json> ...]

Pictures are made by an image model (through Codex) into a working folder under .cache/oknos/,
listed in a requests.json with a status per picture (docs/brand/IMAGES.md). This script takes every
request whose status is "accepted", makes a 512×512 WebP of it in content/open/open-pictures/pictures/,
and adds or updates its entry in pictures.json. Running it again changes nothing that is already in.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "content" / "open" / "open-pictures"
SIZE = 512


def slug(item_key: str) -> str:
    # a file name in the pack allows only letters, digits, '.', '_' and '-' (an item such as v-politis~2 has a '~')
    return re.sub(r"[^A-Za-z0-9._-]", "-", item_key.split("/", 1)[-1])


def take(requests_file: Path) -> int:
    data = json.loads(requests_file.read_text(encoding="utf-8"))
    folder = ROOT / data["folder"] if data.get("folder") else requests_file.parent
    index_file = PACK / "pictures" / "pictures.json"
    index = json.loads(index_file.read_text(encoding="utf-8"))
    by_word = {p["word"]: p for p in index["pictures"]}
    added = 0
    for r in data["requests"]:
        if r.get("status") != "accepted" or not r.get("file"):
            continue
        name = f"{slug(r['item'])}.webp"
        target = PACK / "pictures" / name
        if not target.is_file():
            with Image.open(folder / r["file"]) as im:
                im.convert("RGB").resize((SIZE, SIZE), Image.LANCZOS).save(target, "WEBP", quality=82, method=6)
            added += 1
        by_word[r["el"]] = {"word": r["el"], "file": name, "item": r["item"], "prompt": r.get("prompt"),
                            "made": f"image model via Codex, reviewed {r.get('reviewed') or date.today().isoformat()}"}
    index["pictures"] = sorted(by_word.values(), key=lambda p: p["file"])
    index_file.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return added


if __name__ == "__main__":
    total = sum(take(Path(f)) for f in sys.argv[1:])
    print(f"{total} new picture(s) in {PACK.relative_to(ROOT)}")
