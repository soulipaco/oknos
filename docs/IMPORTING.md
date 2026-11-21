# Importing your own material

Oknos can turn material you already have into a **private** content pack. Your own word lists, a coursebook you scanned, course handouts. Private packs live in `content/private/`, which git ignores, so copyrighted material never leaves your computer.

The importer needs to know where things are in your files. You tell it with a small **mapping** file. The mapping describes the *shape* of your material: file names, field names, level names. It never contains the material itself.

If you use an agent, say *"import my material from <folder>"*. The `import-material` skill writes the mapping, runs the import and explains the report. The rest of this page is for doing it by hand.

## 1. What the importer can read

Everything is optional except the pack name. Use the parts you have.

| Part | What it is | Becomes |
|---|---|---|
| `vocabulary` | JSON lists of words with a Greek field and a meaning (`en` and/or `tr`), optionally part of speech, level, document and page | `vocab` items, deduplicated, with provenance |
| `pages` | The running text of a book (`.json` or `.jsonl`), with the unit each page belongs to | links each word to the first unit that uses it (`topics: ["unit:<id>"]`), so new words follow the book |
| `units` | The course outline: one entry per lesson with title, theme, functions, grammar, vocabulary | `units.json` in the pack |
| `raw` | Exercises, tests and answer keys, usually OCR | `raw/<name>.json`: **source prompts, never shown as exercises.** The coach rebuilds them, one lesson at a time, into checkable items in `items/rebuilt-<unit>.json` (say "turn lesson 5 into exercises"; see `.agents/skills/rebuild-imported/SKILL.md`). `oknos raw <pack> --unit <id>` shows them. |
| `audio` | A folder of audio files, and optionally a file of transcripts | files copied to `audio/`; `raw/audio.json` links each file to its transcript and flags it `needs_review`; missing files are listed |

## 2. Write a mapping

Save a JSON file anywhere, for example `my-book.json`. Paths inside it are relative to the folder that holds your material. Field names use dots for nesting (`source.page`). A minimal mapping for a word list:

```json
{
  "pack": {"id": "my-book", "title": {"en": "My coursebook", "tr": "Ders kitabım"}},
  "vocabulary": {
    "file": "words.json",
    "fields": {"greek": "greek", "en": "english", "pos": "type", "level": "level", "doc": "book", "page": "page"},
    "levels": {"Beginner": "A1", "Elementary": "A1", "Pre-intermediate": "A2", "Intermediate": "B1"},
    "pos": {"n": "noun", "v": "verb", "adj": "adj"}
  }
}
```

`src/oknos/importer/mappings/greek-helper.json` is a complete example that uses every part. The model with all options is `src/oknos/importer/mapping.py`. For `raw` sources, `kind_rules` sort entries into `exercise`, `test`, `answer_key` and similar kinds by looking at a field.

## 3. Run it

```bash
uv run oknos import my-book.json --source "C:\path\to\my material"
```

The pack goes to `content/private/<id>/`. The importer refuses to write anywhere git could pick it up. It prints the counts, checks that the pack loads, and writes `IMPORT_REPORT.md` with samples of what was kept and what was dropped. Restart the app, or ask the coach to reload content, and the words appear in your daily sessions.

Running the import again is safe. It rewrites the pack from the source, and it keeps the Turkish overlay (`overlays/tr.json`), which the coach writes. Fixing a meaning in the overlay and importing again updates the items.

## 4. What the importer does to the text

- Reads UTF-8 and normalises to NFC.
- Folds polytonic OCR characters to monotonic: ἄ→ά, ὧν→ων, καὶ→και.
- **Flags OCR damage instead of importing it.** Flagged entries go to `raw/vocab_flagged.json` with the reason:
  - `header_junk`: a page or unit header got into the entry;
  - `latin_mixed`: Latin letters in the Greek;
  - `truncated`: a word cut off or split.
- **Repairs split words** such as `υπογ ράφω` → `υπογράφω`, but only when the dictionary knows the joined word.
- **Dedupes** on lemma + part of speech, merging the meanings and the page references.
- **Adds articles and genders** to nouns from the dictionary data described below. Common-gender nouns get `ο/η`; plural-only nouns get `οι` or `τα`. Nouns the dictionary does not know are listed in the report.

## 5. Dictionary data (optional, needs your OK)

Articles and genders come from the English Wiktionary's Greek entries, as extracted by [kaikki.org](https://kaikki.org/dictionary/Greek/). The licence is CC BY-SA 4.0, and the download is about 210 MB. It is downloaded once into `.cache/oknos/`, which git ignores, and then shrunk to a small index. Download it only if the learner agrees:

```bash
curl -L -o .cache/oknos/kaikki.org-dictionary-Greek.jsonl https://kaikki.org/dictionary/Greek/kaikki.org-dictionary-Greek.jsonl
```

Without it the import still works; nouns just stay without an article.
