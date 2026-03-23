# Phase 2: Semantic Engine and Knowledge Graph

## 1. Context & Discussion (Narrative)

> Phase 2 introduces search intelligence. Semantic search applies
> **only to commit Markdown notes**.
>
> Following user feedback, the indexing architecture moves upmarket while
> remaining local:
> 1. **Bi-Encoder** (`all-MiniLM-L6-v2`): For roughing out and quickly retrieving a Top K.
> 2. **Cross-Encoder**: For precisely reranking the Top K and isolating the ultra-relevant Top N.
>
> All of this must necessarily run in an isolated virtual environment (`~/.aivc/`) to avoid polluting the host OS.
>
> **Architect's Decision (2026-03-18)**: The visual interface (Web UI) is cancelled for now. Installation will be handled by an automated bash `install.sh` script (via `curl | bash`) which will dynamically inject AIVC's configuration into Gemini Antigravity's `mcp_config.json` file, making integration instantaneous.
> Integration with Phase 1's `core` will be done via a `SemanticEngine` wrapper (Option B) to preserve Phase 1's stdlib purity.

## 2. Concerned Files

- `pyproject.toml`
- `src/aivc/semantic/indexer.py` — Vector database (ChromaDB)
- `src/aivc/semantic/searcher.py` — Reranking pipeline (Bi-encoder -> Cross-encoder)
- `src/aivc/semantic/graph.py` — Co-occurrence graph algorithm
- `src/aivc/semantic/engine.py` — Orchestrator (wrapper around Workspace + Indexer + Graph)
- `install.sh` — Bash script + `mcp_config.json` setup

## 3. Objectives (Definition of Done)

* Local vector indexing with `all-MiniLM-L6-v2` via ChromaDB.
* Retrieval & Reranking pipeline with Cross-Encoder for maximum precision.
* Dynamically updated co-occurrence graph.
* The "SemanticEngine" wraps the "Workspace" without introducing regressions on the latter.
* A functional `install.sh` script, executable via pipe (`cat install.sh | bash`), which configures the `uv` venv AND modifies the `~/.gemini/antigravity/mcp_config.json` file by parsing JSON in Python.
* The operating environment must be strictly limited to `~/.aivc/`.
* **No fallback**: any error must crash cleanly.
