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
