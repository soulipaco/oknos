-- Phase 5c: reading progress in a stage's chapter (docs/SPEC.md §4.8, §5.4).
-- A stage's new items enter daily sessions only once its chapter is finished.

CREATE TABLE IF NOT EXISTS chapter_reads (
    curriculum      TEXT NOT NULL,
    stage           TEXT NOT NULL,
    chapter_version INTEGER NOT NULL DEFAULT 1,
    opened_at       TEXT NOT NULL,
    finished_at     TEXT,                  -- "Done reading" was pressed
    sections_json   TEXT NOT NULL DEFAULT '[]',   -- the section numbers seen, in order
    PRIMARY KEY (curriculum, stage)
);
