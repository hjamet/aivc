"""
NativeDriveSyncManager: Google Drive synchronization using the official API.

Replaces the legacy rclone-based sync with a native Python implementation
using google-api-python-client, google-auth-httplib2, and google-auth-oauthlib.
"""

import json
import sys
from pathlib import Path
from typing import Any

from aivc.config import (
    get_aivc_config,
    get_machine_id,
    get_credentials_path,
    get_token_path,
)

# Scopes: full read/write on user's own Drive files
_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
_ROOT_FOLDER_NAME = "AIVC_Sync"


class NativeDriveSyncManager:
    """Manages push/pull of commits and blobs to Google Drive natively."""

    def __init__(self, storage_root: Path):
        self.storage_root = storage_root
        self.config = get_aivc_config().get("sync", {})
        self.enabled = self.config.get("enabled", False)
        self.machine_id = get_machine_id()

        # Lazy Google Drive service
        self._service = None

        # Folder ID cache to avoid repeated API lookups
        self._folder_cache: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _get_service(self):
        """Lazy-load and authenticate with Google Drive API."""
        if self._service is not None:
            return self._service

        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError:
            raise RuntimeError(
                "Google Drive API libraries are not installed. "
                "Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

        creds = None
        token_path = get_token_path()

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), _SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                token_path.write_text(creds.to_json(), encoding="utf-8")
            else:
                raise RuntimeError(
                    "Google Drive authentication expired or missing. "
                    "Run 'aivc sync setup' to re-authenticate."
                )

        self._service = build("drive", "v3", credentials=creds)
        return self._service

    # ------------------------------------------------------------------
    # Folder management (cached)
    # ------------------------------------------------------------------

    def _find_or_create_folder(self, name: str, parent_id: str | None = None) -> str:
        """Find or create a folder in Google Drive, caching the result."""
        cache_key = f"{parent_id or 'root'}/{name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        service = self._get_service()

        # Search for existing folder
        query = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        files = results.get("files", [])

        if files:
            folder_id = files[0]["id"]
        else:
            # Create the folder
            metadata: dict[str, Any] = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_id:
                metadata["parents"] = [parent_id]
            folder = service.files().create(body=metadata, fields="id").execute()
            folder_id = folder["id"]

        self._folder_cache[cache_key] = folder_id
        return folder_id

    def _get_root_folder_id(self) -> str:
        """Get (or create) the AIVC_Sync root folder."""
        return self._find_or_create_folder(_ROOT_FOLDER_NAME)

    def _get_machine_folder_id(self) -> str:
        """Get (or create) the machine-specific folder under AIVC_Sync."""
        root_id = self._get_root_folder_id()
        return self._find_or_create_folder(self.machine_id, root_id)

    def _get_commits_folder_id(self) -> str:
        """Get (or create) the commits/ folder under the machine folder."""
        machine_id = self._get_machine_folder_id()
        return self._find_or_create_folder("commits", machine_id)

    def _get_blobs_folder_id(self) -> str:
        """Get (or create) the global blobs/ folder under AIVC_Sync."""
        root_id = self._get_root_folder_id()
        return self._find_or_create_folder("blobs", root_id)

    # ------------------------------------------------------------------
    # Upload helpers
    # ------------------------------------------------------------------

    def _upload_file(self, local_path: Path, folder_id: str, filename: str | None = None, skip_if_exists: bool = False) -> str:
        """Upload a file to a specific Drive folder. Returns file ID."""
        from googleapiclient.http import MediaFileUpload

        service = self._get_service()
        target_name = filename or local_path.name

        # Check if file already exists in folder
        query = f"name = '{target_name}' and '{folder_id}' in parents and trashed = false"
        results = service.files().list(q=query, spaces="drive", fields="files(id)").execute()
        existing = results.get("files", [])

        if existing and skip_if_exists:
            return existing[0]["id"]

        media = MediaFileUpload(str(local_path), resumable=True)

        if existing:
            # Update existing file
            file_id = existing[0]["id"]
            service.files().update(fileId=file_id, media_body=media).execute()
            return file_id
        else:
            # Create new file
            metadata: dict[str, Any] = {"name": target_name, "parents": [folder_id]}
            result = service.files().create(body=metadata, media_body=media, fields="id").execute()
            return result["id"]

    def _download_file(self, file_id: str, local_path: Path) -> None:
        """Download a file from Drive to disk."""
        from googleapiclient.http import MediaIoBaseDownload
        import io

        service = self._get_service()
        request = service.files().get_media(fileId=file_id)

        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

    # ------------------------------------------------------------------
    # Public API (same interface as old RcloneSyncManager)
    # ------------------------------------------------------------------

    def push_commit(self, commit_id: str) -> None:
        """Push a local commit JSON to Google Drive."""
        if not self.enabled:
            return

        local_path = self.storage_root / "commits" / f"{commit_id}.json"
        if not local_path.exists():
            return

        folder_id = self._get_commits_folder_id()
        self._upload_file(local_path, folder_id)

    def push_blob(self, blob_hash: str) -> None:
        """Push a local blob to the global blob pool on Drive."""
        if not self.enabled or not self.config.get("sync_blobs", True):
            return

        local_path = self.storage_root / "blobs" / blob_hash[:2] / blob_hash
        if not local_path.exists():
            return

        folder_id = self._get_blobs_folder_id()
        self._upload_file(local_path, folder_id, filename=blob_hash, skip_if_exists=True)

    def push_missing(self) -> dict:
        """Finds all local commits and pushes those missing from Google Drive.
        
        Returns:
            dict with 'commits_pushed' and 'blobs_pushed' counts.
        """
        if not self.enabled:
            return {"commits_pushed": 0, "blobs_pushed": 0}

        service = self._get_service()
        commits_folder_id = self._get_commits_folder_id()

        # 1. Get all local commits
        local_commits_dir = self.storage_root / "commits"
        if not local_commits_dir.exists():
            return {"commits_pushed": 0, "blobs_pushed": 0}
            
        local_commits = {f.name for f in local_commits_dir.iterdir() if f.suffix == ".json"}
        
        # 2. Get remote commits for this machine
        query = f"'{commits_folder_id}' in parents and trashed = false"
        # We might need pagination if > 100 commits, but fine for MVP
        results = service.files().list(q=query, spaces="drive", fields="files(name)").execute()
        remote_commits = {f["name"] for f in results.get("files", [])}
        
        missing_commits = local_commits - remote_commits
        
        commits_pushed = 0
        blobs_pushed = 0
        
        for commit_file in missing_commits:
            commit_id = commit_file.replace(".json", "")
            
            # Read local commit to find blobs and push them first
            try:
                content = json.loads((local_commits_dir / commit_file).read_text(encoding="utf-8"))
                for change in content.get("changes", []):
                    if change.get("blob_hash"):
                        self.push_blob(change["blob_hash"])
                        blobs_pushed += 1
            except Exception:
                pass
                
            self.push_commit(commit_id)
            commits_pushed += 1
            
        return {"commits_pushed": commits_pushed, "blobs_attempted": blobs_pushed}

    def pull_commits_from_others(self) -> None:
        """Pull commits from other machines listed in config."""
        if not self.enabled:
            return

        service = self._get_service()
        root_id = self._get_root_folder_id()

        # List machine folders in AIVC_Sync
        query = f"'{root_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        machine_folders = results.get("files", [])

        local_commits_dir = self.storage_root / "commits"
        local_commits_dir.mkdir(parents=True, exist_ok=True)
        existing_commits = {f.name for f in local_commits_dir.iterdir() if f.suffix == ".json"}

        for mf in machine_folders:
            if mf["name"] == self.machine_id or mf["name"] == "blobs":
                continue

            # Find commits/ subfolder
            commits_query = (
                f"name = 'commits' and '{mf['id']}' in parents "
                f"and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            )
            commits_result = service.files().list(
                q=commits_query, spaces="drive", fields="files(id)"
            ).execute()
            commits_folders = commits_result.get("files", [])
            if not commits_folders:
                continue

            commits_folder_id = commits_folders[0]["id"]

            # List commit files
            files_query = f"'{commits_folder_id}' in parents and trashed = false"
            files_result = service.files().list(
                q=files_query, spaces="drive", fields="files(id, name)"
            ).execute()

            for remote_file in files_result.get("files", []):
                if remote_file["name"] in existing_commits:
                    continue
                self._download_file(remote_file["id"], local_commits_dir / remote_file["name"])

    def fetch_blob(self, blob_hash: str, machine_id: str | None = None) -> None:
        """Fetch a missing blob from the global pool on Drive."""
        if not self.enabled:
            raise RuntimeError("Cloud sync is disabled. Cannot fetch distant blob.")

        service = self._get_service()
        blobs_folder_id = self._get_blobs_folder_id()

        query = f"name = '{blob_hash}' and '{blobs_folder_id}' in parents and trashed = false"
        results = service.files().list(q=query, spaces="drive", fields="files(id)").execute()
        files = results.get("files", [])

        local_dir = self.storage_root / "blobs" / blob_hash[:2]
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / blob_hash

        if files:
            self._download_file(files[0]["id"], local_path)
        else:
            raise FileNotFoundError(f"Blob {blob_hash} not found in global pool on Google Drive.")

    def list_remote_machines(self) -> list[str]:
        """List machine IDs found on the remote Drive."""
        if not self.enabled:
            return []

        service = self._get_service()
        root_id = self._get_root_folder_id()

        query = f"'{root_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, spaces="drive", fields="files(name)").execute()
        folders = results.get("files", [])

        return [f["name"] for f in folders if f["name"] != "blobs" and f["name"] != self.machine_id]
