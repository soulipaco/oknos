-- Phase 2: the tables the walking skeleton uses (docs/SPEC.md §5.1).
-- Later phases add review_state, lookups, flags, submissions and mock_runs
-- as further numbered migrations.

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS items (
    item_key      TEXT PRIMARY KEY,      -- "<pack-id>/<item-id>"
    pack_id       TEXT NOT NULL,
    type          TEXT NOT NULL,
    skill         TEXT NOT NULL,
    exam_task     TEXT,
    level         TEXT NOT NULL,
    content_hash  TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    retired_at    TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    kind            TEXT NOT NULL,       -- daily | extra | mock | practice
    planned_minutes INTEGER,
    items_planned   INTEGER,
    items_done      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS attempts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    INTEGER REFERENCES sessions(id),
    item_key      TEXT NOT NULL REFERENCES items(item_key),
    ts            TEXT NOT NULL,
    response_json TEXT NOT NULL,
    score         REAL,                  -- 0..1
    correct       INTEGER,               -- 1/0, NULL for write/speak
    latency_ms    INTEGER,
    lookups       INTEGER NOT NULL DEFAULT 0,
    audio_plays   INTEGER NOT NULL DEFAULT 0,
    accent_note   TEXT
);

CREATE INDEX IF NOT EXISTS attempts_item ON attempts(item_key, ts);
CREATE INDEX IF NOT EXISTS attempts_session ON attempts(session_id);
