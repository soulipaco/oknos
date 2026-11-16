"""Building the daily session, resuming it, summarising it, and the home-screen numbers.

A daily session (docs/SPEC.md §7, phase 3) is assembled from four segments, sized to the
learner's time budget with their own median seconds per card type:

  review  due spaced-repetition cards, most overdue first, capped at REVIEW_CAP
  verbs   a daily slot of verb-form cards: due ones first, then new ones
  task    one task in exam format, rotating skills with the weakest weighted up
  new     a few new words: the coach's packs first, then open packs, then the learner's book

Every answer is saved as it is given. A daily session that was left early is resumed by the
same button; once it is finished, the button offers five more minutes instead.
"""

from __future__ import annotations

import json
import random
import sqlite3
import statistics
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from greek_coach import coachfiles, db, scheduler
from greek_coach.checking import meaning
from greek_coach.packs import (
    OPEN_TASKS,
    SELECTION_TASKS,
    Catalog,
    CategoriseItem,
    FormItem,
    GapBankItem,
    MatchItem,
    McqItem,
    Pack,
    SpeakItem,
    TrueFalseItem,
    VocabItem,
    WriteItem,
    servable,
)

DEFAULT_SECONDS = {"vocab": 20, "form": 30, "task": 90, "write": 360, "speak": 120}
SECONDS_RANGE = {"vocab": (8, 45), "form": (12, 75), "task": (40, 300)}
REVIEW_CAP = 25
NEW_MIN, NEW_MAX = 5, 12
# After this many days without practice, the first session back is lighter (SPEC §2).
AWAY_DAYS = 3
AWAY_REVIEW_CAP, AWAY_NEW = 15, 3
OPEN_TASK_EVERY_DAYS = 7  # a writing prompt once a week, and a speaking card once a week
OPEN_TASK_MIN_MINUTES = 10
SUPPRESSING_FLAGS = ("wrong", "confusing")
VERB_SLOT = 4
VERB_SLOT_MAX = 8
COACH_VERB_SHARE = 3  # unseen coach-written forms per day, even when old forms are due
OPTIONS_PER_CARD = 4
EVIDENCE_MIN = 10  # attempts before an area's accuracy is shown
PACK_RANK = {"generated": 0, "open": 1, "private": 2}
LEVEL_RANK = {"A1": 0, "A2": 1, "B1": 2}
PERSON_EL = {"1sg": "εγώ", "2sg": "εσύ", "3sg": "αυτός/αυτή", "1pl": "εμείς", "2pl": "εσείς", "3pl": "αυτοί"}


def card_class(item) -> str:
    if isinstance(item, VocabItem):
        return "vocab"
    if isinstance(item, FormItem):
        return "form"
    if isinstance(item, WriteItem):
        return "write"
    if isinstance(item, SpeakItem):
        return "speak"
    return "task"


# ---------- timing ----------

def seconds_per_card(conn: sqlite3.Connection, catalog: Catalog) -> dict[str, float]:
    """The learner's median seconds per card type over recent answers, or the spec defaults."""
    rows = conn.execute(
        "SELECT item_key, latency_ms FROM attempts WHERE latency_ms IS NOT NULL ORDER BY id DESC LIMIT 600"
    ).fetchall()
    samples: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        entry = catalog.items.get(r["item_key"])
        if entry:
            samples[card_class(entry[1])].append(r["latency_ms"] / 1000)
    out = {}
    for kind, default in DEFAULT_SECONDS.items():
        if kind not in SECONDS_RANGE:  # writing and speaking: a fixed allowance
            out[kind] = default
            continue
        values = samples.get(kind, [])
        lo, hi = SECONDS_RANGE[kind]
        # Feedback reading adds a few seconds on top of answering.
        out[kind] = min(hi, max(lo, statistics.median(values) + 4)) if len(values) >= 8 else default
    return out


# ---------- cards ----------

def _text(t) -> dict[str, str | None] | None:
    return t.model_dump() if t is not None else None


class Distractors:
    """Wrong options for vocab cards: same part of speech and pack where possible."""

    def __init__(self, words: list[tuple[str, Pack, VocabItem]]):
        self.by_pack_pos: dict[tuple[str, str | None], list[VocabItem]] = defaultdict(list)
        self.by_pack: dict[str, list[VocabItem]] = defaultdict(list)
        for _, pack, item in words:
            self.by_pack_pos[(pack.id, item.pos)].append(item)
            self.by_pack[pack.id].append(item)

    def pick(self, pack: Pack, item: VocabItem, values, right: str, rng: random.Random, lang: str | None = None) -> list[str]:
        """Up to three wrong options. With `lang`, only words that have a meaning in that language
        (no English among Turkish options, which would give the answer away)."""
        out: list[str] = []
        for pool in (self.by_pack_pos[(pack.id, item.pos)], self.by_pack[pack.id]):
            if lang:
                pool = [x for x in pool if getattr(x, lang, None)]
            candidates = [v for v in (values(x) for x in rng.sample(pool, min(len(pool), 40)) if x is not item)
                          if v and v != right and v not in out]
            out += candidates[: OPTIONS_PER_CARD - 1 - len(out)]
            if len(out) >= OPTIONS_PER_CARD - 1:
                break
        return out


def vocab_direction(state: scheduler.State | None, has_voice: bool, rng: random.Random) -> str:
    reps = state.reps if state else 0
    if reps == 0:
        return "el_meaning"
    if reps == 1:
        return "meaning_el"
    choices = ["el_meaning", "meaning_el"] + (["audio_meaning"] if has_voice else [])
    if state and state.reps >= 3 and state.interval_days >= 6:
        choices += ["meaning_el_typed", "meaning_el_typed"]
    return rng.choice(choices)


def vocab_card(item_key: str, pack: Pack, item: VocabItem, lang: str, direction: str, distract: Distractors,
               rng: random.Random, state: scheduler.State | None) -> dict:
    card = {"item_key": item_key, "type": "vocab", "direction": direction, "lang": lang, "speak": item.el,
            "reps": state.reps if state else 0, "pos": item.pos}
    if direction in ("el_meaning", "audio_meaning"):
        right = meaning(item, lang)
        card["prompt"] = item.el if direction == "el_meaning" else None
        values = lambda v: meaning(v, lang)  # noqa: E731
    else:
        right = item.el
        card["prompt"] = meaning(item, lang)
        values = lambda v: v.el  # noqa: E731
    if direction != "meaning_el_typed":
        same_lang = lang if direction in ("el_meaning", "audio_meaning") and getattr(item, lang, None) else None
        options = distract.pick(pack, item, values, right, rng, same_lang) + [right]
        rng.shuffle(options)
        card["options"] = options
    return card


def form_card(item_key: str, item: FormItem, state: scheduler.State | None, rng: random.Random) -> dict:
    card: dict[str, Any] = {
        "item_key": item_key, "type": "form", "skill": item.skill, "text": item.text,
        "cue": item.cue.model_dump(exclude_none=True) if item.cue else None,
        "translation": _text(item.translation), "rubric": _text(item.rubric),
        "reps": state.reps if state else 0, "grammar": item.grammar,
    }
    # Choices while a form is new; typed with the Greek keyboard once it has been seen.
    if item.options and (state is None or state.reps == 0):
        card["options"] = {g: rng.sample(opts, len(opts)) for g, opts in item.options.items()}
    return card


def task_card(item_key: str, item, rng: random.Random) -> dict:
    card: dict[str, Any] = {
        "item_key": item_key, "type": item.type, "skill": item.skill, "exam_task": item.exam_task,
        "rubric": _text(item.rubric),
        "stimulus": item.stimulus.model_dump(exclude_none=True) if item.stimulus else None,
    }
    if isinstance(item, McqItem):
        card["prompt"] = _text(item.prompt)
        card["options"] = item.options
    elif isinstance(item, TrueFalseItem):
        card["statements"] = [{"el": s.el, "en": s.en, "tr": s.tr} for s in item.statements]
    elif isinstance(item, MatchItem):
        card["prompt"] = _text(item.prompt)
        card["left"] = item.left
        card["right"] = item.right
    elif isinstance(item, GapBankItem):
        card["text"] = item.text
        card["bank"] = rng.sample(item.bank, len(item.bank))
        card["translation"] = _text(item.translation)
    elif isinstance(item, CategoriseItem):
        card["prompt"] = _text(item.prompt)
        card["categories"] = item.categories
        card["items"] = item.items
    elif isinstance(item, WriteItem):
        card["prompt"] = _text(item.prompt)
        card["words"] = item.words
        card["must_include"] = [{"en": m} if isinstance(m, str) else m.model_dump() for m in item.must_include]
    elif isinstance(item, SpeakItem):
        card["prompt"] = _text(item.prompt)
        card["seconds"] = item.seconds
        card["model"] = _text(item.model)
        card["useful"] = item.useful
    return card


# ---------- picking ----------

def _last_attempts(conn: sqlite3.Connection) -> dict[str, tuple[str, int | None]]:
    rows = conn.execute(
        """
        SELECT a.item_key, a.ts, a.correct FROM attempts a
        JOIN (SELECT item_key, MAX(id) AS last_id FROM attempts GROUP BY item_key) l ON a.id = l.last_id
        """
    ).fetchall()
    return {r["item_key"]: (r["ts"], r["correct"]) for r in rows}


def skill_accuracy(conn: sqlite3.Connection, catalog: Catalog, days: int = 30) -> dict[str, tuple[float, int]]:
    since = (db.today() - timedelta(days=days)).isoformat()
    acc: dict[str, list[int]] = defaultdict(list)
    for r in conn.execute("SELECT item_key, correct FROM attempts WHERE ts >= ? AND correct IS NOT NULL", (since,)):
        entry = catalog.items.get(r["item_key"])
        if entry and isinstance(entry[1], SELECTION_TASKS):
            acc[entry[1].skill].append(r["correct"])
    return {k: (sum(v) / len(v), len(v)) for k, v in acc.items()}


def flagged_keys(conn: sqlite3.Connection) -> set[str]:
    """Items with an open "wrong" or "confusing" flag. They stay out of daily sessions until the
    coach has looked at them (its verdicts are in coach/resolved-flags.json)."""
    resolved = coachfiles.resolved_flag_ids()
    marks = ",".join("?" * len(SUPPRESSING_FLAGS))
    rows = conn.execute(f"SELECT id, item_key FROM flags WHERE resolved_at IS NULL AND reason IN ({marks})",
                        SUPPRESSING_FLAGS)
    return {r["item_key"] for r in rows if r["id"] not in resolved}


def days_away(conn: sqlite3.Connection) -> int | None:
    """Days since the last practice before today: 0 if there was practice today, None if never."""
    today = db.today().isoformat()
    if conn.execute("SELECT 1 FROM attempts WHERE substr(ts, 1, 10) = ? LIMIT 1", (today,)).fetchone():
        return 0
    last = conn.execute("SELECT MAX(substr(ts, 1, 10)) FROM attempts").fetchone()[0]
    return (db.today() - date.fromisoformat(last)).days if last else None


OPEN_TASK_SKIP_WAIT_DAYS = 3  # a skipped writing or speaking card comes back after this many days


def _open_task_due(conn: sqlite3.Connection, kind: str) -> bool:
    """A writing (or speaking) card is due when none was submitted in the last week and none was
    offered in the last few days (so skipping it does not take the exam-task slot every day), and
    no writing or speaking card at all was offered yesterday or today."""
    today = db.today()
    since = (today - timedelta(days=OPEN_TASK_EVERY_DAYS - 1)).isoformat()
    if conn.execute("SELECT 1 FROM submissions WHERE kind=? AND substr(ts, 1, 10) >= ? LIMIT 1",
                    ("writing" if kind == "write" else "speaking", since)).fetchone():
        return False
    offered = lambda types, days: conn.execute(  # noqa: E731
        f"SELECT 1 FROM attempts a JOIN items i USING(item_key) WHERE i.type IN ({','.join('?' * len(types))}) "
        "AND substr(a.ts, 1, 10) >= ? LIMIT 1",
        (*types, (today - timedelta(days=days - 1)).isoformat())).fetchone() is not None
    return not offered((kind,), OPEN_TASK_SKIP_WAIT_DAYS) and not offered(("write", "speak"), 2)


def _gen_first(entry) -> int:
    return PACK_RANK.get(entry[1].manifest.visibility, 3)


def _unit_rank(pack: Pack) -> dict[str, int]:
    return {f"unit:{u.id}": u.order for u in pack.units}


def new_word_order(words: list[tuple[str, Pack, VocabItem]]) -> list[tuple[str, Pack, VocabItem]]:
    """What the coach prepared comes first. After that, open packs and the learner's own book
    take turns, so the first session already has words from the book. Within each: A1 first,
    then words met in the earliest unit of the book, then pack order."""
    ranks = {p.id: _unit_rank(p) for _, p, _ in words}

    def key(entry):
        position, (_, pack, item) = entry
        units = [ranks[pack.id][t] for t in item.topics if t in ranks[pack.id]]
        return (LEVEL_RANK.get(item.level, 3), 0 if units else 1, min(units) if units else 0, position)

    queues: dict[str, list] = defaultdict(list)
    for _, w in sorted(enumerate(words), key=key):
        queues[w[1].manifest.visibility].append(w)
    out = list(queues.pop("generated", []))
    rest = [queues[v] for v in sorted(queues, key=lambda v: PACK_RANK.get(v, 3))]
    while any(rest):
        for q in rest:
            if q:
                out.append(q.pop(0))
    return out


def plan(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str, minutes: int, kind: str = "daily",
         rng: random.Random | None = None, has_voice: bool = False) -> list[dict]:
    rng = rng or random.Random()
    today = db.today()
    states = scheduler.all_states(conn)
    last = _last_attempts(conn)
    flagged = flagged_keys(conn)
    items = [(k, p, i) for k, p, i in servable(catalog, ui_lang) if k not in flagged]
    by_key = {k: (p, i) for k, p, i in items}
    words = [(k, p, i) for k, p, i in items if isinstance(i, VocabItem)]
    # Coach-written items come first in every segment, so a check-in shows up in the next session.
    forms = sorted(((k, p, i) for k, p, i in items if isinstance(i, FormItem)), key=_gen_first)
    tasks = [(k, p, i) for k, p, i in items if isinstance(i, SELECTION_TASKS)]
    open_tasks = [(k, p, i) for k, p, i in items if isinstance(i, OPEN_TASKS)]
    away = days_away(conn) if kind == "daily" else None
    returning = away is not None and away >= AWAY_DAYS
    review_cap = AWAY_REVIEW_CAP if returning else REVIEW_CAP
    secs = seconds_per_card(conn, catalog)
    budget = max(1, minutes) * 60
    distract = Distractors(words)

    is_due = lambda k: k in states and states[k].due_at <= today.isoformat()  # noqa: E731
    due_keys = [s.item_key for s in scheduler.due(conn, today) if s.item_key in by_key]
    extra = kind != "daily"

    # Exam-format task: what was wrong before and is due, then unseen, then least recently done;
    # within a tier the weakest skill and the least recently practised skill go first.
    accuracy = skill_accuracy(conn, catalog)
    n_tasks = 0 if not tasks else (2 if minutes >= 15 else 1 if minutes >= 5 else 0)

    def task_key(entry):
        k, _, item = entry
        fresh_coach = k not in last and entry[1].manifest.visibility == "generated"
        tier = 0 if is_due(k) or fresh_coach else 1 if k not in last else 2
        acc = accuracy.get(item.skill, (0.5, 0))[0]
        return (tier, _gen_first(entry), round(acc, 1), last.get(k, ("", None))[0], rng.random())

    chosen_tasks = []
    for t in sorted(tasks, key=task_key):
        if len(chosen_tasks) >= n_tasks:
            break
        if any(c[2].skill == t[2].skill for c in chosen_tasks) and len({x[2].skill for x in tasks}) > 1:
            continue  # two different skills when there are two tasks
        chosen_tasks.append(t)

    # Once a week the exam-task slot holds a writing prompt, and on another day a speaking card.
    open_card = None
    if kind == "daily" and minutes >= OPEN_TASK_MIN_MINUTES and not returning:
        for cls, name in ((WriteItem, "write"), (SpeakItem, "speak")):
            pool = [t for t in open_tasks if isinstance(t[2], cls)]
            if pool and _open_task_due(conn, name):
                pool.sort(key=lambda t: (t[0] in last, _gen_first(t), last.get(t[0], ("", None))[0], rng.random()))
                open_card = pool[0]
                break
    if open_card:
        chosen_tasks = chosen_tasks[1:]
        budget -= secs[card_class(open_card[2])]
    budget -= len(chosen_tasks) * secs["task"]

    # Verbs: due forms, then new ones in pack order, a fixed daily slot.
    due_forms = [k for k in due_keys if isinstance(by_key[k][1], FormItem)]
    new_forms = [k for k, _, _ in forms if k not in states]
    # Unseen coach forms get a share of the slot even when old forms are due, so what the check-in
    # wrote shows up the next day instead of waiting behind the review backlog.
    coach_new = [k for k in new_forms if by_key[k][0].manifest.visibility == "generated"][:COACH_VERB_SHARE]
    verb_keys = due_forms[: VERB_SLOT_MAX - len(coach_new)] + coach_new
    n_verbs = max(VERB_SLOT if minutes >= 8 else 2, len(verb_keys)) if forms else 0
    verb_keys += [k for k in new_forms if k not in verb_keys][: max(0, n_verbs - len(verb_keys))]
    if extra and not verb_keys:
        verb_keys = [k for k, _, _ in sorted(forms, key=lambda f: states[f[0]].due_at if f[0] in states else "")][:2]
    budget -= len(verb_keys) * secs["form"]

    # Reviews: due vocab (and due tasks beyond the task slot), most overdue first, capped.
    review_keys = [k for k in due_keys if isinstance(by_key[k][1], VocabItem)]
    review_keys = review_keys[: min(review_cap, max(0, int(budget // secs["vocab"])))]
    if extra:  # "5 more minutes": the soonest-due learning cards, ahead of time
        upcoming = sorted((s for k, s in states.items() if k in by_key and isinstance(by_key[k][1], VocabItem)
                           and k not in review_keys), key=lambda s: (s.due_at, s.ease))
        review_keys += [s.item_key for s in upcoming][: max(0, int(budget // secs["vocab"]) // 2 - len(review_keys))]
    budget -= len(review_keys) * secs["vocab"]

    # New words: a few every day, more on a light day.
    new_cap = AWAY_NEW if returning else NEW_MAX if len(review_keys) < 10 else NEW_MIN
    n_new = max(0, min(new_cap, int(budget // secs["vocab"])))
    if kind == "daily" and n_new == 0 and not review_keys:
        n_new = AWAY_NEW if returning else NEW_MIN
    new_keys = [k for k, _, _ in new_word_order([w for w in words if w[0] not in states])][:n_new]

    cards: list[dict] = []
    for k in review_keys:
        pack, item = by_key[k]
        cards.append({**vocab_card(k, pack, item, ui_lang, vocab_direction(states.get(k), has_voice, rng),
                                   distract, rng, states.get(k)), "segment": "review"})
    for k in verb_keys:
        cards.append({**form_card(k, by_key[k][1], states.get(k), rng), "segment": "verbs"})
    for k, _, item in chosen_tasks:
        cards.append({**task_card(k, item, rng), "segment": "task"})
    if open_card:
        cards.append({**task_card(open_card[0], open_card[2], rng), "segment": "task"})
    for k in new_keys:
        pack, item = by_key[k]
        cards.append({**vocab_card(k, pack, item, ui_lang, "el_meaning", distract, rng, None), "segment": "new"})
    return cards


# ---------- sessions ----------

def _today_daily(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM sessions WHERE kind='daily' AND substr(started_at, 1, 10)=? ORDER BY id DESC LIMIT 1",
        (db.today().isoformat(),),
    ).fetchone()


def remaining_cards(conn: sqlite3.Connection, row: sqlite3.Row) -> list[dict]:
    if not row or not row["plan_json"]:
        return []
    done = {r["item_key"] for r in conn.execute("SELECT item_key FROM attempts WHERE session_id=?", (row["id"],))}
    return [c for c in json.loads(row["plan_json"]) if c["item_key"] not in done]


def today_status(conn: sqlite3.Connection) -> dict:
    """'fresh' (no session today), 'resume' (cards left), or 'done'."""
    row = _today_daily(conn)
    if row is None:
        return {"state": "fresh"}
    left = remaining_cards(conn, row)
    planned = len(json.loads(row["plan_json"])) if row["plan_json"] else row["items_planned"] or 0
    return {"state": "resume" if left else "done", "left": len(left), "planned": planned, "session_id": row["id"]}


def build(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str, minutes: int, kind: str = "daily",
          rng: random.Random | None = None, has_voice: bool = False) -> dict:
    if kind == "daily":
        row = _today_daily(conn)
        if row is not None:
            left = [c for c in remaining_cards(conn, row) if c["item_key"] in catalog.items]
            if any(c["type"] == "vocab" and c.get("lang") != ui_lang for c in left):
                # The UI language changed since the session was planned: rebuild the word cards.
                rng = rng or random.Random()
                words = [(k, p, i) for k, (p, i) in catalog.items.items() if isinstance(i, VocabItem)]
                distract, states = Distractors(words), scheduler.all_states(conn)
                left = [{**vocab_card(c["item_key"], *catalog.items[c["item_key"]], ui_lang, c["direction"], distract, rng,
                                      states.get(c["item_key"])), "segment": c["segment"]}
                        if c["type"] == "vocab" and c.get("lang") != ui_lang else c for c in left]
            if left:
                with conn:
                    conn.execute("UPDATE sessions SET ended_at=NULL WHERE id=?", (row["id"],))
                return {"session_id": row["id"], "kind": "daily", "minutes": row["planned_minutes"],
                        "cards": left, "resumed": True,
                        "total": len(json.loads(row["plan_json"])), "done": len(json.loads(row["plan_json"])) - len(left)}
            kind = "extra"  # today's session is finished: offer more instead of the same again
            minutes = 5
    cards = plan(conn, catalog, ui_lang, minutes, kind, rng, has_voice)
    with conn:
        cur = conn.execute(
            "INSERT INTO sessions(started_at, kind, planned_minutes, items_planned, plan_json) VALUES (?, ?, ?, ?, ?)",
            (db.now(), kind, minutes, len(cards), json.dumps(cards, ensure_ascii=False)),
        )
    return {"session_id": cur.lastrowid, "kind": kind, "minutes": minutes, "cards": cards, "resumed": False,
            "total": len(cards), "done": 0}


def practice(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str, keys: list[str],
             rng: random.Random | None = None) -> dict:
    """A session of chosen items (the coach's "practise these", and for checking content)."""
    rng = rng or random.Random()
    states = scheduler.all_states(conn)
    words = [(k, p, i) for k, (p, i) in catalog.items.items() if isinstance(i, VocabItem)]
    distract = Distractors(words)
    cards = []
    for k in keys:
        pack, item = catalog.items[k]
        if isinstance(item, VocabItem):
            card = vocab_card(k, pack, item, ui_lang, vocab_direction(states.get(k), False, rng), distract, rng, states.get(k))
        elif isinstance(item, FormItem):
            card = form_card(k, item, states.get(k), rng)
        else:
            card = task_card(k, item, rng)
        cards.append({**card, "segment": "review" if card_class(item) in ("vocab", "form") else "task"})
    with conn:
        cur = conn.execute(
            "INSERT INTO sessions(started_at, kind, planned_minutes, items_planned, plan_json) VALUES (?, 'practice', NULL, ?, ?)",
            (db.now(), len(cards), json.dumps(cards, ensure_ascii=False)),
        )
    return {"session_id": cur.lastrowid, "kind": "practice", "minutes": None, "cards": cards, "resumed": False,
            "total": len(cards), "done": 0}


def end(conn: sqlite3.Connection, session_id: int) -> None:
    with conn:
        conn.execute(
            """
            UPDATE sessions SET ended_at=COALESCE(ended_at, ?),
                items_done=(SELECT COUNT(*) FROM attempts WHERE session_id=?)
            WHERE id=?
            """,
            (db.now(), session_id, session_id),
        )


def _area(item, card: dict | None = None) -> str:
    """The area an attempt counts towards on the home screen."""
    if isinstance(item, VocabItem):
        return "vocab"
    if isinstance(item, FormItem):
        tense = item.cue.tense if item.cue and item.cue.tense else "other"
        return f"verbs.{tense}"
    return f"skill.{item.skill}"


def summary(conn: sqlite3.Connection, catalog: Catalog, session_id: int, ui_lang: str) -> dict | None:
    row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if row is None:
        return None
    attempts = conn.execute(
        "SELECT item_key, ts, score, correct, latency_ms FROM attempts WHERE session_id=? ORDER BY id", (session_id,)
    ).fetchall()
    by_area: dict[str, dict[str, int]] = {}
    missed: list[dict[str, str]] = []
    every = attempts
    # Writing and speaking are marked later by the coach, so they do not count towards accuracy.
    written = conn.execute("SELECT COUNT(*) FROM submissions WHERE session_id=?", (session_id,)).fetchone()[0]
    attempts = [a for a in every if a["correct"] is not None]
    for a in attempts:
        entry = catalog.items.get(a["item_key"])
        area = _area(entry[1]) if entry else "other"
        s = by_area.setdefault(area, {"done": 0, "right": 0})
        s["done"] += 1
        s["right"] += 1 if a["correct"] else 0
        if entry and not a["correct"]:
            item = entry[1]
            if isinstance(item, VocabItem):
                word = {"el": item.el, "meaning": meaning(item, ui_lang)}
            elif isinstance(item, FormItem):
                cue = item.cue
                word = {"el": " / ".join(f[0] for f in item.answer.values()),
                        "meaning": ", ".join(x for x in (cue.lemma, PERSON_EL.get(cue.person or "")) if x) if cue else ""}
            else:
                continue
            if word not in missed:
                missed.append(word)
    done = len(attempts)
    right = sum(1 for a in attempts if a["correct"])
    seconds = sum(min(a["latency_ms"] or 0, 600_000 if a["correct"] is None else 120_000) for a in every) / 1000
    tomorrow = (db.today() + timedelta(days=1)).isoformat()
    due_tomorrow = conn.execute("SELECT COUNT(*) FROM review_state WHERE due_at <= ?", (tomorrow,)).fetchone()[0]
    return {
        "session_id": session_id,
        "kind": row["kind"],
        "done": done,
        "right": right,
        "accuracy": round(right / done, 3) if done else None,
        "minutes": max(1, round(seconds / 60)) if every else 0,
        "written": written,
        "by_area": by_area,
        "missed": missed,
        "due_tomorrow": min(due_tomorrow, REVIEW_CAP),
        "due_tomorrow_all": due_tomorrow,
        "left": len(remaining_cards(conn, row)),
    }


# ---------- home ----------

def home_stats(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str) -> dict:
    today = db.today()
    items = servable(catalog, ui_lang)
    by_key = {k: i for k, _, i in items}
    states = scheduler.all_states(conn)
    due = [s for s in states.values() if s.due_at <= today.isoformat() and s.item_key in by_key]
    due_vocab = sum(1 for s in due if isinstance(by_key[s.item_key], VocabItem))
    due_forms = sum(1 for s in due if isinstance(by_key[s.item_key], FormItem))
    due_tasks = len(due) - due_vocab - due_forms
    vocab_keys = [k for k, i in by_key.items() if isinstance(i, VocabItem)]
    form_keys = [k for k, i in by_key.items() if isinstance(i, FormItem)]

    def counts(keys):
        known = sum(1 for k in keys if k in states and states[k].interval_days >= scheduler.KNOWN_DAYS)
        learning = sum(1 for k in keys if k in states) - known
        return {"total": len(keys), "unseen": len(keys) - known - learning, "learning": learning, "known": known}

    # Consistency: answering time per day over 28 days (each answer capped at 2 minutes).
    start = today - timedelta(days=27)
    per_day: dict[str, dict[str, float]] = {}
    for r in conn.execute(
        "SELECT substr(ts, 1, 10) AS d, COUNT(*) AS n, SUM(MIN(COALESCE(latency_ms, 20000), 120000)) AS ms "
        "FROM attempts WHERE ts >= ? GROUP BY d", (start.isoformat(),)
    ):
        per_day[r["d"]] = {"answers": r["n"], "minutes": round(r["ms"] / 60000, 1)}
    grid = []
    for i in range(28):
        d = (start + timedelta(days=i)).isoformat()
        grid.append({"date": d, **per_day.get(d, {"answers": 0, "minutes": 0})})
    days_14 = sum(1 for g in grid[-14:] if g["answers"])

    # Weakest: accuracy per area over 30 days, shown only with enough evidence.
    since = (today - timedelta(days=30)).isoformat()
    areas: dict[str, list[int]] = defaultdict(list)
    retention: list[int] = []
    for r in conn.execute("SELECT item_key, correct, response_json FROM attempts WHERE ts >= ? AND correct IS NOT NULL",
                          (since,)):
        entry = catalog.items.get(r["item_key"])
        if not entry:
            continue
        areas[_area(entry[1])].append(r["correct"])
        if isinstance(entry[1], VocabItem):
            try:
                reps = json.loads(r["response_json"]).get("card", {}).get("reps", 0)
            except (ValueError, AttributeError):
                reps = 0
            if reps and reps >= 1:
                retention.append(r["correct"])
    area_list = sorted(
        ({"area": a, "accuracy": round(sum(v) / len(v), 3), "n": len(v), "enough": len(v) >= EVIDENCE_MIN}
         for a, v in areas.items()),
        key=lambda x: (not x["enough"], x["accuracy"]),
    )
    weakest = next((a for a in area_list if a["enough"]), None)
    lookups_30 = conn.execute("SELECT COUNT(*) FROM lookups WHERE ts >= ?", (since,)).fetchone()[0]

    total = conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
    today_n = conn.execute("SELECT COUNT(*) FROM attempts WHERE substr(ts, 1, 10)=?", (today.isoformat(),)).fetchone()[0]
    new_available = sum(1 for k in vocab_keys if k not in states)
    return {
        "answers_total": total,
        "answers_today": today_n,
        "today": today_status(conn),
        "due": {"vocab": due_vocab, "vocab_shown": min(due_vocab, REVIEW_CAP), "verbs": due_forms, "tasks": due_tasks},
        "new_available": new_available,
        "verbs_new_available": sum(1 for k in form_keys if k not in states),
        "words": counts(vocab_keys),
        "verbs": counts(form_keys),
        "grid": grid,
        "days_studied_14": days_14,
        "areas": area_list,
        "weakest": weakest,
        "retention": {"rate": round(sum(retention) / len(retention), 3) if retention else None, "n": len(retention)},
        "lookups_30": lookups_30,
        # kept for the phase-2 front end and tests
        "words_seen": sum(1 for k in vocab_keys if k in states),
        "words_total": len(vocab_keys),
    }
