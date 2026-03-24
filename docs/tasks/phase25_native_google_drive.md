# Phase 25 — Native Google Drive Sync (Replacing Rclone)

## 1. Context & Discussion
> The user found rclone configuration too cumbersome (requires external tool install + manual remote setup).
> Decision: Replace rclone entirely with a native Python integration using the official Google Drive API 
> (`google-api-python-client`, `google-auth-oauthlib`).
> The `aivc sync setup` command now guides the user through:
>   1. Creating OAuth credentials on Google Cloud Console (with inline tutorial).
>   2. Browser-based OAuth authorization.
>   3. Automatic token persistence for background sync.

## 2. Files Concerned
- `src/aivc/sync/drive.py` (NEW: NativeDriveSyncManager)
- `src/aivc/sync/sync.py` (LEGACY: RcloneSyncManager, no longer imported)
- `src/aivc/sync/background.py` (MODIFIED: switched to NativeDriveSyncManager)
- `src/aivc/semantic/engine.py` (MODIFIED: switched to NativeDriveSyncManager)
- `src/aivc/server.py` (MODIFIED: switched to NativeDriveSyncManager)
- `src/aivc/cli.py` (MODIFIED: OAuth flow in cmd_sync_setup)
- `src/aivc/config.py` (MODIFIED: removed rclone, added credentials/token paths)
- `pyproject.toml` (MODIFIED: added google-api-python-client deps)

## 3. Goals (Definition of Done)
* `aivc sync setup` authenticates with Google Drive natively (no rclone).
* Background sync pushes/pulls commits and blobs via the Drive API.
* All existing tests pass without regression.
* No remaining runtime references to rclone in the codebase.
