"""Make the Oknos brand files in docs/brand/ (the rope ring, the wordmark, the Ὄ icon, the donkey).

    uv run --with fonttools python scripts/make_brand.py

The wordmark is Noto Serif (SIL Open Font Licence) turned into outlines, so it looks the same
wherever the SVG is shown. The font is read from .cache/oknos/fonts/ (download it once from
https://github.com/google/fonts/tree/main/ofl/notoserif). Everything else is drawn here.
The decisions behind the shapes are in docs/brand/README.md.
"""

from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "brand"
FONT = ROOT / ".cache" / "oknos" / "fonts" / "NotoSerif[wdth,wght].ttf"

# The app's tokens (web/style.css), light and dark.
INK = {"light": "#1e2a32", "dark": "#ece6dc"}
AEGEAN = {"light": "#1f5f8b", "dark": "#80b4da"}
PAPER = {"light": "#f6f2ea", "dark": "#151a1e"}
LINEN = {"light": "#fffdf8", "dark": "#1d242a"}
FAINT = {"light": "#d9d0be", "dark": "#3a444b"}


def num(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def poly(pts) -> str:
    return "M" + " L".join(f"{num(x)} {num(y)}" for x, y in pts)


# ---------- the rope: two strands crossing over and under ----------

def ring(cx=50.0, cy=50.0, R=33.0, a=4.2, n=7, steps=8):
    """Two strands r = R ± a·sin(nθ), cut into segments centred on the crossings."""
    segs = {"A": [], "B": []}
    for k in range(2 * n):
        t0, t1 = (k - 0.5) * math.pi / n, (k + 0.5) * math.pi / n
        for s, sg in (("A", 1), ("B", -1)):
            pts = []
            for i in range(steps + 1):
                t = t0 + (t1 - t0) * i / steps
                r = R + sg * a * math.sin(n * t)
                pts.append((cx + r * math.sin(t), cy - r * math.cos(t)))
            segs[s].append((poly(pts), (k % 2 == 0) == (s == "A")))
    return segs


def rope_line(x0=0.0, x1=240.0, y=0.0, a=2.6, n=15, steps=6):
    L = x1 - x0
    segs = {"A": [], "B": []}
    for k in range(2 * n + 1):
        u0, u1 = max(0, (k - 0.5) / (2 * n)), min(1, (k + 0.5) / (2 * n))
        for s, sg in (("A", 1), ("B", -1)):
            pts = [(x0 + L * (u0 + (u1 - u0) * i / steps),
                    y + sg * a * math.sin(2 * math.pi * n * (u0 + (u1 - u0) * i / steps))) for i in range(steps + 1)]
            segs[s].append((poly(pts), (k % 2 == 0) == (s == "A")))
    return segs


def rope(segs, width, gap, colour, box, mask_id, upto=None):
    """The strands, the 'over' ones cut out of the 'under' ones with a mask: transparent on any ground."""
    x, y, w, h = box
    keep = (lambda i: True) if upto is None else (lambda i: i < upto)
    under = " ".join(d for s in "AB" for i, (d, o) in enumerate(segs[s]) if not o and keep(i))
    over = " ".join(d for s in "AB" for i, (d, o) in enumerate(segs[s]) if o and keep(i))
    return (f'<defs><mask id="{mask_id}" maskUnits="userSpaceOnUse" x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}">'
            f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" fill="#fff"/>'
            f'<path d="{over}" fill="none" stroke="#000" stroke-width="{num(width + 2 * gap)}" stroke-linecap="round"/></mask></defs>'
            f'<g fill="none" stroke="{colour}" stroke-width="{num(width)}" stroke-linecap="round" stroke-linejoin="round">'
            f'<path mask="url(#{mask_id})" d="{under}"/><path d="{over}"/></g>')


def ring_mark(colour, mask_id="oknos-ring", small=False):
    if small:  # fewer, thicker twists for 16–32 px
        return rope(ring(R=32, a=5.0, n=5, steps=8), 8.4, 1.8, colour, (0, 0, 100, 100), mask_id)
    return rope(ring(), 6.2, 1.1, colour, (0, 0, 100, 100), mask_id)


# ---------- the wordmark ----------

def wordmark(text="oknos", weight=500, tracking=18):
    """Outlines of `text` in Noto Serif, in font units with y down; returns (path d, width, x-height, ascender)."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    font = instancer.instantiateVariableFont(TTFont(FONT), {"wght": weight, "wdth": 100})
    glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
    x, parts = 0, []
    for i, ch in enumerate(text):
        name = cmap[ord(ch)]
        pen = SVGPathPen(glyphs, ntos=lambda v: num(v))
        glyphs[name].draw(TransformPen(pen, (1, 0, 0, -1, x, 0)))
        parts.append(pen.getCommands())
        x += glyphs[name].width + (tracking if i < len(text) - 1 else 0)
    os2 = font["OS/2"]
    return " ".join(parts), x, os2.sxHeight, os2.sTypoAscender


# ---------- the Ὄ: an omicron with its breathing and accent drawn as a donkey's ears ----------

OMICRON = '<path fill-rule="evenodd" d="M50 43 a31 33 0 1 0 0.01 0 Z M50 50.5 a19.5 25.5 0 1 1 -0.01 0 Z"/>'
# Short ear on the left (the breathing), long ear on the right (the accent). Splayed sideways,
# as a donkey holds them, not upright like a rabbit's (chosen 2026-11-21 over upright, pointed
# and drooping versions).
EARS = ('<path d="M41 43 C35 37 26 32 13 31 C16 40 25 46 35 47 Z"/>'
        '<path d="M55 41 C61 30 72 19 91 12 C90 27 79 39 64 45 Z"/>')


def omicron_ears(colour, ears_colour=None):
    return f'<g fill="{colour}">{OMICRON}</g><g fill="{ears_colour or colour}">{EARS}</g>'


# ---------- the donkey (the agent), three moods ----------

DONKEY = ("M66 114 C64 102 60 94 54 90 C46 88 36 90 28 90 C16 90 9 83 9 74 C9 64 15 58 24 57 "
          "C33 55 39 48 43 41 {e1} {e2} C71 50 80 60 84 74 C87 86 88 100 90 114")
MOODS = {
    "ready": (("C40 30 40 16 47 6 C53 14 55 28 53 39", "C59 30 68 20 79 15 C79 26 71 37 62 44"), "open"),
    "working": (("C40 30 40 16 47 6 C53 14 55 28 53 39", "C61 36 74 30 92 30 C86 38 74 42 62 44"), "open"),
    "resting": (("C40 31 44 18 55 10 C58 20 56 30 53 39", "C61 36 74 30 92 30 C86 38 74 42 62 44"), "closed"),
}


def donkey(colour, mood):
    (e1, e2), eye = MOODS[mood]
    eye_svg = (f'<circle cx="39" cy="54" r="2.4" stroke="none" fill="{colour}"/>' if eye == "open"
               else '<path d="M36 55 q3 2.6 6 0"/>')
    return (f'<g fill="none" stroke="{colour}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="{DONKEY.format(e1=e1, e2=e2)}"/>{eye_svg}'
            f'<path d="M14 72 q2 -1.6 4 0"/><path d="M13 83 q5 2.2 10 0.6"/></g>')


# ---------- files ----------

def svg(view_box, body, title, w=None, h=None):
    size = f' width="{num(w)}" height="{num(h)}"' if w else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}"{size} role="img" aria-label="{title}">'
            f"<title>{title}</title>{body}</svg>\n")


def write(name, text):
    (OUT / name).write_text(text, encoding="utf-8", newline="\n")
    print("wrote", name)


def lockup(theme, ring_colour, ink):
    d, width, xh, asc = wordmark()
    s = 100 / asc * 0.62          # the wordmark's ascender is 62% of the ring's height
    gap = 26
    w = 100 + gap + width * s
    body = (f'<g>{ring_mark(ring_colour, f"oknos-ring-{theme}")}</g>'
            f'<g fill="{ink}" transform="translate({num(100 + gap)} {num(50 + xh * s / 2)}) scale({s:.6f})"><path d="{d}"/></g>')
    return svg(f"0 0 {num(w)} 100", body, "Oknos", w=w * 0.6, h=60)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for t in ("light", "dark"):
        write(f"oknos-mark-{t}.svg", svg("0 0 100 100", ring_mark(AEGEAN[t], f"oknos-ring-{t}"), "Oknos"))
        write(f"oknos-mark-small-{t}.svg", svg("0 0 100 100", ring_mark(AEGEAN[t], f"oknos-ring-s-{t}", small=True), "Oknos"))
        write(f"oknos-lockup-{t}.svg", lockup(t, AEGEAN[t], INK[t]))
        write(f"oknos-o-{t}.svg", svg("8 8 88 104", omicron_ears(INK[t], AEGEAN[t]), "Ὄ"))
        for mood in MOODS:
            write(f"donkey-{mood}-{t}.svg", svg("2 2 96 116", donkey(INK[t], mood), f"The donkey, {mood}"))
    icon = (f'<rect width="128" height="128" rx="28" fill="{AEGEAN["light"]}"/>'
            f'<g transform="translate(64 64) scale(0.86) translate(-52 -60.5)">{omicron_ears(LINEN["light"])}</g>')
    write("oknos-icon.svg", svg("0 0 128 128", icon, "Oknos"))
    write("meander.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="-1 -1 10 10">'
          f'<path d="M0 8 V0 H8 V6 H2 V2 H6 V4 H4 M-1 8 H9" fill="none" stroke="{AEGEAN["light"]}" stroke-width="0.75" '
          'stroke-linecap="square"/></svg>\n')
    (ROOT / "web" / "favicon.svg").write_text(svg("0 0 128 128", icon, "Oknos"), encoding="utf-8", newline="\n")
    print("wrote web/favicon.svg")
    social_preview()


TAGLINE = "Learn Greek the lazy way. Your agent does the rest."
SECOND_LINE = "You plait the rope. The donkey carries the load."


def social_preview():
    """The GitHub social preview (1280×640 PNG), drawn as a page and photographed by headless Chrome."""
    import shutil
    import subprocess

    page = ROOT / ".cache" / "oknos" / "social-preview.html"
    page.write_text(f"""<!doctype html><meta charset="utf-8"><style>
@font-face {{ font-family: "Noto Serif"; src: url("{FONT.as_uri()}"); font-weight: 100 900; }}
html, body {{ margin: 0; width: 1280px; height: 640px; overflow: hidden; background: {PAPER["light"]}; }}
.band {{ position: absolute; left: 0; right: 0; height: 28px; opacity: .55;
         background: url("{(OUT / "meander.svg").as_uri()}") repeat-x center / 28px 28px; }}
.top {{ top: 28px; }} .bottom {{ bottom: 28px; }}
.card {{ position: absolute; left: 112px; right: 112px; top: 0; bottom: 0; display: flex; align-items: center; gap: 72px; }}
.text {{ flex: 1; }}
.text img {{ height: 132px; display: block; margin: 0 0 36px -10px; }}
h1 {{ font: 600 46px/1.2 "Noto Serif", serif; color: {INK["light"]}; margin: 0 0 18px; letter-spacing: -.3px; }}
p {{ font: 400 27px/1.4 "Segoe UI", system-ui, sans-serif; color: #627079; margin: 0; }}
.donkey {{ height: 300px; }}
</style>
<div class="band top"></div><div class="band bottom"></div>
<div class="card"><div class="text"><img src="{(OUT / "oknos-lockup-light.svg").as_uri()}" alt="Oknos">
<h1>{TAGLINE.replace(". ", ".<br>", 1)}</h1><p>{SECOND_LINE}</p></div>
<img class="donkey" src="{(OUT / "donkey-ready-light.svg").as_uri()}" alt=""></div>""", encoding="utf-8")
    candidates = (shutil.which("chrome"), shutil.which("google-chrome"), shutil.which("chromium"),
                  r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    chrome = next((c for c in candidates if c and Path(c).exists()), None)
    if not chrome:
        print(f"social preview: no Chrome found; open {page} at 1280x640 and save it as docs/brand/social-preview.png")
        return
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                    "--window-size=1280,640", f"--user-data-dir={page.parent / 'chrome-profile'}",
                    f"--screenshot={OUT / 'social-preview.png'}", page.as_uri()], capture_output=True, timeout=120)
    print("wrote social-preview.png")


if __name__ == "__main__":
    main()
