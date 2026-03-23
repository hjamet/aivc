# Phase 5: Stabilization and Bug Fixing (MVP)

## 1. Context & Discussion (Narrative)
> Following exhaustive tests of the MCP server and the Web Dashboard, we identified several critical bugs preventing smooth usage, particularly in agent contexts like Cursor or Claude Desktop. One major issue was that the agent lost track of files (shown as "missing" by `get_status`) due to current working directory (CWD) conflicts. Furthermore, the web interface loaded indefinitely when Cytoscape CDNs were unreachable. This phase aims to correct these design flaws to make AIVC robust, autonomous (zero external CDN dependencies), and resilient to unpredictable launch environments.

## 2. Concerned Files
- `src/aivc/core/workspace.py`
- `src/aivc/cli.py`
- `src/aivc/web/dashboard.py`
- `src/aivc/web/static/index.html`
- `src/aivc/web/static/vendor/` (new folder)

## 3. Objectives (Definition of Done)
- Newly tracked files are handled via their absolute path (resolved during `track()` call). The status view works independently of the directory from which the agent or CLI is launched.
- The Web Dashboard includes `cytoscape.min.js` and `cytoscape-fcose.js` files locally in the `static/vendor` folder. There are no more external network calls in the JS.
- In case of network conflict (port 8765 often being used, e.g., by `semcp`), the web server automatically iterates through the next ports (+1) until an available port is found.
- HTTP `HEAD` calls on `/api/*` endpoints no longer return a `404` but a `200` status without a `body`.
- All unit tests still pass without error (and existing tests on `workspace.py` correctly handle path name mutations if necessary).
