from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from memory_mesh.core.store import MemoryStore
from memory_mesh.core.models import MemoryEntry, Resolution
from memory_mesh.config import Config


@pytest.fixture
def store(tmp_path):
    cfg = Config(data_dir=tmp_path)
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
