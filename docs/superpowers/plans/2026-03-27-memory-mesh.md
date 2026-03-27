# memory-mesh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first MCP + REST server that gives all AI assistants shared persistent memory with semantic search and 3-layer conflict detection.

**Architecture:** Monolith with a shared `MemoryStore` core. Two thin transport adapters (MCP stdio for Claude Desktop, FastAPI REST for others) call into the same `MemoryStore`. ChromaDB owns vector embeddings; SQLite owns all structured metadata. Both stores share a UUID primary key.

**Tech Stack:** Python 3.11, `mcp` (FastMCP), `chromadb`, `sentence-transformers`, `fastapi`, `uvicorn`, `pydantic` v2, `click`, `pytest`, `httpx`

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Package config, dependencies, script entry points |
| `memory_mesh/__init__.py` | Package version export |
| `memory_mesh/config.py` | `Config` dataclass; load/save `~/.memory-mesh/config.json` |
| `memory_mesh/core/models.py` | `MemoryEntry`, `Conflict`, `Resolution` Pydantic v2 models |
| `memory_mesh/core/store.py` | `MemoryStore`: save, search, delete, list/resolve conflicts |
| `memory_mesh/core/conflict.py` | `ConflictDetector`: 3-layer pipeline |
| `memory_mesh/storage/sqlite.py` | `SQLiteAdapter`: CRUD for memories + conflicts |
| `memory_mesh/storage/chroma.py` | `ChromaAdapter`: upsert, search, delete |
| `memory_mesh/storage/migrations/001_initial.sql` | Schema v1 |
| `memory_mesh/transports/rest_server.py` | FastAPI app with 5 endpoints |
| `memory_mesh/transports/mcp_server.py` | FastMCP server with 5 tools |
| `memory_mesh/cli.py` | Click CLI: `serve`, `mcp`, `conflicts` subcommands |
| `tests/unit/test_config.py` | Config load/save/defaults |
| `tests/unit/test_models.py` | Pydantic validation edge cases |
| `tests/unit/test_conflict_detector.py` | All 3 layers with mocked adapters |
| `tests/integration/test_store.py` | Save/search/delete round-trips; real SQLite + ChromaDB in tmp dir |
| `tests/integration/test_conflict_pipeline.py` | End-to-end conflict detection + resolution |
| `tests/transports/test_rest.py` | FastAPI TestClient: happy path + error per endpoint |
| `tests/transports/test_mcp.py` | MCP tool wiring: verify delegation to MemoryStore |

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `memory_mesh/__init__.py`
- Create: `memory_mesh/core/__init__.py`
- Create: `memory_mesh/storage/__init__.py`
- Create: `memory_mesh/transports/__init__.py`
- Create: `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/transports/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
cd C:/Users/Chinmay/memory-mesh
mkdir -p memory_mesh/core memory_mesh/storage/migrations memory_mesh/transports
mkdir -p tests/unit tests/integration tests/transports
```

- [ ] **Step 2: Write pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "memory-mesh"
version = "0.1.0"
description = "Local-first shared memory for all AI assistants"
license = {text = "MIT"}
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "chromadb>=0.5.0",
    "sentence-transformers>=3.0.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.0.0",
    "click>=8.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.27.0",
]

[project.scripts]
memory-mesh = "memory_mesh.cli:cli"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Create all `__init__.py` files**

`memory_mesh/__init__.py`:
```python
__version__ = "0.1.0"
```

All other `__init__.py` files are empty. Create:
- `memory_mesh/core/__init__.py`
- `memory_mesh/storage/__init__.py`
- `memory_mesh/transports/__init__.py`
- `tests/__init__.py`
- `tests/unit/__init__.py`
- `tests/integration/__init__.py`
- `tests/transports/__init__.py`

- [ ] **Step 4: Install in dev mode**

```bash
cd C:/Users/Chinmay/memory-mesh
pip install -e ".[dev]"
```

Expected: Package installs without errors. `memory-mesh --help` may fail (cli not written yet) — that's fine.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/Chinmay/memory-mesh
git add pyproject.toml memory_mesh/ tests/
git commit -m "chore: project scaffold and package structure"
```

---

## Task 2: Config Module

**Files:**
- Create: `memory_mesh/config.py`
- Create: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_config.py`:
```python
import json
from pathlib import Path
from memory_mesh.config import Config


def test_default_config():
    cfg = Config()
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8765
    assert cfg.similarity_threshold == 0.85
    assert cfg.diff_ratio_threshold == 0.20
    assert cfg.nli_enabled is False
    assert cfg.auth_enabled is False
    assert cfg.auth_token is None


def test_db_path_is_under_data_dir():
    cfg = Config()
    assert cfg.db_path == cfg.data_dir / "memories.db"
    assert cfg.chroma_path == cfg.data_dir / "chroma"


def test_load_from_file(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"port": 9000, "nli_enabled": True}))
    cfg = Config.load(config_path=config_file)
    assert cfg.port == 9000
    assert cfg.nli_enabled is True
    assert cfg.host == "127.0.0.1"  # default preserved


def test_save_and_reload(tmp_path):
    cfg = Config(port=9001, data_dir=tmp_path)
    cfg.save()
    cfg2 = Config.load(config_path=tmp_path / "config.json")
    assert cfg2.port == 9001


def test_missing_config_file_returns_defaults(tmp_path):
    cfg = Config.load(config_path=tmp_path / "nonexistent.json")
    assert cfg.port == 8765
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/Chinmay/memory-mesh
pytest tests/unit/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'memory_mesh.config'`

- [ ] **Step 3: Implement config.py**

`memory_mesh/config.py`:
```python
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Config:
    data_dir: Path = field(default_factory=lambda: Path.home() / ".memory-mesh")
    similarity_threshold: float = 0.85
    diff_ratio_threshold: float = 0.20
    nli_enabled: bool = False
    nli_model: str = "cross-encoder/nli-deberta-v3-small"
    host: str = "127.0.0.1"
    port: int = 8765
    auth_enabled: bool = False
    auth_token: str | None = None

    @property
    def db_path(self) -> Path:
        return self.data_dir / "memories.db"

    @property
    def chroma_path(self) -> Path:
        return self.data_dir / "chroma"

    @classmethod
    def load(cls, config_path: Path | None = None) -> Config:
        if config_path is None:
            config_path = Path.home() / ".memory-mesh" / "config.json"
        if not config_path.exists():
            return cls()
        data = json.loads(config_path.read_text())
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        if "data_dir" in filtered:
            filtered["data_dir"] = Path(filtered["data_dir"])
        return cls(**filtered)

    def save(self, config_path: Path | None = None) -> None:
        if config_path is None:
            config_path = self.data_dir / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        raw = asdict(self)
        raw["data_dir"] = str(raw["data_dir"])
        config_path.write_text(json.dumps(raw, indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_config.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add memory_mesh/config.py tests/unit/test_config.py
git commit -m "feat: Config dataclass with load/save"
```

---

## Task 3: Pydantic Models

**Files:**
- Create: `memory_mesh/core/models.py`
- Create: `tests/unit/test_models.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_models.py`:
```python
from datetime import datetime, timezone
from memory_mesh.core.models import Conflict, MemoryEntry, Resolution
import pytest


def make_entry(**kwargs) -> MemoryEntry:
    defaults = dict(
        id="abc-123",
        agent_id="claude",
        content="Python is the best language",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return MemoryEntry(**(defaults | kwargs))


def test_memory_entry_defaults():
    entry = make_entry()
    assert entry.tags == []
    assert entry.key is None
    assert entry.session_id is None


def test_memory_entry_requires_content():
    with pytest.raises(Exception):
        MemoryEntry(id="x", agent_id="claude", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))


def test_conflict_status_default():
    a = make_entry(id="aaa")
    b = make_entry(id="bbb")
    c = Conflict(
        id="c1",
        memory_a_id="aaa",
        memory_b_id="bbb",
        memory_a=a,
        memory_b=b,
        trigger="key_match",
        created_at=datetime.now(timezone.utc),
    )
    assert c.status == "pending"
    assert c.resolution_id is None


def test_resolution_default_resolved_by():
    r = Resolution(conflict_id="c1", winning_id="aaa")
    assert r.resolved_by == "mcp"


def test_memory_entry_serializes_tags():
    entry = make_entry(tags=["project", "preference"])
    data = entry.model_dump()
    assert data["tags"] == ["project", "preference"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'memory_mesh.core.models'`

- [ ] **Step 3: Implement models.py**

`memory_mesh/core/models.py`:
```python
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    id: str
    agent_id: str
    key: str | None = None
    content: str
    tags: list[str] = Field(default_factory=list)
    session_id: str | None = None
    created_at: datetime
    updated_at: datetime


class Conflict(BaseModel):
    id: str
    memory_a_id: str
    memory_b_id: str
    memory_a: MemoryEntry | None = None
    memory_b: MemoryEntry | None = None
    trigger: Literal["key_match", "similarity", "nli"]
    status: Literal["pending", "resolved"] = "pending"
    resolution_id: str | None = None
    resolved_by: Literal["cli", "mcp", "rest"] | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class Resolution(BaseModel):
    conflict_id: str
    winning_id: str
    resolved_by: Literal["cli", "mcp", "rest"] = "mcp"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_models.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add memory_mesh/core/models.py tests/unit/test_models.py
git commit -m "feat: Pydantic models for MemoryEntry, Conflict, Resolution"
```

---

## Task 4: SQLite Migration + Adapter

**Files:**
- Create: `memory_mesh/storage/migrations/001_initial.sql`
- Create: `memory_mesh/storage/sqlite.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_sqlite.py`:
```python
from datetime import datetime, timezone
from pathlib import Path
import pytest
from memory_mesh.storage.sqlite import SQLiteAdapter
from memory_mesh.core.models import Conflict, MemoryEntry, Resolution


@pytest.fixture
def db(tmp_path) -> SQLiteAdapter:
    adapter = SQLiteAdapter(tmp_path / "test.db")
    adapter.connect()
    return adapter


def make_entry(id="e1", agent_id="claude", content="hello world", **kwargs) -> MemoryEntry:
    now = datetime.now(timezone.utc)
    return MemoryEntry(id=id, agent_id=agent_id, content=content,
                       created_at=now, updated_at=now, **kwargs)


def test_insert_and_get_by_id(db):
    entry = make_entry()
    db.insert_memory(entry)
    result = db.get_by_id("e1")
    assert result is not None
    assert result.content == "hello world"
    assert result.agent_id == "claude"


def test_get_by_id_missing_returns_none(db):
    assert db.get_by_id("nonexistent") is None


def test_get_by_key(db):
    db.insert_memory(make_entry(id="e1", key="user.lang", content="Python"))
    db.insert_memory(make_entry(id="e2", key="user.lang", content="Go"))
    db.insert_memory(make_entry(id="e3", key="other", content="ignored"))
    results = db.get_by_key("user.lang")
    assert len(results) == 2
    assert {r.id for r in results} == {"e1", "e2"}


def test_delete_memory(db):
    db.insert_memory(make_entry())
    assert db.delete_memory("e1") is True
    assert db.get_by_id("e1") is None
    assert db.delete_memory("e1") is False


def test_tags_roundtrip(db):
    entry = make_entry(tags=["project", "pref"])
    db.insert_memory(entry)
    result = db.get_by_id("e1")
    assert result.tags == ["project", "pref"]


def test_insert_and_list_conflicts(db):
    db.insert_memory(make_entry(id="a"))
    db.insert_memory(make_entry(id="b"))
    now = datetime.now(timezone.utc)
    conflict = Conflict(id="c1", memory_a_id="a", memory_b_id="b",
                        trigger="key_match", created_at=now)
    db.insert_conflict(conflict)
    results = db.list_conflicts(status="pending")
    assert len(results) == 1
    assert results[0].id == "c1"


def test_conflict_exists(db):
    db.insert_memory(make_entry(id="a"))
    db.insert_memory(make_entry(id="b"))
    now = datetime.now(timezone.utc)
    db.insert_conflict(Conflict(id="c1", memory_a_id="a", memory_b_id="b",
                                trigger="key_match", created_at=now))
    assert db.conflict_exists("a", "b") is True
    assert db.conflict_exists("a", "c") is False


def test_resolve_conflict(db):
    db.insert_memory(make_entry(id="a"))
    db.insert_memory(make_entry(id="b"))
    now = datetime.now(timezone.utc)
    db.insert_conflict(Conflict(id="c1", memory_a_id="a", memory_b_id="b",
                                trigger="similarity", created_at=now))
    resolution = Resolution(conflict_id="c1", winning_id="a", resolved_by="cli")
    updated = db.resolve_conflict(resolution)
    assert updated.status == "resolved"
    assert updated.resolution_id == "a"
    assert updated.resolved_by == "cli"


def test_migration_creates_schema(db):
    # Tables exist after connect()
    cursor = db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    assert "memories" in tables
    assert "conflicts" in tables
    assert "schema_migrations" in tables
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_sqlite.py -v
```

Expected: `ModuleNotFoundError: No module named 'memory_mesh.storage.sqlite'`

- [ ] **Step 3: Write the migration SQL**

`memory_mesh/storage/migrations/001_initial.sql`:
```sql
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
```

- [ ] **Step 4: Implement sqlite.py**

`memory_mesh/storage/sqlite.py`:
```python
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from memory_mesh.core.models import Conflict, MemoryEntry, Resolution

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class SQLiteAdapter:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._apply_migrations()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("SQLiteAdapter.connect() not called")
        return self._conn

    def _apply_migrations(self) -> None:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        self.conn.commit()
        for sql_file in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            version = sql_file.stem
            row = self.conn.execute(
                "SELECT version FROM schema_migrations WHERE version = ?", (version,)
            ).fetchone()
            if row is None:
                self.conn.executescript(sql_file.read_text())
                self.conn.execute(
                    "INSERT INTO schema_migrations VALUES (?, ?)",
                    (version, datetime.now(timezone.utc).isoformat()),
                )
                self.conn.commit()

    # --- Memories ---

    def insert_memory(self, entry: MemoryEntry) -> None:
        self.conn.execute(
            "INSERT INTO memories (id, agent_id, key, content, tags, session_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry.id,
                entry.agent_id,
                entry.key,
                entry.content,
                json.dumps(entry.tags),
                entry.session_id,
                entry.created_at.isoformat(),
                entry.updated_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_by_id(self, memory_id: str) -> MemoryEntry | None:
        row = self.conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        return _row_to_entry(row) if row else None

    def get_by_key(self, key: str) -> list[MemoryEntry]:
        rows = self.conn.execute(
            "SELECT * FROM memories WHERE key = ?", (key,)
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def delete_memory(self, memory_id: str) -> bool:
        cursor = self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # --- Conflicts ---

    def insert_conflict(self, conflict: Conflict) -> None:
        self.conn.execute(
            "INSERT INTO conflicts (id, memory_a_id, memory_b_id, trigger, status, "
            "resolution_id, resolved_by, resolved_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                conflict.id,
                conflict.memory_a_id,
                conflict.memory_b_id,
                conflict.trigger,
                conflict.status,
                conflict.resolution_id,
                conflict.resolved_by,
                conflict.resolved_at.isoformat() if conflict.resolved_at else None,
                conflict.created_at.isoformat(),
            ),
        )
        self.conn.commit()

    def conflict_exists(self, memory_a_id: str, memory_b_id: str) -> bool:
        a, b = sorted([memory_a_id, memory_b_id])
        row = self.conn.execute(
            "SELECT id FROM conflicts WHERE memory_a_id = ? AND memory_b_id = ? "
            "AND status = 'pending'",
            (a, b),
        ).fetchone()
        return row is not None

    def list_conflicts(self, status: str = "pending") -> list[Conflict]:
        rows = self.conn.execute(
            "SELECT * FROM conflicts WHERE status = ?", (status,)
        ).fetchall()
        return [_row_to_conflict(r) for r in rows]

    def resolve_conflict(self, resolution: Resolution) -> Conflict:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE conflicts SET status='resolved', resolution_id=?, resolved_by=?, resolved_at=? "
            "WHERE id=?",
            (resolution.winning_id, resolution.resolved_by, now, resolution.conflict_id),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM conflicts WHERE id = ?", (resolution.conflict_id,)
        ).fetchone()
        return _row_to_conflict(row)


def _row_to_entry(row: sqlite3.Row) -> MemoryEntry:
    return MemoryEntry(
        id=row["id"],
        agent_id=row["agent_id"],
        key=row["key"],
        content=row["content"],
        tags=json.loads(row["tags"]),
        session_id=row["session_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _row_to_conflict(row: sqlite3.Row) -> Conflict:
    return Conflict(
        id=row["id"],
        memory_a_id=row["memory_a_id"],
        memory_b_id=row["memory_b_id"],
        trigger=row["trigger"],
        status=row["status"],
        resolution_id=row["resolution_id"],
        resolved_by=row["resolved_by"],
        resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
        created_at=datetime.fromisoformat(row["created_at"]),
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_sqlite.py -v
```

Expected: 10 passed

- [ ] **Step 6: Commit**

```bash
git add memory_mesh/storage/ tests/unit/test_sqlite.py
git commit -m "feat: SQLite adapter with migrations"
```

---

## Task 5: ChromaDB Adapter

**Files:**
- Create: `memory_mesh/storage/chroma.py`
- Create: `tests/unit/test_chroma.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_chroma.py`:
```python
from datetime import datetime, timezone
from pathlib import Path
import pytest
import chromadb
from chromadb import EmbeddingFunction, Embeddings
from memory_mesh.storage.chroma import ChromaAdapter
from memory_mesh.core.models import MemoryEntry


class FakeEF(EmbeddingFunction):
    """Deterministic fake embeddings: each char sums to a float vector."""
    def __call__(self, input: list[str]) -> Embeddings:
        result = []
        for text in input:
            # 384-dim vector where dim[i % 384] = 1.0 for each char
            vec = [0.0] * 384
            for i, ch in enumerate(text):
                vec[i % 384] += ord(ch) / 1000.0
            # normalize
            norm = sum(v ** 2 for v in vec) ** 0.5 or 1.0
            result.append([v / norm for v in vec])
        return result


@pytest.fixture
def chroma(tmp_path) -> ChromaAdapter:
    adapter = ChromaAdapter(tmp_path / "chroma", embedding_function=FakeEF())
    adapter.connect()
    return adapter


def make_entry(id="e1", content="hello world", agent_id="claude") -> MemoryEntry:
    now = datetime.now(timezone.utc)
    return MemoryEntry(id=id, agent_id=agent_id, content=content,
                       created_at=now, updated_at=now)


def test_upsert_and_search_returns_id(chroma):
    entry = make_entry()
    chroma.upsert(entry)
    results = chroma.search("hello world", limit=5)
    ids = [r[0] for r in results]
    assert "e1" in ids


def test_search_returns_similarity_score(chroma):
    chroma.upsert(make_entry(id="e1", content="Python is a great language"))
    results = chroma.search("Python is a great language", limit=1)
    assert len(results) == 1
    _id, similarity = results[0]
    assert 0.0 <= similarity <= 1.0


def test_delete_removes_from_search(chroma):
    chroma.upsert(make_entry())
    chroma.delete("e1")
    results = chroma.search("hello world", limit=5)
    ids = [r[0] for r in results]
    assert "e1" not in ids


def test_upsert_is_idempotent(chroma):
    entry = make_entry()
    chroma.upsert(entry)
    chroma.upsert(entry)  # should not raise
    results = chroma.search("hello world", limit=5)
    assert len([r for r in results if r[0] == "e1"]) == 1


def test_where_filter_by_agent_id(chroma):
    chroma.upsert(make_entry(id="a", content="memory alpha", agent_id="claude"))
    chroma.upsert(make_entry(id="b", content="memory beta", agent_id="chatgpt"))
    results = chroma.search("memory", limit=10, where={"agent_id": {"$eq": "claude"}})
    ids = [r[0] for r in results]
    assert "a" in ids
    assert "b" not in ids
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_chroma.py -v
```

Expected: `ModuleNotFoundError: No module named 'memory_mesh.storage.chroma'`

- [ ] **Step 3: Implement chroma.py**

`memory_mesh/storage/chroma.py`:
```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from memory_mesh.core.models import MemoryEntry


class ChromaAdapter:
    def __init__(self, chroma_path: Path, embedding_function: Any = None) -> None:
        self.chroma_path = chroma_path
        self._ef = embedding_function
        self._collection = None

    def connect(self) -> None:
        import chromadb

        self.chroma_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(self.chroma_path))

        if self._ef is None:
            from chromadb.utils.embedding_functions import (
                SentenceTransformerEmbeddingFunction,
            )
            self._ef = SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )

        self._collection = client.get_or_create_collection(
            name="memory_mesh",
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def collection(self):
        if self._collection is None:
            raise RuntimeError("ChromaAdapter.connect() not called")
        return self._collection

    def upsert(self, entry: MemoryEntry) -> None:
        self.collection.upsert(
            ids=[entry.id],
            documents=[entry.content],
            metadatas=[{"agent_id": entry.agent_id, "key": entry.key or ""}],
        )

    def search(
        self,
        query: str,
        limit: int = 10,
        where: dict | None = None,
    ) -> list[tuple[str, float]]:
        kwargs: dict = {"query_texts": [query], "n_results": min(limit, self.collection.count() or 1)}
        if where:
            kwargs["where"] = where
        results = self.collection.query(**kwargs)
        ids = results["ids"][0]
        # ChromaDB cosine space returns distance = 1 - cosine_similarity
        distances = results["distances"][0]
        return [(id_, 1.0 - dist) for id_, dist in zip(ids, distances)]

    def delete(self, memory_id: str) -> None:
        self.collection.delete(ids=[memory_id])
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_chroma.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add memory_mesh/storage/chroma.py tests/unit/test_chroma.py
git commit -m "feat: ChromaDB adapter with cosine similarity search"
```

---

## Task 6: MemoryStore Core (save, search, delete)

No conflict detection yet — that gets wired in Task 10.

**Files:**
- Create: `memory_mesh/core/store.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_store.py`:
```python
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from memory_mesh.core.store import MemoryStore
from memory_mesh.core.models import MemoryEntry, Resolution
from memory_mesh.config import Config


@pytest.fixture
def store(tmp_path):
    cfg = Config(data_dir=tmp_path)
    # Use mock embedding function so no model download in unit tests
    from tests.unit.test_chroma import FakeEF
    s = MemoryStore(cfg, embedding_function=FakeEF())
    s.connect()
    return s


def test_save_returns_memory_entry(store):
    entry, conflicts = store.save(content="hello", agent_id="claude")
    assert entry.content == "hello"
    assert entry.agent_id == "claude"
    assert isinstance(entry.id, str) and len(entry.id) > 0
    assert conflicts == []


def test_save_assigns_uuid(store):
    e1, _ = store.save(content="first", agent_id="claude")
    e2, _ = store.save(content="second", agent_id="claude")
    assert e1.id != e2.id


def test_save_with_key_and_tags(store):
    entry, _ = store.save(content="Python", agent_id="claude", key="lang", tags=["pref"])
    assert entry.key == "lang"
    assert entry.tags == ["pref"]


def test_search_returns_results(store):
    store.save(content="Python is great for data science", agent_id="claude")
    results = store.search(query="Python data science", limit=5)
    assert len(results) >= 1
    entry, score = results[0]
    assert "Python" in entry.content
    assert 0.0 <= score <= 1.0


def test_delete_existing_entry(store):
    entry, _ = store.save(content="to delete", agent_id="claude")
    assert store.delete(entry.id) is True
    assert store.sqlite.get_by_id(entry.id) is None


def test_delete_nonexistent_returns_false(store):
    assert store.delete("ghost-id") is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_store.py -v
```

Expected: `ModuleNotFoundError: No module named 'memory_mesh.core.store'`

- [ ] **Step 3: Implement store.py**

`memory_mesh/core/store.py`:
```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from memory_mesh.config import Config
from memory_mesh.core.models import Conflict, MemoryEntry, Resolution
from memory_mesh.storage.chroma import ChromaAdapter
from memory_mesh.storage.sqlite import SQLiteAdapter


class MemoryStore:
    def __init__(self, config: Config, embedding_function: Any = None) -> None:
        self.config = config
        self.sqlite = SQLiteAdapter(config.db_path)
        self.chroma = ChromaAdapter(config.chroma_path, embedding_function=embedding_function)
        self._detector = None  # injected in Task 10

    def connect(self) -> None:
        self.sqlite.connect()
        self.chroma.connect()

    def save(
        self,
        content: str,
        agent_id: str,
        key: str | None = None,
        tags: list[str] | None = None,
        session_id: str | None = None,
    ) -> tuple[MemoryEntry, list[Conflict]]:
        now = datetime.now(timezone.utc)
        entry = MemoryEntry(
            id=str(uuid4()),
            agent_id=agent_id,
            content=content,
            key=key,
            tags=tags or [],
            session_id=session_id,
            created_at=now,
            updated_at=now,
        )
        # SQLite first (source of truth), then ChromaDB
        self.sqlite.insert_memory(entry)
        self.chroma.upsert(entry)

        conflicts: list[Conflict] = []
        if self._detector is not None:
            conflicts = self._detector.check(entry, self.sqlite, self.chroma)
            for c in conflicts:
                self.sqlite.insert_conflict(c)

        return entry, conflicts

    def search(
        self,
        query: str,
        limit: int = 10,
        agent_id: str | None = None,
        key: str | None = None,
        tags: list[str] | None = None,
    ) -> list[tuple[MemoryEntry, float]]:
        where: dict = {}
        if agent_id:
            where["agent_id"] = {"$eq": agent_id}
        if key:
            where["key"] = {"$eq": key}

        fetch_limit = limit * 3 if tags else limit
        id_scores = self.chroma.search(query, limit=fetch_limit, where=where or None)

        results: list[tuple[MemoryEntry, float]] = []
        for mem_id, score in id_scores:
            mem = self.sqlite.get_by_id(mem_id)
            if mem is None:
                continue
            if tags and not any(t in mem.tags for t in tags):
                continue
            results.append((mem, score))
            if len(results) >= limit:
                break
        return results

    def delete(self, memory_id: str) -> bool:
        removed = self.sqlite.delete_memory(memory_id)
        if removed:
            self.chroma.delete(memory_id)
        return removed

    def list_conflicts(self, status: str = "pending") -> list[Conflict]:
        conflicts = self.sqlite.list_conflicts(status)
        return [_hydrate(c, self.sqlite) for c in conflicts]

    def resolve_conflict(self, resolution: Resolution) -> Conflict:
        conflict = self.sqlite.resolve_conflict(resolution)
        return _hydrate(conflict, self.sqlite)


def _hydrate(conflict: Conflict, sqlite: SQLiteAdapter) -> Conflict:
    """Attach full MemoryEntry objects to a Conflict for display."""
    return conflict.model_copy(update={
        "memory_a": sqlite.get_by_id(conflict.memory_a_id),
        "memory_b": sqlite.get_by_id(conflict.memory_b_id),
    })
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_store.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add memory_mesh/core/store.py tests/unit/test_store.py
git commit -m "feat: MemoryStore core with save/search/delete"
```

---

## Task 7: ConflictDetector — Layer 1 (Key Match)

**Files:**
- Create: `memory_mesh/core/conflict.py`
- Create: `tests/unit/test_conflict_detector.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_conflict_detector.py`:
```python
from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from memory_mesh.core.conflict import ConflictDetector
from memory_mesh.core.models import Conflict, MemoryEntry
from memory_mesh.config import Config


def make_entry(id="e1", content="Python is best", key=None, agent_id="claude",
               session_id=None) -> MemoryEntry:
    now = datetime.now(timezone.utc)
    return MemoryEntry(id=id, agent_id=agent_id, content=content, key=key,
                       session_id=session_id, created_at=now, updated_at=now)


def make_sqlite(existing_by_key=None, conflict_exists=False):
    sqlite = MagicMock()
    sqlite.get_by_key.return_value = existing_by_key or []
    sqlite.conflict_exists.return_value = conflict_exists
    return sqlite


def make_chroma(neighbors=None):
    chroma = MagicMock()
    chroma.search.return_value = neighbors or []
    return chroma


# --- Layer 1: Key Match ---

def test_layer1_no_conflict_when_no_key():
    detector = ConflictDetector(Config())
    new = make_entry(key=None)
    sqlite = make_sqlite()
    conflicts = detector.check(new, sqlite, make_chroma())
    assert conflicts == []
    sqlite.get_by_key.assert_not_called()


def test_layer1_no_conflict_when_key_matches_same_content():
    existing = make_entry(id="old", key="lang", content="Python is best")
    detector = ConflictDetector(Config())
    new = make_entry(id="new", key="lang", content="Python is best")
    sqlite = make_sqlite(existing_by_key=[existing])
    conflicts = detector.check(new, sqlite, make_chroma())
    assert conflicts == []


def test_layer1_conflict_when_key_has_different_value():
    existing = make_entry(id="old", key="lang", content="Go is best")
    detector = ConflictDetector(Config())
    new = make_entry(id="new", key="lang", content="Python is best")
    sqlite = make_sqlite(existing_by_key=[existing])
    conflicts = detector.check(new, sqlite, make_chroma())
    assert len(conflicts) == 1
    assert conflicts[0].trigger == "key_match"
    assert set([conflicts[0].memory_a_id, conflicts[0].memory_b_id]) == {"old", "new"}


def test_layer1_skips_self():
    existing = make_entry(id="same", key="lang", content="different")
    detector = ConflictDetector(Config())
    new = make_entry(id="same", key="lang", content="different")
    sqlite = make_sqlite(existing_by_key=[existing])
    conflicts = detector.check(new, sqlite, make_chroma())
    assert conflicts == []


def test_layer1_dedup_skips_existing_pending_conflict():
    existing = make_entry(id="old", key="lang", content="Go")
    detector = ConflictDetector(Config())
    new = make_entry(id="new", key="lang", content="Python")
    sqlite = make_sqlite(existing_by_key=[existing], conflict_exists=True)
    conflicts = detector.check(new, sqlite, make_chroma())
    assert conflicts == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_conflict_detector.py -v
```

Expected: `ModuleNotFoundError: No module named 'memory_mesh.core.conflict'`

- [ ] **Step 3: Implement Layer 1 in conflict.py**

`memory_mesh/core/conflict.py`:
```python
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from memory_mesh.config import Config
from memory_mesh.core.models import Conflict, MemoryEntry
from memory_mesh.storage.chroma import ChromaAdapter
from memory_mesh.storage.sqlite import SQLiteAdapter


class ConflictDetector:
    def __init__(self, config: Config) -> None:
        self.config = config

    def check(
        self,
        new_entry: MemoryEntry,
        sqlite: SQLiteAdapter,
        chroma: ChromaAdapter,
    ) -> list[Conflict]:
        conflicts: list[Conflict] = []
        seen_pairs: set[tuple[str, str]] = set()

        # Layer 1: Key match
        if new_entry.key:
            for existing in sqlite.get_by_key(new_entry.key):
                if existing.id == new_entry.id:
                    continue
                if existing.content == new_entry.content:
                    continue
                pair = _sorted_pair(new_entry.id, existing.id)
                if pair in seen_pairs or sqlite.conflict_exists(*pair):
                    continue
                seen_pairs.add(pair)
                conflicts.append(_make_conflict(new_entry.id, existing.id, "key_match"))

        return conflicts


def _sorted_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def _make_conflict(id_a: str, id_b: str, trigger: str) -> Conflict:
    a, b = _sorted_pair(id_a, id_b)
    return Conflict(
        id=str(uuid4()),
        memory_a_id=a,
        memory_b_id=b,
        trigger=trigger,  # type: ignore[arg-type]
        created_at=datetime.now(timezone.utc),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_conflict_detector.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add memory_mesh/core/conflict.py tests/unit/test_conflict_detector.py
git commit -m "feat: ConflictDetector Layer 1 (key match)"
```

---

## Task 8: ConflictDetector — Layer 2 (Similarity Threshold)

**Files:**
- Modify: `memory_mesh/core/conflict.py`
- Modify: `tests/unit/test_conflict_detector.py`

- [ ] **Step 1: Write the failing tests for Layer 2**

Add these tests to `tests/unit/test_conflict_detector.py`:
```python
import difflib

# --- Layer 2: Similarity Threshold ---

def test_layer2_no_conflict_below_similarity_threshold():
    detector = ConflictDetector(Config(similarity_threshold=0.85))
    new = make_entry(id="new", content="Python is great")
    existing = make_entry(id="old", content="completely different topic altogether")
    # Return low similarity (0.3 < 0.85)
    chroma = make_chroma(neighbors=[("old", 0.3)])
    sqlite = make_sqlite(existing_by_key=[])
    sqlite.get_by_id = MagicMock(return_value=existing)
    conflicts = detector.check(new, sqlite, chroma)
    assert conflicts == []


def test_layer2_conflict_when_similar_but_different_content():
    detector = ConflictDetector(Config(similarity_threshold=0.85, diff_ratio_threshold=0.20))
    new = make_entry(id="new", content="Python is the best programming language")
    existing = make_entry(id="old", content="Go is the best programming language")
    # High similarity (same structure, different subject)
    chroma = make_chroma(neighbors=[("old", 0.92)])
    sqlite = make_sqlite()
    sqlite.get_by_id = MagicMock(return_value=existing)
    conflicts = detector.check(new, sqlite, chroma)
    assert len(conflicts) == 1
    assert conflicts[0].trigger == "similarity"


def test_layer2_skips_same_agent_same_session():
    detector = ConflictDetector(Config(similarity_threshold=0.85))
    new = make_entry(id="new", content="Python is best", agent_id="claude", session_id="s1")
    existing = make_entry(id="old", content="Python is great", agent_id="claude", session_id="s1")
    chroma = make_chroma(neighbors=[("old", 0.95)])
    sqlite = make_sqlite()
    sqlite.get_by_id = MagicMock(return_value=existing)
    conflicts = detector.check(new, sqlite, chroma)
    assert conflicts == []


def test_layer2_does_not_skip_different_session_same_agent():
    detector = ConflictDetector(Config(similarity_threshold=0.85, diff_ratio_threshold=0.20))
    new = make_entry(id="new", content="Python is the best language", agent_id="claude", session_id="s2")
    existing = make_entry(id="old", content="Go is the best language", agent_id="claude", session_id="s1")
    chroma = make_chroma(neighbors=[("old", 0.92)])
    sqlite = make_sqlite()
    sqlite.get_by_id = MagicMock(return_value=existing)
    conflicts = detector.check(new, sqlite, chroma)
    assert len(conflicts) == 1


def test_layer2_does_not_skip_same_session_different_agent():
    detector = ConflictDetector(Config(similarity_threshold=0.85, diff_ratio_threshold=0.20))
    new = make_entry(id="new", content="Python is the best language", agent_id="claude", session_id="s1")
    existing = make_entry(id="old", content="Go is the best language", agent_id="chatgpt", session_id="s1")
    chroma = make_chroma(neighbors=[("old", 0.92)])
    sqlite = make_sqlite()
    sqlite.get_by_id = MagicMock(return_value=existing)
    conflicts = detector.check(new, sqlite, chroma)
    assert len(conflicts) == 1


def test_layer2_dedup_against_layer1():
    """Same pair caught by Layer 1 should not appear again in Layer 2."""
    detector = ConflictDetector(Config(similarity_threshold=0.85, diff_ratio_threshold=0.20))
    new = make_entry(id="new", key="lang", content="Python is the best language")
    existing = make_entry(id="old", key="lang", content="Go is the best language")
    chroma = make_chroma(neighbors=[("old", 0.92)])
    sqlite = make_sqlite(existing_by_key=[existing])
    sqlite.get_by_id = MagicMock(return_value=existing)
    conflicts = detector.check(new, sqlite, chroma)
    # Only one conflict despite both layers triggering
    assert len(conflicts) == 1
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/unit/test_conflict_detector.py -v -k "layer2"
```

Expected: All Layer 2 tests fail

- [ ] **Step 3: Add Layer 2 to conflict.py**

Replace the `check` method in `memory_mesh/core/conflict.py`:
```python
import difflib

def check(
    self,
    new_entry: MemoryEntry,
    sqlite: SQLiteAdapter,
    chroma: ChromaAdapter,
) -> list[Conflict]:
    conflicts: list[Conflict] = []
    seen_pairs: set[tuple[str, str]] = set()

    # Layer 1: Key match
    if new_entry.key:
        for existing in sqlite.get_by_key(new_entry.key):
            if existing.id == new_entry.id:
                continue
            if existing.content == new_entry.content:
                continue
            pair = _sorted_pair(new_entry.id, existing.id)
            if pair in seen_pairs or sqlite.conflict_exists(*pair):
                continue
            seen_pairs.add(pair)
            conflicts.append(_make_conflict(new_entry.id, existing.id, "key_match"))

    # Layer 2: Similarity threshold
    neighbors = chroma.search(new_entry.content, limit=5)
    for mem_id, similarity in neighbors:
        if mem_id == new_entry.id:
            continue
        if similarity < self.config.similarity_threshold:
            continue
        existing = sqlite.get_by_id(mem_id)
        if existing is None:
            continue
        # Same agent + same session = update, not conflict
        if (
            existing.agent_id == new_entry.agent_id
            and existing.session_id is not None
            and existing.session_id == new_entry.session_id
        ):
            continue
        ratio = difflib.SequenceMatcher(None, new_entry.content, existing.content).ratio()
        if (1.0 - ratio) <= self.config.diff_ratio_threshold:
            continue  # too similar in content — same thing, not a conflict
        pair = _sorted_pair(new_entry.id, mem_id)
        if pair in seen_pairs or sqlite.conflict_exists(*pair):
            continue
        seen_pairs.add(pair)
        conflicts.append(_make_conflict(new_entry.id, mem_id, "similarity"))

    return conflicts
```

- [ ] **Step 4: Run all conflict tests to verify they pass**

```bash
pytest tests/unit/test_conflict_detector.py -v
```

Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add memory_mesh/core/conflict.py tests/unit/test_conflict_detector.py
git commit -m "feat: ConflictDetector Layer 2 (similarity threshold + same-agent skip)"
```

---

## Task 9: ConflictDetector — Layer 3 (NLI, opt-in)

**Files:**
- Modify: `memory_mesh/core/conflict.py`
- Modify: `tests/unit/test_conflict_detector.py`

- [ ] **Step 1: Write the failing tests for Layer 3**

Add to `tests/unit/test_conflict_detector.py`:
```python
# --- Layer 3: NLI (opt-in) ---

def test_layer3_skipped_when_nli_disabled():
    detector = ConflictDetector(Config(nli_enabled=False, similarity_threshold=0.85,
                                      diff_ratio_threshold=0.20))
    new = make_entry(id="new", content="The sky is blue")
    existing = make_entry(id="old", content="The sky is not blue")
    chroma = make_chroma(neighbors=[("old", 0.92)])
    sqlite = make_sqlite()
    sqlite.get_by_id = MagicMock(return_value=existing)
    # Layer 2 content diff ratio check: these ARE textually similar, so similarity layer
    # may or may not fire depending on ratio. Test that NLI is not called at all.
    with patch("memory_mesh.core.conflict.ConflictDetector._run_nli") as mock_nli:
        detector.check(new, sqlite, chroma)
        mock_nli.assert_not_called()


def test_layer3_fires_when_nli_enabled_and_contradiction_found():
    detector = ConflictDetector(Config(nli_enabled=True, similarity_threshold=0.85,
                                      diff_ratio_threshold=0.20))
    new = make_entry(id="new", content="Paris is the capital of Germany")
    existing = make_entry(id="old", content="Berlin is the capital of Germany")
    chroma = make_chroma(neighbors=[("old", 0.91)])
    sqlite = make_sqlite()
    sqlite.get_by_id = MagicMock(return_value=existing)

    # Mock _run_nli to return True (contradiction detected)
    with patch.object(detector, "_run_nli", return_value=True):
        conflicts = detector.check(new, sqlite, chroma)

    nli_conflicts = [c for c in conflicts if c.trigger == "nli"]
    assert len(nli_conflicts) >= 1


def test_layer3_no_conflict_when_nli_returns_no_contradiction():
    detector = ConflictDetector(Config(nli_enabled=True, similarity_threshold=0.85,
                                      diff_ratio_threshold=0.20))
    new = make_entry(id="new", content="Cats are mammals")
    existing = make_entry(id="old", content="Dogs are mammals")
    chroma = make_chroma(neighbors=[("old", 0.88)])
    sqlite = make_sqlite()
    sqlite.get_by_id = MagicMock(return_value=existing)

    with patch.object(detector, "_run_nli", return_value=False):
        conflicts = detector.check(new, sqlite, chroma)

    assert all(c.trigger != "nli" for c in conflicts)
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/unit/test_conflict_detector.py -v -k "layer3"
```

Expected: All Layer 3 tests fail

- [ ] **Step 3: Add Layer 3 to conflict.py**

Add `_run_nli` and the Layer 3 block to `ConflictDetector` in `memory_mesh/core/conflict.py`:

```python
# Add to the check() method, after Layer 2 loop:

    # Layer 3: NLI contradiction (opt-in)
    if self.config.nli_enabled:
        # Re-fetch Layer 2 candidates that passed similarity but NOT already flagged
        for mem_id, similarity in neighbors:
            if mem_id == new_entry.id:
                continue
            if similarity < self.config.similarity_threshold:
                continue
            existing = sqlite.get_by_id(mem_id)
            if existing is None:
                continue
            pair = _sorted_pair(new_entry.id, mem_id)
            if pair in seen_pairs or sqlite.conflict_exists(*pair):
                continue
            if self._run_nli(new_entry.content, existing.content):
                seen_pairs.add(pair)
                conflicts.append(_make_conflict(new_entry.id, mem_id, "nli"))

    return conflicts

# Add as a method on ConflictDetector:
def _run_nli(self, text_a: str, text_b: str) -> bool:
    """Returns True if texts are contradictory per NLI model."""
    import numpy as np
    from sentence_transformers import CrossEncoder

    if not hasattr(self, "_nli_model"):
        self._nli_model = CrossEncoder(self.config.nli_model)

    scores = self._nli_model.predict([[text_a, text_b]])[0]
    # Labels: 0=contradiction, 1=entailment, 2=neutral
    exp_scores = np.exp(scores - np.max(scores))
    probs = exp_scores / exp_scores.sum()
    return float(probs[0]) > 0.7
```

- [ ] **Step 4: Run all conflict tests to verify they pass**

```bash
pytest tests/unit/test_conflict_detector.py -v
```

Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add memory_mesh/core/conflict.py tests/unit/test_conflict_detector.py
git commit -m "feat: ConflictDetector Layer 3 (NLI, opt-in)"
```

---

## Task 10: Wire ConflictDetector into MemoryStore

**Files:**
- Modify: `memory_mesh/core/store.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_store.py`:
```python
def test_save_detects_key_conflict(store):
    store.save(content="Go is best", agent_id="claude", key="lang")
    entry, conflicts = store.save(content="Python is best", agent_id="chatgpt", key="lang")
    assert len(conflicts) == 1
    assert conflicts[0].trigger == "key_match"
    assert conflicts[0].status == "pending"


def test_list_conflicts_returns_pending(store):
    store.save(content="Go is best", agent_id="claude", key="lang")
    store.save(content="Python is best", agent_id="chatgpt", key="lang")
    pending = store.list_conflicts(status="pending")
    assert len(pending) == 1
    assert pending[0].memory_a is not None
    assert pending[0].memory_b is not None


def test_resolve_conflict(store):
    store.save(content="Go is best", agent_id="claude", key="lang")
    _, conflicts = store.save(content="Python is best", agent_id="chatgpt", key="lang")
    conflict = conflicts[0]
    resolution = Resolution(conflict_id=conflict.id, winning_id=conflict.memory_a_id,
                            resolved_by="cli")
    resolved = store.resolve_conflict(resolution)
    assert resolved.status == "resolved"
    assert resolved.resolution_id == conflict.memory_a_id
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/unit/test_store.py -v -k "conflict"
```

Expected: Conflicts == [] because `_detector` is None

- [ ] **Step 3: Update store.py to inject ConflictDetector**

In `memory_mesh/core/store.py`, update `__init__` and `connect`:
```python
from memory_mesh.core.conflict import ConflictDetector

class MemoryStore:
    def __init__(self, config: Config, embedding_function: Any = None) -> None:
        self.config = config
        self.sqlite = SQLiteAdapter(config.db_path)
        self.chroma = ChromaAdapter(config.chroma_path, embedding_function=embedding_function)
        self._detector = ConflictDetector(config)  # always injected

    def connect(self) -> None:
        self.sqlite.connect()
        self.chroma.connect()
    # rest unchanged
```

- [ ] **Step 4: Run all store tests to verify they pass**

```bash
pytest tests/unit/test_store.py -v
```

Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add memory_mesh/core/store.py tests/unit/test_store.py
git commit -m "feat: wire ConflictDetector into MemoryStore"
```

---

## Task 11: REST Transport

**Files:**
- Create: `memory_mesh/transports/rest_server.py`
- Create: `tests/transports/test_rest.py`

- [ ] **Step 1: Write the failing tests**

`tests/transports/test_rest.py`:
```python
import pytest
from fastapi.testclient import TestClient
from memory_mesh.config import Config
from memory_mesh.core.store import MemoryStore
from memory_mesh.transports.rest_server import make_app
from tests.unit.test_chroma import FakeEF


@pytest.fixture
def client(tmp_path):
    cfg = Config(data_dir=tmp_path)
    store = MemoryStore(cfg, embedding_function=FakeEF())
    store.connect()
    app = make_app(store)
    return TestClient(app)


def test_save_memory(client):
    resp = client.post("/v1/memories", json={
        "content": "Python is great",
        "agent_id": "chatgpt",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["memory"]["content"] == "Python is great"
    assert data["memory"]["agent_id"] == "chatgpt"
    assert "conflicts" in data


def test_search_memory(client):
    client.post("/v1/memories", json={"content": "Python data science", "agent_id": "chatgpt"})
    resp = client.get("/v1/memories/search", params={"q": "Python"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert results[0]["content"] == "Python data science"


def test_list_conflicts_empty(client):
    resp = client.get("/v1/conflicts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_resolve_conflict(client):
    client.post("/v1/memories", json={"content": "Go is best", "agent_id": "claude", "key": "lang"})
    resp = client.post("/v1/memories", json={"content": "Python is best", "agent_id": "chatgpt", "key": "lang"})
    conflicts = resp.json()["conflicts"]
    assert len(conflicts) == 1
    conflict_id = conflicts[0]["id"]
    winning_id = conflicts[0]["memory_a_id"]

    resp = client.post(f"/v1/conflicts/{conflict_id}/resolve", json={"winning_id": winning_id})
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


def test_delete_memory(client):
    resp = client.post("/v1/memories", json={"content": "to delete", "agent_id": "claude"})
    mem_id = resp.json()["memory"]["id"]
    resp = client.delete(f"/v1/memories/{mem_id}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_delete_nonexistent_returns_404(client):
    resp = client.delete("/v1/memories/ghost")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/transports/test_rest.py -v
```

Expected: `ModuleNotFoundError: No module named 'memory_mesh.transports.rest_server'`

- [ ] **Step 3: Implement rest_server.py**

`memory_mesh/transports/rest_server.py`:
```python
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from memory_mesh.config import Config
from memory_mesh.core.models import MemoryEntry, Resolution
from memory_mesh.core.store import MemoryStore


class SaveRequest(BaseModel):
    content: str
    agent_id: str
    key: str | None = None
    tags: list[str] | None = None
    session_id: str | None = None


class ResolveRequest(BaseModel):
    winning_id: str
    resolved_by: str = "rest"


def make_app(store: MemoryStore, config: Config | None = None) -> FastAPI:
    app = FastAPI(title="memory-mesh", version="0.1.0")

    # Auth middleware — only active when config.auth_enabled is True
    if config is not None and config.auth_enabled and config.auth_token:
        expected_token = config.auth_token

        @app.middleware("http")
        async def auth_middleware(request: Request, call_next):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer ") or auth[7:] != expected_token:
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
            return await call_next(request)

    @app.post("/v1/memories")
    def save_memory(req: SaveRequest):
        entry, conflicts = store.save(
            content=req.content,
            agent_id=req.agent_id,
            key=req.key,
            tags=req.tags,
            session_id=req.session_id,
        )
        return {
            "memory": entry.model_dump(mode="json"),
            "conflicts": [c.model_dump(mode="json") for c in conflicts],
        }

    @app.get("/v1/memories/search")
    def search_memories(
        q: str,
        limit: int = 10,
        agent_id: str | None = None,
        key: str | None = None,
        tags: str | None = None,
    ):
        tag_list = tags.split(",") if tags else None
        results = store.search(query=q, limit=limit, agent_id=agent_id, key=key, tags=tag_list)
        return [entry.model_dump(mode="json") for entry, _score in results]

    @app.get("/v1/conflicts")
    def list_conflicts(status: str = "pending"):
        conflicts = store.list_conflicts(status=status)
        return [c.model_dump(mode="json") for c in conflicts]

    @app.post("/v1/conflicts/{conflict_id}/resolve")
    def resolve_conflict(conflict_id: str, req: ResolveRequest):
        resolution = Resolution(
            conflict_id=conflict_id,
            winning_id=req.winning_id,
            resolved_by=req.resolved_by,  # type: ignore[arg-type]
        )
        conflict = store.resolve_conflict(resolution)
        return conflict.model_dump(mode="json")

    @app.delete("/v1/memories/{memory_id}")
    def delete_memory(memory_id: str):
        success = store.delete(memory_id)
        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")
        return {"success": True}

    return app
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/transports/test_rest.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add memory_mesh/transports/rest_server.py tests/transports/test_rest.py
git commit -m "feat: FastAPI REST transport with 5 endpoints"
```

---

## Task 12: MCP Transport

**Files:**
- Create: `memory_mesh/transports/mcp_server.py`
- Create: `tests/transports/test_mcp.py`

- [ ] **Step 1: Write the failing tests**

`tests/transports/test_mcp.py`:
```python
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from memory_mesh.core.models import Conflict, MemoryEntry, Resolution
from memory_mesh.transports.mcp_server import make_mcp_server


def make_entry(id="e1", content="hello") -> MemoryEntry:
    now = datetime.now(timezone.utc)
    return MemoryEntry(id=id, agent_id="claude", content=content, created_at=now, updated_at=now)


@pytest.fixture
def store():
    s = MagicMock()
    s.save.return_value = (make_entry(), [])
    s.search.return_value = [(make_entry(), 0.95)]
    s.list_conflicts.return_value = []
    s.delete.return_value = True
    return s


@pytest.fixture
def tools(store):
    _mcp, tool_fns = make_mcp_server(store)
    return tool_fns


def test_save_context_calls_store(store, tools):
    tools["save_context"](content="hello", key=None, tags=None, session_id=None)
    store.save.assert_called_once_with(
        content="hello", agent_id="claude", key=None, tags=None, session_id=None
    )


def test_save_context_returns_memory_and_conflicts(store, tools):
    result = tools["save_context"](content="hello", key=None, tags=None, session_id=None)
    assert "memory" in result
    assert "conflicts" in result


def test_search_context_calls_store(store, tools):
    tools["search_context"](query="hello", limit=5, agent_id=None, key=None, tags=None)
    store.search.assert_called_once_with(query="hello", limit=5, agent_id=None, key=None, tags=None)


def test_list_conflicts_calls_store(store, tools):
    tools["list_conflicts"](status="pending")
    store.list_conflicts.assert_called_once_with(status="pending")


def test_resolve_conflict_calls_store(store, tools):
    now = datetime.now(timezone.utc)
    resolved = Conflict(id="c1", memory_a_id="a", memory_b_id="b", trigger="key_match",
                        status="resolved", resolution_id="a", resolved_by="mcp",
                        created_at=now)
    store.resolve_conflict.return_value = resolved
    result = tools["resolve_conflict"](conflict_id="c1", winning_id="a")
    assert result["status"] == "resolved"


def test_delete_context_calls_store(store, tools):
    result = tools["delete_context"](memory_id="e1")
    store.delete.assert_called_once_with("e1")
    assert result["success"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/transports/test_mcp.py -v
```

Expected: `ModuleNotFoundError: No module named 'memory_mesh.transports.mcp_server'`

- [ ] **Step 3: Implement mcp_server.py**

`make_mcp_server` returns a `(FastMCP, dict)` tuple so tests can call tool functions directly without depending on FastMCP internals.

`memory_mesh/transports/mcp_server.py`:
```python
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from memory_mesh.core.models import Resolution
from memory_mesh.core.store import MemoryStore


def make_mcp_server(store: MemoryStore) -> tuple[FastMCP, dict]:
    """Returns (mcp_app, tools) where tools is a dict of raw callables for testing."""
    mcp = FastMCP("memory-mesh")
    tools: dict = {}

    @mcp.tool()
    def save_context(
        content: str,
        key: str | None = None,
        tags: list[str] | None = None,
        session_id: str | None = None,
        agent_id: str = "claude",
    ) -> dict:
        """Save a memory entry. Returns the saved entry and any detected conflicts."""
        entry, conflicts = store.save(
            content=content,
            agent_id=agent_id,
            key=key,
            tags=tags,
            session_id=session_id,
        )
        return {
            "memory": entry.model_dump(mode="json"),
            "conflicts": [c.model_dump(mode="json") for c in conflicts],
        }

    @mcp.tool()
    def search_context(
        query: str,
        limit: int = 10,
        agent_id: str | None = None,
        key: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict]:
        """Search memory entries by semantic similarity."""
        results = store.search(query=query, limit=limit, agent_id=agent_id, key=key, tags=tags)
        return [entry.model_dump(mode="json") for entry, _score in results]

    @mcp.tool()
    def list_conflicts(status: str = "pending") -> list[dict]:
        """List memory conflicts. status: 'pending' or 'resolved'."""
        conflicts = store.list_conflicts(status=status)
        return [c.model_dump(mode="json") for c in conflicts]

    @mcp.tool()
    def resolve_conflict(conflict_id: str, winning_id: str) -> dict:
        """Resolve a conflict by choosing the winning memory entry."""
        resolution = Resolution(conflict_id=conflict_id, winning_id=winning_id, resolved_by="mcp")
        conflict = store.resolve_conflict(resolution)
        return conflict.model_dump(mode="json")

    @mcp.tool()
    def delete_context(memory_id: str) -> dict:
        """Delete a memory entry by ID."""
        success = store.delete(memory_id)
        return {"success": success}

    tools["save_context"] = save_context
    tools["search_context"] = search_context
    tools["list_conflicts"] = list_conflicts
    tools["resolve_conflict"] = resolve_conflict
    tools["delete_context"] = delete_context

    return mcp, tools
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/transports/test_mcp.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add memory_mesh/transports/mcp_server.py tests/transports/test_mcp.py
git commit -m "feat: MCP transport with 5 tools (FastMCP)"
```

---

## Task 13: CLI Entry Points

**Files:**
- Create: `memory_mesh/cli.py`

- [ ] **Step 1: Implement cli.py**

`memory_mesh/cli.py`:
```python
from __future__ import annotations

import click

from memory_mesh.config import Config


def _make_store(cfg: Config, **kwargs):
    from memory_mesh.core.store import MemoryStore
    store = MemoryStore(cfg, **kwargs)
    store.connect()
    return store


@click.group()
def cli() -> None:
    """memory-mesh — shared memory for all AI assistants."""


@cli.command()
@click.option("--host", default=None, help="Bind host (default: 127.0.0.1)")
@click.option("--port", default=None, type=int, help="Port (default: 8765)")
@click.option("--auth", is_flag=True, help="Enable Bearer token auth")
@click.option("--config", "config_path", default=None, help="Path to config.json")
def serve(host: str | None, port: int | None, auth: bool, config_path: str | None) -> None:
    """Start the REST API server on localhost:8765."""
    import uvicorn
    from pathlib import Path
    from memory_mesh.transports.rest_server import make_app

    cfg = Config.load(Path(config_path) if config_path else None)
    if host:
        cfg.host = host
    if port:
        cfg.port = port
    if auth:
        cfg.auth_enabled = True

    store = _make_store(cfg)
    app = make_app(store, config=cfg)
    click.echo(f"memory-mesh REST server starting on http://{cfg.host}:{cfg.port}")
    uvicorn.run(app, host=cfg.host, port=cfg.port)


@cli.command()
@click.option("--config", "config_path", default=None, help="Path to config.json")
def mcp(config_path: str | None) -> None:
    """Start the MCP stdio server (used by Claude Desktop)."""
    from pathlib import Path
    from memory_mesh.transports.mcp_server import make_mcp_server

    cfg = Config.load(Path(config_path) if config_path else None)
    store = _make_store(cfg)
    server, _ = make_mcp_server(store)
    server.run()


@cli.command("conflicts")
@click.option("--status", default="pending", help="'pending' or 'resolved'")
@click.option("--config", "config_path", default=None, help="Path to config.json")
def list_conflicts(status: str, config_path: str | None) -> None:
    """List and interactively resolve memory conflicts."""
    from pathlib import Path
    from memory_mesh.core.models import Resolution

    cfg = Config.load(Path(config_path) if config_path else None)
    store = _make_store(cfg)
    conflicts = store.list_conflicts(status=status)

    if not conflicts:
        click.echo(f"No {status} conflicts.")
        return

    for conflict in conflicts:
        click.echo(f"\n{'='*60}")
        click.echo(f"Conflict ID: {conflict.id}  [{conflict.trigger}]")
        a = conflict.memory_a
        b = conflict.memory_b
        click.echo(f"\n  A [{conflict.memory_a_id}] ({a.agent_id if a else '?'}):")
        click.echo(f"    {a.content if a else '(not found)'}")
        click.echo(f"\n  B [{conflict.memory_b_id}] ({b.agent_id if b else '?'}):")
        click.echo(f"    {b.content if b else '(not found)'}")

        if status == "resolved":
            click.echo(f"\n  Winner: {conflict.resolution_id} (by {conflict.resolved_by})")
            continue

        choice = click.prompt(
            "\n  Which is correct? [a/b/skip]",
            type=click.Choice(["a", "b", "skip"], case_sensitive=False),
            default="skip",
        )
        if choice == "skip":
            continue
        winning_id = conflict.memory_a_id if choice == "a" else conflict.memory_b_id
        resolution = Resolution(conflict_id=conflict.id, winning_id=winning_id, resolved_by="cli")
        store.resolve_conflict(resolution)
        click.echo(f"  Resolved: {winning_id} wins.")
```

- [ ] **Step 2: Verify CLI is wired up**

```bash
cd C:/Users/Chinmay/memory-mesh
memory-mesh --help
```

Expected:
```
Usage: memory-mesh [OPTIONS] COMMAND [ARGS]...

  memory-mesh — shared memory for all AI assistants.

Options:
  --help  Show this message and exit.

Commands:
  conflicts  List and interactively resolve memory conflicts.
  mcp        Start the MCP stdio server (used by Claude Desktop).
  serve      Start the REST API server on localhost:8765.
```

- [ ] **Step 3: Verify serve command help**

```bash
memory-mesh serve --help
```

Expected: Shows `--host`, `--port`, `--auth`, `--config` options.

- [ ] **Step 4: Commit**

```bash
git add memory_mesh/cli.py
git commit -m "feat: CLI entry points (serve, mcp, conflicts)"
```

---

## Task 14: Integration Tests

**Files:**
- Create: `tests/integration/test_store.py`
- Create: `tests/integration/test_conflict_pipeline.py`

- [ ] **Step 1: Write integration tests for store round-trips**

`tests/integration/test_store.py`:
```python
import pytest
from memory_mesh.config import Config
from memory_mesh.core.store import MemoryStore
from tests.unit.test_chroma import FakeEF


@pytest.fixture
def store(tmp_path):
    cfg = Config(data_dir=tmp_path)
    s = MemoryStore(cfg, embedding_function=FakeEF())
    s.connect()
    return s


def test_save_search_roundtrip(store):
    entry, _ = store.save(content="Python is great for data science", agent_id="claude")
    results = store.search("Python data science")
    ids = [e.id for e, _ in results]
    assert entry.id in ids


def test_uuid_consistent_across_stores(store):
    entry, _ = store.save(content="test content", agent_id="claude")
    from_sqlite = store.sqlite.get_by_id(entry.id)
    from_chroma = store.chroma.search("test content", limit=1)
    assert from_sqlite is not None
    assert from_chroma[0][0] == entry.id


def test_delete_removes_from_both_stores(store):
    entry, _ = store.save(content="to delete", agent_id="claude")
    store.delete(entry.id)
    assert store.sqlite.get_by_id(entry.id) is None
    chroma_results = store.chroma.search("to delete", limit=5)
    assert entry.id not in [r[0] for r in chroma_results]


def test_migration_schema_applied(store):
    cursor = store.sqlite.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    assert {"memories", "conflicts", "schema_migrations"}.issubset(tables)


def test_migration_recorded_once(store):
    rows = store.sqlite.conn.execute(
        "SELECT version FROM schema_migrations"
    ).fetchall()
    versions = [r[0] for r in rows]
    assert "001_initial" in versions
    assert versions.count("001_initial") == 1
```

- [ ] **Step 2: Write integration tests for conflict pipeline**

`tests/integration/test_conflict_pipeline.py`:
```python
import pytest
from memory_mesh.config import Config
from memory_mesh.core.models import Resolution
from memory_mesh.core.store import MemoryStore
from tests.unit.test_chroma import FakeEF


@pytest.fixture
def store(tmp_path):
    cfg = Config(data_dir=tmp_path)
    s = MemoryStore(cfg, embedding_function=FakeEF())
    s.connect()
    return s


def test_key_conflict_detected_and_stored(store):
    store.save(content="Go is the best language", agent_id="claude", key="preferred_lang")
    entry, conflicts = store.save(content="Python is the best language", agent_id="chatgpt", key="preferred_lang")

    assert len(conflicts) == 1
    assert conflicts[0].trigger == "key_match"
    assert conflicts[0].status == "pending"

    # Verify written to SQLite
    pending = store.list_conflicts(status="pending")
    assert len(pending) == 1
    assert pending[0].id == conflicts[0].id


def test_conflict_hydrates_memory_entries(store):
    store.save(content="Go is best", agent_id="claude", key="lang")
    _, conflicts = store.save(content="Python is best", agent_id="chatgpt", key="lang")
    pending = store.list_conflicts(status="pending")
    assert pending[0].memory_a is not None
    assert pending[0].memory_b is not None
    assert pending[0].memory_a.content in ("Go is best", "Python is best")


def test_resolve_conflict_marks_resolved(store):
    store.save(content="Go is best", agent_id="claude", key="lang")
    _, conflicts = store.save(content="Python is best", agent_id="chatgpt", key="lang")
    conflict = conflicts[0]

    resolution = Resolution(conflict_id=conflict.id, winning_id=conflict.memory_a_id, resolved_by="cli")
    resolved = store.resolve_conflict(resolution)

    assert resolved.status == "resolved"
    assert resolved.resolution_id == conflict.memory_a_id
    assert resolved.resolved_by == "cli"

    # No longer in pending
    pending = store.list_conflicts(status="pending")
    assert len(pending) == 0
    resolved_list = store.list_conflicts(status="resolved")
    assert len(resolved_list) == 1


def test_duplicate_conflict_not_created(store):
    store.save(content="Go is best", agent_id="claude", key="lang")
    store.save(content="Python is best", agent_id="chatgpt", key="lang")
    # Save again with same key — should not create a duplicate pending conflict
    _, conflicts = store.save(content="Rust is best", agent_id="gemini", key="lang")
    pending = store.list_conflicts(status="pending")
    # Only unique pairs
    pairs = {(c.memory_a_id, c.memory_b_id) for c in pending}
    assert len(pairs) == len(pending)
```

- [ ] **Step 3: Run all integration tests**

```bash
pytest tests/integration/ -v
```

Expected: 9 passed

- [ ] **Step 4: Run the full test suite**

```bash
pytest -v
```

Expected: All tests pass. Note: ChromaDB may emit a telemetry warning — safe to ignore.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/
git commit -m "test: integration tests for store round-trips and conflict pipeline"
```

---

## Final Verification

- [ ] **Verify package installs cleanly**

```bash
pip install -e .
memory-mesh --help
```

- [ ] **Verify all tests pass**

```bash
pytest -v --tb=short
```

Expected: All tests pass.

- [ ] **Verify Claude Desktop config snippet works**

Add to `claude_desktop_config.json`:
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

- [ ] **Final commit**

```bash
git add -A
git commit -m "chore: final verification — all tests passing"
```
