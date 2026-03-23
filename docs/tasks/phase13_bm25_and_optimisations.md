# Phase 13 — BM25 Lexical Search & CoreIndex Optimization

## 1. Context & Discussion (Narrative)

> *Following the handover style: Tell the story of why we're doing this.*
During an architecture session, we identified that AIVC lacked a way to search by keyword (lexical) within the content of tracked files (initial Phase 13). 

In parallel, the Architect spotted a major technical debt introduced during Phase 15 (CoreIndex): the `Workspace.__init__` constructor systematically scans the entire `commits/*.json` folder at startup to check if historical commits are missing from the SQLite index. With 50,000 commits, this check would cause the response times of every CLI call (`aivc status`, etc.) to collapse. 

The user therefore demanded grouping the addition of BM25 and this critical optimization into a single large phase to avoid multiplying mini-tasks, while also asking to move hardcoded ML configuration (e.g., `all-MiniLM-L6-v2`) to the newly created `config.py` file.

## 2. Concerned Files

- `install.sh` and `install_dev.sh` (Migration hook addition)
- `src/aivc/cli.py` (New `migrate` subcommand)
- `src/aivc/core/workspace.py` (Removal of synchronous migration)
- `src/aivc/config.py` (Addition of ML model constants)
- `src/aivc/semantic/indexer.py` (Use of centralized ML config)
- `src/aivc/semantic/searcher.py` (BM25 & ML config usage)
- `src/aivc/semantic/engine.py` (Making BM25 search available)
- `src/aivc/server.py` (New MCP tool for BM25)
- `src/aivc/cli.py` (New CLI subcommand)

## 3. Objectives (Definition of Done)

* **Explicit Migration (via Install)**: Heavy I/O (JSON `glob`) is **completely removed** from `Workspace.__init__`. Migration logic is moved to a new `aivc migrate` CLI command.
* **Installation Hooks**: The `install.sh` and `install_dev.sh` scripts automatically execute `aivc migrate` at the end of their run to ensure a seamless transition for the user.
* **ML Centralization**: Model IDs (`all-MiniLM-L6-v2`, `ms-marco-MiniLM-L-6-v2`, etc.) are no longer hardcoded in the semantic logic but extracted from `src/aivc/config.py`.
* **BM25 Search**: The system implements a BM25 base (via `rank_bm25` or equivalent) on the raw text content of files tracked by AIVC, to allow searching for *exact code* (function names, variables) where semantic search fails.
* **MCP / CLI Exposure**: BM25 lexical search is exposed via a `search_files_bm25` MCP tool and a CLI subcommand.
* The test suite runs successfully with no regression on system performance.
