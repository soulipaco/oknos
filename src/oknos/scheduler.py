"""Spaced repetition: SM-2, as in SuperMemo 2 and early Anki (docs/SPEC.md §5.1).

Every vocab and verb-form item is scheduled from the first time it is seen. Any other item
joins the schedule the first time it is answered wrongly, and stays until it is learnt.

Quality (0-5) comes from the attempt, because the learner never grades themselves:
  wrong (or any part wrong)                 -> 1, a lapse: back tomorrow, ease down
  right, but after a lookup or accent note  -> 3
  right                                     -> 4
  right and quick                           -> 5
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta

from oknos import db

ALWAYS_SCHEDULED = {"vocab", "form"}
MIN_EASE = 1.3
START_EASE = 2.5
KNOWN_DAYS = 21  # an item with an interval this long counts as "known" on the home screen
LOOKUP_EASE_PENALTY = 0.15


@dataclass
class State:
    item_key: str
    due_at: str
    interval_days: float = 0.0
    ease: float = START_EASE
    reps: int = 0
    lapses: int = 0
    last_score: float | None = None
    last_seen_at: str | None = None


def quality(correct: bool, lookups: int = 0, accent_note: bool = False, quick: bool = False) -> int:
    if not correct:
        return 1
    if lookups or accent_note:
        return 3
    return 5 if quick else 4


def next_state(state: State, q: int, today: date) -> State:
    """The SM-2 step. Intervals: 1 day, 6 days, then the previous interval times the ease."""
    if q < 3:
        state.reps = 0
        state.lapses += 1
        state.interval_days = 1
    else:
        state.reps += 1
        if state.reps == 1:
            state.interval_days = 1
        elif state.reps == 2:
            state.interval_days = 6
        else:
            state.interval_days = round(state.interval_days * state.ease, 1)
    state.ease = max(MIN_EASE, state.ease + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    state.due_at = (today + timedelta(days=max(1, round(state.interval_days)))).isoformat()
    return state


def get(conn: sqlite3.Connection, item_key: str) -> State | None:
    row = conn.execute("SELECT * FROM review_state WHERE item_key=?", (item_key,)).fetchone()
    return State(**dict(row)) if row else None


def save(conn: sqlite3.Connection, s: State) -> None:
    conn.execute(
        """
        INSERT INTO review_state(item_key, due_at, interval_days, ease, reps, lapses, last_score, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(item_key) DO UPDATE SET due_at=excluded.due_at, interval_days=excluded.interval_days,
            ease=excluded.ease, reps=excluded.reps, lapses=excluded.lapses,
            last_score=excluded.last_score, last_seen_at=excluded.last_seen_at
        """,
        (s.item_key, s.due_at, s.interval_days, s.ease, s.reps, s.lapses, s.last_score, s.last_seen_at),
    )


def record(conn: sqlite3.Connection, item_key: str, item_type: str, correct: bool, score: float,
           lookups: int = 0, accent_note: bool = False, quick: bool = False) -> State | None:
    """Update the schedule after an attempt. Call inside the attempt's transaction."""
    today = db.today()
    state = get(conn, item_key)
    if state is None:
        if item_type not in ALWAYS_SCHEDULED and correct:
            return None  # right first time: not worth scheduling
        state = State(item_key=item_key, due_at=today.isoformat())
    state = next_state(state, quality(correct, lookups, accent_note, quick), today)
    state.last_score = score
    state.last_seen_at = db.now()
    save(conn, state)
    return state


def lookup_signal(conn: sqlite3.Connection, vocab_key: str) -> None:
    """Tapping a word means "I did not know it": its card comes back today, a little harder."""
    today = db.today().isoformat()
    state = get(conn, vocab_key)
    if state is None:
        state = State(item_key=vocab_key, due_at=today)  # an unseen word joins today's reviews
    else:
        state.due_at = min(state.due_at, today)
        state.ease = max(MIN_EASE, state.ease - LOOKUP_EASE_PENALTY)
    save(conn, state)


def due(conn: sqlite3.Connection, on: date | None = None) -> list[State]:
    """Items due on or before a day, most overdue first, then most-lapsed first."""
    day = (on or db.today()).isoformat()
    rows = conn.execute(
        "SELECT * FROM review_state WHERE due_at <= ? ORDER BY due_at, lapses DESC, ease", (day,)
    ).fetchall()
    return [State(**dict(r)) for r in rows]


def all_states(conn: sqlite3.Connection) -> dict[str, State]:
    return {r["item_key"]: State(**dict(r)) for r in conn.execute("SELECT * FROM review_state").fetchall()}
