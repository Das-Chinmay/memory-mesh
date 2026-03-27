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
        count = self.collection.count()
        if count == 0:
            return []
        n = min(limit, count)
        kwargs: dict = {"query_texts": [query], "n_results": n}
        if where:
            kwargs["where"] = where
        results = self.collection.query(**kwargs)
        ids = results["ids"][0]
        # ChromaDB cosine space: distance = 1 - cosine_similarity
        distances = results["distances"][0]
        return [(id_, max(0.0, min(1.0, 1.0 - dist))) for id_, dist in zip(ids, distances)]

    def delete(self, memory_id: str) -> None:
        self.collection.delete(ids=[memory_id])
