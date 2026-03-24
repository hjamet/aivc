# Phase 26 — Auto Sync Push at Startup

## 1. Context & Discussion
> During Phase 25, we implemented `aivc sync push` as a manual CLI command to force-push
> missing local commits to Google Drive. The user then asked if this could be automated
> at every server startup. The Architect analysis confirmed this is safe and lightweight 
> because the `BackgroundSyncer` already runs as a daemon thread and won't block the MCP
> server's responsiveness.
>
> The `push_missing()` method is already optimized:
>   - It only compares local vs remote commit filenames (string set diff).
>   - Blobs use `skip_if_exists=True` to avoid re-uploading immutable files.
>   - The entire operation runs in a background thread, invisible to the agent.

## 2. Files Concerned
- `src/aivc/sync/background.py` (main change: add `push_missing()` call to `_run()`)
- `src/aivc/sync/drive.py` (already has `push_missing()` — no changes needed)

## 3. Goals (Definition of Done)
* When the MCP server starts (`python -m aivc.server`), the `BackgroundSyncer` thread
  automatically:
  1. Pulls commits from other machines (`pull_commits_from_others()`).
  2. Pushes any local commits missing from Drive (`push_missing()`).
* The startup push must be **silent** (no stdout noise) unless commits are actually pushed.
* The MCP server must remain responsive during this background operation.
* All existing tests must continue to pass.
