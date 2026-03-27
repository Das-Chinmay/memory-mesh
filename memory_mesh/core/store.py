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
