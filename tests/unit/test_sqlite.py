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
    cursor = db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    assert "memories" in tables
    assert "conflicts" in tables
    assert "schema_migrations" in tables
