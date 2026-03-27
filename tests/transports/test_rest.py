import pytest
from fastapi.testclient import TestClient
from memory_mesh.config import Config
from memory_mesh.core.store import MemoryStore
from memory_mesh.transports.rest_server import make_app
from tests.unit.test_chroma import FakeEF


@pytest.fixture
def client(tmp_path):
    cfg = Config(data_dir=tmp_path)
    store = MemoryStore(cfg, embedding_function=FakeEF())
    store.connect()
    app = make_app(store)
    return TestClient(app)


def test_save_memory(client):
    resp = client.post("/v1/memories", json={
        "content": "Python is great",
        "agent_id": "chatgpt",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["memory"]["content"] == "Python is great"
    assert data["memory"]["agent_id"] == "chatgpt"
    assert "conflicts" in data


def test_search_memory(client):
    client.post("/v1/memories", json={"content": "Python data science", "agent_id": "chatgpt"})
    resp = client.get("/v1/memories/search", params={"q": "Python"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert results[0]["content"] == "Python data science"


def test_list_conflicts_empty(client):
    resp = client.get("/v1/conflicts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_resolve_conflict(client):
    client.post("/v1/memories", json={"content": "Go is best", "agent_id": "claude", "key": "lang"})
    resp = client.post("/v1/memories", json={"content": "Python is best", "agent_id": "chatgpt", "key": "lang"})
    conflicts = resp.json()["conflicts"]
    assert len(conflicts) == 1
    conflict_id = conflicts[0]["id"]
    winning_id = conflicts[0]["memory_a_id"]

    resp = client.post(f"/v1/conflicts/{conflict_id}/resolve", json={"winning_id": winning_id})
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


def test_delete_memory(client):
    resp = client.post("/v1/memories", json={"content": "to delete", "agent_id": "claude"})
    mem_id = resp.json()["memory"]["id"]
    resp = client.delete(f"/v1/memories/{mem_id}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_delete_nonexistent_returns_404(client):
    resp = client.delete("/v1/memories/ghost")
    assert resp.status_code == 404
