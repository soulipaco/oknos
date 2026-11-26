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
    for t in ("light", "dark"):
        diagram("how-it-works", t, how_it_works(t))
        diagram("a-day", t, a_day(t))
        diagram("what-you-learn", t, what_you_learn(t))
    developer_diagrams()
    print("the social preview and the README's screenshots: scripts/readme_images.py")


# ---------- the README's diagrams (docs/img/) ----------

UI_FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MUTED = {"light": "#627079", "dark": "#a1a9ae"}
LINE = {"light": "#e3dccd", "dark": "#2e373d"}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def label(x, y, s, t, size=15, weight=400, anchor="middle", colour=None, mono=False):
    family = "ui-monospace, Consolas, monospace" if mono else UI_FONT
    return (f'<text x="{num(x)}" y="{num(y)}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{colour or INK[t]}">{esc(s)}</text>')


def box(x, y, w, h, t, fill=None):
    return (f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" rx="14" '
            f'fill="{fill or LINEN[t]}" stroke="{LINE[t]}" stroke-width="1.5"/>')


def place(x, y, size, view_box, body):
    """Another drawing (the ring, the donkey) placed at x, y in a size×size square."""
    return f'<svg x="{num(x)}" y="{num(y)}" width="{num(size)}" height="{num(size)}" viewBox="{view_box}">{body}</svg>'


def arrow(x1, y1, x2, y2, t, both=False):
    m = f'url(#arrow-{t})'
    start = f' marker-start="{m}"' if both else ""
    return (f'<line x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" stroke="{AEGEAN[t]}" stroke-width="2"'
            f' marker-end="{m}"{start}/>')


def diagram(name, t, parts):
    w, h, body, title = parts
    defs = (f'<defs><marker id="arrow-{t}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 Z" fill="{AEGEAN[t]}"/></marker></defs>')
    top = 40  # the README's own heading names the diagram, so the drawing starts below where a title was
    panel = f'<rect y="{top}" width="{w}" height="{h - top}" rx="20" fill="{PAPER[t]}"/>'
    folder = ROOT / "docs" / "img"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}-{t}.svg").write_text(svg(f"0 {top} {w} {h - top}", defs + panel + body, title), encoding="utf-8", newline="\n")
    print(f"wrote docs/img/{name}-{t}.svg")


def person(x, y, t):
    return (f'<g fill="none" stroke="{INK[t]}" stroke-width="3" stroke-linecap="round">'
            f'<circle cx="{num(x)}" cy="{num(y)}" r="13"/>'
            f'<path d="M{num(x - 24)} {num(y + 46)} C{num(x - 22)} {num(y + 22)} {num(x + 22)} {num(y + 22)} {num(x + 24)} {num(y + 46)}"/></g>')


def how_it_works(t):
    W, H = 900, 420
    b = []
    cols = {"you": 140, "app": 450, "agent": 760}
    for x in cols.values():
        b.append(box(x - 100, 80, 200, 160, t))
    b.append(person(cols["you"], 112, t))
    b.append(place(cols["app"] - 32, 96, 64, "0 0 100 100", ring_mark(AEGEAN[t], f"diag-ring-{t}")))
    b.append(place(cols["agent"] - 34, 92, 68, "2 2 96 116", donkey(INK[t], "working")))
    for key, title, line in (("you", "You", "a few minutes a day"),
                             ("app", "The app", "in your browser"),
                             ("agent", "Your agent", "Claude Code, Codex…")):
        b.append(label(cols[key], 196, title, t, 17, 600))
        b.append(label(cols[key], 218, line, t, 14, colour=MUTED[t]))
    b.append(arrow(246, 150, 344, 150, t, both=True))
    b.append(label(295, 136, "study", t, 13, colour=MUTED[t]))
    b.append(label(295, 172, "no agent", t, 12, colour=MUTED[t]))
    b.append(label(295, 187, "needed", t, 12, colour=MUTED[t]))
    # the learner folder: what the app saves and what the agent reads and writes
    b.append(box(320, 300, 560, 64, t, fill=PAPER[t]))
    b.append(f'<rect x="320" y="300" width="560" height="64" rx="14" fill="none" stroke="{AEGEAN[t]}" stroke-width="1.5" stroke-dasharray="5 5"/>')
    b.append(label(600, 328, "learner/   your progress, your writing, the coach's files", t, 15, 600))
    b.append(label(600, 350, "a folder on your computer", t, 13, colour=MUTED[t]))
    b.append(arrow(450, 244, 450, 294, t, both=True))
    b.append(label(438, 274, "saves your progress", t, 13, anchor="end", colour=MUTED[t]))
    b.append(arrow(760, 244, 760, 294, t, both=True))
    b.append(label(748, 266, "reads the report", t, 13, anchor="end", colour=MUTED[t]))
    b.append(label(748, 284, "writes exercises, feedback, a plan", t, 13, anchor="end", colour=MUTED[t]))
    b.append(label(40, 396, "Everything stays on your computer. No accounts, no cloud, no tracking.", t, 14, anchor="start",
                   colour=MUTED[t]))
    return W, H, "".join(b), "How Oknos works: you study in the app; your agent reads your progress and prepares what comes next"


def a_day(t):
    W, H = 900, 290
    b = []
    x0, x1, y = 90, 810, 130
    b.append(rope(rope_line(x0, x1, y, a=3.2, n=24), 3, 1.4, AEGEAN[t], (x0 - 6, y - 10, x1 - x0 + 12, 20), f"day-rope-{t}"))
    steps = (("Read the chapter", "a dialogue, grammar in", "Turkish or English"),
             ("Today's session", "reviews, verbs, an exam", "task, new words"),
             ("Tap any word", "every Greek word", "has a meaning"),
             ("Once a week", "write an e-mail or", "record yourself"),
             ("The donkey works", "marks your writing,", "prepares tomorrow"))
    for i, (title, l1, l2) in enumerate(steps):
        x = x0 + (x1 - x0) * i / (len(steps) - 1)
        b.append(f'<circle cx="{num(x)}" cy="{y}" r="17" fill="{LINEN[t]}" stroke="{AEGEAN[t]}" stroke-width="2.5"/>')
        b.append(label(x, y + 5.5, str(i + 1), t, 15, 700, colour=AEGEAN[t]))
        b.append(label(x, y + 52, title, t, 15, 600))
        b.append(label(x, y + 74, l1, t, 13, colour=MUTED[t]))
        b.append(label(x, y + 92, l2, t, 13, colour=MUTED[t]))
    b.append(place(x1 - 26, 58, 52, "2 2 96 116", donkey(INK[t], "working")))
    b.append(label(40, 266, "You plait the rope. The donkey carries the load.", t, 14, anchor="start", colour=MUTED[t]))
    return W, H, "".join(b), "A day with Oknos: read, practise, tap words; once a week write or speak; the agent marks and prepares tomorrow"


def what_you_learn(t):
    W, H = 900, 340
    b = []
    levels = (("A1", 13, "reading Greek, meeting people, shops, getting around"),
              ("A2", 12, "a flat, the future, travel, the past, errands, health"),
              ("B1", 1, "towards B1"))
    x, y, step = 62, 110, 22
    i = 0
    for level, count, about in levels:
        start = x + i * step
        for _ in range(count):
            cx = x + i * step
            if i < 4:   # learned stages: the ring is closed
                b.append(place(cx - 10, y - 10, 20, "0 0 100 100", ring_mark(AEGEAN[t], f"wyl-{t}-{i}", small=True)))
            else:
                b.append(f'<circle cx="{num(cx)}" cy="{y}" r="7.5" fill="none" stroke="{FAINT[t]}" stroke-width="2.2" '
                         'stroke-dasharray="1.5 3.5" stroke-linecap="round"/>')
            i += 1
        end = x + (i - 1) * step
        b.append(f'<path d="M{num(start - 8)} {y + 22} v8 H{num(end + 8)} v-8" fill="none" stroke="{LINE[t]}" stroke-width="2"/>')
        b.append(label((start + end) / 2, y + 62, level, t, 15, 700, colour=AEGEAN[t]))
    b.append(label(62, y + 92, "The Oknos book: 26 stages, each with a chapter to read first", t, 14, anchor="start"))
    b.append(label(62, y + 112, "A stage's ring closes as you learn it. A shorter 12-chapter course is there too.", t, 13, anchor="start", colour=MUTED[t]))
    # the exams
    ex = 650
    b.append(arrow(x + 25 * step + 16, y, ex - 8, y - 24, t))
    b.append(arrow(x + 25 * step + 16, y, ex - 8, y + 44, t))
    b.append(box(ex, 62, 210, 52, t))
    b.append(label(ex + 105, 84, "A2 + history", t, 15, 600))
    b.append(label(ex + 105, 103, "for long-term residence", t, 12, colour=MUTED[t]))
    b.append(box(ex, 128, 210, 52, t))
    b.append(label(ex + 105, 150, "Ελληνομάθεια B1", t, 15, 600))
    b.append(label(ex + 105, 169, "with a readiness score", t, 12, colour=MUTED[t]))
    b.append(box(40, 250, 820, 64, t, fill=PAPER[t]))
    b.append(f'<rect x="40" y="250" width="820" height="64" rx="14" fill="none" stroke="{AEGEAN[t]}" stroke-width="1.5" stroke-dasharray="5 5"/>')
    b.append(label(64, 278, "+ your own coursebook", t, 15, 600, anchor="start"))
    b.append(label(64, 299, "Import a book you own and its lessons become the course. It stays private, on your computer.", t, 13,
                   anchor="start", colour=MUTED[t]))
    return W, H, "".join(b), "What you learn: the Oknos book, 26 stages from reading Greek to B1, aimed at the A2 + history and B1 exams"


# ---------- the developer face: how agents build and run Oknos (docs/img/, README and docs/BUILT-WITH-AGENTS.md) ----------

# Who made a thing, one colour each: Claude Code, Codex, a voice service, plain code (no model).
SOFT = {"claude": {"light": "#e2ecf3", "dark": "#213240"}, "codex": {"light": "#e8efd9", "dark": "#243021"},
        "voice": {"light": "#f5e2da", "dark": "#3b2622"}, "code": LINEN}
EDGE = {"claude": AEGEAN, "codex": {"light": "#4f7227", "dark": "#a7c879"},
        "voice": {"light": "#b0503a", "dark": "#e59b85"}, "code": LINE}
WHO = (("claude", "Claude Code (Opus, Sonnet subagents)"), ("codex", "Codex (an image model)"),
       ("voice", "a voice service"), ("code", "plain code, no model"))


def chip(x, y, w, h, text, t, kind="code", size=13, mono=False, sub=None):
    out = (f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" rx="10" fill="{SOFT[kind][t]}" '
           f'stroke="{EDGE[kind][t]}" stroke-width="1.5"/>')
    if sub:
        out += label(x + w / 2, y + h / 2 - 3, text, t, size, 600, mono=mono)
        out += label(x + w / 2, y + h / 2 + 14, sub, t, 11.5, colour=MUTED[t])
    else:
        out += label(x + w / 2, y + h / 2 + size * 0.36, text, t, size, 500, mono=mono)
    return out


def legend(x, y, t, kinds=WHO):
    out = []
    for kind, name in kinds:
        out.append(f'<rect x="{num(x)}" y="{num(y - 11)}" width="14" height="14" rx="4" fill="{SOFT[kind][t]}" '
                   f'stroke="{EDGE[kind][t]}" stroke-width="1.5"/>')
        out.append(label(x + 22, y, name, t, 13, anchor="start", colour=MUTED[t]))
        x += 32 + len(name) * 6.6
    return "".join(out)


def _items(path: Path) -> list:
    import json
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["items"] if isinstance(data, dict) else data


def repo_numbers() -> dict:
    """Everything the developer diagrams count, read from this checkout (nothing typed by hand)."""
    import json
    import re
    import subprocess
    import sys
    open_ = ROOT / "content" / "open"
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True,  # noqa: E731
                                    encoding="utf-8").stdout.strip()
    pictures = json.loads((open_ / "open-pictures" / "pictures" / "pictures.json").read_text(encoding="utf-8"))
    tests = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, capture_output=True,
                           text=True, encoding="utf-8").stdout
    found = re.search(r"(\d+) tests? collected", tests)
    bodies = git("log", "--format=%B%x00").split("\x00")
    commits = [b for b in bodies if b.strip()]
    voice = json.loads((ROOT / "content" / "open-voice" / "index.json").read_text(encoding="utf-8"))
    return {
        "chapters": sum(1 for book in ("oknos-book", "open-book") for f in (open_ / book / "lessons").glob("*.json")
                        if f.stem != "outline"),
        "words": sum(len(_items(f)) for f in (open_ / "oknos-book" / "items").glob("words-*.json")),
        "pictures": len({p["file"] for p in pictures["pictures"]}),
        "scenes": len(list((open_ / "open-book" / "pictures").glob("*.webp"))),
        "frames": len(list((ROOT / "docs" / "brand" / "animations" / "frames").glob("*.webp"))),
        "clips": len(voice["clips"]) + len(list((ROOT / "docs" / "brand" / "animations" / "voice").glob("*.mp3"))),
        "skills": len(list((ROOT / ".agents" / "skills").glob("*/SKILL.md"))),
        "tests": int(found.group(1)) if found else 0,
        "commits": len(commits),
        "with_claude": sum(1 for b in commits if re.search(r"Co-Authored-By: Claude", b, re.I)),
        "since": git("log", "--reverse", "--format=%cs").splitlines()[0],
    }


def by_the_numbers(t, n):
    W, H = 900, 330
    tiles = ((n["chapters"], "chapters in two open books", "drafted and reviewed by Claude"),
             (n["words"], "words with meanings", "written new, by Sonnet"),
             (n["pictures"], "word pictures", "via Codex, each one reviewed"),
             (n["scenes"] + n["frames"], "scenes and film frames", "drawn through Codex too"),
             (n["clips"], "shipped voice clips", "Google Chirp 3 HD, Gemini"),
             (n["skills"], "agent skills", "one copy for every harness"),
             (n["tests"], "tests", "on Ubuntu and Windows in CI"),
             (n["commits"], "commits", "all made with Claude Code" if n["with_claude"] == n["commits"]
              else f"{n['with_claude']} made with Claude Code"))
    b = []
    for i, (value, what, how) in enumerate(tiles):
        x, y = 30 + (i % 4) * 213, 60 + (i // 4) * 116
        b.append(box(x, y, 199, 100, t))
        b.append(label(x + 18, y + 44, f"{value:,}", t, 30, 700, anchor="start", colour=AEGEAN[t]))
        b.append(label(x + 18, y + 68, what, t, 14, 600, anchor="start"))
        b.append(label(x + 18, y + 86, how, t, 12, anchor="start", colour=MUTED[t]))
    b.append(label(30, 312, f"Counted from the repository by scripts/make_brand.py. Commits since {n['since']}.", t, 13,
                   anchor="start", colour=MUTED[t]))
    return W, H, "".join(b), "Oknos by the numbers, counted from the repository"


def harness(t):
    W, H = 900, 520
    b = []
    # the harnesses read one instruction file and one set of skills
    for x, w, name, kind in ((90, 180, "Claude Code", "claude"), (300, 180, "Codex", "codex"),
                             (510, 300, "any agent that reads AGENTS.md", "code")):
        b.append(chip(x, 62, w, 42, name, t, kind, size=15))
        b.append(f'<line x1="{num(x + w / 2)}" y1="104" x2="{num(x + w / 2)}" y2="138" stroke="{LINE[t]}" stroke-width="2"/>')
    b.append(box(90, 138, 720, 104, t))
    b.append(place(104, 150, 64, "2 2 96 116", donkey(INK[t], "working")))
    b.append(label(480, 168, "AGENTS.md  +  13 skills in .agents/skills/", t, 16, 600))
    b.append(label(480, 196, "setup · import-material · coach · capture · mark · tutor · plan", t, 13, mono=True))
    b.append(label(480, 218, "mock-exam · daily-prep · watch · rebuild-imported · write-chapter · podcast", t, 13,
                   mono=True))
    # the files between the agent and the app
    b.append(box(40, 330, 210, 100, t))
    b.append(place(54, 344, 40, "0 0 100 100", ring_mark(AEGEAN[t], f"harness-ring-{t}")))
    b.append(label(104, 366, "The app", t, 16, 600, anchor="start"))
    b.append(label(54, 398, "browser + SQLite", t, 13, anchor="start", colour=MUTED[t]))
    b.append(label(54, 416, "needs no agent to study", t, 13, anchor="start", colour=MUTED[t]))
    b.append(box(340, 330, 220, 100, t, fill=PAPER[t]))
    b.append(f'<rect x="340" y="330" width="220" height="100" rx="14" fill="none" stroke="{AEGEAN[t]}" '
             'stroke-width="1.5" stroke-dasharray="5 5"/>')
    b.append(label(450, 362, "learner/", t, 16, 600, mono=True))
    b.append(label(450, 390, "progress, answers, writing", t, 13, colour=MUTED[t]))
    b.append(label(450, 408, "and the coach's files", t, 13, colour=MUTED[t]))
    b.append(arrow(244, 380, 334, 380, t, both=True))
    b.append(label(289, 368, "saves", t, 12, colour=MUTED[t]))
    b.append(label(289, 400, "takes in", t, 12, colour=MUTED[t]))
    b.append(arrow(410, 324, 410, 248, t))
    b.append(label(400, 278, "reads", t, 13, anchor="end", colour=MUTED[t]))
    b.append(label(400, 296, "oknos report", t, 13, anchor="end", mono=True))
    b.append(arrow(490, 248, 490, 324, t))
    b.append(label(500, 278, "writes packs, feedback, a plan", t, 13, anchor="start", colour=MUTED[t]))
    b.append(label(500, 296, "checked by oknos validate", t, 13, anchor="start", colour=MUTED[t]))
    b.append(box(650, 330, 210, 100, t))
    b.append(label(668, 358, "Scheduled runs", t, 16, 600, anchor="start"))
    b.append(label(668, 382, "daily-prep: tomorrow", t, 13, anchor="start", mono=True))
    b.append(label(668, 401, "watch: exam dates", t, 13, anchor="start", mono=True))
    b.append(label(668, 420, "claude -p · codex exec", t, 12, anchor="start", mono=True, colour=MUTED[t]))
    b.append(arrow(800, 324, 800, 248, t))
    b.append(label(810, 290, "after a yes", t, 12, anchor="start", colour=MUTED[t]))
    b.append(label(40, 478, "The coach writes files, never the database. Nothing about the learner leaves the computer.",
                   t, 14, anchor="start", colour=MUTED[t]))
    return W, H, "".join(b), ("The harness: Claude Code, Codex or any agent reads AGENTS.md and 13 skills, reads the "
                              "learner's report and writes files the app takes in; scheduled runs prepare tomorrow")


def pipelines(t, n):
    W, H = 900, 520
    rows = (("The book", "lessons to read", (("Sonnet drafts", "claude"), ("Opus reviews", "claude"),
                                            ("oknos validate", "code")), n["chapters"], "chapters"),
            ("Word pictures", "a picture per word", (("Claude writes prompts", "claude"), ("image model", "codex"),
                                                     ("Claude reviews each", "claude")), n["pictures"], "pictures"),
            ("Scenes and films", "the story, drawn", (("storyboards, sheets", "claude"), ("image model", "codex"),
                                                      ("reviewed, redrawn", "claude")),
             n["scenes"] + n["frames"], "scenes and frames"),
            ("Voice", "every open text", (("the open Greek text", "code"), ("Chirp 3 HD, Gemini", "voice"),
                                          ("oknos guard", "code")), n["clips"], "shipped clips"),
            ("Film ambience", "wind, cicadas, bells", (("seeded noise, sines", "code"), ("film_ambience.py", "code"),
                                                       ("ffmpeg to mp3", "code")), 3, "loops"),
            ("Podcasts", "a lesson to listen to", (("podcast skill: script", "claude"), ("oknos podcast check", "code"),
                                                   ("cast and voiced", "voice")), None, "on your computer"))
    b = []
    for r, (title, sub, steps, value, unit) in enumerate(rows):
        y = 62 + r * 62
        b.append(label(30, y + 20, title, t, 15, 600, anchor="start"))
        b.append(label(30, y + 38, sub, t, 12, anchor="start", colour=MUTED[t]))
        for i, (text, kind) in enumerate(steps):
            x = 190 + i * 185
            b.append(chip(x, y + 4, 160, 40, text, t, kind, mono=text.startswith(("oknos", "film_"))))
            b.append(arrow(x + 162, y + 24, x + 182, y + 24, t))
        b.append(label(752, y + 22, "local" if value is None else f"{value:,}", t, 18, 700, anchor="start",
                       colour=AEGEAN[t]))
        b.append(label(752, y + 40, unit, t, 12, anchor="start", colour=MUTED[t]))
    b.append(legend(30, 470, t))
    return W, H, "".join(b), ("Who made what: chapters by Claude, pictures through Codex, voices by Google's services, "
                              "the films' background by plain code")


def build_loop(t, n):
    W, H = 900, 490
    b = []
    b.append(box(30, 150, 180, 120, t))
    b.append(place(44, 162, 48, "2 2 96 116", donkey(INK[t], "ready")))
    b.append(label(100, 188, "Coordinating", t, 15, 600, anchor="start"))
    b.append(label(100, 206, "session", t, 15, 600, anchor="start"))
    b.append(label(44, 236, "starts the sessions,", t, 12, anchor="start", colour=MUTED[t]))
    b.append(label(44, 253, "merges what they made", t, 12, anchor="start", colour=MUTED[t]))
    names = ("the book's voice", "word pictures", "podcast lessons", "this page")
    for i, name in enumerate(names):
        y = 66 + i * 76
        b.append(arrow(212, 210, 262, y + 30, t))
        b.append(chip(266, y, 210, 60, name, t, "claude", sub="own worktree and branch"))
        b.append(arrow(478, y + 30, 540, 210, t))
    b.append(box(544, 140, 160, 140, t))
    b.append(label(624, 170, "Checks", t, 15, 600))
    for i, c in enumerate(("oknos guard", "pytest", "oknos validate")):
        b.append(label(624, 200 + i * 24, c, t, 13, mono=True))
    b.append(arrow(706, 210, 736, 210, t))
    b.append(rope(rope_line(744, 870, 210, a=3, n=8), 3, 1.4, AEGEAN[t], (738, 198, 138, 24), f"build-rope-{t}"))
    b.append(label(807, 180, "main", t, 15, 600, mono=True))
    b.append(label(807, 244, "fast-forward only", t, 12, colour=MUTED[t]))
    b.append(arrow(807, 262, 807, 336, t))
    b.append(chip(700, 340, 170, 60, "GitHub CI", t, "code", sub="Ubuntu and Windows"))
    b.append(label(690, 366, "push only when", t, 12, anchor="end", colour=MUTED[t]))
    b.append(label(690, 383, "the maintainer asks", t, 12, anchor="end", colour=MUTED[t]))
    b.append(label(30, 412, "Examples of side sessions; a session that writes code", t, 13, anchor="start", colour=MUTED[t]))
    b.append(label(30, 430, "never shares files with another one at the same time.", t, 13, anchor="start",
                   colour=MUTED[t]))
    b.append(label(30, 466, f"{n['commits']} commits since {n['since']}, {n['with_claude']} of them made with Claude Code. "
                   "The guard keeps learner data and private content out of git.", t, 13, anchor="start",
                   colour=MUTED[t]))
    return W, H, "".join(b), ("How Oknos is built: one coordinating Claude Code session starts side sessions, each in "
                              "its own git worktree; checks pass, main moves forward, CI runs on Ubuntu and Windows")


def developer_diagrams():
    n = repo_numbers()
    print("counted:", n)
    for t in ("light", "dark"):
        diagram("by-the-numbers", t, by_the_numbers(t, n))
        diagram("harness", t, harness(t))
        diagram("who-made-what", t, pipelines(t, n))
        diagram("how-it-is-built", t, build_loop(t, n))


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["developer"]:
        developer_diagrams()   # needs no font: uv run --no-sync python scripts/make_brand.py developer
    else:
        main()
