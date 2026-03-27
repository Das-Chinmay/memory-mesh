CREATE TABLE IF NOT EXISTS memories (
    id          TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    key         TEXT,
    content     TEXT NOT NULL,
    tags        TEXT NOT NULL DEFAULT '[]',
    session_id  TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conflicts (
    id              TEXT PRIMARY KEY,
    memory_a_id     TEXT NOT NULL REFERENCES memories(id),
    memory_b_id     TEXT NOT NULL REFERENCES memories(id),
    trigger         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    resolution_id   TEXT,
    resolved_by     TEXT,
    resolved_at     TEXT,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memories_key
    ON memories(key) WHERE key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_memories_session
    ON memories(session_id) WHERE session_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_conflicts_status
    ON conflicts(status);
