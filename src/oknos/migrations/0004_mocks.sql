-- Phase 5: timed mock exams (docs/SPEC.md §5.1). A run is one sitting of a mock the coach
-- defined in learner/coach/mocks/<id>.json; each unit of the exam is a timed section.

CREATE TABLE IF NOT EXISTS mock_runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    blueprint        TEXT NOT NULL,             -- a2ltr | b1-keg
    mock_id          TEXT NOT NULL,             -- the file name in coach/mocks/
    started_at       TEXT NOT NULL,
    finished_at      TEXT,
    status           TEXT NOT NULL DEFAULT 'running',   -- running | finished | abandoned
    unit_scores_json TEXT                       -- {unit: {points, out_of, ...}} once finished
);

CREATE TABLE IF NOT EXISTS mock_sections (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        INTEGER NOT NULL REFERENCES mock_runs(id),
    unit          TEXT NOT NULL,
    session_id    INTEGER REFERENCES sessions(id),     -- kind 'mock'; the graded attempts belong to it
    started_at    TEXT NOT NULL,
    ends_at       TEXT NOT NULL,                       -- the server's clock decides when time is up
    closed_at     TEXT,
    closed_by     TEXT,                                -- learner | time | time_away
    answers_json  TEXT NOT NULL DEFAULT '{}',          -- drafts, saved as the learner answers
    last_saved_at TEXT,
    result_json   TEXT,
    UNIQUE(run_id, unit)
);

CREATE INDEX IF NOT EXISTS mock_sections_run ON mock_sections(run_id);
