# Phase 16 — BM25 Reliability & CLI UX

## 1. Context & Discussion (Narrative)

> *Following Phase 13 post-deployment feedback.*

During the architectural review of Phase 13, two critical technical debts were identified:
1. **BM25 Performance**: The implementation of `search_files_bm25` reads and tokenizes every tracked file from disk at each call. On a large repository, the repeated I/O and tokenization considerably slow down the search.
2. **CLI UX**: When a human uses the CLI (e.g., `aivc status`) without the `AIVC_STORAGE_ROOT` variable defined in their environment (unlike the MCP environment), the application crashes brutally instead of using the default directory.

This phase aims to ensure the lexical search tool is instantaneous over thousands of files and to make the CLI pleasant to use "out of the box."

## 2. Concerned Files

- `src/aivc/cli.py`
- `src/aivc/semantic/engine.py`
- `src/aivc/search/bm25_index.py` (NEW)
- `src/tests/test_cli.py`
- `src/tests/test_engine.py` (or `test_bm25.py`)
- `README.md`
- `docs/index_architecture.md` (or similar, to be updated)

## 3. Objectives (Definition of Done)

* **Smooth CLI UX**: The CLI uses the default fallback (`~/.aivc/storage`) if the `AIVC_STORAGE_ROOT` environment variable is not defined. The user no longer needs to edit their `.bashrc`.
* **BM25 Tokenization Cache**: Heavy operations (disk reading and regex tokenization) are cached. A SQLite index (e.g., `bm25_cache.db`) stores the tokens of each file with its `mtime` or size.
* **Incremental Update**: During a BM25 search, only files whose `mtime` or size has changed since the last caching are reread and re-tokenized.
* **Performance**: The `search_files_bm25` search responds in less than 100ms on a cached corpus.
* **Compatibility**: The current `rank_bm25` library is kept, with the performance gain coming from the elimination of unnecessary I/O.
