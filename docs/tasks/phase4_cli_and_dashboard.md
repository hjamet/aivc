# Phase 4: CLI & Web Dashboard (Memory Visualization)

## 1. Context & Discussion (Narrative)
> *Following the handover style: Tell the story of why we're doing this.*

After setting up the MCP server (Phase 3), the LLM agent has full access to its long-term memory (AIVC). However, the user wisely pointed out that the human developer was "blind" to it.
It was decided to launch a dual **Phase 4**:
1. **A CLI (`aivc`)**: To interact quickly via terminal (`status`, `log`, `search`, `commit`).
2. **An elegant Web Dashboard**: To visualize memory structure as an interactive graph.

The user's specific request for the Dashboard:
- Visualization as a graph where **Nodes = Files (Documents)**.
- **Node size**: Proportional to the number of commits that touched the file.
- **Node color**: Based on the directory tree (files in the same or nearby folders share similar colors).
- **Search Function**: Performs a semantic search among commits, then **highlights** on the graph the nodes (files) linked to those commits, and displays the corresponding commit messages.
The whole interface must be extremely clean, simple, and visually stunning.

Links:
- Root file: [README.md](../../README.md)
- Semantic engine (for search): `src/aivc/semantic/engine.py`
- Graph data: `src/aivc/semantic/graph.py` (which has a `to_vis_data()` function)

## 2. Concerned Files
- `src/aivc/cli.py` (to be created)
- `src/aivc/web/` or equivalent interface (static HTML/JS/CSS or mini Flask/FastAPI server)
- `.agent/workflows/` (if specific web run scripts are needed)

## 3. Objectives (Definition of Done)
- **CLI**: An `aivc` command line is accessible locally with at least `aivc status`, `aivc log`, and `aivc search "query"`.
- **Web App (Visualization)**: A modern and "premium" web interface is accessible.
- **Graph Topology**: The graph displays with nodes representing files.
- **Aesthetics (Visual encoding)**: Node size reflects commit frequency, and color reflects hierarchy (parent folder).
- **Interactivity (Semantic Search)**: A search bar allows querying semantic memory. Results light up/filter relevant nodes in the graph and expose details (notes) of pertinent commits.
- CLI error fallbacks must remain pure crashes ("No fallbacks" global AIVC rule).
