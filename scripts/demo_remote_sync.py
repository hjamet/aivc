#!/usr/bin/env python3
"""
demo_remote_sync.py — Simulate a remote commit from a Windows machine.
This helps verify that AIVC correctly identifies remote commits and
provides local path hints.
"""

import json
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone

# Resolve storage root
AIVC_STORAGE_ROOT = os.environ.get("AIVC_STORAGE_ROOT")
if not AIVC_STORAGE_ROOT:
    AIVC_STORAGE_ROOT = str(Path.home() / ".aivc" / "storage")

storage_path = Path(AIVC_STORAGE_ROOT)
commits_dir = storage_path / "commits"
commits_dir.mkdir(parents=True, exist_ok=True)

# 1. Create a fake remote commit
remote_machine_id = "HEC41700-Windows"
commit_id = str(uuid.uuid4())

# We use README.md as it's guaranteed to exist locally
# Remote path is Windows-style to check the mapping heuristic
remote_path = r"C:\Users\lopilo\code\aivc\README.md"
fake_blob_hash = "deadbeef" * 8 # Fake hash

commit_data = {
    "id": commit_id,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "title": "Remote Commit from Windows",
    "note": "This commit was created on a Windows machine to test multi-machine consultation.\n\nIt modifies README.md with Windows-style paths.",
    "parent_id": None, # Initial commit for this demo
    "machine_id": remote_machine_id,
    "changes": [
        {
            "path": remote_path,
            "action": "modified",
            "blob_hash": fake_blob_hash,
            "bytes_added": 1234,
            "bytes_removed": 1100
        }
    ]
}

commit_file = commits_dir / f"{commit_id}.json"
commit_file.write_text(json.dumps(commit_data, indent=2), encoding="utf-8")

print(f"✅ Created remote commit {commit_id}")
print(f"Machine    : {remote_machine_id}")
print(f"Remote path : {remote_path}")
print(f"File saved : {commit_file}")

print("\n--- NEXT STEPS ---")
print("1. Run: aivc migrate  (to index this commit)")
print("2. In the AI chat, use search_memory or get_recent_commits to find it.")
print("3. Check for the [Remote] tag and local path hints in consult_commit.")
