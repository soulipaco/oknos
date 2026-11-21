-- Phase 4: writing and speaking submissions, which the coach marks (docs/SPEC.md §5.1).
-- The coach never writes here: it writes learner/feedback/<id>.json, and the app sets
-- status='marked' and feedback_path when it sees the file.

CREATE TABLE IF NOT EXISTS submissions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    item_key       TEXT NOT NULL,
    session_id     INTEGER REFERENCES sessions(id),
    attempt_id     INTEGER REFERENCES attempts(id),
    ts             TEXT NOT NULL,
    kind           TEXT NOT NULL,        -- writing | speaking
    text           TEXT,                 -- writing: what the learner wrote
    recording_path TEXT,                 -- speaking: relative to learner/, e.g. recordings/12.webm
    word_count     INTEGER,
    status         TEXT NOT NULL DEFAULT 'new',   -- new | marked
    feedback_path  TEXT,                 -- relative to learner/, e.g. feedback/12.json
    feedback_seen_at TEXT                -- when the learner opened the feedback in the app
);

CREATE INDEX IF NOT EXISTS submissions_status ON submissions(status, ts);
