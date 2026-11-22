# The Rope of Oknos: three films

Three short painted films (about 45 seconds each) for the app's name. Each is a motion comic: 9–10 illustrations with a slow camera move, cross-fades and captions in simple modern Greek, with a Turkish or English line under them (TR/EN switch), so they also work as reading practice.

| File | Story |
|---|---|
| `1-oknos-and-the-donkey.html` | Pausanias 10.29.1: at Delphi, Polygnotus' painting of the underworld shows Oknos plaiting a rope while a she-donkey eats it as fast as he plaits. Day and night, centuries. Then the brand's turn: the donkey stops and carries the coiled rope, and Oknos's new rope grows. Ends on the logo. |
| `2-oknos-and-his-wife.html` | Pausanias 10.29.2: a hard-working Oknos sells rope and fills a jar with coins; his wife spends them as fast; the painter puts a donkey in her place, and she is not amused. |
| `3-the-dream.html` | New: Oknos dozes under an olive tree and dreams the endless story, faster and faster, until the dream donkey reaches his hands. He wakes with a start; the real donkey is only eating a carrot. |

- **The pictures** (`frames/`, 1200×800 WebP) were drawn by an image model through Codex from written storyboards, with the cast's reference sheets attached so the people stay the same (`docs/brand/characters/`: Oknos, the donkey, the wife), and reviewed one by one; 8 of 28 were drawn again (a halter that made the donkey look led, a rope that changed colour, the donkey eating grass instead of rope). The requests and prompts are in `.cache/oknos/pictures/film/` (not tracked).
- **The player** is `film.js` (shots, camera, fades, flash and shake, captions, pause on tap, replay, reduced motion); `anim.css` is the page style. No libraries and no build: serve the folder (`uv run python -m http.server 8670 --directory docs/brand/animations`) or open a file in a browser.
- For checking one moment: `?t=12` starts at second 12, `?still=12` holds the picture there.
- A voice for the films is part of phase 10 (`docs/prompts/10-voice.md`).

The source text: Pausanias, *Description of Greece* 10.29.1–2. The captions are new Greek written for the app, not quotations.
