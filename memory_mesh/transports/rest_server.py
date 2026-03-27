from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from memory_mesh.config import Config
from memory_mesh.core.models import Resolution
from memory_mesh.core.store import MemoryStore


class SaveRequest(BaseModel):
    content: str
    agent_id: str
    key: str | None = None
    tags: list[str] | None = None
    session_id: str | None = None


class ResolveRequest(BaseModel):
    winning_id: str
    resolved_by: str = "rest"


def make_app(store: MemoryStore, config: Config | None = None) -> FastAPI:
    app = FastAPI(title="memory-mesh", version="0.1.0")

    # Auth middleware — only active when config.auth_enabled is True
    if config is not None and config.auth_enabled and config.auth_token:
        expected_token = config.auth_token

        @app.middleware("http")
        async def auth_middleware(request: Request, call_next):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer ") or auth[7:] != expected_token:
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
            return await call_next(request)

    @app.post("/v1/memories")
    def save_memory(req: SaveRequest):
        entry, conflicts = store.save(
            content=req.content,
            agent_id=req.agent_id,
            key=req.key,
            tags=req.tags,
            session_id=req.session_id,
        )
        return {
            "memory": entry.model_dump(mode="json"),
            "conflicts": [c.model_dump(mode="json") for c in conflicts],
        }

    @app.get("/v1/memories/search")
    def search_memories(
        q: str,
        limit: int = 10,
        agent_id: str | None = None,
        key: str | None = None,
        tags: str | None = None,
    ):
        tag_list = tags.split(",") if tags else None
        results = store.search(query=q, limit=limit, agent_id=agent_id, key=key, tags=tag_list)
        return [entry.model_dump(mode="json") for entry, _score in results]

    @app.get("/v1/conflicts")
    def list_conflicts(status: str = "pending"):
        conflicts = store.list_conflicts(status=status)
        return [c.model_dump(mode="json") for c in conflicts]

    @app.post("/v1/conflicts/{conflict_id}/resolve")
    def resolve_conflict(conflict_id: str, req: ResolveRequest):
        resolution = Resolution(
            conflict_id=conflict_id,
            winning_id=req.winning_id,
            resolved_by=req.resolved_by,  # type: ignore[arg-type]
        )
        conflict = store.resolve_conflict(resolution)
        return conflict.model_dump(mode="json")

    @app.delete("/v1/memories/{memory_id}")
    def delete_memory(memory_id: str):
        success = store.delete(memory_id)
        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")
        return {"success": True}

    return app
