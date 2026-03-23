# Phase 8 — GEMINI.md Injection (Agent Best Practices)

## 1. Context & Discussion (Narrative)

After Phase 7, AIVC is a functional MVP with filtered semantic search. However, a critical issue remains: **the LLM agent using AIVC doesn't know how to use it properly**.

The `install.sh` script configures the MCP server but transmits no usage instructions to the agent. Yet, AIVC's memory quality directly depends on the agent's practices:
- Committing too rarely = memory gaps
- Commit messages too short = degraded recall
- Not exploring memory at startup = redundancies, repeated errors

The idea is for `install.sh` to automatically inject a best practices block into `~/.gemini/GEMINI.md` (the global rules file for the Gemini/Antigravity agent).

### Technical decisions
- **Idempotence**: HTML markers `<!-- AIVC:START -->` / `<!-- AIVC:END -->` to frame the block. If already present, the content between the markers is replaced.
- **Non-destructive**: The rest of the GEMINI.md file is never modified.
- **Content**: Prescriptive rules for the LLM agent (commit often, explore memory, detailed messages).

## 2. Concerned Files

- `install.sh` — Added step 6: injection of the AIVC block into `~/.gemini/GEMINI.md`

## 3. Objectives (Definition of Done)

* After `bash install.sh`, the `~/.gemini/GEMINI.md` file contains an AIVC block between markers.
* If `install.sh` is rerun, the block is **updated** (not duplicated).
* The block contains the following recommendations:
  - Commit (via the `create_commit` tool, not git) at the slightest modification
  - Always start with `get_recent_commits` + **5 `search_memory` minimum** to reconstruct the work context
  - Consult file history (`consult_file`) and commit history (`consult_commit`) to understand links and history
  - Do not attempt modifications already made in the past
  - Very detailed commit messages: errors encountered, resolutions, decisions made, observations, future recommendations
* The existing content of `~/.gemini/GEMINI.md` is fully preserved.
