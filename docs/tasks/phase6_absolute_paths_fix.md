# Phase 6: Absolute Paths Consolidation & CLI

## 1. Context & Discussion (Narrative)
During the Architect's MVP crash test, two issues were raised: 
- The appearance of blocking WSL `/mnt/c/...` paths.
- Early commits (Phases 1-4) stored relative paths, which breaks the `read_historical_file` functionality since the move to absolute paths (Phase 5).

After discussion, the user confirmed wanting to stick with the **absolute paths** architecture. The goal is therefore to sanitize the AIVC database so the entire history is 100% absolute, and to add a missing feature (`track`) to the CLI.

## 2. Concerned Files
- `.aivc/storage/commits/*.json` (Migration)
- `src/aivc/cli.py` (Command addition)

## 3. Objectives (Definition of Done)
* Write and execute a migration script that retroactively converts all relative paths from old commits into absolute paths (based on the current project root).
* Clean up any remaining `/mnt/c/` traces if necessary.
* Verify that `consult_file` and `read_historical_file` successfully read a file from the very first commit.
* Implement the `aivc track <path>` command so the user doesn't have to use Python code to index a new file.
