# Phase 12 — "Consulted" Files in Commits

## 1. Context & Discussion (Narrative)

During the architecture session on March 19, 2026, the user proposed enriching the commit data model to allow the agent to associate **unmodified** files with a commit, in "consultation" mode.

The idea: when an agent works on a task, it often consults reference files without modifying them. These files provide crucial context but are not recorded in the commit. As a result, the co-occurrence graph loses information, and `get_related_files` queries become less relevant.

### User emphasis

The user **strongly insisted** on the quality of the documentation for this parameter in the system prompt. The model must understand that it should mention **only those documents that were TRULY useful** — not surface-level utility, but documents containing information that the agent **did not know before reading them**.

### Technical decisions

- Consulted files have the `consulted` action in `FileChange`.
- **No blobs** are stored (no snapshot of the content).
- **No refcount** is modified.
- The co-occurrence graph regularly records file↔commit edges.
- Consulted files **must be tracked** to be mentioned.
- The `consulted_files` parameter in `create_commit` is optional (empty list by default).

## 2. Concerned Files

- `src/aivc/core/commit.py` — Add `consulted` to valid `FileChange` actions
- `src/aivc/core/workspace.py` — Accept `consulted_files` in `create_commit()`
- `src/aivc/semantic/engine.py` — Parameter pass-through
- `src/aivc/server.py` — Add the parameter to the `create_commit` MCP tool
- `src/aivc/server.py` — Update of `_SYSTEM_PROMPT` to document behavior
- `src/aivc/cli.py` — Configuration centralization (bonus)
- `src/aivc/web/dashboard.py` — Configuration centralization (bonus)
- `src/tests/test_commit.py` — Tests of the new action
- `src/tests/test_workspace.py` — Tests of `create_commit` with consulted files

## 3. Objectives (Definition of Done)

* `FileChange` accepts `action="consulted"` with `blob_hash=None`, `bytes_added=0`, `bytes_removed=0`.
* `create_commit(title, note, consulted_files=[...])` adds consulted files as `FileChange(action="consulted")`.
* Consulted files appear in the co-occurrence graph (file↔commit edges).
* No blobs are stored for consulted files.
* The MCP server's system prompt clearly documents the expected behavior: mention ONLY truly useful documents, containing unknown information before consultation.
* Consulted files are displayed distinctly in `consult_commit` (e.g., `[consulted]` vs `[modified]`).
* Serialization/deserialization (`commit_to_dict`/`commit_from_dict`) supports the new action.

### Bonus: Configuration Centralization

* The `AIVC_STORAGE_ROOT` environment variable is loaded and validated in ONLY ONE place (new `src/aivc/config.py` file or equivalent mechanism).
* `server.py`, `cli.py`, and `dashboard.py` use this single entry point instead of each reading `os.environ` independently.
* No regressions on existing tests.
