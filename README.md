# AIVC — AI Version Control (Memory System)

**Long-term memory MCP server for LLM agents**, designed to help AI assistants remember their reasoning, decisions, and context across sessions.

> **Status**: 🟢 **Phase 31 (Done)** : Ultra-Fast Search Engine (ThreadPool-based).

### Concept

AIVC transforms **memories** (formerly commits) into a searchable knowledge base for AI agents. 

1. **Remember**: The agent records its "achievements" in memories containing an **extremely detailed Markdown note**.
2. **Recall**: Semantic indexing (Bi-encoder + Cross-encoder) operates on these notes to retrieve past context by meaning.
3. **Recursive Context**: File history is preserved locally, allowing agents to see what changed and how.
4. **Metadata-only Sync**: Reasoning is shared across machines via Google Drive, while file contents (blobs) remain local for privacy and performance.

---

## Installation

```bash
# Quick install (automatically configures the MCP server)
curl -fsSL "https://raw.githubusercontent.com/hjamet/aivc/main/install.sh" | bash
```

```bash
# OR local installation from the repo
bash install.sh
```

**Prerequisites**: Python 3.11+, `uv` (`curl -fsSL https://astral.sh/uv/install.sh | sh`)

---

## Tool Reference (MCP)

| Tool | Type | Description |
|-------|------|-------------|
| `remember` | Write | Records a memory (Title + Detailed Note) and snapshots files. **Call after every significant step.** |
| `recall` | Read | Semantic search over past memories. Returns Top results (ID, title, score) + snippets. |
| `get_recent_memories`| Read | Chronological journal of the last N memories. |
| `consult_memory`| Read | Full content (Markdown note + Files) of a specific memory. |
| `get_status` | Read | Tracked files with a navigable folder tree and storage usage. |
| `consult_file` | Read | AIVC history of a file: list of memories that touched it. |
| `read_historical_file` | Read | Content of a file as it was during a past memory (Local only). |
| `track` / `untrack` | Management | Manage file surveillance and history. |
| `search_files` | Read | Fast lexical search (Keywords/Regex) in current file contents. **Parallel & Case-insensitive.** |

---

## CLI Commands

| Command | Description |
|----------|-------------|
| `aivc status [path]` | Show tracked files tree (recursive sizes) |
| `aivc track <path...>` | Add files/directories/globs to tracking |
| `aivc untrack <path...>` | Remove files and ERASE history (DESTRUCTIVE) |
| `aivc memories` | Show memory history (aliases: `log`) |
| `aivc recall <query>` | Semantic search in memory (aliases: `search`) |
| `aivc sync setup` | Interactive Google Drive metadata sync setup |
| `aivc sync push` | Force push all missing local memories to Drive |

---

## Documentation Index

| Title (Link) | Description |
|--------------|-------------|
| [Architecture Index](docs/index_architecture.md) | Technical architecture of the project |
| [Tasks Index](docs/index_tasks.md) | Roadmap task specifications |
| [Sync Policy](docs/index_sync.md) | Details on Phase 29/30 metadata-only sync |

---

## Roadmap

- `[x]` Phase 28: Synchronous I/O Optimization.
- `[x]` Phase 29: Memory Refactor & Tree Status. [[Spec](docs/tasks/phase29.md)]
- `[x]` Phase 30: System Unification & Debt Cleanup. [[Spec](docs/tasks/phase30_debt_cleanup.md)]
- `[x]` Phase 31: Ultra-Fast Parallel Search (Obsidian-like).
- `[x]` Bugfix: Infinite loading of large graphs in Web UI
