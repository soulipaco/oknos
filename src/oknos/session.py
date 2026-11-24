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

from oknos import coachfiles, db, greek, paths, scheduler
from oknos.checking import meaning, meaning_lang
from oknos.packs import (
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
    TableFillItem,
    TrueFalseItem,
    VocabItem,
    all_picture_urls,
    chapter_text,
    picture_url,
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
PICTURE_SHARE = 0.4  # of the seen words that have a picture, how often the card is "pick the picture"
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


_examples_cache: dict[int, dict[str, dict]] = {}


def chapter_examples(catalog: Catalog) -> dict[str, dict]:
    """Folded Greek word -> the first chapter sentence that uses it ({el, tr, en}), for learn cards."""
    from oknos import greek

    key = id(catalog)
    if key not in _examples_cache:
        out: dict[str, dict] = {}
        for _, ch in catalog.chapters.values():
            for line in ch.greek_lines():
                for w in greek.words(line["el"]):
                    out.setdefault(greek.fold(w), line)
        if len(_examples_cache) > 4:
            _examples_cache.clear()
        _examples_cache[key] = out
    return _examples_cache[key]


def learn_part(item: VocabItem, lang: str, catalog: Catalog | None) -> dict:
    """What a learn card shows before a word is tested for the first time (phase 5c): the word,
    its meaning, and an example sentence (the item's own, else one from a chapter)."""
    from oknos import greek

    example = item.example.model_dump() if item.example else None
    if example is None and catalog is not None:
        index = chapter_examples(catalog)
        words = [w for w in greek.words(item.lemma or item.el) if greek.fold(w) not in greek.ARTICLES]
        for w in sorted(words, key=len, reverse=True):
            if greek.fold(w) in index:
                example = index[greek.fold(w)]
                break
    return {"el": item.el, "say": item.say, "meaning": meaning(item, lang), "meaning_lang": meaning_lang(item, lang),
            "gender": item.gender, "pos": item.pos, "example": example}


def vocab_card(item_key: str, pack: Pack, item: VocabItem, lang: str, direction: str, distract: Distractors,
               rng: random.Random, state: scheduler.State | None, catalog: Catalog | None = None) -> dict:
    card = {"item_key": item_key, "type": "vocab", "direction": direction, "lang": lang, "speak": item.say or item.el,
            "el": item.el, "reps": state.reps if state else 0, "pos": item.pos}
    picture = picture_url(item)
    if picture:
        card["picture"] = picture
    if state is None:  # never seen: show it first, then test it (teach before testing)
        card["learn"] = learn_part(item, lang, catalog)
        if picture:
            card["learn"]["picture"] = picture
    others = [u for u in all_picture_urls() if u != picture] if picture else []
    if (picture and state is not None and len(others) >= OPTIONS_PER_CARD - 1
            and direction in ("el_meaning", "audio_meaning") and rng.random() < PICTURE_SHARE):
        # pick the picture: the Greek word, and four pictures to choose from
        options = rng.sample(others, OPTIONS_PER_CARD - 1) + [picture]
        rng.shuffle(options)
        card.update(direction="el_picture", prompt=item.el, options=options, meaning=meaning(item, lang))
        return card
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
        "translation": _text(item.translation), "rubric": _text(item.rubric), "ask": _text(item.ask),
        "reps": state.reps if state else 0, "grammar": item.grammar,
    }
    # Choices while a form is new; typed with the Greek keyboard once it has been seen.
    if item.options and (state is None or state.reps == 0):
        card["options"] = {g: rng.sample(opts, len(opts)) for g, opts in item.options.items()}
    return card


def match_order(answer: list[int], size: int, rng: random.Random) -> list[int]:
    """The order to show a match item's right column in: a list of right-hand positions, row by row.

    Items are often written with each pair on the same row (answer 0, 1, 2…), which gives the answer
    away. So the column is shuffled until no left item has its own pair beside it. With a single
    row there is nothing to shuffle. The positions stay those of `item.right`, so checking is unchanged.
    """
    order = list(range(size))
    if size < 2:
        return order
    rows = min(len(answer), size)
    for _ in range(200):
        rng.shuffle(order)
        if all(order[r] != answer[r] for r in range(rows)):
            return order
    # Very unlikely after 200 tries; a rotation of the answer always works when every row has a pair.
    shifted = answer[1:] + answer[:1] + [j for j in range(size) if j not in answer]
    return shifted if all(shifted[r] != answer[r] for r in range(rows)) else order


def task_card(item_key: str, item, rng: random.Random, in_chapter: bool = False) -> dict:
    """An exam-format task's card. `in_chapter`: shown in the chapter reader, under the chapter's own
    dialogue; anywhere else a comprehension question carries that dialogue as its text."""
    card: dict[str, Any] = {
        "item_key": item_key, "type": item.type, "skill": item.skill, "exam_task": item.exam_task,
        "rubric": _text(item.rubric), "ask": _text(item.ask),
        "stimulus": item.stimulus.model_dump(exclude_none=True) if item.stimulus else None,
    }
    if card["stimulus"] is None and not in_chapter and (text := chapter_text(item_key)):
        card["stimulus"] = {"text": text}
    if item.stimulus and item.stimulus.pictures:
        card["stimulus"]["pictures"] = [f"/pictures/{item_key.split('/', 1)[0]}/{f}" for f in item.stimulus.pictures]
    if isinstance(item, McqItem):
        card["prompt"] = _text(item.prompt)
        card["options"] = item.options
    elif isinstance(item, TrueFalseItem):
        card["statements"] = [{"el": s.el, "en": s.en, "tr": s.tr} for s in item.statements]
    elif isinstance(item, MatchItem):
        card["prompt"] = _text(item.prompt)
        card["left"] = item.left
        card["right"] = item.right
        card["right_order"] = match_order(item.answer, len(item.right), rng)
    elif isinstance(item, GapBankItem):
        card["text"] = item.text
        card["bank"] = rng.sample(item.bank, len(item.bank))
        card["translation"] = _text(item.translation)
    elif isinstance(item, CategoriseItem):
        card["prompt"] = _text(item.prompt)
        card["categories"] = item.categories
        card["items"] = item.items
    elif isinstance(item, TableFillItem):
        card["prompt"] = _text(item.prompt)
        card["columns"] = item.columns
        card["rows"] = item.rows
        asked = {(i, j) for i, j, _ in item.cells()}
        card["cells"] = [[(i, j) in asked for j in range(len(item.columns))] for i in range(len(item.rows))]
        card["given"] = item.given
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


def learner_level() -> str:
    """The level the learner works at, from profile.json `level` (the coach sets it; A1 if unset).

    Daily sessions never serve an item above it: someone who still reads slowly must not get a
    B1 passive or a 150-word letter because a pack happens to contain one."""
    try:
        level = coachfiles.read_json(paths.profile_path()).get("level")
    except (FileNotFoundError, ValueError, AttributeError, OSError):
        level = None
    return level if level in LEVEL_RANK else "A1"


def at_level(item, level: str) -> bool:
    return LEVEL_RANK.get(item.level, 0) <= LEVEL_RANK[level]


def gate(conn: sqlite3.Connection, catalog: Catalog):
    """What daily sessions may serve: the stages of the curriculum reached so far (docs/SPEC.md
    §5.4). Returns (allowed(key, item) -> bool, rank(key) -> sort key). Without a curriculum,
    the learner's level is the limit."""
    from oknos import curriculum  # curriculum imports this module's neighbours

    try:
        prog = curriculum.progress(conn, catalog, record=True)
    except Exception:  # a broken curriculum file must never stop the daily session
        prog = None
    if prog is None:
        level = learner_level()
        return (lambda k, i: at_level(i, level)), (lambda k: (0, 0))
    current = prog.current
    # Teach before testing (phase 5c): an item seen before is always allowed (a review); a new one
    # only once its stage's chapter has been read.
    seen = set(scheduler.all_states(conn))

    def rank(k):
        idx = prog.assigned.get(k)
        # the current stage first, then what is left of earlier stages, level-pool extras last
        if k in prog.pooled:
            return (2, idx if idx is not None else 99)
        return (0, 0) if idx == current else (1, idx if idx is not None else 99)

    return (lambda k, i: prog.unlocked(k) and (k in seen or prog.introducible(k))), rank


def plan_focus_tasks(today: date) -> set[str]:
    """The exam tasks of the units the coach's plan puts in focus this week (empty without a plan)."""
    try:
        from oknos import exams

        plan = coachfiles.plan()
        if plan is None:
            return set()
        monday = (today - timedelta(days=today.weekday())).isoformat()
        week = next((w for w in plan.weeks if w.start == monday), None)
        bp = exams.load_blueprints().get(plan.exam)
        if week is None or bp is None:
            return set()
        return {t.id for u in bp.units if u.id in week.focus for t in u.tasks}
    except Exception:  # a broken plan must never stop the daily session
        return set()


def reserved_for_mocks(conn: sqlite3.Connection) -> set[str]:
    """Items of a mock exam the learner has not taken yet stay out of daily sessions, so the
    mock is a first sight of them (and so counts as readiness evidence)."""
    from oknos import mock  # mock builds its cards with this module

    try:
        return mock.reserved_keys(conn)
    except Exception:  # a broken mock file must never stop the daily session
        return set()


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
    flagged = flagged_keys(conn) | reserved_for_mocks(conn)
    allowed, stage_rank = gate(conn, catalog)
    items = [(k, p, i) for k, p, i in servable(catalog, ui_lang) if k not in flagged and allowed(k, i)]
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

    focus = plan_focus_tasks(today)

    def task_key(entry):
        k, _, item = entry
        fresh_coach = k not in last and entry[1].manifest.visibility == "generated"
        tier = 0 if is_due(k) or fresh_coach else 1 if k not in last else 2
        acc = accuracy.get(item.skill, (0.5, 0))[0]
        in_focus = 0 if item.exam_task in focus else 1
        return (tier, stage_rank(k)[0], in_focus, _gen_first(entry), round(acc, 1), last.get(k, ("", None))[0], rng.random())

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
    # New forms: the coach's first, then the easiest level first, then pack order.
    new_forms = [k for k, _, i in sorted(forms, key=lambda f: (_gen_first(f), stage_rank(f[0]),
                                                                  LEVEL_RANK.get(f[2].level, 3)))
                 if k not in states]
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
    unseen_words = new_word_order([w for w in words if w[0] not in states])
    new_keys = [k for k, _, _ in sorted(unseen_words, key=lambda w: (stage_rank(w[0]), _gen_first(w)))][:n_new]

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
        cards.append({**vocab_card(k, pack, item, ui_lang, "el_meaning", distract, rng, None, catalog), "segment": "new"})
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


def _open_leftovers(conn: sqlite3.Connection, catalog: Catalog, row: sqlite3.Row) -> list[dict] | None:
    """Today's unanswered cards, or None when the plan is stale: it holds cards of a lesson not
    reached (planned before the curriculum, or under another one). A stale plan is replaced by a
    fresh session; the answers already given stay."""
    allowed, _ = gate(conn, catalog)
    left = remaining_cards(conn, row)
    if any(c["item_key"] not in catalog.items or not allowed(c["item_key"], catalog.items[c["item_key"]][1])
           for c in left):
        return None
    return left


def today_status(conn: sqlite3.Connection, catalog: Catalog | None = None) -> dict:
    """'fresh' (no session today, or a stale one), 'resume' (cards left), or 'done'."""
    row = _today_daily(conn)
    if row is None:
        return {"state": "fresh"}
    left = remaining_cards(conn, row) if catalog is None else _open_leftovers(conn, catalog, row)
    if left is None:
        return {"state": "fresh"}
    planned = len(json.loads(row["plan_json"])) if row["plan_json"] else row["items_planned"] or 0
    return {"state": "resume" if left else "done", "left": len(left), "planned": planned, "session_id": row["id"]}


def build(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str, minutes: int, kind: str = "daily",
          rng: random.Random | None = None, has_voice: bool = False) -> dict:
    if kind == "daily":
        row = _today_daily(conn)
        left = _open_leftovers(conn, catalog, row) if row is not None else None
        if row is not None and left is None:  # a stale plan: close it and plan today afresh
            with conn:
                conn.execute("UPDATE sessions SET ended_at=COALESCE(ended_at, ?) WHERE id=?", (db.now(), row["id"]))
        if left is not None:
            if any(c["type"] == "vocab" and c.get("lang") != ui_lang for c in left):
                # The UI language changed since the session was planned: rebuild the word cards.
                rng = rng or random.Random()
                words = [(k, p, i) for k, (p, i) in catalog.items.items() if isinstance(i, VocabItem)]
                distract, states = Distractors(words), scheduler.all_states(conn)
                left = [{**vocab_card(c["item_key"], *catalog.items[c["item_key"]], ui_lang, c["direction"], distract, rng,
                                      states.get(c["item_key"]), catalog), "segment": c["segment"]}
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


def _segment(item, state) -> str:
    """The label of a chosen card: a new word, a review, or an exam-format task."""
    if card_class(item) not in ("vocab", "form"):
        return "task"
    return "new" if state is None and isinstance(item, VocabItem) else "review"


def practice(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str, keys: list[str],
             rng: random.Random | None = None, kind: str = "practice") -> dict:
    """A session of chosen items (the coach's "practise these", and for checking content)."""
    rng = rng or random.Random()
    states = scheduler.all_states(conn)
    words = [(k, p, i) for k, (p, i) in catalog.items.items() if isinstance(i, VocabItem)]
    distract = Distractors(words)
    cards = []
    for k in keys:
        pack, item = catalog.items[k]
        if isinstance(item, VocabItem):
            card = vocab_card(k, pack, item, ui_lang, vocab_direction(states.get(k), False, rng), distract, rng, states.get(k),
                              catalog)
        elif isinstance(item, FormItem):
            card = form_card(k, item, states.get(k), rng)
        else:
            card = task_card(k, item, rng, in_chapter=kind == "lesson")
        cards.append({**card, "segment": _segment(item, states.get(k))})
    with conn:
        cur = conn.execute(
            "INSERT INTO sessions(started_at, kind, planned_minutes, items_planned, plan_json) VALUES (?, ?, NULL, ?, ?)",
            (db.now(), kind, len(cards), json.dumps(cards, ensure_ascii=False)),
        )
    return {"session_id": cur.lastrowid, "kind": kind, "minutes": None, "cards": cards, "resumed": False,
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
                word = {"el": item.el, "say": item.say, "meaning": meaning(item, ui_lang)}
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
    # only what a daily session may serve now: the lessons reached so far (SPEC §5.4)
    allowed, _ = gate(conn, catalog)

    def open_new(keys):
        return sum(1 for k in keys if k not in states and k in catalog.items and allowed(k, catalog.items[k][1]))

    new_available = open_new(vocab_keys)
    return {
        "answers_total": total,
        "answers_today": today_n,
        "today": today_status(conn, catalog),
        "due": {"vocab": due_vocab, "vocab_shown": min(due_vocab, REVIEW_CAP), "verbs": due_forms, "tasks": due_tasks},
        "new_available": new_available,
        "verbs_new_available": open_new(form_keys),
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


# ---------- practice the learner chooses (phase 5b) ----------

CHOICES = ("all", "words", "verbs", "reading", "listening", "tasks", "writing", "speaking", "review")


def chosen(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str, what: str, minutes: int = 10,
           stage: str | None = None, lemma: str | None = None, topic: str | None = None,
           rng: random.Random | None = None, has_voice: bool = False) -> dict:
    """A practice session of what the learner picked, from the stages they have reached.

    Due items come first, then ones not seen yet, then the longest unseen. Sized to `minutes`."""
    from oknos import curriculum

    if what not in CHOICES:
        raise ValueError(f"unknown choice {what!r}")
    rng = rng or random.Random()
    allowed, stage_rank = gate(conn, catalog)
    prog = curriculum.progress(conn, catalog)
    stage_ids = [s.id for s in prog.curriculum.stages] if prog else []
    stage_idx = stage_ids.index(stage) if stage in stage_ids else None
    states = scheduler.all_states(conn)
    last = _last_attempts(conn)
    today = db.today().isoformat()
    secs = seconds_per_card(conn, catalog)
    reserved = reserved_for_mocks(conn)

    def wanted(k, item) -> bool:
        if what == "all":
            ok = not isinstance(item, OPEN_TASKS)
        elif what == "words":
            ok = isinstance(item, VocabItem)
        elif what == "verbs":
            ok = isinstance(item, FormItem) and (not lemma or bool(item.cue and item.cue.lemma == lemma))
        elif what in ("reading", "listening"):
            ok = isinstance(item, SELECTION_TASKS) and item.skill == what
        elif what == "tasks":
            ok = isinstance(item, SELECTION_TASKS)
        elif what == "writing":
            ok = isinstance(item, WriteItem)
        elif what == "speaking":
            ok = isinstance(item, SpeakItem)
        else:  # review: what was seen and is due, or was wrong the last time
            ok = k in states and (states[k].due_at <= today or last.get(k, ("", 1))[1] == 0)
        if not ok:
            return False
        if topic and topic not in item.topics:
            return False
        if stage_idx is not None and prog.assigned.get(k) != stage_idx:
            return False
        return True

    pool = [(k, p, i) for k, p, i in servable(catalog, ui_lang)
            if allowed(k, i) and k not in reserved and wanted(k, i)]
    pool.sort(key=lambda e: (0 if e[0] in states and states[e[0]].due_at <= today else 1 if e[0] not in last else 2,
                             stage_rank(e[0]), last.get(e[0], ("", None))[0], rng.random()))
    budget = max(1, minutes) * 60
    words = [(k, p, i) for k, p, i in servable(catalog, ui_lang) if isinstance(i, VocabItem)]
    distract = Distractors(words)
    cards = []
    for k, pack, item in pool:
        cost = secs.get(card_class(item), 90)
        if cards and budget - cost < 0:
            break
        budget -= cost
        if isinstance(item, VocabItem):
            card = vocab_card(k, pack, item, ui_lang, vocab_direction(states.get(k), has_voice, rng), distract, rng,
                              states.get(k), catalog)
        elif isinstance(item, FormItem):
            card = form_card(k, item, states.get(k), rng)
        else:
            card = task_card(k, item, rng)
        cards.append({**card, "segment": _segment(item, states.get(k))})
    with conn:
        cur = conn.execute(
            "INSERT INTO sessions(started_at, kind, planned_minutes, items_planned, plan_json) VALUES (?, 'practice', ?, ?, ?)",
            (db.now(), minutes, len(cards), json.dumps(cards, ensure_ascii=False)))
    return {"session_id": cur.lastrowid, "kind": "practice", "minutes": minutes, "cards": cards, "resumed": False,
            "total": len(cards), "done": 0, "available": len(pool)}


def status_of(state: scheduler.State | None) -> str:
    """new (not seen yet), learning, secure (an interval of 6+ days) or known (21+ days)."""
    if state is None:
        return "new"
    if state.interval_days >= scheduler.KNOWN_DAYS:
        return "known"
    if state.interval_days >= 6:
        return "secure"
    return "learning"


def choice_counts(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str, stage: str | None = None) -> dict:
    """For the Practise screen: per choice, how many cards are due, how many are new, and the mistakes.

    The same classes as `chosen`, from the stages reached (and one stage, when given)."""
    from oknos import curriculum

    allowed, _ = gate(conn, catalog)
    prog = curriculum.progress(conn, catalog)
    stage_ids = [s.id for s in prog.curriculum.stages] if prog else []
    stage_idx = stage_ids.index(stage) if stage in stage_ids else None
    states = scheduler.all_states(conn)
    last = _last_attempts(conn)
    today = db.today().isoformat()
    reserved = reserved_for_mocks(conn)
    out = {c: {"due": 0, "new": 0, "total": 0} for c in ("words", "verbs", "reading", "listening", "writing", "speaking")}
    mistakes = due_all = 0
    for k, _, item in servable(catalog, ui_lang):
        if not allowed(k, item) or k in reserved:
            continue
        if stage_idx is not None and (not prog or prog.assigned.get(k) != stage_idx):
            continue
        if isinstance(item, VocabItem):
            kind = "words"
        elif isinstance(item, FormItem):
            kind = "verbs"
        elif isinstance(item, SELECTION_TASKS) and item.skill in ("reading", "listening"):
            kind = item.skill
        elif isinstance(item, WriteItem):
            kind = "writing"
        elif isinstance(item, SpeakItem):
            kind = "speaking"
        else:
            kind = None
        st = states.get(k)
        due = st is not None and st.due_at <= today
        wrong = st is not None and last.get(k, ("", 1))[1] == 0
        due_all += due
        mistakes += wrong
        if kind:
            c = out[kind]
            c["total"] += 1
            c["due"] += due
            c["new"] += st is None
    out["review"] = {"due": due_all, "mistakes": mistakes}
    return out


def stage_pictures(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str, per_stage: int = 4) -> dict[str, list[dict]]:
    """For the Book: a few of each stage's words that have a picture."""
    from oknos import curriculum

    prog = curriculum.progress(conn, catalog)
    if not prog:
        return {}
    stages = prog.curriculum.stages
    out: dict[str, list[dict]] = {}
    for k, idx in prog.assigned.items():
        entry = catalog.items.get(k)
        if idx is None or entry is None or not isinstance(entry[1], VocabItem):
            continue
        pics = out.setdefault(stages[idx].id, [])
        if len(pics) >= per_stage:
            continue
        url = picture_url(entry[1])
        if url and all(x["picture"] != url for x in pics):
            pics.append({"el": entry[1].el, "meaning": meaning(entry[1], ui_lang), "picture": url})
    return out


def word_list(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str) -> dict:
    """Every word, with its stage, whether it is open yet, and how well it is known."""
    from oknos import curriculum

    prog = curriculum.progress(conn, catalog)
    states = scheduler.all_states(conn)
    allowed, _ = gate(conn, catalog)
    stages = prog.curriculum.stages if prog else []
    rows = []
    for k, p, i in servable(catalog, ui_lang):
        if not isinstance(i, VocabItem):
            continue
        idx = prog.assigned.get(k) if prog else None
        rows.append({"key": k, "el": i.el, "say": i.say, "meaning": meaning(i, ui_lang), "meaning_lang": meaning_lang(i, ui_lang),
                     "pos": i.pos, "level": i.level,
                     "stage": stages[idx].id if idx is not None else None, "stage_order": idx,
                     "open": allowed(k, i), "extra": bool(prog and k in prog.pooled),
                     "status": status_of(states.get(k)), "picture": picture_url(i),
                     "topics": [t for t in i.topics if not t.startswith(("unit:", "stage:"))]})
    rows.sort(key=lambda r: (r["stage_order"] if r["stage_order"] is not None else 999, r["extra"], r["el"]))
    return {"words": rows, "stages": [{"id": s.id, "title": s.title.model_dump()} for s in stages]}


def verb_table(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str) -> dict:
    """Every verb with its forms per tense and person, and whether each is open and known."""
    from oknos import curriculum

    prog = curriculum.progress(conn, catalog)
    states = scheduler.all_states(conn)
    allowed, _ = gate(conn, catalog)
    verbs: dict[str, dict] = {}
    for k, p, i in servable(catalog, ui_lang):
        if not isinstance(i, FormItem) or not i.cue or not i.cue.lemma:
            continue
        v = verbs.setdefault(i.cue.lemma, {"lemma": i.cue.lemma, "forms": [], "first_stage": 999})
        idx = prog.assigned.get(k) if prog else None
        if idx is not None:
            v["first_stage"] = min(v["first_stage"], idx)
        answer = next(iter(i.answer.values()))[0]
        v["forms"].append({"key": k, "tense": i.cue.tense, "person": i.cue.person, "form": answer, "text": i.text,
                           "open": allowed(k, i), "status": status_of(states.get(k))})
    out = sorted(verbs.values(), key=lambda v: (v["first_stage"], v["lemma"]))
    for v in out:
        v["open"] = any(f["open"] for f in v["forms"])
        v["known"] = sum(1 for f in v["forms"] if f["status"] in ("secure", "known"))
    # the lessons the verbs are grouped under: the screen lists them lesson by lesson
    stages = ([{"index": i, "id": st.id, "title": st.title.model_dump()} for i, st in enumerate(prog.curriculum.stages)]
              if prog else [])
    return {"verbs": out, "stages": stages, "current": prog.current if prog else None}


def stage_detail(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str, stage_id: str) -> dict | None:
    from oknos import curriculum

    prog = curriculum.progress(conn, catalog)
    if prog is None or stage_id not in [s.id for s in prog.curriculum.stages]:
        return None
    idx = prog.curriculum.index(stage_id)
    st = prog.stages[idx]
    states = scheduler.all_states(conn)
    seen = {r[0] for r in conn.execute("SELECT DISTINCT item_key FROM attempts")}
    words, forms, tasks = [], [], []
    for k, v in prog.assigned.items():
        if v != idx or k in prog.pooled:
            continue
        i = catalog.items[k][1]
        if i.status != "ok":
            continue
        if isinstance(i, VocabItem):
            words.append({"key": k, "el": i.el, "say": i.say, "meaning": meaning(i, ui_lang),
                          "meaning_lang": meaning_lang(i, ui_lang), "status": status_of(states.get(k))})
        elif isinstance(i, FormItem):
            forms.append({"key": k, "lemma": i.cue.lemma if i.cue else None, "tense": i.cue.tense if i.cue else None,
                          "person": i.cue.person if i.cue else None, "form": next(iter(i.answer.values()))[0],
                          "status": status_of(states.get(k))})
        else:
            tasks.append({"key": k, "type": i.type, "skill": i.skill, "exam_task": i.exam_task, "seen": k in seen})
    spec = prog.curriculum.stages[idx]
    return {**st, "can_check": idx <= prog.current + 1 and bool(words or forms or tasks),
            "review_of": spec.review_of, "words_list": words, "forms_list": forms, "tasks_list": tasks,
            "extra_words": st["extra_from_pool"]}


# ---------- chapters: read first, then practise (phase 5c) ----------

def _letter_says(catalog: Catalog) -> dict[str, str]:
    """What a letter's card says aloud ("άλφα. ταξί"), by the letter as written ("Α α")."""
    if getattr(catalog, "_letter_says", None) is None:
        catalog._letter_says = {" ".join(i.el.split()): i.say for _, i in catalog.items.values()  # type: ignore[attr-defined]
                                if isinstance(i, VocabItem) and i.say and i.pos in ("letter", "digraph")}
    return catalog._letter_says  # type: ignore[attr-defined]


def table_say(cell, catalog: Catalog) -> str | None:
    """What the ▶ of a chapter table's row reads: a letter as its alphabet card says it (its name and
    an example word), a Greek word or letter pair as written; nothing for a row headed in Turkish or
    English, or for a lone letter with no card (a voice reading "Α α" helps no one)."""
    if not isinstance(cell, str) or not greek.has_greek(cell):
        return None
    text = " ".join(cell.split())
    if text in _letter_says(catalog):
        return _letter_says(catalog)[text]
    return text if any(len(w) > 1 for w in greek.words(text)) else None


def chapter_view(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str, stage_id: str) -> dict | None:
    """A stage's chapter as the reader shows it: the blocks, with words resolved to their item
    (Greek, meaning, status), and where the learner is in it."""
    from oknos import curriculum

    prog = curriculum.progress(conn, catalog)
    if prog is None or stage_id not in [s.id for s in prog.curriculum.stages]:
        return None
    ch = catalog.chapter(prog.curriculum.id, stage_id)
    if ch is None:
        return None
    states = scheduler.all_states(conn)
    idx = prog.curriculum.index(stage_id)
    sections = []
    for sec in ch.sections:
        blocks = []
        for b in sec.blocks:
            out = b.model_dump()
            if b.type == "words":
                out["words"] = []
                for k in b.items:
                    entry = catalog.items.get(k)
                    if entry is None or not isinstance(entry[1], VocabItem):
                        continue
                    i = entry[1]
                    out["words"].append({"key": k, "el": i.el, "say": i.say, "meaning": meaning(i, ui_lang),
                                         "meaning_lang": meaning_lang(i, ui_lang), "pos": i.pos,
                                         "gender": i.gender, "status": status_of(states.get(k)),
                                         "example": i.example.model_dump() if i.example else None})
            elif b.type == "dialogue":
                from oknos import voice
                for ln in out["lines"]:
                    ln["role"] = voice.role_of(ln["who"])  # each speaker's voice (phase 10)
                if b.picture:
                    out["picture"] = f"/pictures/{catalog.chapters[(prog.curriculum.id, stage_id)][0].id}/{b.picture}"
            elif b.type == "check":
                out["items"] = [k for k in b.items if k in catalog.items and catalog.items[k][1].type not in ("write", "speak")]
            elif b.type == "table":
                out["says"] = [table_say(row[0], catalog) if row else None for row in b.rows]
            blocks.append(out)
        sections.append({"kind": sec.kind, "title": sec.title.model_dump() if sec.title else None, "blocks": blocks})
    read = curriculum.chapter_reads(conn, prog.curriculum.id).get(stage_id)
    st = prog.stages[idx]
    nxt = prog.stages[idx + 1] if idx + 1 < len(prog.stages) else None
    # the neighbouring chapters, for "previous / next chapter" (stages without one are skipped)
    with_chapter = [(i, s) for i, s in enumerate(prog.curriculum.stages) if catalog.chapter(prog.curriculum.id, s.id)]

    def brief(i, s):
        c = catalog.chapter(prog.curriculum.id, s.id)
        return {"id": s.id, "title": c.title.model_dump(), "stage_title": s.title.model_dump()}

    prev_ch = next((brief(i, s) for i, s in reversed(with_chapter) if i < idx), None)
    next_ch = next((brief(i, s) for i, s in with_chapter if i > idx), None)
    return {"prev_chapter": prev_ch, "next_chapter": next_ch,"curriculum": prog.curriculum.id, "stage": stage_id, "stage_title": st["title"], "state": st["state"],
            "id": ch.id, "version": ch.version, "level": ch.level, "title": ch.title.model_dump(), "minutes": ch.minutes,
            "sections": sections, "share": st["share"], "learned": st["learned"], "core": st["core"],
            "read": {"opened_at": read["opened_at"], "finished_at": read["finished_at"],
                     "sections": json.loads(read["sections_json"])} if read else None,
            "next": {"id": nxt["id"], "title": nxt["title"], "chapter": bool(nxt["chapter"])} if nxt else None}


def chapter_checks(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str, stage_id: str, keys: list[str]) -> dict:
    """A short session of a chapter's "try it" items, of kind 'lesson': the answers train the
    review schedule but never count as exam evidence (readiness.for_blueprint)."""
    from oknos import curriculum

    cur = curriculum.active(catalog)
    ch = catalog.chapter(cur.id, stage_id) if cur else None
    if ch is None:
        raise ValueError("this stage has no chapter")
    allowed = set(ch.check_keys())
    keys = [k for k in keys if k in allowed and k in catalog.items] or [k for k in ch.check_keys() if k in catalog.items]
    if not keys:
        raise ValueError("this chapter has no check items")
    return practice(conn, catalog, ui_lang, keys, kind="lesson")


def chapter_practice(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str, stage_id: str, minutes: int = 10,
                     has_voice: bool = False) -> dict:
    """"Done reading — practise this chapter": marks the chapter read, then a session of exactly
    this stage's items (its words first: the ones the chapter taught)."""
    from oknos import curriculum

    cur = curriculum.active(catalog)
    ch = catalog.chapter(cur.id, stage_id) if cur else None
    if ch is None:
        raise ValueError("this stage has no chapter")
    curriculum.mark_read(conn, cur.id, stage_id, ch.version, finished=True)
    out = chosen(conn, catalog, ui_lang, "all", minutes, stage=stage_id, has_voice=has_voice)
    words = ch.word_keys()
    order = {k: i for i, k in enumerate(words)}
    out["cards"].sort(key=lambda c: (0 if c["item_key"] in order else 1, order.get(c["item_key"], 0)))
    with conn:
        conn.execute("UPDATE sessions SET plan_json=? WHERE id=?", (json.dumps(out["cards"], ensure_ascii=False), out["session_id"]))
    out["stage"] = stage_id
    return out


def home_words(conn: sqlite3.Connection, catalog: Catalog, ui_lang: str, limit: int = 4) -> dict | None:
    """The words the home screen shows: the current lesson's, and the new ones that come next.
    Those with a picture come first (phase 9). None without a curriculum."""
    from oknos import curriculum

    prog = curriculum.progress(conn, catalog)
    if prog is None:
        return None
    states = scheduler.all_states(conn)
    allowed, _ = gate(conn, catalog)
    lesson, new = [], []
    for k, idx in prog.assigned.items():
        entry = catalog.items.get(k)
        if idx is None or entry is None or not isinstance(entry[1], VocabItem) or entry[1].status != "ok":
            continue
        item = entry[1]
        word = {"key": k, "el": item.el, "meaning": meaning(item, ui_lang), "picture": picture_url(item)}
        if idx == prog.current and k not in prog.pooled:
            lesson.append(word)
        if k not in states and idx <= prog.current and allowed(k, item):
            new.append(word)
    pictures_first = lambda words: sorted(words, key=lambda w: w["picture"] is None)  # noqa: E731
    return {"lesson": pictures_first(lesson)[:limit], "new": pictures_first(new)[:limit], "new_count": len(new)}
