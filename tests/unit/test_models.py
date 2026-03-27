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
