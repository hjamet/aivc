# Phase 14 — Commit Context (Prev/Next)

## 1. Context & Discussion (Narrative)
During an architecture planning session, the user suggested a UX improvement for the `consult_commit` MCP tool: to display, when consulting a commit, the titles of the parent (Previous) and child (Next) commits.

The goal is to provide a chronological overview ("what followed? what preceded?") without forcing the LLM agent to repeatedly call `get_recent_commits` or multiple semantic searches. 
This approach was adopted and validated by the Architect. It streamlines memory exploration and strengthens context continuity for the agent.

## 2. Concerned Files
- `src/aivc/server.py` (Formatting of the `consult_commit` tool output)
- `src/aivc/core/workspace.py` or `src/aivc/semantic/engine.py` (Adding logic to identify the direct child)
- `src/tests/test_server.py` (Addition of display tests)

## 3. Objectives (Definition of Done)
* The return message of the `consult_commit` tool visually includes the title and ID of the Previous (parent) and Next (child) commits, if they exist.
* Do not clutter the output (add only 2 concise lines).
* The absence of a parent (first commit) or child (HEAD) must be handled without error (displayed discreetly or not displayed).
* Unit tests added or updated to verify the presence of this information in the tool's text response.
