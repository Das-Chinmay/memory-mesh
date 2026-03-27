from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    id: str
    agent_id: str
    key: str | None = None
    content: str
    tags: list[str] = Field(default_factory=list)
    session_id: str | None = None
    created_at: datetime
    updated_at: datetime


class Conflict(BaseModel):
    id: str
    memory_a_id: str
    memory_b_id: str
    memory_a: MemoryEntry | None = None
    memory_b: MemoryEntry | None = None
    trigger: Literal["key_match", "similarity", "nli"]
    status: Literal["pending", "resolved"] = "pending"
    resolution_id: str | None = None
    resolved_by: Literal["cli", "mcp", "rest"] | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class Resolution(BaseModel):
    conflict_id: str
    winning_id: str
    resolved_by: Literal["cli", "mcp", "rest"] = "mcp"
