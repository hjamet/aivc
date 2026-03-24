"""
RcloneSyncManager: Manages cloud synchronization using rclone.
"""

import subprocess
import json
import os
import sys
from pathlib import Path
from aivc.config import get_rclone_exe, get_aivc_config, get_machine_id

class RcloneSyncManager:
    """Manages push/pull of commits and blobs to a remote cloud storage via rclone."""

    def __init__(self, storage_root: Path):
        self.storage_root = storage_root
        self.config = get_aivc_config().get("sync", {})
        self.enabled = self.config.get("enabled", False)
        self.remote_name = self.config.get("remote_name", "aivc_remote")
        self.rclone_exe = get_rclone_exe()
        self.machine_id = get_machine_id()

    def _run_rclone(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run rclone command as a subprocess."""
        cmd = [self.rclone_exe] + args
        try:
            return subprocess.run(cmd, capture_output=True, text=True, check=check)
        except subprocess.CalledProcessError as e:
            print(f"Rclone error: {e.stderr}", file=sys.stderr)
            raise
        except FileNotFoundError:
            raise RuntimeError(f"rclone not found at {self.rclone_exe}. Please run install.sh.")

    def push_commit(self, commit_id: str):
        """Push a local commit JSON to the remote."""
        if not self.enabled:
            return
        
        local_path = self.storage_root / "commits" / f"{commit_id}.json"
        remote_path = f"{self.remote_name}:AIVC_Sync/{self.machine_id}/commits/"
        
        self._run_rclone(["copy", str(local_path), remote_path])

    def push_blob(self, blob_hash: str):
        """Push a local blob to the remote global pool."""
        if not self.enabled or not self.config.get("sync_blobs", True):
            return
            
        local_path = self.storage_root / "blobs" / blob_hash[:2] / blob_hash
        # GLOBAL POOL: AIVC_Sync/blobs/
        remote_path = f"{self.remote_name}:AIVC_Sync/blobs/"
        
        self._run_rclone(["copy", str(local_path), remote_path])

    def pull_commits_from_others(self):
        """Pull commits from other machines listed in config."""
        if not self.enabled:
            return
            
        others = self.config.get("remote_machines", [])
        for other_id in others:
            if other_id == self.machine_id:
                continue
            
            remote_path = f"{self.remote_name}:AIVC_Sync/{other_id}/commits/"
            local_path = self.storage_root / "commits"
            
            # Use --ignore-existing to avoid overwriting or redundant downloads
            self._run_rclone(["copy", remote_path, str(local_path), "--ignore-existing"])

    def fetch_blob(self, blob_hash: str, machine_id: str | None = None):
        """Fetch a missing blob from the remote global pool."""
        if not self.enabled:
            raise RuntimeError("Cloud sync is disabled. Cannot fetch distant blob.")
            
        # Try global pool first
        remote_path = f"{self.remote_name}:AIVC_Sync/blobs/{blob_hash}"
        local_dir = self.storage_root / "blobs" / blob_hash[:2]
        local_dir.mkdir(parents=True, exist_ok=True)
        
        self._run_rclone(["copy", remote_path, str(local_dir)])
        
        local_path = local_dir / blob_hash
        if not local_path.exists() and machine_id:
            # Fallback to legacy machine-specific folder if provided
            remote_path = f"{self.remote_name}:AIVC_Sync/{machine_id}/blobs/{blob_hash}"
            self._run_rclone(["copy", remote_path, str(local_dir)])
            
        if not local_path.exists():
            machine_info = f" on remote machine {machine_id}" if machine_id else ""
            raise FileNotFoundError(f"Blob {blob_hash} not found in global pool{machine_info}.")
