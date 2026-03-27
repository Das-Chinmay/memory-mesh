from __future__ import annotations

import difflib
from datetime import datetime, timezone
from uuid import uuid4

from memory_mesh.config import Config
from memory_mesh.core.models import Conflict, MemoryEntry
from memory_mesh.storage.chroma import ChromaAdapter
from memory_mesh.storage.sqlite import SQLiteAdapter


class ConflictDetector:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._nli_model = None

    def check(
        self,
        new_entry: MemoryEntry,
        sqlite: SQLiteAdapter,
        chroma: ChromaAdapter,
    ) -> list[Conflict]:
        conflicts: list[Conflict] = []
        seen_pairs: set[tuple[str, str]] = set()

        # Layer 1: Key match
        if new_entry.key:
            for existing in sqlite.get_by_key(new_entry.key):
                if existing.id == new_entry.id:
                    continue
                if existing.content == new_entry.content:
                    continue
                pair = _sorted_pair(new_entry.id, existing.id)
                if pair in seen_pairs or sqlite.conflict_exists(*pair):
                    continue
                seen_pairs.add(pair)
                conflicts.append(_make_conflict(new_entry.id, existing.id, "key_match"))

        return conflicts

    def _run_nli(self, text_a: str, text_b: str) -> bool:
        """Returns True if texts are contradictory per NLI model."""
        import numpy as np
        from sentence_transformers import CrossEncoder

        if self._nli_model is None:
            self._nli_model = CrossEncoder(self.config.nli_model)

        scores = self._nli_model.predict([[text_a, text_b]])[0]
        # Labels: 0=contradiction, 1=entailment, 2=neutral
        exp_scores = np.exp(scores - np.max(scores))
        probs = exp_scores / exp_scores.sum()
        return float(probs[0]) > 0.7


def _sorted_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def _make_conflict(id_a: str, id_b: str, trigger: str) -> Conflict:
    a, b = _sorted_pair(id_a, id_b)
    return Conflict(
        id=str(uuid4()),
        memory_a_id=a,
        memory_b_id=b,
        trigger=trigger,  # type: ignore[arg-type]
        created_at=datetime.now(timezone.utc),
    )
