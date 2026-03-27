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
    # Save another conflicting entry — should not create a duplicate pending conflict for same pair
    _, conflicts = store.save(content="Rust is best", agent_id="gemini", key="lang")
    pending = store.list_conflicts(status="pending")
    # Verify all conflict pairs are unique
    pairs = {(c.memory_a_id, c.memory_b_id) for c in pending}
    assert len(pairs) == len(pending)
