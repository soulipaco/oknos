"""What a personal podcast episode is written from (phase 11, docs/PODCASTS.md, "Personal episodes").

`oknos podcast material daily|weekly` prints one JSON document for the agent (the `podcast` skill,
run by `daily-prep`): the words due on the episode's day and the weak ones, with their meanings and an
example sentence; the recent mistakes with the right answer; the words met lately; the current lesson;
the words and verbs the learner has met (for the story); and the last personal episodes, so the next
one does not repeat them. It reads the database and writes nothing: listening is not answering.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from oknos import curriculum, db, paths, report, scheduler
from oknos.checking import meaning
from oknos.packs import Catalog, FormItem, VocabItem

# Reading cards (letters, letter pairs) are vocab items but not words to talk about.
NOT_WORDS = {"open-alphabet"}

# Minutes an episode aims at, and how many words it can carry (docs/PODCASTS.md).
TARGET = {"daily": {"minutes": [10, 20], "due": 12, "weak": 6, "mistakes": 4, "new": 10, "window": 2},
          "weekly": {"minutes": [20, 30], "due": 20, "weak": 10, "mistakes": 10, "new": 25, "window": 7}}


def learner_lang(profile: dict) -> str:
    """The language a learner's episodes explain in: podcast.lang, else the app's language."""
    lang = (profile.get("podcast") or {}).get("lang") or profile.get("ui_lang") or "en"
    return lang if lang in ("tr", "en") else "en"


def episode_id(kind: str, day: date, lang: str) -> str:
    """daily.2026-11-25.tr; weekly.2026-w48.tr (the ISO week of the day it is for)."""
    if kind == "weekly":
        year, week, _ = day.isocalendar()
        return f"weekly.{year}-w{week:02d}.{lang}"
    return f"daily.{day.isoformat()}.{lang}"


def _word(key: str, item: VocabItem, lang: str, catalog: Catalog, state: scheduler.State | None) -> dict:
    from oknos import session

    learn = session.learn_part(item, lang, catalog)
    out = {"key": key, "el": item.el, "meaning": meaning(item, lang), "level": item.level}
    if item.gender:
        out["gender"] = item.gender
    ex = learn.get("example")
    if ex:
        out["example"] = {"el": ex.get("el"), lang: ex.get(lang) or ex.get("en") or ex.get("tr")}
    if state is not None:
        out |= {"due": state.due_at, "lapses": state.lapses, "ease": round(state.ease, 2), "reps": state.reps}
    return out


def _previous(lang: str, limit: int = 6) -> list[dict]:
    """The last personal episodes' scripts (rendered or not): their ids, days and what they drilled."""
    base = paths.learner_dir() / "podcasts"
    out = []
    if not base.is_dir():
        return out
    for d in base.iterdir():
        f = d / "script.json"
        if not (d.is_dir() and f.is_file() and d.name.split(".", 1)[0] in ("daily", "weekly")):
            continue
        try:
            raw = json.loads(f.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if raw.get("lang") != lang:
            continue
        out.append({"id": raw.get("id"), "kind": raw.get("kind"), "date": raw.get("date"),
                    "title": raw.get("title"), "focus": raw.get("focus", [])})
    out.sort(key=lambda r: r.get("date") or "", reverse=True)
    return out[:limit]


def material(conn: sqlite3.Connection, catalog: Catalog, kind: str, day: date, profile: dict) -> dict:
    if kind not in TARGET:
        raise ValueError(f"kind must be daily or weekly, not {kind!r}")
    lang = learner_lang(profile)
    want = TARGET[kind]
    today = db.today()  # usually the day before the episode's day: it is written ahead
    states = scheduler.all_states(conn)
    vocab = {k: e[1] for k, e in catalog.items.items() if isinstance(e[1], VocabItem) and e[1].status == "ok"
             and k.split("/", 1)[0] not in NOT_WORDS}

    # Due on the episode's day (or in its week). Only scheduled words: met in a session or tapped. A word
    # never met is the session's learn card, not the podcast's.
    until = (day + timedelta(days=6 if kind == "weekly" else 0)).isoformat()
    due_keys = [k for k, s in states.items() if k in vocab and s.due_at <= until]
    weakness = lambda k: (-states[k].lapses, states[k].ease, states[k].due_at)  # noqa: E731
    due_keys.sort(key=weakness)
    due = [_word(k, vocab[k], lang, catalog, states[k]) for k in due_keys[:want["due"]]]

    taken = {w["key"] for w in due}
    weak_keys = [k for k, s in states.items() if k in vocab and k not in taken and (s.lapses > 0 or (s.last_score or 1) < 0.6)]
    weak_keys.sort(key=weakness)
    weak = [_word(k, vocab[k], lang, catalog, states[k]) for k in weak_keys[:want["weak"]]]

    # Mistakes: one per item, newest first (the agent teaches the right form; never quotes the answer as theirs).
    mistakes, seen = [], set()
    for m in report.recent_wrong(conn, catalog, today, want["window"], limit=80):
        if m["key"] in seen:
            continue
        seen.add(m["key"])
        mistakes.append({k: m[k] for k in ("key", "type", "given", "right")})
        if len(mistakes) >= want["mistakes"]:
            break

    since = (today - timedelta(days=want["window"] - 1)).isoformat()
    new_keys = [r[0] for r in conn.execute(
        "SELECT item_key FROM attempts GROUP BY item_key HAVING MIN(ts) >= ? ORDER BY MIN(ts) DESC", (since,))]
    new = [_word(k, vocab[k], lang, catalog, states.get(k)) for k in new_keys if k in vocab][:want["new"]]

    met_words = sorted({vocab[k].el for k in states if k in vocab})
    verbs: dict[str, set[str]] = {}
    for k in states:
        e = catalog.items.get(k)
        if e and isinstance(e[1], FormItem) and e[1].cue and e[1].cue.lemma:
            verbs.setdefault(e[1].cue.lemma, set()).add(e[1].cue.tense or "?")

    cur = curriculum.summary(conn, catalog)
    current = None
    if cur:
        c = cur["current"]
        current = {"curriculum": cur["curriculum"], "id": c["id"], "level": c["level"], "title": c["title"],
                   "chapter": c["chapter"], "can_do": c["can_do"], "share": c["share"]}

    pid = episode_id(kind, day, lang)
    script = paths.learner_dir() / "podcasts" / pid / "script.json"
    return {
        "material_version": 1, "kind": kind, "id": pid, "date": day.isoformat(), "lang": lang,
        "exists": script.is_file(), "minutes": want["minutes"], "level": profile.get("level"),
        "current": current, "due": due, "due_total": len(due_keys), "weak": weak, "mistakes": mistakes,
        "new": new, "met_words": met_words, "met_verbs": {k: sorted(v) for k, v in sorted(verbs.items())},
        "previous": _previous(lang),
        "rules": ["Listening is not answering: the episode is never exam evidence and moves no review.",
                  "Teach the right form of a mistake; never quote the learner's answer as theirs, never say "
                  "scores, counts, dates of study or anything personal (the text goes to a voice service).",
                  "The story uses met_words and this lesson's words; new words only if explained."],
    }

