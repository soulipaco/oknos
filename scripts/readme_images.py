"""Make the README's pictures from a demo learner: the screenshots, the hero, the films' preview, the social preview.

    uv run --with playwright --with pillow python scripts/readme_images.py [--port 8690] [--keep]

Run it in a fresh clone (only the open content): it refuses when content/private/ holds anything,
so no private material can reach a tracked image. It never touches learner/:
1. a throwaway learner folder gets 24 days of simulated practice (scripts/simulate.py), a profile
   (English, B1, 20 minutes) and a coach's note, as the agent would write it;
2. a demo coach pack copies the open exam-format items three times, and the demo learner answers
   them once, about half right, so the exam screen has evidence to show (the open content alone has
   too few such items for numbers, AGENTS.md "Known limits"; a real learner gets them from the coach);
3. the app runs on its own port (8690, never the maintainer's) with that folder, and headless Chrome
   (Playwright's "chrome" channel, or Edge) photographs the screens in light and dark;
4. docs/img/app-*.webp, docs/img/hero-{light,dark}.webp, docs/img/film-preview.webp (film 1, a short
   animated WebP from the film's own player) and docs/brand/social-preview.png are written;
5. the app is stopped and the folder deleted (--keep keeps it and prints where it is).

Playwright and Pillow are used only here, through `uv run --with`; they are not the app's dependencies.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs" / "img"
BRAND = ROOT / "docs" / "brand"
FILMS = BRAND / "animations"
FONT = ROOT / ".cache" / "oknos" / "fonts" / "NotoSerif[wdth,wght].ttf"

# name: (address, viewport width, what to photograph, width of docs/img/app-<name>-<theme>.webp, None for none)
SHOTS = {
    "home": ("", 1100, "top:760", None),  # only in the hero
    "reader": ("?lesson=shopping", 720, "dialogue", 820),
    "picture": ("?practice={seen_pictures}", 720, "card", 820),  # "pick the picture": only for words seen before
    "scene": ("?practice=open-book/ch05-scene-fournos", 720, "card:900", 820),
    "exam": ("?exam", 720, "top:820", 820),
    "book": ("?book", 720, "top:900", 820),
    "films": ("?films", 720, "top:700", 820),
}
FILM = "1-oknos-and-the-donkey.html"
FILM_SHOTS = [0, 2, 5, 7, 8]  # the shots of film 1 in the preview (0-based)


def log(*a):
    print(*a, flush=True)


# ---------- the demo learner ----------

def make_learner(folder: Path) -> None:
    env = {**os.environ, "OKNOS_LEARNER_DIR": str(folder), "PYTHONIOENCODING": "utf-8"}
    log("simulating 24 days of practice…")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "simulate.py"), "--days", "24", "--recent",
                    "--learner-dir", str(folder)],
                   env=env, check=True, stdout=subprocess.DEVNULL)
    (folder / "profile.json").write_text(json.dumps(
        {"ui_lang": "en", "name": "Zeynep", "target_exam": "b1-keg", "minutes": 20, "days_per_week": 6,
         "welcome_film_seen": True}, ensure_ascii=False), encoding="utf-8")
    (folder / "coach").mkdir(exist_ok=True)
    (folder / "coach" / "message.json").write_text(json.dumps(
        {"date": date.today().isoformat(),
         "en": "Eleven days in a row: well done. I added short reading and listening tasks in the exam's "
               "format, about the market, the pharmacy and the bus.",
         "tr": "Üst üste on bir gün: harika. Sınav formatında pazar, eczane ve otobüs üzerine kısa okuma ve "
               "dinleme görevleri ekledim."}, ensure_ascii=False), encoding="utf-8")
    # The demo coach pack: the open exam-format items (not writing or speaking), three copies each.
    from oknos import exams, packs
    from oknos.readiness import _evidence_items
    catalog = packs.load_all()
    want = set()
    for bp in exams.load_blueprints().values():
        want |= set(_evidence_items(catalog, bp))
    items = []
    for f in sorted((ROOT / "content" / "open").glob("*/items/*.json")):
        pack_id = f.parents[1].name
        for it in json.loads(f.read_text(encoding="utf-8")):
            if f"{pack_id}/{it['id']}" in want and it["type"] not in ("write", "speak"):
                for n in (1, 2, 3):
                    items.append({**it, "id": f"{it['id']}-demo{n}"})
    out = folder / "generated" / "demo-coach"
    (out / "items").mkdir(parents=True, exist_ok=True)
    (out / "pack.json").write_text(json.dumps(
        {"id": "demo-coach", "title": {"en": "Demo coach items", "tr": "Demo koç alıştırmaları"}, "version": 1,
         "levels": ["A2", "B1"], "visibility": "generated", "licence": "CC-BY-SA-4.0",
         "source": "Copies of the open exam-format items, for the README's demo learner only."},
        ensure_ascii=False), encoding="utf-8")
    (out / "items" / "tasks.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


def post(base: str, path: str, body: dict) -> dict:
    req = urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def answer_exam_items(base: str) -> None:
    """The demo learner's first tries at the demo coach items, through the app, about half right."""
    sys.path.insert(0, str(ROOT / "tests"))
    from oknos import packs
    from test_scheduler import _answer  # the same right/wrong helper the tests and simulate.py use
    catalog = packs.load_all()
    keys = sorted(k for k in catalog.items if k.startswith("demo-coach/"))
    rng = random.Random(7)
    s = post(base, "/api/session", {"kind": "practice", "items": keys, "ui_lang": "en"})
    for card in s["cards"]:
        item = catalog.items[card["item_key"]][1]
        post(base, "/api/attempt", {"session_id": s["session_id"], "item_key": card["item_key"], "card": card,
                                    "response": _answer(card, item, rng.random() < 0.5), "latency_ms": 40000})
    post(base, f"/api/session/{s['session_id']}/end", {})
    log(f"answered {len(s['cards'])} exam-format items")


def start_app(folder: Path, port: int) -> subprocess.Popen:
    env = {**os.environ, "OKNOS_LEARNER_DIR": str(folder), "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.Popen([sys.executable, "-m", "oknos", "start", "--foreground", "--no-browser", "--port",
                             str(port)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/home", timeout=2)
            return proc
        except OSError:
            time.sleep(0.5)
    proc.terminate()
    raise SystemExit(f"the demo app did not start on port {port}")


# ---------- the pictures ----------

def to_webp(png: bytes, width: int, path: Path, quality: int = 80) -> None:
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(path, "WEBP", quality=quality, method=6)
    log(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)")


def launch(p):
    for channel in ("chrome", "msedge"):
        try:
            return p.chromium.launch(channel=channel, headless=True)
        except Exception:  # noqa: BLE001 - try the next browser
            continue
    return p.chromium.launch(headless=True)


def seen_picture_words() -> str:
    """The words with a picture that the demo learner has already met, for the "pick the picture" card."""
    from oknos import db, packs, scheduler
    from oknos.packs import VocabItem, picture_url
    catalog = packs.load_all()
    conn = db.open_db()
    try:
        seen = scheduler.all_states(conn)
    finally:
        conn.close()
    keys = [k for k in seen if k in catalog.items and isinstance(catalog.items[k][1], VocabItem)
            and picture_url(catalog.items[k][1])]
    if not keys:
        raise SystemExit("the demo learner has met no word with a picture yet")
    return ",".join(keys[:8])


def screenshots(browser, base: str, raw: Path) -> None:
    seen_pictures = seen_picture_words()
    for theme in ("light", "dark"):
        for name, (query, width, what, out_w) in SHOTS.items():
            query = query.format(seen_pictures=seen_pictures)
            ctx = browser.new_context(viewport={"width": width, "height": 1000}, device_scale_factor=2,
                                      color_scheme=theme, reduced_motion="reduce")
            ctx.add_init_script(f"try {{ localStorage.setItem('gc-theme', '{theme}') }} catch (e) {{}}")
            page = ctx.new_page()
            for _ in range(30):  # "pick the picture" comes up at random among the cards: ask again until it does
                page.goto(base + query, wait_until="networkidle")
                page.wait_for_timeout(900)
                if name != "picture" or page.locator(".picture-option").count():
                    break
            page.evaluate("document.activeElement && document.activeElement.blur()")
            kind, _, limit = what.partition(":")
            if kind == "top":
                clip = {"x": 0, "y": 0, "width": width, "height": int(limit)}
            else:
                sel = {"dialogue": ".ch-dialogue", "card": "article.card"}[kind]
                box = page.locator(sel).first.bounding_box()
                y = box["y"] + page.evaluate("scrollY")
                pad, top = 20, 100 if kind == "dialogue" else 20  # a dialogue with its heading and first line
                clip = {"x": max(0, box["x"] - pad), "y": max(0, y - top), "width": box["width"] + 2 * pad,
                        "height": min(box["height"], int(limit or 820)) + pad + top}
            png = page.screenshot(clip=clip, full_page=True)
            (raw / f"{name}-{theme}.png").write_bytes(png)
            if out_w:
                to_webp(png, out_w, IMG / f"app-{name}-{theme}.webp")
            ctx.close()


def film_preview(browser, base: str, raw: Path) -> None:
    """Film 1 in about twenty seconds: five shots, each with its cross-fade, camera and caption."""
    from PIL import Image
    html = (FILMS / FILM).read_text(encoding="utf-8")
    shots = [(m[0], float(m[1])) for m in re.findall(r'"src": "frames/(f\d-\d+)\.webp",\s*"d": ([\d.]+)', html)]
    starts = [sum(d for _, d in shots[:i]) for i in range(len(shots))]
    ctx = browser.new_context(viewport={"width": 720, "height": 600})
    page = ctx.new_page()
    frames, durations = [], []
    for n in FILM_SHOTS:
        t0 = starts[n]
        times = ([] if n == 0 else [(t0 + x * 0.3, 130) for x in range(4)])  # the cross-fade from the shot before
        times += [(t0 + 0.9 + x * 0.5, 500) for x in range(6)] + [(t0 + 3.9, 1000)]
        for t, ms in times:
            page.goto(f"{base}films/{FILM}?embed=welcome&lang=en&theme=dark&voice=none&still={t:.2f}",
                      wait_until="networkidle")
            page.wait_for_timeout(300)
            im = Image.open(io.BytesIO(page.screenshot(clip={"x": 0, "y": 0, "width": 720, "height": 592})))
            frames.append(im.convert("RGB").resize((560, 460), Image.LANCZOS))
            durations.append(ms)
    ctx.close()
    frames[0].save(raw / "film-first.png")
    out = IMG / "film-preview.webp"
    frames[0].save(out, "WEBP", save_all=True, append_images=frames[1:], duration=durations, loop=0, quality=60,
                   method=6, minimize_size=True)
    log(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB, {sum(durations) / 1000:.0f} s)")


TOKENS = {  # web/style.css
    "light": {"bg": "#f6f2ea", "surface": "#fffdf8", "ink": "#1e2a32", "muted": "#627079", "line": "#e3dccd",
              "aegean": "#1f5f8b", "shadow": "rgba(30, 42, 50, .16)"},
    "dark": {"bg": "#151a1e", "surface": "#1d242a", "ink": "#ece6dc", "muted": "#a1a9ae", "line": "#2e373d",
             "aegean": "#80b4da", "shadow": "rgba(0, 0, 0, .5)"},
}


def page_style(t: dict) -> str:
    font = f'@font-face {{ font-family: "Noto Serif"; src: url("{FONT.as_uri()}"); font-weight: 100 900; }}' \
        if FONT.exists() else ""
    return f"""{font}
html, body {{ margin: 0; overflow: hidden; background: {t["bg"]}; }}
.shot {{ position: absolute; border-radius: 16px; overflow: hidden; border: 1px solid {t["line"]};
         box-shadow: 0 22px 54px {t["shadow"]}, 0 2px 6px {t["shadow"]}; background: {t["surface"]}; }}
.shot img {{ display: block; width: 100%; }}
.band {{ position: absolute; left: 0; right: 0; height: 28px; opacity: .5;
         background: url("{(BRAND / "meander.svg").as_uri()}") repeat-x center / 28px 28px; }}"""


def photograph(browser, html: str, size: tuple[int, int], scale: int, folder: Path) -> bytes:
    page_file = folder / "compose.html"
    page_file.write_text(html, encoding="utf-8")
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, device_scale_factor=scale)
    page = ctx.new_page()
    page.goto(page_file.as_uri(), wait_until="networkidle")
    page.wait_for_timeout(300)
    png = page.screenshot()
    ctx.close()
    return png


def hero(browser, raw: Path) -> None:
    """The README's first picture: the home screen, with a picture card and a chapter's scene over it."""
    for theme, t in TOKENS.items():
        src = lambda n: (raw / f"{n}-{theme}.png").as_uri()  # noqa: E731
        html = f"""<!doctype html><meta charset="utf-8"><style>{page_style(t)}
body {{ width: 1200px; height: 640px; }}
.glow {{ position: absolute; inset: 0; background: radial-gradient(60% 70% at 70% 45%, {t["aegean"]}22, transparent 70%); }}
</style><div class="glow"></div>
<div class="shot" style="left: 28px; top: 36px; width: 720px"><img src="{src('home')}"></div>
<div class="shot" style="left: 700px; top: 92px; width: 260px"><img src="{src('picture')}"></div>
<div class="shot" style="left: 916px; top: 196px; width: 256px; max-height: 410px"><img src="{src('scene')}"></div>"""
        to_webp(photograph(browser, html, (1200, 640), 2, raw), 2000, IMG / f"hero-{theme}.webp", 82)


def social_preview(browser, raw: Path) -> None:
    """GitHub's social preview (1280×640 PNG): the lockup and tagline beside two cards from the app."""
    t = TOKENS["light"]
    src = lambda n: (raw / f"{n}-light.png").as_uri()  # noqa: E731
    tagline = "Learn Greek the lazy way.<br>Your agent does the rest."
    html = f"""<!doctype html><meta charset="utf-8"><style>{page_style(t)}
body {{ width: 1280px; height: 640px; }}
.top {{ top: 22px; }} .bottom {{ bottom: 22px; }}
.text {{ position: absolute; left: 96px; top: 150px; width: 600px; }}
.text img {{ height: 104px; display: block; margin: 0 0 30px -8px; }}
h1 {{ font: 600 44px/1.2 "Noto Serif", Georgia, serif; color: {t["ink"]}; margin: 0 0 16px; letter-spacing: -.3px; }}
p {{ font: 400 25px/1.4 "Segoe UI", system-ui, sans-serif; color: {t["muted"]}; margin: 0; }}
</style><div class="band top"></div><div class="band bottom"></div>
<div class="text"><img src="{(BRAND / "oknos-lockup-light.svg").as_uri()}" alt="Oknos">
<h1>{tagline}</h1><p>You plait the rope. The donkey carries the load.</p></div>
<div class="shot" style="left: 730px; top: 150px; width: 270px; max-height: 410px"><img src="{src('scene')}"></div>
<div class="shot" style="left: 940px; top: 76px; width: 270px"><img src="{src('picture')}"></div>"""
    from PIL import Image
    png = photograph(browser, html, (1280, 640), 1, raw)
    out = BRAND / "social-preview.png"
    Image.open(io.BytesIO(png)).convert("RGB").save(out, optimize=True)
    log(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


# ---------- main ----------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8690)
    ap.add_argument("--keep", action="store_true", help="keep the demo learner folder")
    args = ap.parse_args()
    private = ROOT / "content" / "private"
    if private.is_dir() and any(private.iterdir()):
        raise SystemExit("content/private/ holds material: run this in a fresh clone, so no private content "
                         "reaches a tracked picture.")
    folder = Path(tempfile.mkdtemp(prefix="oknos-readme-"))
    os.environ["OKNOS_LEARNER_DIR"] = str(folder)
    sys.path.insert(0, str(ROOT / "src"))
    IMG.mkdir(parents=True, exist_ok=True)
    make_learner(folder)
    proc = start_app(folder, args.port)
    base = f"http://127.0.0.1:{args.port}/"
    try:
        answer_exam_items(base.rstrip("/"))
        from playwright.sync_api import sync_playwright
        raw = folder / "raw"
        raw.mkdir()
        with sync_playwright() as p:
            browser = launch(p)
            screenshots(browser, base, raw)
            film_preview(browser, base, raw)
            hero(browser, raw)
            social_preview(browser, raw)
            browser.close()
    finally:
        proc.terminate()
        proc.wait(timeout=20)
        if args.keep:
            log(f"the demo learner is in {folder}")
        else:
            shutil.rmtree(folder, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
