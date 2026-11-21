-- Phase 3: spaced repetition, lookups, flags, and resumable sessions (docs/SPEC.md §5.1).

CREATE TABLE IF NOT EXISTS review_state (
    item_key      TEXT PRIMARY KEY REFERENCES items(item_key),
    due_at        TEXT NOT NULL,          -- local date YYYY-MM-DD the item is next due
    interval_days REAL NOT NULL DEFAULT 0,
    ease          REAL NOT NULL DEFAULT 2.5,
    reps          INTEGER NOT NULL DEFAULT 0,   -- successful reviews in a row
    lapses        INTEGER NOT NULL DEFAULT 0,
    last_score    REAL,
    last_seen_at  TEXT
);

CREATE INDEX IF NOT EXISTS review_due ON review_state(due_at);

CREATE TABLE IF NOT EXISTS lookups (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    item_key TEXT,                 -- the item on screen when the word was tapped
    word     TEXT NOT NULL,
    found    TEXT                  -- item_key of the vocab item that explained it, if any
);

CREATE INDEX IF NOT EXISTS lookups_ts ON lookups(ts);

CREATE TABLE IF NOT EXISTS flags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    item_key    TEXT NOT NULL,
    reason      TEXT NOT NULL,     -- wrong | confusing | audio
    note        TEXT,
    resolved_at TEXT,
    resolution  TEXT
);

ALTER TABLE sessions ADD COLUMN plan_json TEXT;
