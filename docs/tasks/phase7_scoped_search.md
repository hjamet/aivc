# Phase 7 — Scoped Semantic Search (Glob Filtering)

## 1. Context & Discussion (Narrative)

When using AIVC as a long-term memory, the agent (or CLI user) often wants to restrict its semantic search to a subset of files. Example: "What did I do on authentication in `src/api/auth/`?" or "Which commits touched `*.py` in `tests/`?".

Currently, `search_memory` searches through **all** commits without distinction. On a large history, this drowns relevant results in noise.

The idea is to add an optional `filter_glob` parameter (empty by default = no filtering) that restricts the search to commits that have modified at least one file matching the provided glob pattern.

### Technical decisions
- **Chosen approach**: Pre-filtering via the SQLite graph (`CooccurrenceGraph`), then passing valid `commit_id`s as an `$in` clause in ChromaDB before the Bi-Encoder. This reduces the search space as much as possible.
- **Fallback**: If the commit IDs list is too large for ChromaDB `$in`, filter in Python post-Bi-Encoder (before Cross-Encoder).
- **API**: The parameter is optional and empty by default (unchanged current behavior).

## 2. Concerned Files

- `src/aivc/semantic/graph.py` — New `get_commits_by_glob(pattern)` method
- `src/aivc/semantic/indexer.py` — Added `filter_ids` support in `query()`
- `src/aivc/semantic/searcher.py` — Filter propagation in the pipeline
- `src/aivc/semantic/engine.py` — Parameter propagation in the facade
- `src/aivc/server.py` — Added `filter_glob` parameter to the `search_memory` MCP tool
- `src/aivc/cli.py` — Added `--glob` / `-g` option to the `aivc search` command
- `src/tests/test_graph.py` — Tests for `get_commits_by_glob`
- `src/tests/test_searcher.py` — Tests for the filtered pipeline

## 3. Objectives (Definition of Done)

* `search_memory(query, filter_glob="src/aivc/semantic/*.py")` only returns commits that touched files in `src/aivc/semantic/` with a `.py` extension.
* `aivc search "my query" --glob "src/aivc/core/*"` works in CLI.
* If `filter_glob` is empty (default), behavior is **strictly identical** to current.
* Filtering works with absolute paths stored in the graph.
* Existing tests continue to pass without modification.
