# Pictures: the style guide

Pictures help the words stick: a word card shows its picture, and "pick the picture" exercises use them. They are made with an image model (through Codex, on the maintainer's machine), reviewed by Claude Code and then by the maintainer, and only accepted ones enter the app. This file is the brief every picture follows; `docs/brand/README.md` has the rest of the look.

## The look

- **Flat illustration** with a **thick, even ink outline** (like the donkey in `docs/brand/`), rounded line ends, no gradients, no photographic detail, no 3D render, very little or no shading.
- **One subject**, centred, filling about 70% of the square, seen from a friendly three-quarter or side view. No background scene for objects; a simple, cropped setting only for places (a room, a shop front).
- **Palette** (the app's tokens; use only these, plus white):
  - ink `#1e2a32` for every outline;
  - paper `#f6f2ea` as the background (a plain square, edge to edge);
  - Aegean `#1f5f8b` and its light tint `#e2ecf3`;
  - olive `#4f7227` and its tint `#e8efd9`;
  - terracotta `#b0503a` and its tint `#f5e2da`;
  - a warm yellow `#e8b64a` only where the thing really is yellow (a taxi, a lemon, bread crust).
- **Greek where it is natural**: a Greek pharmacy has the green cross, a bus is a city bus, coffee is a Greek coffee cup (μπρίκι or a small cup), bread is a round village loaf. Never a flag, a monument or a cliché unless the word is about it.

## Never

- **No text, letters, numbers or logos** anywhere in the picture: no shop signs with words, no "TAXI" on the roof, no labels on packets. Image models garble Greek letters, and the app shows the word itself.
- No real people, no faces of anyone identifiable, no brand, no copyrighted character or style of a named artist.
- No hands holding things unless the word needs it; no people at all for objects.
- No cartoon faces on objects, food or weather (a smiling sun, cloud, moon or fish): eyes and a mouth belong to people and animals only.
- Nothing beside the subject that could be its own answer (a star next to the moon, olives on a leaf): the picture must not also mean another word.

## People (verbs and jobs, from 2026-11-22)

Some words need a person: an action (τρώω, κολυμπάω, μαγειρεύω) or a job (ο γιατρός, ο χασάπης). Then:

- **One person** (two only when the word is about talking to someone), adult, full body or from the waist up, doing the one thing the word says, so clearly that the picture could not mean another verb.
- **Simple, friendly figures** in the same flat style and outline: a round head, **two dot eyes and a small line for the mouth, no other facial detail**, simple hair shapes, everyday clothes from the palette. They must not look like any real or famous person.
- **Varied people** across the set: women and men, different ages and skin tones (warm browns and beiges, outlined like everything else).
- The props of a job say what it is (a white coat and a stethoscope, a butcher's apron and a counter), never a name tag or a sign.

## Files

- Square PNG at 1024×1024 from the model. The app uses a 512×512 WebP made from it once accepted.
- One file per picture: `<id>.png`, where the id is the word's item key with `/` replaced by `--` (`open-book--ch05-psomi.png`).
- Every request, its prompt and its status are in a `requests.json` next to the pictures: `todo` → `generated` → `accepted` or `rejected` (with the reason). A rejected picture is asked for again with a corrected prompt.

## The prompt

Each prompt is this template with the subject filled in:

> Flat vector-style illustration of {subject}. Thick even dark-navy outline (#1e2a32), rounded line ends, flat colours only from this palette: Aegean blue #1f5f8b, light blue #e2ecf3, olive #4f7227, light olive #e8efd9, terracotta #b0503a, light terracotta #f5e2da, warm yellow #e8b64a, white. Plain warm paper background #f6f2ea filling the square. Single subject centred, about 70% of the frame, friendly three-quarter view. No text, no letters, no numbers, no logos, no people. Minimal, calm, friendly, consistent icon-like style for a language-learning app.

For a word that needs a person, the template's "no people" becomes: "One simple friendly adult figure with dot eyes and a small mouth line, no other facial detail, not resembling any real person."

The subject line says what it is and, where it matters, the Greek touch ("a round Greek village loaf of bread with a scored crust", "a Greek pharmacy shop front with a green cross sign and no lettering").

## The pipeline

1. **Requests.** A batch of about 24 words goes into a `requests.json` in a working folder under `.cache/oknos/` (never tracked): the word's item key, the Greek, the meaning and a `subject` line written for it. Words that need a person (verbs, jobs) follow the People rules above and are marked `"people": true`.
2. **Generation.** Claude Code starts Codex headless with a short brief that points at this guide and the request file: `codex exec --cd <repo> --sandbox workspace-write "Follow the task in <brief>"`, in the background. Codex saves one PNG per request and marks it `generated`, with the prompt it used. A batch of 24 takes about 30 minutes; the pilot's 12 used about 7% of a ChatGPT Plus five-hour Codex limit. Batches can run one after another unattended (a small runner under `.cache/oknos/pictures/` that stops when Codex reports its usage limit); on 2026-11-22 one five-hour limit covered about 100 pictures.
3. **Review.** Claude Code looks at every picture against this guide (text or letters, a person, wrong object, odd perspective, off-palette) and marks it `accepted` or `rejected` with the reason; the maintainer can overrule. Rejected ones go back with a corrected subject.
4. **Taking them in.** `uv run --with pillow python scripts/pictures.py <requests.json>` makes a 512×512 WebP of every accepted picture in `content/open/open-pictures/pictures/` and records it (word, file, item, prompt) in `pictures.json`. About 15 KB each.

## In the app

- **Scenes** (pictures of a moment of the story, with its people) follow `docs/brand/CHARACTERS.md` and live in the book's own pack (`content/open/open-book/pictures/`, 768×768 WebP); a dialogue shows one with `picture`, a task with `stimulus.pictures`.

- A picture belongs to a **word**, not to one item: every pack's vocab item with the same word (with or without its article) shows it, so the maintainer's book gets the open pictures too (`packs.picture_url`).
- The **learn card** of a new word shows its picture; after any answer the picture appears under the feedback; "what is it in Greek?" shows it with the meaning.
- **Pick the picture** (`direction: el_picture`): for a word already seen, four in ten of its "what does it mean?" cards become "which picture is it?": the Greek word (and its sound), four pictures.
