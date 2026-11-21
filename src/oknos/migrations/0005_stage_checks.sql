-- Phase 5b: stage checks ("I know this lesson, test me"), docs/SPEC.md §5.4.
-- A passed check marks a curriculum stage done, so the next one opens.

CREATE TABLE IF NOT EXISTS stage_checks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    curriculum  TEXT NOT NULL,
    stage       TEXT NOT NULL,
    session_id  INTEGER REFERENCES sessions(id),
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    score       REAL,
    passed      INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS stage_checks_stage ON stage_checks(curriculum, stage, passed);
