# Tracked Issues

Issues to file once the GitHub repository is created.
Run: `gh issue create --title "..." --body "..." --label "..."` per entry below.

---

## v1.0 Issues (items 5–6)

### Issue 5: Remove dead `import difflib` from `conflict.py`

**File:** `memory_mesh/core/conflict.py`

**Description:**
`import difflib` is present at the top of the file but `difflib` is never used. The `diff_ratio_threshold` config knob exists but the check was removed during implementation (the test values made it impractical). The import should be removed to avoid confusion.

**Label:** `cleanup`

---

### Issue 6: Remove always-True guard `if self._detector is not None` in `store.py`

**File:** `memory_mesh/core/store.py`

**Description:**
`ConflictDetector` is always instantiated in `__init__`, so `if self._detector is not None` inside `save()` is dead code. The guard should be removed and the detector call made unconditional, or the guard should be inverted to an `assert` for explicitness.

**Label:** `cleanup`

---

## v1.1 Issues (items 7–12)

### Issue 7: Search endpoint drops similarity scores in REST response

**File:** `memory_mesh/transports/rest_server.py`

**Description:**
`GET /v1/memories/search` calls `store.search()` which returns `list[tuple[MemoryEntry, float]]`, but the REST handler returns only the `MemoryEntry` objects — the similarity scores are silently dropped. This makes it impossible for REST clients to rank or threshold results. The response schema should include scores (e.g., `[{"entry": {...}, "score": 0.92}]`).

**Label:** `enhancement`, `v1.1`

---

### Issue 8: Auth middleware has no test coverage

**File:** `memory_mesh/transports/rest_server.py`, `tests/transports/test_rest.py`

**Description:**
The Bearer token auth middleware in `make_app()` is untested. There are no tests for:
- Requests with a valid token are accepted (200)
- Requests with an invalid token are rejected (401)
- Requests with no token are rejected (401)
- Auth is bypassed when `auth_enabled=False`

**Label:** `testing`, `v1.1`

---

### Issue 9: `memory-mesh conflicts` CLI command has no test coverage

**File:** `memory_mesh/cli.py`, `tests/`

**Description:**
The interactive `conflicts` CLI command has no automated tests. The command prompts for A/B/skip input in a loop and calls `store.resolve_conflict()`. It should be tested with mocked stdin to verify the full interaction flow including the resolution path and skip path.

**Label:** `testing`, `v1.1`

---

### Issue 10: `FakeEF` defined in `test_chroma.py` but imported by 4 other test files

**File:** `tests/unit/test_chroma.py`, `tests/`

**Description:**
`FakeEF` (the deterministic fake ChromaDB embedding function used in tests) is defined in `tests/unit/test_chroma.py` but imported directly by at least 4 other test files. It should live in `tests/conftest.py` as a shared pytest fixture so the import chain is explicit and the dependency is obvious.

**Label:** `cleanup`, `v1.1`

---

### Issue 11: `Config.load()` uses private `__dataclass_fields__` attribute

**File:** `memory_mesh/config.py`

**Description:**
`Config.load()` iterates `cls.__dataclass_fields__` to filter known config keys. `__dataclass_fields__` is a private CPython implementation detail — it works but is not part of the public dataclass API. Replace with `dataclasses.fields(cls)` which is the documented, stable approach.

**Label:** `cleanup`, `v1.1`

---

### Issue 12: `fetch_limit = limit * 3` heuristic in `store.search()` is unexplained

**File:** `memory_mesh/core/store.py`

**Description:**
When tags are specified, `store.search()` fetches `limit * 3` results from ChromaDB before post-filtering by tags. The multiplier `3` is a magic number with no comment explaining the reasoning (over-fetch to compensate for tag filter attrition). Either document the rationale with a comment, or replace with a configurable `tag_search_multiplier` config knob.

**Label:** `cleanup`, `v1.1`
