# Phase 10 — Search Result Snippets

## 1. Context & Discussion (Narrative)
During the architecture session on March 18, 2026, it was found that `search_memory` results lacked context: they only displayed a short title and a raw score. Choosing the right commit was nearly impossible without calling `consult_commit` on each result, which saturates the agent's context.

The user emphasized two points:
- **No file snippets**: some files are binary (PDFs, images) and this risks saturating the context.
- **Commit note snippets**: this is the right granularity. The note is always readable Markdown and contains the semantic "memory."
- **Complementary alternative**: push agents to write longer titles (4-5 sentences) in system instructions, so that even without a snippet, the title is sufficiently informative.

The idea of an `aivc diff` was explicitly rejected by the user (it would slow down the agent, with no added value since we always want to commit everything).

## 2. Concerned Files
- `src/aivc/semantic/searcher.py` — The Bi-Encoder → Cross-Encoder pipeline already returns a `SearchResult`. This is where the `snippet` field should be added.
- `src/aivc/server.py` — The MCP formatting of `search_memory` results.
- `src/aivc/cli.py` — The `aivc search` command that displays results in the terminal.
- `src/tests/test_searcher.py` — Searcher unit tests.

## 3. Objectives (Definition of Done)
* Each `search_memory` result (MCP and CLI) contains a ~200-character snippet from the matching commit note.
* The snippet is centered on the most relevant portion of the note (the one with the best similarity score with the query, if possible).
* No regression on existing tests.
* The Web Dashboard (`/api/search`) also returns the snippet (it already does on the frontend side, check for consistency).
