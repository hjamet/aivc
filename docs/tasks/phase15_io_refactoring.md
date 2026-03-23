# Phase 15 — I/O Performance Refactoring (CoreIndex)

## 1. Context & Discussion (Narrative)
During the architecture review on March 19, 2026, the Architect identified a critical bottleneck in `Workspace._all_commits()`. This function loads **every JSON file** in the `commits/` folder for each call to `get_status()` or `untrack()`. Over a history of several hundred commits, this generates a prohibitive number of disk accesses and JSON parsings.

Two architectural options were proposed:
- **Option A**: Move the logic up to `SemanticEngine` (making the engine the orchestrator for performant queries).
- **Option B**: Create a standalone SQLite `CoreIndex` in `core/` so that `Workspace` becomes ultra-fast by itself, without dependencies on the semantic layer.

**The user validated Option B** on March 19, 2026. The main reason: to preserve strict isolation between the versioning engine (`core/`) and the semantic layer (`semantic/`). `CoreIndex` is a lightweight, stdlib-compatible component (SQLite is in the Python stdlib) that stores fast metadata (commit ID, parent_id, file paths, blob hashes).

The existing `CooccurrenceGraph` in `semantic/graph.py` remains but focuses exclusively on semantic search (file↔commit co-occurrence, glob queries).

## 2. Concerned Files
- `src/aivc/core/index.py` — **[NEW]** SQLite CoreIndex: `commits` table (id, parent_id, timestamp, title), `file_changes` table (commit_id, path, blob_hash, action, bytes_added, bytes_removed)
- `src/aivc/core/workspace.py` — Integrates `CoreIndex`, removes `_all_commits()`, optimizes `get_status()`, `untrack()`, `find_child_commit()`
- `src/aivc/semantic/engine.py` — No structural changes expected (pass-throughs remain the same)
- `src/tests/test_index.py` — **[NEW]** CoreIndex unit tests
- `src/tests/test_workspace.py` — Non-regression verification
- `src/tests/test_server.py` — Verification that MCP tools remain functional

## 3. Objectives (Definition of Done)
* A `src/aivc/core/index.py` file exists, containing a SQLite `CoreIndex` with `commits` and `file_changes` tables.
* `Workspace` owns and populates this `CoreIndex` at every `create_commit()`.
* On first run, existing JSON commits are automatically migrated to the `CoreIndex`.
* `Workspace.get_status()` no longer calls `_all_commits()` but queries the `CoreIndex`.
* `Workspace.untrack()` no longer calls `_all_commits()` but queries the `CoreIndex`.
* `Workspace.find_child_commit()` uses the `CoreIndex` for an O(1) lookup instead of traversing the entire chain.
* `_all_commits()` is removed or deprecated.
* No regression on existing tests.
* No dependency from `core/` to `semantic/` is introduced.
