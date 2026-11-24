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
    levels = (("A1", 7, "reading Greek, first sentences, verbs, shops, getting around"),
              ("A2", 4, "the future, the past, daily life in Greece"),
              ("B1", 1, "towards B1"))
    x, y, step = 70, 110, 47
    i = 0
    for level, count, about in levels:
        start = x + i * step
        for _ in range(count):
            cx = x + i * step
            if i < 3:   # learned stages: the ring is closed
                b.append(place(cx - 19, y - 19, 38, "0 0 100 100", ring_mark(AEGEAN[t], f"wyl-{t}-{i}", small=True)))
            else:
                b.append(f'<circle cx="{num(cx)}" cy="{y}" r="15" fill="none" stroke="{FAINT[t]}" stroke-width="3" '
                         'stroke-dasharray="2 5" stroke-linecap="round"/>')
            i += 1
        end = x + (i - 1) * step
        b.append(f'<path d="M{num(start - 12)} {y + 32} v8 H{num(end + 12)} v-8" fill="none" stroke="{LINE[t]}" stroke-width="2"/>')
        b.append(label((start + end) / 2, y + 62, level, t, 15, 700, colour=AEGEAN[t]))
    b.append(label(70, y + 92, "12 stages of an open course, each with a chapter to read first", t, 14, anchor="start"))
    b.append(label(70, y + 112, "A stage's ring closes as you learn it.", t, 13, anchor="start", colour=MUTED[t]))
    # the exams
    ex = 650
    b.append(arrow(x + 11 * step + 26, y, ex - 8, y - 24, t))
    b.append(arrow(x + 11 * step + 26, y, ex - 8, y + 44, t))
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
    return W, H, "".join(b), "What you learn: 12 stages from reading Greek to B1, aimed at the A2 + history and B1 exams"


if __name__ == "__main__":
    main()
