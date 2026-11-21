# The name and the look

## Oknos

**Oknos** (Ὄκνος, said "OK-nos") is the figure of sloth and hesitation in Greek myth. Pausanias (10.29.1–2) describes him in Polygnotus' painting in the Lesche of the Cnidians at Delphi: a man seated, plaiting a rope, while a she-donkey beside him eats the rope as fast as he plaits it. The Ionians said of someone labouring at nothing that he was "plaiting the rope of Oknos".

That is the learner's problem: what you learn unravels unless it is reviewed. The app's job is to stop the donkey. The name also says who the app is for: someone who has struggled to keep studying, not a model student.

In ancient Greek ὄκνος first meant shrinking back, hesitation; in modern Greek οκνηρός means lazy.

The app was called **Greek Coach** until 2026-11-21. The old command (`greek-coach`), the old environment variables (`GREEK_COACH_*`), the old database name (`learner/greek-coach.db`) and the old cache folder still work; the files are renamed the first time the app uses them.

Checked on 2026-11-21: no OKNOS trademark found in the US aggregators, and `oknos` was free on PyPI, npm and GitHub. This was not a legal search: the EU and Greek registers (TMview) were not checked.

## The look

The direction is Aegean: paper white, ink, Aegean blue, with olive and terracotta for right and wrong, and a thin meander as an optional motif. The colours are the tokens at the top of `web/style.css` (light and dark). Greek text and the wordmark use Noto Serif; the interface uses the system font.

**Tagline:** "Learn Greek the lazy way. Your agent does the rest." Second line: "You plait the rope. The donkey carries the load."

## Three marks, three roles

| Mark | Role | Files |
|---|---|---|
| **The rope ring** | The logo: the lockup, the README, the social preview, the app bar. Also progress: a stage's ring closes as it is learned, and the session bar is a plaited rope. | `oknos-lockup-{light,dark}.svg`, `oknos-mark-{light,dark}.svg`, `oknos-mark-small-{light,dark}.svg` (16–32 px) |
| **The donkey** | The mascot, standing for the agent ("works like a donkey"). Only where the agent has done something: the coach's note, feedback ready, an empty day, "how it works". Never in the logo. Three moods, shown by the ears. | `donkey-{ready,working,resting}-{light,dark}.svg` |
| **Ὄ** | The app icon and favicon: an omicron whose breathing (short ear) and accent (long ear) are a donkey's ears, splayed sideways. It also reads as the Turkish ö. Linen on an Aegean tile. | `oknos-icon.svg` (also `web/favicon.svg`), `oknos-o-{light,dark}.svg` |

Also: `meander.svg` (a repeatable border tile) and `social-preview.png` (1280×640, for GitHub's social preview).

In a README, show the light or dark file with `<picture>` and `prefers-color-scheme`. Inline in the app, give each rope's mask a unique id.

## Remaking the files

All of them come from one script, so a change is made there, never by hand in an SVG:

```
uv run --with fonttools python scripts/make_brand.py
```

It needs Noto Serif (SIL Open Font Licence) in `.cache/oknos/fonts/`, from <https://github.com/google/fonts/tree/main/ofl/notoserif>; the wordmark is turned into outlines, so the font is not needed to show it. The social preview is photographed by headless Chrome or Edge.
