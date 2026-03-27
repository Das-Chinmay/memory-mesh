# Git Cleanup & Production README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strip all Co-Authored-By lines from the git history using git-filter-repo, then write and publish a production README.md with badges, quick starts, architecture diagram, and conflict demo.

**Architecture:** Task 1 rewrites commit messages atomically via git-filter-repo then force-pushes. Task 2 writes README.md, sets GitHub repo metadata via gh CLI, commits (no Co-Authored-By), and pushes.

**Tech Stack:** git-filter-repo (pip), gh CLI, GitHub Shields.io badges

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `README.md` | Full project documentation |

No Python files are touched. This plan is purely git history + docs.

---

### Task 1: Install git-filter-repo and strip Co-Authored-By from all commits

**Files:**
- No files created or modified — rewrites commit messages only

- [ ] **Step 1: Install git-filter-repo**

```bash
pip install git-filter-repo
```

Expected: `Successfully installed git-filter-repo-...`

Verify it's on PATH:
```bash
git filter-repo --version
```

Expected: prints a version string like `2.x.x`

- [ ] **Step 2: Run the message-callback filter**

```bash
cd "C:\Users\Chinmay\memory-mesh"
git filter-repo --force --message-callback '
import re
message = re.sub(rb"\nCo-Authored-By:[^\n]*", b"", message)
message = re.sub(rb"\n{3,}", b"\n\n", message)
return message.rstrip() + b"\n"
'
```

Expected output: git-filter-repo prints a summary of rewritten commits and exits cleanly. All 21 commits will have new SHAs.

- [ ] **Step 3: Verify no Co-Authored-By lines remain**

```bash
git log --format="%B" | grep "Co-Authored-By"
```

Expected: **no output**. If any lines appear, re-run Step 2.

- [ ] **Step 4: Spot-check a few commit messages are intact**

```bash
git log --oneline
```

Expected (subjects unchanged, SHAs will differ):
```
<sha> docs: add design spec for git cleanup and production README
<sha> Add .gitignore for Python artifacts
<sha> docs: track code review issues 5-12 for GitHub filing
<sha> test: integration tests for store round-trips and conflict pipeline
...
```

- [ ] **Step 5: Re-add the remote**

git-filter-repo removes all remotes as a safety measure. Re-add it:

```bash
git remote add origin https://github.com/Das-Chinmay/memory-mesh.git
```

Verify:
```bash
git remote -v
```

Expected:
```
origin  https://github.com/Das-Chinmay/memory-mesh.git (fetch)
origin  https://github.com/Das-Chinmay/memory-mesh.git (push)
```

- [ ] **Step 6: Force-push master**

```bash
git push --force origin master
```

Expected: `To https://github.com/Das-Chinmay/memory-mesh.git` followed by `+ <old-sha>...<new-sha> master -> master (forced update)`

---

### Task 2: Write README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

Create `README.md` at the repo root with this exact content:

````markdown
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
                │  L3: NLI (opt)  │
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
````

- [ ] **Step 2: Verify the file was written correctly**

```bash
head -5 README.md
```

Expected:
```
# 🧠 memory-mesh

[![PyPI](https://img.shields.io/pypi/v/memory-mesh)]...
```

- [ ] **Step 3: Commit the README**

```bash
git add README.md
git commit -m "docs: add production README with badges, quick starts, and architecture"
```

Verify no Co-Authored-By in this commit:
```bash
git log -1 --format="%B"
```

Expected: just the commit subject, no Co-Authored-By line.

---

### Task 3: Set GitHub repo metadata and push

**Files:**
- No files modified

- [ ] **Step 1: Set repo description**

```bash
gh repo edit Das-Chinmay/memory-mesh \
  --description "🧠 Local-first MCP server giving Claude, ChatGPT and Gemini shared memory with conflict detection"
```

Expected: `✓ Edited repository Das-Chinmay/memory-mesh`

- [ ] **Step 2: Add repo topics**

```bash
gh repo edit Das-Chinmay/memory-mesh \
  --add-topic mcp \
  --add-topic memory \
  --add-topic llm \
  --add-topic ai \
  --add-topic python \
  --add-topic chromadb \
  --add-topic claude \
  --add-topic chatgpt \
  --add-topic gemini \
  --add-topic mcp-server
```

Expected: `✓ Edited repository Das-Chinmay/memory-mesh`

- [ ] **Step 3: Push the README commit**

```bash
git push origin master
```

Expected: `master -> master` (regular push, not forced — README commit is new on top of the rebased history).

- [ ] **Step 4: Verify the repo looks correct**

```bash
gh repo view Das-Chinmay/memory-mesh
```

Expected: description and topics appear. README renders in the output.

---

## Self-Review Checklist

- [x] git-filter-repo strips Co-Authored-By from all commits including the spec commit (which has none, so it's a no-op)
- [x] Remote re-add step is included after filter-repo (it removes remotes)
- [x] README contains all required sections: badges, tagline, magic moment, install, Claude Desktop quick start, ChatGPT/Gemini quick start, architecture, config table, contributing
- [x] Magic moment uses semantic similarity (Layer 2 / `trigger: similarity`) — correct per design
- [x] Config table covers all 9 fields from `memory_mesh/config.py` (`diff_ratio_threshold` omitted — spec says it's reserved/not active, confirmed in ISSUES.md issue #5)
- [x] Commit in Task 2 has no Co-Authored-By
- [x] gh CLI commands use exact flag syntax (`--add-topic` one per flag, not comma-separated)
- [x] No placeholders, TBDs, or "implement later" anywhere
