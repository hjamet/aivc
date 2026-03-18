"""
Diff engine: detect file changes between the current workspace state and disk.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from aivc.core.blob_store import BlobStore
from aivc.core.commit import FileChange


def _hash_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file without storing it."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_diff(
    tracked_files: dict[str, str | None],
    blob_store: BlobStore,
) -> list[FileChange]:
    """Detect changes between the last-known state and the current disk state.

    Args:
        tracked_files: Mapping of relative-path → last blob hash (None if never committed).
        blob_store: The BlobStore used to store new blob content and resolve sizes.

    Returns:
        A list of FileChange objects for every tracked file that has changed.
        Files with no change are not included.

    Raises:
        IsADirectoryError: if a tracked path resolves to a directory.
        PermissionError: if a tracked file exists but cannot be read.
    """
    changes: list[FileChange] = []

    for rel_path, last_hash in tracked_files.items():
        file_path = Path(rel_path)

        if file_path.is_dir():
            raise IsADirectoryError(
                f"Tracked path {rel_path!r} is a directory, not a file. "
                "Only individual files should be in tracked_files."
            )

        if not file_path.exists():
            # File was deleted from disk since last commit.
            old_size = blob_store.get_size(last_hash) if last_hash else 0
            changes.append(
                FileChange(
                    path=rel_path,
                    action="deleted",
                    blob_hash=None,
                    bytes_added=0,
                    bytes_removed=old_size,
                )
            )
            continue

        # File exists on disk — read and hash it in memory first.
        raw_data = file_path.read_bytes()
        current_hash = hashlib.sha256(raw_data).hexdigest()

        if last_hash is None:
            # New file, never been committed.
            new_hash = blob_store.store(raw_data)
            changes.append(
                FileChange(
                    path=rel_path,
                    action="added",
                    blob_hash=new_hash,
                    bytes_added=len(raw_data),
                    bytes_removed=0,
                )
            )
        elif current_hash != last_hash:
            # File content has changed.
            old_size = blob_store.get_size(last_hash)
            new_hash = blob_store.store(raw_data)
            changes.append(
                FileChange(
                    path=rel_path,
                    action="modified",
                    blob_hash=new_hash,
                    bytes_added=len(raw_data),
                    bytes_removed=old_size,
                )
            )
        # else: identical content — no change recorded.

    return changes
