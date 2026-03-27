from datetime import datetime, timezone
from pathlib import Path
import pytest
import chromadb
from chromadb import EmbeddingFunction
from chromadb.api.types import Documents, Embeddings
from memory_mesh.storage.chroma import ChromaAdapter
from memory_mesh.core.models import MemoryEntry


class FakeEF(EmbeddingFunction[Documents]):
    """Deterministic fake embeddings: each char sums to a float vector."""

    def __init__(self) -> None:
        pass  # suppress DeprecationWarning about missing __init__

    def __call__(self, input: Documents) -> Embeddings:
        result = []
        for text in input:
            vec = [0.0] * 384
            for i, ch in enumerate(text):
                vec[i % 384] += ord(ch) / 1000.0
            norm = sum(v ** 2 for v in vec) ** 0.5 or 1.0
            result.append([v / norm for v in vec])
        return result

    @staticmethod
    def name() -> str:
        return "fake_ef"

    @staticmethod
    def build_from_config(config: dict) -> "FakeEF":
        return FakeEF()

    def get_config(self) -> dict:
        return {}


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
