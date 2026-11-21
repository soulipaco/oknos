---
name: import-material
description: Import someone's own Greek learning material (word lists, a scanned coursebook, handouts, audio, an earlier project) as a private content pack. Use when someone says "import my old project", "import this book", "add my word list", "use my course material", "eski materyalimi ekle", or points at a folder of their own material.
---

# Import my material

Turn material the learner already has into a private pack in `content/private/<id>/`. The full guide is `docs/IMPORTING.md`; read it first. This file is the checklist.

## Rules

- **Copyright.** Imported material is private. Write only to `content/private/` (or `learner/generated/`), which git ignores. Never copy any of it into a tracked file, a test, an example or a commit. The importer refuses tracked folders; do not work around that.
- **Learner or maintainer?** With a learner (see `AGENTS.md`), do everything yourself and explain the result in plain words. Never ask them to edit the mapping.
- **Downloads need a yes.** The dictionary data for articles and genders is about 210 MB from kaikki.org (`docs/IMPORTING.md` §5). Ask before downloading it. If they say no, import without it.

## Steps

1. **Look at the material, read-only.** List the folder and open a few files to find the word lists, the lesson outline, the book text, exercises and audio. Count the entries, and note the field names, the encoding, and anything that looks like OCR damage.
2. **Write a mapping** in the scratch area, not in the repo. Copy the shape of `src/oknos/importer/mappings/greek-helper.json` and keep only the parts that exist. Paths are relative to the material folder. A mapping for a common, public format may be added to `src/oknos/importer/mappings/` only if it holds no personal paths or content.
3. **Run** `uv run oknos import <mapping> --source "<folder>"`. A non-zero exit means the pack has problems; read them and fix the mapping.
4. **Check the result.** Read `content/private/<id>/IMPORT_REPORT.md`:
   - What fraction was flagged, and does a sample of flagged entries really look damaged?
   - Do the merged duplicates look right?
   - How many nouns have no gender?
   - Do the kept and dropped raw samples make sense?

   Open 10 random vocab items and confirm each meaning matches its Greek. Run `uv run oknos validate content/private/<id>`.
5. **Turkish meanings** (when the learner's UI language is Turkish). Write them into `content/private/<id>/overlays/tr.json` as `{"by": "coach", "verified": false, "words": {"<folded lemma>|<pos>": {"tr": "..."}}}`, starting with the A1 words, then import again. Mark anything uncertain in a `"doubtful"` list.
6. **Make it visible**: if the app is running, `POST /api/reload` (or restart it with `uv run oknos stop` then `start`). Start a session and confirm words from the new pack appear among the new words.
7. **Confirm nothing private is tracked**: `git status --short` must not list anything under `content/private/`.
8. **Tell the learner** in two or three sentences: how many words were imported, what was set aside and why, and that the exercises were kept as material for the coach to rebuild later.
