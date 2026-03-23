# Phase 19 — Web Dashboard UX: Sidebar Git Log, File History, Fix Forces

## 1. Context & Discussion (Narrative)

The AIVC Web Dashboard (`aivc web`) was implemented in Phase 4 with Cytoscape.js.
Currently, the sidebar is hidden and only opens during a semantic search.
The force system (cose layout) automatically restarts after each node drag, which causes buggy behavior where all nodes involuntarily reposition themselves.

The user wants three improvements:
1. **Sidebar open at startup** with a git log of the last 10 commits (infinite scroll)
2. **File history on node click** — the sidebar displays commits that touched this file
3. **Removal of automatic relayout** — dragging should only move the targeted node

## 2. Concerned Files

- `src/aivc/web/dashboard.py` — New `/api/log` and `/api/file-history/` endpoints
- `src/aivc/web/static/index.html` — Sidebar redesign, force removal, node click
- `src/aivc/semantic/engine.py` — Added `get_log` with `offset`
- `src/aivc/core/workspace.py` — `offset` support in `get_log()`
- `src/aivc/semantic/graph.py` — `get_file_commits` enrichment with metadata
- `src/tests/test_dashboard.py` — Tests for the new endpoints

## 3. Objectives (Definition of Done)

* **At startup**, the sidebar is open and displays the last 10 commits (title, date, short ID).
* **By scrolling** in the sidebar, older commits automatically load (infinite scroll).
* **By clicking on a graph node**, the sidebar switches to "file history" mode showing all commits that touched/consulted this file, ordered chronologically.
* **Dragging a node** no longer triggers a global relayout: only the moved node moves.
* Existing tests still pass. New tests for the added endpoints.
