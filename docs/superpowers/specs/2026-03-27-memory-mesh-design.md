# memory-mesh Design Spec

**Date:** 2026-03-27
**Status:** Approved
**License:** MIT
**Target:** pip-installable, 1k GitHub stars

---

## 1. Overview

memory-mesh is a local-first MCP server that gives all AI assistants (Claude, ChatGPT, Gemini, and others) shared, persistent memory. It exposes two transports over a single `MemoryStore` core: an MCP stdio server for Claude Desktop (zero-config) and a REST API on `localhost:8765` for any other AI or integration.

Core capabilities:
- `save_context` — persist a memory entry with optional key, tags, and session grouping
- `search_context` — semantic search via ChromaDB embeddings
- Conflict detection — 3-layer pipeline catches when AIs disagree
- Conflict resolution — user resolves truth via CLI or MCP tools

---

## 2. Architecture

### Package Structure

```
memory_mesh/
├── __init__.py
├── cli.py                    # Entry points: serve, mcp, conflicts
├── config.py                 # Config from ~/.memory-mesh/config.json
├── core/
│   ├── store.py              # MemoryStore — all business logic
│   ├── conflict.py           # ConflictDetector (3-layer pipeline)
│   └── models.py             # Pydantic models: MemoryEntry, Conflict, Resolution
├── storage/
│   ├── chroma.py             # ChromaDB adapter (embeddings + search)
│   ├── sqlite.py             # SQLite adapter (metadata + conflict state)
│   └── migrations/
│       └── 001_initial.sql   # Schema v1
└── transports/
    ├── mcp_server.py         # MCP stdio adapter — thin wrapper over MemoryStore
    └── rest_server.py        # FastAPI REST adapter — thin wrapper over MemoryStore
```

### Data Flow

1. Client calls `save_context` or `search_context` via MCP or REST
2. Transport adapter validates input, calls `MemoryStore`
3. `MemoryStore` writes to SQLite (metadata) first, then ChromaDB (embedding) — same UUID links both; SQLite is source of truth if ChromaDB write fails
4. `ConflictDetector` runs synchronously on every save — fast layers first
5. Detected conflicts written to SQLite `conflicts` table, returned in the response so the calling AI can surface them immediately without polling

### Entry Points (pyproject.toml scripts)

| Command | Effect |
|---------|--------|
| `memory-mesh serve` | REST API on `127.0.0.1:8765` |
| `memory-mesh mcp` | stdio MCP server (referenced in `claude_desktop_config.json`) |
| `memory-mesh conflicts` | Interactive CLI conflict browser |

---

## 3. Data Model

### SQLite Schema (`001_initial.sql`)

```sql
CREATE TABLE memories (
    id          TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    key         TEXT,
    content     TEXT NOT NULL,
    tags        TEXT,               -- JSON array e.g. ["project", "preference"]
    session_id  TEXT,               -- groups saves from the same conversation
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE conflicts (
    id              TEXT PRIMARY KEY,
    memory_a_id     TEXT NOT NULL REFERENCES memories(id),
    memory_b_id     TEXT NOT NULL REFERENCES memories(id),
    trigger         TEXT NOT NULL,  -- "key_match" | "similarity" | "nli"
    status          TEXT NOT NULL,  -- "pending" | "resolved"
    resolution_id   TEXT,           -- winning memory UUID, NULL until resolved
    resolved_by     TEXT,           -- "cli" | "mcp" | null
    resolved_at     TEXT,
    created_at      TEXT NOT NULL
);

CREATE INDEX idx_memories_key     ON memories(key)        WHERE key        IS NOT NULL;
CREATE INDEX idx_memories_session ON memories(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX idx_conflicts_status ON conflicts(status);
```

### ChromaDB

- One collection: `memory_mesh`
- Documents keyed by the same UUID as SQLite `memories.id`
- Metadata stored in ChromaDB: `agent_id`, `key` (for pre-filter before vector search)
- Everything else lives in SQLite

### Pydantic Models (`models.py`)

- `MemoryEntry` — mirrors `memories` table; `tags` as `list[str]`
- `Conflict` — mirrors `conflicts` table; embeds both `MemoryEntry` objects for display
- `Resolution` — input model: `conflict_id`, `winning_id`, `resolved_by`

---

## 4. API Surface

### MCP Tools

| Tool | Input | Returns |
|------|-------|---------|
| `save_context` | `content`, `key?`, `tags?`, `session_id?` | `MemoryEntry` + `Conflict[]` |
| `search_context` | `query`, `limit?=10`, `agent_id?`, `key?`, `tags?` | `MemoryEntry[]` with scores |
| `list_conflicts` | `status?="pending"` | `Conflict[]` |
| `resolve_conflict` | `conflict_id`, `winning_id` | updated `Conflict` |
| `delete_context` | `memory_id` | `{success: bool}` |

### REST Endpoints (FastAPI, prefix `/v1`)

```
POST   /v1/memories               save_context
GET    /v1/memories/search?q=...  search_context
GET    /v1/conflicts              list_conflicts
POST   /v1/conflicts/{id}/resolve resolve_conflict
DELETE /v1/memories/{id}          delete_context
```

All REST responses use the same Pydantic models as MCP — identical JSON.

**`agent_id` source:**
- MCP: inferred from the MCP client name in the handshake; defaults to `"claude"` if not provided
- REST: required field in the request body (callers self-identify)

`save_context` always returns detected conflicts inline — no polling needed.

---

## 5. Conflict Detection Pipeline

`ConflictDetector.check(new_entry, store)` runs synchronously on every save.

### Layer 1 — Key Match (always on, ~0ms)

```
IF new_entry.key IS NOT NULL:
    fetch all memories WHERE key = new_entry.key AND id != new_entry.id
    IF any exist with different content → conflict(trigger="key_match")
```

### Layer 2 — Similarity Threshold (always on, ~10–50ms)

```
search ChromaDB for top-5 nearest neighbors to new_entry embedding
FOR each result WHERE cosine_similarity > 0.85:
    SKIP if same agent_id AND same session_id   ← update, not conflict
    IF content differs by > 20% (difflib ratio) → conflict(trigger="similarity")
    SKIP if already caught by Layer 1 (dedup by memory pair)
```

### Layer 3 — NLI Contradiction (opt-in, ~200–500ms)

```
IF config.nli_enabled:
    FOR each candidate from Layer 2:
        run cross-encoder contradiction classifier
        IF label="contradiction" AND score > 0.7 → conflict(trigger="nli")
```

### Conflict Deduplication

Before inserting a new conflict, check if a `pending` conflict already exists for the same `(memory_a_id, memory_b_id)` pair — skip if so.

### Config Knobs (`~/.memory-mesh/config.json`)

```json
{
  "similarity_threshold": 0.85,
  "diff_ratio_threshold": 0.20,
  "nli_enabled": false,
  "nli_model": "cross-encoder/nli-deberta-v3-small",
  "host": "127.0.0.1",
  "port": 8765,
  "auth_enabled": false,
  "auth_token": null
}
```

---

## 6. Security Model

- REST binds to `127.0.0.1` by default (localhost-only, same pattern as Ollama)
- No auth required in default config — zero friction for onboarding
- Optional auth + LAN exposure: `memory-mesh serve --auth --host 0.0.0.0`
- When `auth_enabled=true`, REST requires `Authorization: Bearer <token>` on all requests
- Token generated on first `serve --auth` run, stored in `~/.memory-mesh/config.json`

---

## 7. Testing Strategy

### Unit Tests (`tests/unit/`) — no I/O, fast

- `test_conflict_detector.py` — each layer independently with mock `MemoryStore`; key match, similarity threshold, same-agent skip, NLI toggle, dedup logic
- `test_models.py` — Pydantic validation, serialization edge cases
- `test_config.py` — config loading, defaults, env var overrides

### Integration Tests (`tests/integration/`) — real SQLite + real ChromaDB (tmp dir)

- `test_store.py` — save/search/delete round-trips, UUID consistency across both stores
- `test_conflict_pipeline.py` — save two conflicting entries, assert conflict row created with correct trigger, resolve, assert status updated
- `test_migrations.py` — apply `001_initial.sql` to fresh DB, assert schema matches models

### Transport Tests (`tests/transports/`) — thin wiring only

- `test_rest.py` — FastAPI `TestClient`, one happy-path + one error case per endpoint
- `test_mcp.py` — invoke MCP tools via SDK test harness, assert correct `MemoryStore` methods called

**Rule:** No mocking of ChromaDB or SQLite in integration tests. Real stores in a temp dir catch the bugs that matter. Mock only in unit tests where I/O is genuinely irrelevant.

---

## 8. Distribution

- **Package:** `pip install memory-mesh`
- **Python:** 3.11+
- **License:** MIT
- **Dependencies:** `mcp`, `chromadb`, `sentence-transformers`, `fastapi`, `uvicorn`, `pydantic`, `click`
- **Optional:** `cross-encoder/nli-deberta-v3-small` (only downloaded if `nli_enabled=true`)

Claude Desktop config snippet (included in docs):
```json
{
  "mcpServers": {
    "memory-mesh": {
      "command": "memory-mesh",
      "args": ["mcp"]
    }
  }
}
```
