# Phase 3: MCP Interface and Exposed Tools

## 1. Context & Discussion (Narrative)

> Phase 3 manages the LLM's attention bottleneck: **the Context**.
>
> The recall flow has been redesigned into a funnel:
> The agent **never** receives full messages or file content during a search, 
> to avoid drowning its tokens. `search_memory` returns only titles and lists of IDs. 
> The agent must explicitly call `consult_commit` if it wants to dig into history.
>
> Regarding space management, the `prune_history` function has been merged into `untrack`.
> The `untrack` call is now the massive space-releasing tool (destructive).

## 2. Concerned Files

- `src/aivc/server.py` — MCP server entry point
- `src/aivc/tools/commit_tool.py` — `create_commit` tool
- `src/aivc/tools/search_tool.py` — `search_memory` and `consult_commit` tools
- `src/aivc/tools/workspace_tool.py` — `get_status` and `untrack` tools
- `src/aivc/tools/history_tool.py` — Historical reading tools

## 3. Objectives (Definition of Done)

* The MCP server must expose the following tools:
  - **`create_commit(title, detailed_markdown)`**: Explicit instruction for the agent to generate a massive report of its reasoning. Modified files are auto-associated.
  - **`search_memory(query)`**: Returns the list of commits (Title, Date, ID) and potential associated files. **Strictly forbidden to include heavy text content of commits or files in this response**.
  - **`consult_commit(commit_id)`**: Returns the full Markdown note of the commit, and the diffs (or diff links) generated during this commit.
  - **`get_status()`**: Exposes the load assessment to the LLM (Current file size AND their respective history weight).
  - **`untrack(file_path)`**: Removal from tracking AND history deletion (triggers the Garbage Collector). Destructive action documented in the prompt.
  - **`consult_file(file_path)`**, **`read_historical_file(file_path, commit_id)`**, **`get_diff(file_path, a, b)`**: Standard consultations.
* A **system instruction (prompt)** must instruct the agent on usage flows (Recall funnel, memory usage).
* **No fallback**: any error must crash cleanly.
