# Phase 11 — Expose the `track` tool in the MCP server

## 1. Context & Discussion (Narrative)

During the architecture session on March 19, 2026, it was noted that the `track` tool is the **only management operation** not exposed in the MCP server. This is an omission: the code exists in `Workspace.track()`, is wrapped in `SemanticEngine.track()`, and is accessible via the CLI (`aivc track`), but simply doesn't appear in `server.py`.

Without this tool, the LLM agent cannot add new files to tracking via MCP. It depends on the CLI or manual tracking, which breaks the agent's autonomous workflow.

The `untrack` tool is exposed, making the absence of `track` even more inconsistent.

## 2. Concerned Files

- `src/aivc/server.py` — Addition of the `track` MCP tool
- `src/aivc/server.py` — Update of the `_SYSTEM_PROMPT` (tool table)
- `src/tests/test_server.py` — Unit tests for the new tool

## 3. Objectives (Definition of Done)

* The `track(path)` MCP tool is exposed in `server.py` via `@mcp.tool()`.
* It accepts a path (file, directory, or glob pattern).
* It returns the list of newly tracked files, or a message indicating that no new files were added.
* The `_SYSTEM_PROMPT` in `server.py` is updated to include `track` in the tool table.
* The MCP tool table in the README is updated.
* Unit tests cover the cases: successful tracking, tracking an already followed file, invalid pattern.
