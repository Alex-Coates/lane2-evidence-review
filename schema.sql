-- Lane 2 Evidence Review: database schema (SQLite)
-- users 1---* submissions 1---* turns
--                         1---* flags 1---0..1 decisions
--                         1---* llm_runs (one row per critique check)
-- settings holds housekeeping values such as the data version.

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('student', 'marker')),
    display_name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submissions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ref          TEXT NOT NULL UNIQUE,              -- shown to users, e.g. SUB-013
    student_id   INTEGER NOT NULL REFERENCES users(id),
    topic        TEXT NOT NULL,
    final_text   TEXT NOT NULL,
    submitted_at TEXT NOT NULL,                     -- UTC, ISO 8601
    status       TEXT NOT NULL DEFAULT 'Not started'
                 CHECK (status IN ('Not started', 'In progress', 'Reviewed')),
    overall_note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS turns (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    position      INTEGER NOT NULL,                 -- 0-based order in the transcript
    role          TEXT NOT NULL CHECK (role IN ('Student', 'AI')),
    text          TEXT NOT NULL,
    UNIQUE (submission_id, position)
);

CREATE TABLE IF NOT EXISTS flags (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    flag_key      TEXT NOT NULL,                    -- e.g. overlap-0, critique-2
    type          TEXT NOT NULL CHECK (type IN ('Text overlap', 'Critique quality')),
    origin        TEXT NOT NULL DEFAULT 'rule' CHECK (origin IN ('rule', 'llm')),  -- rule = wording comparison, llm = critique check
    verdict       TEXT,                             -- critique flags: blind_acceptance or generic
    quote         TEXT,                             -- critique flags: verified quote from the student reply
    paragraph     INTEGER,                          -- overlap flags only
    turn_index    INTEGER NOT NULL,
    score         REAL,                             -- overlap flags only
    source_text   TEXT NOT NULL,
    target_text   TEXT NOT NULL,
    reason        TEXT NOT NULL,
    UNIQUE (submission_id, flag_key)
);

CREATE TABLE IF NOT EXISTS decisions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flag_id    INTEGER NOT NULL UNIQUE REFERENCES flags(id) ON DELETE CASCADE,
    marker_id  INTEGER NOT NULL REFERENCES users(id),
    decision   TEXT NOT NULL
               CHECK (decision IN ('Accept flag', 'Dismiss flag', 'Need more context')),
    rationale  TEXT NOT NULL,
    decided_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- One row per critique check (see llm_flags.py). The newest row for a submission is the one used.
CREATE TABLE IF NOT EXISTS llm_runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id  INTEGER NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    status         TEXT NOT NULL,                   -- ok, error, unavailable, not_run, off, not_applicable
    mode           TEXT NOT NULL,                   -- live, cached, mock, none
    model          TEXT,
    rubric_version TEXT NOT NULL,
    error          TEXT,                            -- plain-English reason, never contains the API key
    result_json    TEXT NOT NULL,                   -- kept assessments and rejected ones
    created_at     TEXT NOT NULL
);
