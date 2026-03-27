# 🧠 memory-mesh

[![PyPI](https://img.shields.io/pypi/v/memory-mesh)](https://pypi.org/project/memory-mesh/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](#)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](#)

> Give Claude, ChatGPT and Gemini shared memory.

memory-mesh is a local-first MCP server and REST API that lets every AI assistant on your machine read and write to the same memory store — with automatic conflict detection when two agents disagree.

---

## The Magic Moment

No shared keys. No coordination. Just two agents writing what they know — and memory-mesh catching when they contradict each other.

```bash
# Claude saves a fact
curl -s -X POST http://localhost:8765/v1/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "The Eiffel Tower is 300 metres tall", "agent_id": "claude"}'

# Gemini saves a contradicting fact
curl -s -X POST http://localhost:8765/v1/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "The Eiffel Tower is 330 metres tall", "agent_id": "gemini"}'
```

The second response includes:

```json
{
  "memory": { "...": "..." },
  "conflicts": [{
    "id": "abc-123",
    "trigger": "similarity",
    "memory_a_id": "...",
    "memory_b_id": "..."
  }]
}
```

Resolve it interactively:

```
$ memory-mesh conflicts

============================================================
Conflict ID: abc-123  [similarity]

  A [...] (claude):
    The Eiffel Tower is 300 metres tall

  B [...] (gemini):
    The Eiffel Tower is 330 metres tall

  Which is correct? [a/b/skip]: a
  Resolved: claude's memory wins.
```

---

## Install

```bash
pip install memory-mesh
```

---

## Quick Start — Claude Desktop (MCP)

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memory-mesh": {
      "command": "memory-mesh",
      "args": ["mcp"]
    }
  }
}
```

Claude can now call `save_context`, `search_context`, `list_conflicts`, `resolve_conflict`, and `delete_context` as tools.

---

## Quick Start — ChatGPT / Gemini (REST)

Start the REST server:

```bash
memory-mesh serve
# memory-mesh REST server starting on http://127.0.0.1:8765
```

Then point your agent at `http://127.0.0.1:8765/v1/`. Available endpoints:

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/memories` | Save a memory entry |
| `GET` | `/v1/memories/search?q=...` | Semantic search |
| `GET` | `/v1/memories/{id}` | Fetch by ID |
| `DELETE` | `/v1/memories/{id}` | Delete a memory |
| `GET` | `/v1/conflicts` | List conflicts |
| `POST` | `/v1/conflicts/{id}/resolve` | Resolve a conflict |

---

## Architecture

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   Claude    │   │   ChatGPT   │   │   Gemini    │
│  (MCP/stdio)│   │  (REST API) │   │  (REST API) │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                  │
       └─────────────────┼──────────────────┘
                         │
                ┌────────▼────────┐
                │   MemoryStore   │
                └────────┬────────┘
                         │
             ┌───────────┴────────────┐
             │                        │
     ┌───────▼──────┐       ┌────────▼───────┐
     │    SQLite    │       │    ChromaDB    │
     │ source of    │       │ vector search  │
     │   truth      │       │ (embeddings)   │
     └──────────────┘       └────────────────┘
                         │
                ┌────────▼────────┐
                │ ConflictDetector│
                │  L1: key match  │
                │  L2: similarity │
                │  L3: NLI (opt) │
                └─────────────────┘
```

Every write flows through the ConflictDetector. Conflicts are stored in SQLite and surfaced in real time on the save response.

---

## Configuration

Config lives at `~/.memory-mesh/config.json` (created on first run with defaults).

| Field | Type | Default | Description |
|---|---|---|---|
| `data_dir` | path | `~/.memory-mesh` | Storage directory for SQLite + ChromaDB |
| `similarity_threshold` | float | `0.85` | Cosine similarity above which entries conflict |
| `nli_enabled` | bool | `false` | Enable Layer 3 NLI contradiction detection |
| `nli_model` | string | `cross-encoder/nli-deberta-v3-small` | HuggingFace model for NLI |
| `host` | string | `127.0.0.1` | REST server bind host |
| `port` | int | `8765` | REST server port |
| `auth_enabled` | bool | `false` | Enable Bearer token auth on REST server |
| `auth_token` | string | `null` | Token required when `auth_enabled` is true |

Example `config.json`:

```json
{
  "similarity_threshold": 0.90,
  "nli_enabled": true,
  "port": 9000
}
```

---

## Contributing

1. Fork and clone the repo
2. Install dev dependencies: `pip install -e ".[dev]"`
3. Run tests: `pytest`
4. Open a PR — all tests must pass

Please file bugs and feature requests as [GitHub Issues](https://github.com/Das-Chinmay/memory-mesh/issues).

---

## License

MIT © Chinmay Das
