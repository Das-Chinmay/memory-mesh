from datetime import datetime, timezone
from unittest.mock import MagicMock
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
