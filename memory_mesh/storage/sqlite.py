from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from memory_mesh.core.models import Conflict, MemoryEntry, Resolution

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class SQLiteAdapter:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._apply_migrations()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("SQLiteAdapter.connect() not called")
        return self._conn

    def _apply_migrations(self) -> None:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        self.conn.commit()
        for sql_file in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            version = sql_file.stem
            row = self.conn.execute(
                "SELECT version FROM schema_migrations WHERE version = ?", (version,)
            ).fetchone()
            if row is None:
                sql = sql_file.read_text()
                self.conn.execute("BEGIN")
                try:
                    for statement in sql.split(";"):
                        stmt = statement.strip()
                        if stmt:
                            self.conn.execute(stmt)
                    self.conn.execute(
                        "INSERT INTO schema_migrations VALUES (?, ?)",
                        (version, datetime.now(timezone.utc).isoformat()),
                    )
                    self.conn.execute("COMMIT")
                except Exception:
                    self.conn.execute("ROLLBACK")
                    raise

    # --- Memories ---

    def insert_memory(self, entry: MemoryEntry) -> None:
        self.conn.execute(
            "INSERT INTO memories (id, agent_id, key, content, tags, session_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry.id,
                entry.agent_id,
                entry.key,
                entry.content,
                json.dumps(entry.tags),
                entry.session_id,
                entry.created_at.isoformat(),
                entry.updated_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_by_id(self, memory_id: str) -> MemoryEntry | None:
        row = self.conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        return _row_to_entry(row) if row else None

    def get_by_key(self, key: str) -> list[MemoryEntry]:
        rows = self.conn.execute(
            "SELECT * FROM memories WHERE key = ?", (key,)
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def delete_memory(self, memory_id: str) -> bool:
        cursor = self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # --- Conflicts ---

    def insert_conflict(self, conflict: Conflict) -> None:
        self.conn.execute(
            "INSERT INTO conflicts (id, memory_a_id, memory_b_id, trigger, status, "
            "resolution_id, resolved_by, resolved_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                conflict.id,
                conflict.memory_a_id,
                conflict.memory_b_id,
                conflict.trigger,
                conflict.status,
                conflict.resolution_id,
                conflict.resolved_by,
                conflict.resolved_at.isoformat() if conflict.resolved_at else None,
                conflict.created_at.isoformat(),
            ),
        )
        self.conn.commit()

    def conflict_exists(self, memory_a_id: str, memory_b_id: str) -> bool:
        a, b = sorted([memory_a_id, memory_b_id])
        row = self.conn.execute(
            "SELECT id FROM conflicts WHERE memory_a_id = ? AND memory_b_id = ? "
            "AND status = 'pending'",
            (a, b),
        ).fetchone()
        return row is not None

    def list_conflicts(self, status: str = "pending") -> list[Conflict]:
        rows = self.conn.execute(
            "SELECT * FROM conflicts WHERE status = ?", (status,)
        ).fetchall()
        return [_row_to_conflict(r) for r in rows]

    def resolve_conflict(self, resolution: Resolution) -> Conflict:
        # Validate the conflict exists and winning_id is valid
        row = self.conn.execute(
            "SELECT * FROM conflicts WHERE id = ?", (resolution.conflict_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Conflict not found: {resolution.conflict_id}")
        if resolution.winning_id not in (row["memory_a_id"], row["memory_b_id"]):
            raise ValueError(
                f"winning_id must be memory_a_id or memory_b_id of the conflict, "
                f"got: {resolution.winning_id}"
            )

        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE conflicts SET status='resolved', resolution_id=?, resolved_by=?, resolved_at=? "
            "WHERE id=?",
            (resolution.winning_id, resolution.resolved_by, now, resolution.conflict_id),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM conflicts WHERE id = ?", (resolution.conflict_id,)
        ).fetchone()
        return _row_to_conflict(row)


def _row_to_entry(row: sqlite3.Row) -> MemoryEntry:
    return MemoryEntry(
        id=row["id"],
        agent_id=row["agent_id"],
        key=row["key"],
        content=row["content"],
        tags=json.loads(row["tags"]),
        session_id=row["session_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _row_to_conflict(row: sqlite3.Row) -> Conflict:
    return Conflict(
        id=row["id"],
        memory_a_id=row["memory_a_id"],
        memory_b_id=row["memory_b_id"],
        trigger=row["trigger"],
        status=row["status"],
        resolution_id=row["resolution_id"],
        resolved_by=row["resolved_by"],
        resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
        created_at=datetime.fromisoformat(row["created_at"]),
    )
