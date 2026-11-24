"""The import pipeline: someone's material + a mapping -> a private content pack and a report.

Steps (docs/SPEC.md §10): read UTF-8 and normalise to NFC monotonic; flag OCR damage instead of
importing it silently; dedupe the vocabulary on lemma + part of speech, merging senses and
sources; enrich nouns with gender and article; link words to the units they appear in; write
the course outline as units.json; keep exercises and audio as raw/ source material.
"""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from oknos import greek, paths
from oknos.importer import enrich
from oknos.importer.mapping import Mapping, RawSource, get

LEVEL_ORDER = {"A1": 0, "A2": 1, "B1": 2}
_TRANSLIT = dict(zip("αβγδεζηθικλμνξοπρσςτυφχψω", ["a", "v", "g", "d", "e", "z", "i", "th", "i", "k", "l", "m", "n", "x", "o", "p", "r", "s", "s", "t", "y", "f", "ch", "ps", "o"]))


class ImportError_(RuntimeError):
    """A problem the person running the import has to fix (bad path, bad mapping)."""


@dataclass
class Report:
    counts: dict[str, Any] = field(default_factory=dict)
    samples: dict[str, list] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _slug(text: str) -> str:
    base = greek.fold(text)
    out = "".join(_TRANSLIT.get(c, c if c.isascii() and c.isalnum() else "-") for c in base)
    return re.sub(r"-+", "-", out).strip("-")[:40] or "x"


def _read(path: Path) -> Any:
    if not path.is_file():
        raise ImportError_(f"the mapping points to {path}, which does not exist")
    if path.suffix == ".jsonl":
        with path.open(encoding="utf-8-sig") as f:
            return [json.loads(line) for line in f if line.strip()]
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _list(data: Any, dotted: str) -> list:
    value = get(data, dotted) if dotted else data
    if not isinstance(value, list):
        raise ImportError_(f"expected a list at '{dotted or '(top level)'}'")
    return value


def _clean(text: Any) -> str:
    if not isinstance(text, str):
        return ""
    return " ".join(greek.to_monotonic(text).split())


def check_output_dir(out: Path) -> Path:
    """Imports may only write where git will never pick them up."""
    out = out.resolve()
    allowed = [(paths.CONTENT_DIR / "private").resolve(), (paths.learner_dir() / "generated").resolve()]
    if not any(out == a or a in out.parents for a in allowed):
        raise ImportError_(
            f"{out} is not inside content/private/ or learner/generated/. Imported material may be "
            "copyrighted, so it is only written to folders git ignores."
        )
    return out


# ---------- vocabulary ----------

def _unit_index(mapping: Mapping, source: Path, order_of: dict[str, int]) -> dict[str, str]:
    """Folded word -> the earliest unit whose pages contain it."""
    if not mapping.pages:
        return {}
    first: dict[str, tuple[int, str]] = {}
    for page in _list(_read(source / mapping.pages.file), mapping.pages.list):
        unit = get(page, mapping.pages.fields.get("unit"))
        text = get(page, mapping.pages.fields.get("text"))
        if not unit or not isinstance(text, str) or unit not in order_of:
            continue
        rank = order_of[unit]
        for w in greek.words(greek.to_monotonic(text)):
            key = greek.fold(w)
            if len(key) > 2 and (key not in first or rank < first[key][0]):
                first[key] = (rank, unit)
    return {k: u for k, (_, u) in first.items()}


def repair_split(el: str, known: set[str]) -> str:
    """Join OCR-split words (υπογ ράφω -> υπογράφω) when the joined word is in the dictionary."""
    toks = el.split(" ")
    i, changed = 0, False
    while i < len(toks) - 1:
        joined = toks[i] + toks[i + 1]
        if joined in known and (toks[i] not in known or toks[i + 1] not in known):
            toks[i:i + 2] = [joined]
            changed = True
        else:
            i += 1
    return " ".join(toks) if changed else el


def import_vocabulary(mapping: Mapping, source: Path, out: Path, report: Report, units: dict[str, str],
                      index: dict | None) -> list[dict]:
    vs = mapping.vocabulary
    assert vs is not None
    data = _read(source / vs.file)
    rows = [row for lst in vs.lists for row in _list(data, lst)]
    report.counts["vocab_rows_read"] = len(rows)
    f = vs.fields

    known = {k.split("|", 1)[0] for k in index["glosses"]} | set(index["nouns"]) if index else set()
    flagged: list[dict] = []
    merged: dict[tuple[str, str], dict] = {}
    duplicates = repaired = 0
    for row in rows:
        el = _clean(get(row, f.get("greek")))
        fixed = repair_split(el, known) if known else el
        repaired += fixed != el
        el = fixed
        en = " ".join(str(get(row, f.get("en"), "") or "").split())
        tr = " ".join(str(get(row, f.get("tr"), "") or "").split())
        pos_raw = str(get(row, f.get("pos"), "") or "").strip()
        pos = vs.pos.get(pos_raw, pos_raw or None)
        level = vs.levels.get(str(get(row, f.get("level"), "")), vs.default_level)
        src = {k: get(row, f[k]) for k in ("doc", "page") if f.get(k) and get(row, f[k]) is not None}
        flags = greek.damage_flags(el, en)
        if flags == ["truncated"] and el in known:
            flags = []  # a real word such as ροζ or κιτ
        if not (en or tr):
            flags.append("no_meaning")
        if flags:
            flagged.append({"greek": el, "en": en, "pos": pos, "level": level, "source": src, "flags": flags,
                            "source_id": get(row, f.get("id"))})
            continue
        lemma = greek.strip_article(el)
        key = (greek.fold(lemma), pos or "")
        if key in merged:
            duplicates += 1
            entry = merged[key]
            for sense in re.split(r"\s*[;,]\s*", en):
                if sense and sense not in entry["senses"]:
                    entry["senses"].append(sense)
            if src and src not in entry["sources"]:
                entry["sources"].append(src)
            if LEVEL_ORDER[level] < LEVEL_ORDER[entry["level"]]:
                entry["level"] = level
            continue
        merged[key] = {"el": el, "lemma": lemma, "pos": pos, "level": level, "tr": tr or None,
                       "senses": [s for s in re.split(r"\s*;\s*", en) if s], "sources": [src] if src else []}

    report.counts["vocab_flagged"] = len(flagged)
    report.counts["vocab_flag_reasons"] = dict(Counter(fl for e in flagged for fl in e["flags"]))
    report.counts["vocab_duplicates_merged"] = duplicates
    report.counts["vocab_split_words_repaired"] = repaired
    report.samples["vocab_flagged"] = flagged[:: max(1, len(flagged) // 8)][:8]

    # Turkish overlay written by the coach; survives re-imports (SPEC §10 step 5).
    overlay_file = out / "overlays" / "tr.json"
    overlay = json.loads(overlay_file.read_text(encoding="utf-8")) if overlay_file.is_file() else {}
    overlay_words = overlay.get("words", {}) if isinstance(overlay, dict) else {}

    items: list[dict] = []
    used_ids: set[str] = set()
    no_gender: list[str] = []
    gendered = tr_applied = linked = 0
    for (folded, pos), e in merged.items():
        item_id = f"v-{_slug(e['lemma'])}" + (f"-{_slug(pos)}" if pos and pos != "noun" else "")
        n = 2
        while item_id in used_ids:
            item_id, n = f"{item_id.rsplit('~', 1)[0]}~{n}", n + 1
        used_ids.add(item_id)
        item: dict[str, Any] = {"id": item_id, "type": "vocab", "skill": "vocab", "level": e["level"],
                                "el": e["el"], "lemma": e["lemma"]}
        if pos:
            item["pos"] = pos
        if pos == "noun" and index and " " not in e["lemma"]:
            gender, article = enrich.noun_gender(index, e["lemma"])
            if article:
                item["el"] = f"{article} {e['lemma']}"
                if gender:
                    item["gender"] = gender
                gendered += 1
            else:
                no_gender.append(e["lemma"])
        elif pos == "noun" and " " not in e["lemma"]:
            no_gender.append(e["lemma"])
        if e["senses"]:
            item["en"] = "; ".join(e["senses"][:4])
        fix = overlay_words.get(f"{folded}|{pos}") or {}
        # A coach's correction of the source itself (a word list that gives κύριος only as the
        # adjective "main", when the lesson teaches ο κύριος, "Mr"): it replaces what the source says,
        # and the item keeps its id so its history and flags stay with it.
        for key in ("el", "pos", "gender", "en"):
            if fix.get(key):
                item[key] = fix[key]
        tr_value = e["tr"] or fix.get("tr")
        if tr_value:
            item["tr"] = tr_value
            tr_applied += 0 if e["tr"] else 1
        unit = units.get(folded)
        item["topics"] = [f"unit:{unit}"] if unit else []
        linked += 1 if unit else 0
        src: dict[str, Any] = dict(e["sources"][0]) if e["sources"] else {}
        if len(e["sources"]) > 1:
            src["also"] = e["sources"][1:]
        if not e["tr"] and tr_value:
            src["tr"] = "coach, unverified"
        item["source"] = src or {"doc": "unknown"}
        items.append(item)

    report.counts["vocab_items"] = len(items)
    report.counts["vocab_by_level"] = dict(Counter(i["level"] for i in items))
    report.counts["vocab_by_pos"] = dict(Counter(i.get("pos") or "?" for i in items))
    report.counts["nouns_with_gender"] = gendered
    report.counts["nouns_without_gender"] = len(no_gender)
    report.counts["vocab_linked_to_unit"] = linked
    report.counts["vocab_tr_from_overlay"] = tr_applied
    report.samples["nouns_without_gender"] = no_gender[:40]
    if index is None:
        report.notes.append("No dictionary data was available, so nouns have no article. See docs/IMPORTING.md.")

    (out / "raw").mkdir(parents=True, exist_ok=True)
    (out / "raw" / "vocab_flagged.json").write_text(json.dumps(flagged, ensure_ascii=False, indent=1), encoding="utf-8")
    return items


# ---------- units, raw material, audio ----------

def import_units(mapping: Mapping, source: Path, report: Report) -> list[dict]:
    us = mapping.units
    assert us is not None
    f = us.fields
    units = []
    for row in _list(_read(source / us.file), us.list):
        def text_list(key: str) -> list[str]:
            value = get(row, f.get(key), []) or []
            return [_clean(v) for v in value if isinstance(v, str) and v.strip()]
        start, end = get(row, f.get("page_start")), get(row, f.get("page_end"))
        units.append({
            "id": str(get(row, f["id"])),
            "order": int(get(row, f.get("order"), len(units))),
            "title": _clean(get(row, f.get("title"), "")) or str(get(row, f["id"])),
            "theme": _clean(get(row, f.get("theme"), "")) or None,
            "pages": [start, end] if start is not None or end is not None else None,
            "is_review": bool(get(row, f.get("is_review"), False)),
            "review_range": [str(v) for v in (get(row, f.get("review_range"), []) or [])],
            "functions": text_list("functions"),
            "grammar": text_list("grammar"),
            "vocabulary": text_list("vocabulary"),
        })
    units.sort(key=lambda u: u["order"])
    report.counts["units"] = len(units)
    return units


def _kind(row: dict, rs: RawSource) -> str:
    for rule in rs.kind_rules:
        value = get(row, rule["field"])
        if "equals" in rule and value == rule["equals"]:
            return rule["kind"]
        if "contains" in rule and isinstance(value, str) and rule["contains"] in value:
            return rule["kind"]
    return rs.default_kind


def _instruction(text: str) -> str:
    """The exercise's instruction line: up to the first full stop or colon, at most 160 chars."""
    m = re.match(r"^\W*\d*\s*(.{8,160}?[.:;!;])", text)
    return (m.group(1) if m else text[:120]).strip()


def import_raw(rs: RawSource, source: Path, out: Path, report: Report) -> None:
    f = rs.fields
    rows = _list(_read(source / rs.file), rs.list)
    kept, dropped = [], []
    seen: set[str] = set()
    for row in rows:
        original = get(row, f.get("text"), "") or ""
        text = _clean(original)
        flags = list(get(row, f.get("flags"), []) or [])
        if original != greek.nfc(original) or any(0x1F00 <= ord(c) <= 0x1FFF for c in original):
            flags.append("polytonic_folded")
        if sum(1 for w in greek.words(text) if sum(1 for c in greek.nfc(w) if c in "άέήίόύώΐΰ") >= 2) >= 2:
            flags.append("glued_words")
        greek_letters = sum(1 for c in text if re.match(greek.GREEK_LETTER, c))
        doc = get(row, f.get("doc"))
        entry = {
            "id": str(get(row, f["id"])),
            "unit": get(row, f.get("unit")),
            "page": get(row, f.get("page")),
            "doc": Path(str(doc)).name if doc else None,  # never keep absolute paths
            "marker": get(row, f.get("marker")),
            "type": get(row, f.get("type")),
            "skill": get(row, f.get("skill")),
            "kind": _kind(row, rs),
            "instruction": _instruction(text),
            "text": text,
            "flags": sorted(set(flags)),
        }
        key = greek.fold(text)
        reason = None
        if greek_letters < rs.min_greek_letters:
            reason = "too_short"
        elif greek.greek_share(text) < rs.min_greek_share:
            reason = "mostly_not_greek"
        elif key in seen:
            reason = "duplicate"
        if reason:
            dropped.append({**entry, "dropped": reason})
            continue
        seen.add(key)
        kept.append(entry)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    (out / "raw" / f"{rs.name}.json").write_text(json.dumps(kept, ensure_ascii=False, indent=1), encoding="utf-8")
    report.counts[f"raw_{rs.name}"] = {
        "read": len(rows), "kept": len(kept), "dropped": len(dropped),
        "dropped_by_reason": dict(Counter(d["dropped"] for d in dropped)),
        "kept_by_kind": dict(Counter(k["kind"] for k in kept)),
        "kept_flags": dict(Counter(fl for k in kept for fl in k["flags"])),
    }
    step = lambda xs: xs[:: max(1, len(xs) // 5)][:5]  # noqa: E731
    report.samples[f"raw_{rs.name}_kept"] = [{k: (v[:200] if k == "text" else v) for k, v in e.items()} for e in step(kept)]
    report.samples[f"raw_{rs.name}_dropped"] = [{k: (v[:200] if k == "text" else v) for k, v in e.items()} for e in step(dropped)]


def import_audio(mapping: Mapping, source: Path, out: Path, report: Report) -> None:
    au = mapping.audio
    assert au is not None
    audio_dir = source / au.dir
    files = {greek.nfc(p.name): p for p in sorted(audio_dir.glob("*")) if p.suffix.lower() in (".mp3", ".wav", ".ogg")}
    transcripts: dict[str, str] = {}
    if au.transcripts:
        data = _read(source / au.transcripts)
        if isinstance(data, dict):
            transcripts = {greek.nfc(k): v for k, v in data.items() if isinstance(v, str)}
        else:
            tf = au.transcript_fields
            transcripts = {greek.nfc(str(get(r, tf["file"]))): get(r, tf["text"]) for r in data}
    (out / "audio").mkdir(parents=True, exist_ok=True)
    entries = []
    for name, path in files.items():
        target = out / "audio" / name
        if not target.exists() or target.stat().st_size != path.stat().st_size:
            shutil.copy2(path, target)
        entries.append({"file": f"audio/{name}", "transcript": _clean(transcripts.get(name, "")) or None,
                        "transcript_source": "speech-to-text, noisy" if name in transcripts else None,
                        "status": "needs_review"})
    missing = sorted(set(transcripts) - set(files), key=lambda n: (len(n), n))
    no_transcript = sorted(set(files) - set(transcripts))
    (out / "raw").mkdir(parents=True, exist_ok=True)
    (out / "raw" / "audio.json").write_text(json.dumps({"files": entries, "missing": missing}, ensure_ascii=False, indent=1), encoding="utf-8")
    report.counts["audio"] = {"files_copied": len(entries), "transcripts": len(transcripts),
                              "transcripts_without_file": len(missing), "files_without_transcript": len(no_transcript)}
    report.samples["audio_missing"] = missing


# ---------- the whole run ----------

def write_report(out: Path, mapping: Mapping, report: Report) -> None:
    (out / "import_report.json").write_text(
        json.dumps({"pack": mapping.pack.id, "counts": report.counts, "samples": report.samples, "notes": report.notes},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    c = report.counts
    lines = [f"# Import report: {mapping.pack.id}", "",
             "Generated by `oknos import`. This folder is private (gitignored); keep it that way.", ""]
    if "vocab_rows_read" in c:
        lines += ["## Vocabulary", "",
                  f"- Rows read: {c['vocab_rows_read']}",
                  f"- Flagged as OCR damage and kept out (see `raw/vocab_flagged.json`): {c['vocab_flagged']} {c['vocab_flag_reasons']}",
                  f"- Words split by OCR and joined again using the dictionary: {c['vocab_split_words_repaired']}",
                  f"- Duplicates merged into another entry: {c['vocab_duplicates_merged']}",
                  f"- Vocabulary items written: {c['vocab_items']}; by level {c['vocab_by_level']}; by part of speech {c['vocab_by_pos']}",
                  f"- Nouns with an article from Wiktionary: {c['nouns_with_gender']}; without: {c['nouns_without_gender']}",
                  f"- Words linked to a unit of the book: {c['vocab_linked_to_unit']}",
                  f"- Turkish meanings from the coach overlay (unverified): {c['vocab_tr_from_overlay']}", ""]
        lines += ["Flagged samples:", ""] + [f"- `{e['greek']}` / {e['en']} → {', '.join(e['flags'])}" for e in report.samples["vocab_flagged"]] + [""]
        lines += ["Nouns without gender (first 40): " + ", ".join(report.samples["nouns_without_gender"]), ""]
    if "units" in c:
        lines += ["## Units", "", f"- Units in `units.json`: {c['units']}", ""]
    for key in [k for k in c if k.startswith("raw_")]:
        name = key[4:]
        r = c[key]
        lines += [f"## Raw: {name}", "",
                  f"- Read {r['read']}, kept {r['kept']} as source prompts, dropped {r['dropped']} {r['dropped_by_reason']}",
                  f"- Kept by kind: {r['kept_by_kind']}", f"- Flags on kept items: {r['kept_flags']}", "",
                  "Kept samples:", ""]
        lines += [f"- `{e['id']}` ({e['kind']}, p. {e['page']}): {e['text'][:140]}" for e in report.samples[f"raw_{name}_kept"]]
        lines += ["", "Dropped samples:", ""]
        lines += [f"- `{e['id']}` ({e['dropped']}): {e['text'][:140]}" for e in report.samples[f"raw_{name}_dropped"]] + [""]
    if "audio" in c:
        a = c["audio"]
        lines += ["## Audio", "",
                  f"- Files copied to `audio/` (all `needs_review`): {a['files_copied']}",
                  f"- Transcripts: {a['transcripts']}; transcripts whose audio file is missing: {a['transcripts_without_file']}",
                  f"- Audio files with no transcript: {a['files_without_transcript']}", "",
                  "Missing audio files: " + ", ".join(report.samples["audio_missing"]), ""]
    if report.notes:
        lines += ["## Notes", ""] + [f"- {n}" for n in report.notes] + [""]
    (out / "IMPORT_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def run(mapping: Mapping, source: Path, out: Path | None = None) -> tuple[Path, Report]:
    source = source.resolve()
    if not source.is_dir():
        raise ImportError_(f"the source folder {source} does not exist")
    out = check_output_dir(out or paths.CONTENT_DIR / "private" / mapping.pack.id)
    out.mkdir(parents=True, exist_ok=True)
    report = Report()

    units: list[dict] = []
    if mapping.units:
        units = import_units(mapping, source, report)
        (out / "units.json").write_text(json.dumps(units, ensure_ascii=False, indent=1), encoding="utf-8")
    order_of = {u["id"]: u["order"] for u in units}

    item_files: dict[str, list[dict]] = defaultdict(list)
    if mapping.vocabulary:
        index = enrich.load_index()
        unit_of = _unit_index(mapping, source, order_of)
        for item in import_vocabulary(mapping, source, out, report, unit_of, index):
            item_files[f"vocab-{item['level'].lower()}"].append(item)
    for rs in mapping.raw:
        import_raw(rs, source, out, report)
    if mapping.audio:
        import_audio(mapping, source, out, report)

    items_dir = out / "items"
    items_dir.mkdir(exist_ok=True)
    for old in items_dir.glob("vocab-*.json"):
        old.unlink()
    for name, items in item_files.items():
        (items_dir / f"{name}.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")

    visibility = "generated" if (paths.learner_dir() / "generated").resolve() in out.parents else "private"
    manifest = {
        "id": mapping.pack.id,
        "title": mapping.pack.title.model_dump(exclude_none=True),
        "version": 1,
        "levels": mapping.pack.levels,
        "visibility": visibility,
        "licence": mapping.pack.licence,
        "source": mapping.pack.source,
    }
    (out / "pack.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(out, mapping, report)
    return out, report
