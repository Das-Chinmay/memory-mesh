from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from memory_mesh.core.models import Resolution
from memory_mesh.core.store import MemoryStore


def make_mcp_server(store: MemoryStore) -> tuple[FastMCP, dict]:
    """Returns (mcp_app, tools) where tools is a dict of raw callables for testing."""
    mcp = FastMCP("memory-mesh")
    tools: dict = {}

    @mcp.tool()
    def save_context(
        content: str,
        key: str | None = None,
        tags: list[str] | None = None,
        session_id: str | None = None,
        agent_id: str = "claude",
    ) -> dict:
        """Save a memory entry. Returns the saved entry and any detected conflicts."""
        entry, conflicts = store.save(
            content=content,
            agent_id=agent_id,
            key=key,
            tags=tags,
            session_id=session_id,
        )
        return {
            "memory": entry.model_dump(mode="json"),
            "conflicts": [c.model_dump(mode="json") for c in conflicts],
        }

    @mcp.tool()
    def search_context(
        query: str,
        limit: int = 10,
        agent_id: str | None = None,
        key: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict]:
        """Search memory entries by semantic similarity."""
        results = store.search(query=query, limit=limit, agent_id=agent_id, key=key, tags=tags)
        return [entry.model_dump(mode="json") for entry, _score in results]

    @mcp.tool()
    def list_conflicts(status: str = "pending") -> list[dict]:
        """List memory conflicts. status: 'pending' or 'resolved'."""
        conflicts = store.list_conflicts(status=status)
        return [c.model_dump(mode="json") for c in conflicts]

    @mcp.tool()
    def resolve_conflict(conflict_id: str, winning_id: str) -> dict:
        """Resolve a conflict by choosing the winning memory entry."""
        resolution = Resolution(conflict_id=conflict_id, winning_id=winning_id, resolved_by="mcp")
        conflict = store.resolve_conflict(resolution)
        return conflict.model_dump(mode="json")

    @mcp.tool()
    def delete_context(memory_id: str) -> dict:
        """Delete a memory entry by ID."""
        success = store.delete(memory_id)
        return {"success": success}

    tools["save_context"] = save_context
    tools["search_context"] = search_context
    tools["list_conflicts"] = list_conflicts
    tools["resolve_conflict"] = resolve_conflict
    tools["delete_context"] = delete_context

    return mcp, tools
