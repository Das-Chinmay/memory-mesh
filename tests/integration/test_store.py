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
