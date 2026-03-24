# AIVC — AI Version Control

**Long-term memory MCP server for LLM agents**, inspired by human memory and Git.

> **Status**: 🟢 **Phase 26 (Finished)** : Auto Sync Push at Startup.

### Concept

AIVC transforms **commits** into memories for an AI agent. The system bypasses the overhead of semantic indexing of raw code:

1. The agent records its "achievements" in commits containing an **extremely detailed Markdown note** (the memory).
2. Semantic indexing (Bi-encoder + Cross-encoder) operates **exclusively** on these notes.
3. Recall works via a funnel: `search_memory` (returns summaries) → `consult_commit` (returns details/diffs), avoiding context saturation.
4. File history is preserved in content-addressable storage (SHA-256).

---

## Installation

```bash
# Quick install (automatically configures the MCP server)
curl -fsSL -H "Cache-Control: no-cache" "https://raw.githubusercontent.com/hjamet/aivc/main/install.sh?v=$(date +%s)&force=true" | bash
```

```bash
# OR local installation from the repo
bash install.sh

# Install only the core engine in development mode
uv pip install -e ".[dev]"

# Run tests
python -m pytest src/tests/ -v
```

**Prerequisites**: Python 3.11+, `uv` (`curl -fsSL https://astral.sh/uv/install.sh | sh`)
**Stack Phase 1**: stdlib only (`hashlib`, `uuid`, `json`, `pathlib`)
**Stack Phase 2**: ChromaDB, SentenceTransformers (`all-MiniLM-L6-v2`), Cross-Encoder (`ms-marco-MiniLM-L-6-v2`).
**Stack Phase 3**: MCP Python SDK (`mcp>=1.0`), FastMCP (stdio transport).

---

## Detailed Description

### Core — Versioning Engine (Phase 1)

SHA-256 content-addressable storage, inspired by Git:

- **BlobStore**: stores immutable binary blobs, deduplicated by hash. Integrated Reference Counting — a blob is physically deleted only when no file references it anymore (Garbage Collection).
- **Commit**: atomic unit of memory. Short title + detailed Markdown note + list of `FileChange` with size impact (`+X B / -Y B`).
- **Diff**: compares the known state (last hash) with the current disk — detects `added`, `modified`, `deleted`.
- **Workspace**: orchestrator. Tracks files/directories/globs, creates commits, computes status (current size + history weight), manages untrack with GC.

### Workflow

```
track(path/glob/dir) --> workspace.json
    | create_commit(title, note)
    --> compute_diff() --> BlobStore.store() --> Commit.json
    | SemanticEngine Indexing Queue (CPU) --> ChromaDB
    | SemanticEngine Sync Queue (I/O) --> rclone (Cloud)
    | untrack(file)
    --> BlobStore.decrement_ref() --> GC if refcount=0
```

### Cloud Sync & Multi-Machine (Phase 20 & 21)

AIVC supports facultative cloud synchronization:
- **Global Blob Pool**: Blobs are shared in `AIVC_Sync/blobs/`, leveraging SHA-256 for cross-machine deduplication.
- **Machine Isolation**: Commits and indexes remain isolated per machine in `AIVC_Sync/<machine_id>/`.
- **Decoupled Workers**: High-latency cloud uploads never block local semantic indexing.
- **Local Path Hints**: Distant commits automatically suggest equivalent local paths based on basename and context.
- **Native Google Drive API**: No external tools needed (replaces legacy rclone integration).

### Exposed MCP Tools (Phase 3)

| Tool | Type | Description |
|-------|------|-------------|
| `create_commit` | Write | Records an accomplishment (Title + Detailed Markdown) and snapshots files. **Call often — after every step.** |
| `search_memory` | Read | Semantic search. Returns Top Commits (ID, title, score) + most frequent files. Supports an optional glob filter. |
| `get_recent_commits`| Read | Journal of the last N commits (paginable via offset/limit), `git log` style. |
| `consult_commit`| Read | Full content (Markdown note + FileChange) of a specific commit. |
| `consult_file` | Read | AIVC history of a file: list of commits that touched it. |
| `get_status` | Read | Tracked files with current size and history weight. |
| `untrack` | Management | ⚠️ DESTRUCTIVE — Removes a **list** of files/directories/globs and purges their history (GC). |
| `track` | Management | Adds a **list** of files, globs or directories (activates automatic surveillance) to AIVC tracking. |
| `read_historical_file` | Read | Content of a file as it was during a past commit. |
| `search_files_bm25` | Read | Lexical search (BM25) in the current content of tracked files. |

---

## Documentation Index

| Title | Description |
|-------|-------------|
| [Architecture Index](docs/index_architecture.md) | Technical architecture of the project |
| [Tasks Index](docs/index_tasks.md) | Roadmap task specifications |
| [Sync Index](docs/index_sync.md) | Documentation for Cloud/Drive synchronization |

---

## Repo Map

```
aivc/
├── .agent/
├── docs/
├── tasks/
│   ├── phase1_versioning_engine.md
│   ├── phase2_semantic_graph.md
│   ├── phase3_mcp_interface.md
│   ├── phase6_absolute_paths_fix.md
│   └── phase9_cli_exposure.md
├── index_architecture.md
└── index_tasks.md
├── scripts/
│   └── migrate_commit_paths.py  # One-shot migration: relative → absolute paths
├── src/
│   ├── aivc/
│   │   ├── __init__.py
│   │   ├── server.py             # MCP Server (Phase 3) — 10 FastMCP tools
│   │   ├── cli.py                # CLI (aivc status/track/log/search/web)
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── blob_store.py    # SHA-256 + Refcount/GC
│   │   │   ├── commit.py        # Commit + FileChange Dataclasses
│   │   │   ├── diff.py          # Change detection
│   │   │   ├── index.py         # SQLite CoreIndex (fast I/O)
│   │   │   └── workspace.py     # Orchestrator Phase 1
│   │   ├── search/
│   │   │   ├── __init__.py
│   │   │   └── bm25_cache.py    # SQLite cache for BM25 tokenization
│   │   ├── config.py             # Central configuration (ML, storage)
│   │   ├── semantic/
│   │   │   ├── __init__.py
│   │   │   ├── indexer.py       # ChromaDB + SentenceTransformer
│   │   │   ├── searcher.py      # Bi-Encoder → Cross-Encoder Pipeline
│   │   │   ├── graph.py         # Bipartite files↔commits graph
│   │   │   └── engine.py        # SemanticEngine Facade (Phase 2)
│   │   └── web/
│   │       └── dashboard.py     # Cytoscape.js Web Dashboard
│   └── tests/
│       ├── conftest.py           # requires_ml marker + --run-ml flag
│       ├── test_blob_store.py
│       ├── test_commit.py
│       ├── test_diff.py
│       ├── test_workspace.py
│       ├── test_migrate.py      # Phase 6
│       ├── test_cli.py          # Phase 4 + 6
│       ├── test_indexer.py      # Phase 2
│       ├── test_searcher.py     # Phase 2
│       ├── test_graph.py        # Phase 2
│       ├── test_engine.py       # Phase 2
│       ├── test_index.py        # Phase 15
│       └── test_server.py       # Phase 3 — mock SemanticEngine
├── install.sh                   # Automatic install + MCP configuration
├── pyproject.toml
├── .gitignore
└── README.md
```

---

## Main Entry Scripts

| Command | Description |
|----------|-------------|
| `aivc status` | Show tracked files and their weight |
| `aivc track <path...>` | Add one or more files/directories/globs to tracking |
| `aivc untrack <path...>` | Remove one or more files/directories/globs from tracking (DESTRUCTIVE) |
| `aivc log [-n N]` | Show commit history |
| `aivc search <query> [-g GLOB]` | Semantic search in memory, with optional filter |
| `aivc search-files <query>` | Lexical search (BM25) in current files |
| `aivc web [-p PORT]` | Launch the interactive Web Dashboard |
| `aivc sync setup` | Interactive Google Drive sync setup (OAuth) |
| `aivc sync status` | Check sync status and remote machines |
| `aivc config [key] [value]` | View or update AIVC configuration |
| `aivc migrate` | Force JSON commit migration to SQLite |
| `python -m pytest src/tests/ -v` | Run full test suite |
| `uv pip install -e ".[dev]"` | Install core only (stdlib) |
| `uv pip install -e ".[semantic]"` | Install with AI dependencies (Phase 2) |

---

## Secondary Executable Scripts & Utilities

| `bash install.sh` | Install AIVC (prod ~/.aivc) and configure MCP server |
| `bash install_dev.sh` | Install AIVC (dev local .venv) for testing with local code |
| `python -m aivc.web.dashboard` | Launch Web Dashboard (interactive graph on port 8765) |
| `python scripts/migrate_commit_paths.py` | One-shot path migration: relative → absolute (Phase 6) |

---

## Roadmap

| Phase | Name | Spec | Status |
|-------|-----|------|------|
| **1** | [Internal Versioning Engine (Core)](docs/tasks/phase1_versioning_engine.md) | SHA-256 Blobs, Garbage Collection | 🟢 Finished |
| **2** | [Semantic Engine and Graph](docs/tasks/phase2_semantic_graph.md) | Bi/Cross Encoder, ChromaDB, install.sh MCP | 🟢 Finished |
| **3** | [MCP Interface and Tools](docs/tasks/phase3_mcp_interface.md) | Recall Funnel, 8 tools, system prompt | 🟢 Finished |
| **4** | [CLI Interface & Web Dashboard](docs/tasks/phase4_cli_and_dashboard.md) | Terminal tools (`aivc`), interactive graph (Size/Color) with targeted semantic search | 🟢 Finished |
| **5** | [MVP Stabilization & Bugfixes](docs/tasks/phase5_stabilization.md) | Absolute paths, port autodiscovery, Cytoscape vendoring | 🟢 Finished |
| **6** | [Absolute Consolidation & CLI](docs/tasks/phase6_absolute_paths_fix.md) | Sanitize history to 100% absolute, add `aivc track` | 🟢 Finished |
| **7** | [Scoped Semantic Search](docs/tasks/phase7_scoped_search.md) | Glob filtering in `search_memory` (MCP + CLI) | 🟢 Finished |
| **8** | [GEMINI.md Injection](docs/tasks/phase8_gemini_injection.md) | Agent best practices injected via `install.sh` | 🟢 Finished |
| **9** | [CLI Exposure](docs/tasks/phase9_cli_exposure.md) | Automatic symlink to `~/.local/bin/aivc` | 🟢 Finished |
| **10** | [Search Result Snippets](docs/tasks/phase10_search_snippets.md) | Contextual snippets in `search_memory` results | 🟢 Finished |
| **11** | [Track MCP Tool](docs/tasks/phase11_track_mcp_tool.md) | Exposure of the `track` tool in the MCP server | 🟢 Finished |
| **12** | [Consulted Files](docs/tasks/phase12_consulted_files.md) | `consulted` action in commits, graph enrichment | 🟢 Finished |
| **13** | [BM25 Search & CoreIndex Optimization](docs/tasks/phase13_bm25_and_optimisations.md) | Lexical search + Centralized ML config + Start perf fix | 🟢 Finished |
| **14** | [Commit Context](docs/tasks/phase14_commit_context.md) | Parent/Child commit display in `consult_commit` | 🟢 Finished |
| **15** | [I/O Performance Refactoring (CoreIndex)](docs/tasks/phase15_io_refactoring.md) | Standalone SQLite CoreIndex, elimination of `_all_commits()` | 🟢 Finished |
| **16** | [BM25 Reliability & CLI UX](docs/tasks/phase16_fiabilisation_bm25_ux_cli.md) | SQLite BM25 cache, Snippet optimization, CLI Storage Fallback | 🟢 Finished |
| **17** | [Watched Directories (JIT Watcher)](docs/tasks/phase17_watched_directories.md) | Transparent auto-tracking of new files in watched directories via JIT. | 🟢 Finished |
| **18** | [Internationalization and English Documentation](docs/tasks/internationalization_and_english_docs.md) | Full translation of README, technical documentation, and docstrings for collaboration with Amir. | 🟢 Finished |
| **19** | [Web Dashboard UX](docs/tasks/phase19_web_dashboard_ux.md) | Sidebar Git Log (Infinite Scroll), File history, cose layout fix | 🟢 Finished |
| **20** | [Cloud Sync & Async Indexing](docs/tasks/phase20_google_drive_sync.md) | Synchronisation inter-machines facultative et asynchrone des commits via Drive | 🟢 Finished |
| **21** | [Async & Sync Consolidation](docs/tasks/phase21_async_sync_consolidation.md) | Dette technique : séparation CPU/IO, Graceful Shutdown, Global Cloud Blobs | 🟢 Finished |
| **22** | [Local Hints Optimization](docs/tasks/phase22_local_hints_optimization.md) | Optimisation O(1) de la recherche de correspondances locales | 🟢 Finished |
| **23** | [State Sync & JIT Reload](docs/tasks/phase23_state_sync_reload.md) | Rechargement conditionnel de workspace.json pour éviter la désync CLI/MCP | 🟢 Finished |
| **25** | [Native Google Drive Sync](docs/tasks/phase25_native_google_drive.md) | Native Google Drive API replacing rclone | 🟢 Finished |
| **26** | [Auto Sync Push at Startup](docs/tasks/phase26_auto_sync_push.md) | Automatic push of missing local commits on server start | 🟢 Finished |

### Documentation Index
| Title (Link) | Description |
|--------------|-------------|
| [Phase 6 Spec](docs/tasks/phase6_absolute_paths_fix.md) | Technical specification for finalizing absolute paths. |
| [Phase 7 Spec](docs/tasks/phase7_scoped_search.md) | Glob-based semantic filtering. |
| [Phase 17 Spec](docs/tasks/phase17_watched_directories.md) | Watched Directories and JIT auto-tracking. |
| [Phase 8 Spec](docs/tasks/phase8_gemini_injection.md) | Injection of agent best practices in GEMINI.md. |
| [Phase 9 Spec](docs/tasks/phase9_cli_exposure.md) | Symbol link creation for global CLI access. |
| [Phase 10 Spec](docs/tasks/phase10_search_snippets.md) | Contextual snippets in semantic search results. |
| [Phase 11 Spec](docs/tasks/phase11_track_mcp_tool.md) | Exposure of the `track` tool in the MCP server. |
| [Phase 12 Spec](docs/tasks/phase12_consulted_files.md) | `consulted` action in commits. |
| [Phase 13 Spec](docs/tasks/phase13_bm25_and_optimisations.md) | BM25 lexical search and optimizations. |
| [Phase 14 Spec](docs/tasks/phase14_commit_context.md) | Chronological commit graph. |
| [Phase 15 Spec](docs/tasks/phase15_io_refactoring.md) | I/O performance refactoring. |
| [Phase 16 Spec](docs/tasks/phase16_fiabilisation_bm25_ux_cli.md) | BM25 reliability and CLI UX. |
| [Phase 17 Spec](docs/tasks/phase17_watched_directories.md) | Watched Directories and JIT auto-tracking. |
| [Phase 19 Spec](docs/tasks/phase19_web_dashboard_ux.md) | Web Dashboard UX improvements (Sidebar + Forces). |
| [Phase 20 Spec](docs/tasks/phase20_google_drive_sync.md) | Google Drive Sync architecture for multi-machine commits. |
| [Phase 21 Spec](docs/tasks/phase21_async_sync_consolidation.md) | Async and Cloud Sync Consolidation. |
| [Phase 22 Spec](docs/tasks/phase22_local_hints_optimization.md) | Local Hints Optimization (O(1)). |
| [Phase 23 Spec](docs/tasks/phase23_state_sync_reload.md) | State Sync & JIT Reload (Multi-process). |
| [Phase 25 Spec](docs/tasks/phase25_native_google_drive.md) | Native Google Drive API replacing rclone. |
| [Phase 26 Spec](docs/tasks/phase26_auto_sync_push.md) | Auto Sync Push at Startup. |
