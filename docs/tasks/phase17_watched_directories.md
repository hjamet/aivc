# Phase 17 — Watched Directories (JIT Watcher)

## 1. Context & Discussion (Narrative)

> *Following architectural discussions after Phase 16.*

The user requires a system of **total, automatic, and continuous surveillance** of large folders, completely relieving the LLM agent of manual tracking management. The goal is to have an "Always-On Surveilled Scope" driven by the MCP server.

The Architect recorded that the most robust model is a hybrid **MCP Watcher Daemon + Startup Sync** architecture. 
1. **The Watcher reality**: A watcher (e.g., `watchdog`) only captures file creation events **when it is running**. If the MCP server is off while the user is working, these creations will be missed.
2. **The solution**: To ensure an infallible system, the MCP server **must** perform a *Startup Scan* (via `os.walk`) at every startup to catch up, THEN launch the *Real-time Watcher* for continuous total comfort.

### 🚨 Critical Rule: Deleted Files
Managing "new files" is simple (we `track()` them). But managing **deleted files** involves a deadly trap:
If the Watcher detects that a file has been deleted from the hard drive, **IT MUST NEVER** call `untrack()`. Setting a file to "untrack" erases it from AIVC's memory, which would prevent the next `create_commit` from detecting the deletion action (and recording it in the database history). 
The Watcher must only react to additions. AIVC's diff engine (`compute_diff`) will naturally handle recording deletions during the next commit.

## 2. Concerned Files

- `pyproject.toml` (Addition of `watchdog` dependency)
- `src/aivc/core/workspace.py` (Update of `track`/`untrack` to handle `watched_dirs`)
- `src/aivc/cli.py` (No new commands, `track` and `untrack` dynamically handle surveillance)
- `src/aivc/server.py` (Implementation of the Watcher thread and startup scan, removal of `watch_directory` tools)

## 3. Objectives (Definition of Done)

* **Automatic surveillance**: If `aivc track <dir>` is called with a directory, it is automatically added to `watched_dirs`.
* **Stop surveillance**: If `aivc untrack <dir>` is called with a directory, it removes surveillance AND destroys the history of all files inside.
* **Startup Scan (Sync)**: The `serve()` function performs the usual JIT scan.
* **Reactive Watcher**: A `watchdog` thread calls `track(path)` on new files created in these directories.
* **Protection of History**: The Watcher intentionally ignores `FileDeletedEvent`.
