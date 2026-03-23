# Phase 13 — BM25 Search on Tracked Files

## 1. Context & Discussion (Narrative)

During the architecture session on March 19, 2026, the user proposed adding a **lexical/keyword** search (BM25 style) on the content of tracked files. Currently, `search_memory` operates on commit notes (semantic). There is no way to search within the content of the files themselves.

### Technical decisions

- **Library**: `bm25s` — pure Python, ultra-lightweight (~50KB), no ML model.
- **Scope**: Only the **current version** of tracked files (not history).
- **Incremental indexing**: At each `create_commit`, only the files in the commit are re-indexed (not a full rebuild).
- **Binary files**: Excluded from indexed content, **but their title (filename) is indexed**.
- **Optional Glob**: The tool accepts an optional glob filter to restrict the search to specific folders/extensions (e.g., `*.py`, `docs/**/*.md`).

### Tool name

`search_files(query, glob?)` — clearly distinguished from `search_memory` (commit notes).

## 2. Concerned Files

- `src/aivc/search/bm25_index.py` (NEW) — BM25 engine (index, tokenization, search)
- `src/aivc/semantic/engine.py` — Integration of the BM25 indexer
- `src/aivc/server.py` — New `search_files` MCP tool
- `src/aivc/server.py` — Update of `_SYSTEM_PROMPT`
- `src/aivc/cli.py` — Eventually a CLI command `aivc search-files`
- `src/tests/test_bm25_index.py` (NEW) — Unit tests
- `pyproject.toml` — Addition of the `bm25s` dependency

## 3. Objectives (Definition of Done)

* A BM25 index is maintained on the textual content (UTF-8) of tracked files.
* The index is updated incrementally at each `create_commit` (only the files in the commit).
* Non-UTF-8 files are excluded from indexed content but their filename remains searchable.
* The `search_files(query, glob?)` MCP tool returns the most relevant files with a relevance score.
* The optional glob filter allows restricting the search (folders, extensions).
* Search is fast (O(ms)) and memory footprint is minimal.
* The system prompt documents the tool and its distinction from `search_memory`.
