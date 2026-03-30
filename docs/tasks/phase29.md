# Phase 29: Memory Refactor, Blob Sync Removal & Tree Status

## 1. Contexte & Discussion (Narratif)
> *Handover note: Transitioning from 'Git for Agents' to 'Long-Term Memory' architecture.*

AIVC was initially built as a file-versioning system with semantic search. In Phase 29, we realized that for AI agents, the **reasoning** (the commit note) is the most valuable asset, while the file blobs are heavy and often redundant between machines (since they are usually synced via Git anyway).

This phase implements a major refactoring:
- **Terminology**: 'Commit' is now 'Memory' or 'Remember'. This matches the agent context better.
- **Security & Storage**: We stopped syncing file blobs to Google Drive. Only the memory metadata (titles, notes) is shared. This prevents leaking large datasets or sensitive contents to Drive while still allowing agents on different machines to know *what* was done.
- **Context Management**: The `get_status` tool was list-based, which saturated the LLM's context with 100+ lines. It is now a folder tree (depth 1) with recursive size calculations.

## 2. Fichiers Concernés
- `src/aivc/server.py`: Renaming tools, tree status, compression, remote warnings.
- `src/aivc/sync/drive.py`: Disabling blob sync.
- `src/aivc/cli.py`: Renaming commands.
- `install.sh` / `install_dev.sh`: Updating agent rules.
- `README.md`: Updating the project documentation.

## 3. Objectifs (Definition of Done)
*   **Renaming**: ALL MCP tools used by the agent (`create_commit`, `search_memory`, `consult_commit`, `get_recent_commits`) MUST be renamed to `remember`, `recall`, `consult_memory`, and `get_recent_memories`.
*   **Sync**: Navigating memories from another machine MUST work without trying to download blobs.
*   **Status**: `aivc status` MUST display a tree structure with directories and their total sizes.
*   **Compression**: When a memory adds many files (e.g. >10), they MUST be grouped by directory in the tool output to avoid context noise.
