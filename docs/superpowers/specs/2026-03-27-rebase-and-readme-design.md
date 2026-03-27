---
title: Git History Cleanup & Production README
date: 2026-03-27
status: approved
---

# Design: Git History Cleanup & Production README

## 1. Git History Cleanup

### Goal
Strip all `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` lines from every commit in the repository. Chinmay is the sole author.

### Approach
Use `git-filter-repo` (the Git-blessed replacement for `filter-branch`) with a Python message callback that removes matching lines and trims leftover blank lines.

### Steps
1. `pip install git-filter-repo`
2. Run:
   ```bash
   git filter-repo --force --message-callback '
   import re
   message = re.sub(rb"\nCo-Authored-By:[^\n]*", b"", message)
   message = re.sub(rb"\n{3,}", b"\n\n", message)
   return message.rstrip() + b"\n"
   '
   ```
3. Verify: `git log --format="%B" | grep "Co-Authored-By"` → empty
4. Re-add remote: `git remote add origin https://github.com/Das-Chinmay/memory-mesh.git`
   (git-filter-repo removes remotes as a safety measure)
5. Force-push: `git push --force origin master`

### Scope
All 20 commits on `master`. No tags, no other branches. All SHAs will change — expected for a fresh repo.

---

## 2. Production README

### Goal
A production-quality `README.md` that makes memory-mesh immediately understandable and installable by any developer who lands on the GitHub page.

### Structure (Hybrid: marketing-scannable + concept hook)

| Section | Purpose |
|---|---|
| Hero + badges | Tagline, PyPI / tests / MIT / Python 3.11+ |
| The Magic Moment | Semantic conflict example — hooks the reader in 10s |
| Install | `pip install memory-mesh` |
| Quick Start: Claude Desktop | `claude_desktop_config.json` snippet |
| Quick Start: ChatGPT / Gemini | `memory-mesh serve` + curl example |
| Architecture | ASCII diagram showing agents → transports → store → conflict detector |
| Configuration Reference | Full table of all Config fields |
| Contributing | Fork / PR / test instructions |

### Magic Moment Scenario
Two agents (no shared keys, same topic area):
- Claude saves: `"The Eiffel Tower is 300 metres tall"`
- Gemini saves: `"The Eiffel Tower is 330 metres tall"`

Layer 2 (cosine similarity) catches the near-duplicate with differing facts and surfaces a conflict. User resolves via `memory-mesh conflicts`.

### Badges
- PyPI version: `https://img.shields.io/pypi/v/memory-mesh`
- Tests: `https://img.shields.io/badge/tests-passing-brightgreen` (static until CI is wired)
- License: `https://img.shields.io/badge/license-MIT-blue`
- Python: `https://img.shields.io/badge/python-3.11%2B-blue`

### Repo metadata (via gh CLI)
- Description: `🧠 Local-first MCP server giving Claude, ChatGPT and Gemini shared memory with conflict detection`
- Topics: `mcp, memory, llm, ai, python, chromadb, claude, chatgpt, gemini, mcp-server`

### Commit
Single commit, no Co-Authored-By line, author Chinmay only.

---

## Success Criteria
- `git log --format="%B" | grep "Co-Authored"` returns nothing
- `git log --oneline` shows all original commit subjects intact
- README renders correctly on GitHub (badges resolve, code blocks syntax-highlighted)
- `gh repo view` shows correct description and topics
