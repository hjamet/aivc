"""
Workspace: main entry point for the AIVC versioning engine.

Manages tracked files, creates commits, computes statuses, and handles
the untrack + GC lifecycle.
"""

from __future__ import annotations

import glob as _glob
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aivc.core.blob_store import BlobStore
from aivc.core.commit import Commit, FileChange, commit_from_dict, commit_to_dict
from aivc.core.diff import compute_diff


@dataclass
class FileStatus:
    """Status of a single tracked file."""

    path: str
    """Relative path of the file."""

    current_size: int | None
    """Current size on disk in bytes. None if the file no longer exists."""

    history_size: int
    """Total bytes consumed by historical blobs associated with this file."""


class Workspace:
    """Orchestrates tracking, commits, GC, and status reporting.

    Disk layout under <storage_root>:
        workspace.json       — tracked files + head commit id
        commits/
            <uuid>.json      — individual commit records
        blobs/               — managed by BlobStore
        refcounts.json       — managed by BlobStore
    """

    _WORKSPACE_FILE = "workspace.json"
    _COMMITS_DIR = "commits"

    def __init__(self, storage_root: Path) -> None:
        self._root = storage_root
        self._commits_dir = self._root / self._COMMITS_DIR
        self._workspace_path = self._root / self._WORKSPACE_FILE

        self._commits_dir.mkdir(parents=True, exist_ok=True)
        self._blob_store = BlobStore(self._root)

        if self._workspace_path.exists():
            self._state = self._load_state()
            
            # Migration: convert stored relative paths to absolute
            migrated = False
            new_tracked = {}
            for path_str, hash_val in self._state["tracked_files"].items():
                p = Path(path_str)
                if not p.is_absolute():
                    migrated = True
                    new_tracked[str(Path.cwd() / p)] = hash_val
                else:
                    new_tracked[path_str] = hash_val
            
            if migrated:
                self._state["tracked_files"] = new_tracked
                self._save_state()
        else:
            self._state: dict[str, Any] = {
                "tracked_files": {},
                "head_commit_id": None,
            }
            self._save_state()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_state(self) -> dict[str, Any]:
        raw = json.loads(self._workspace_path.read_text(encoding="utf-8"))
        _required = {"tracked_files", "head_commit_id"}
        _missing = _required - raw.keys()
        if _missing:
            raise ValueError(
                f"workspace.json is corrupted — missing keys: {_missing}."
            )
        return raw

    def _save_state(self) -> None:
        self._workspace_path.write_text(
            json.dumps(self._state, indent=2), encoding="utf-8"
        )

    def _commit_path(self, commit_id: str) -> Path:
        return self._commits_dir / f"{commit_id}.json"

    def _save_commit(self, commit: Commit) -> None:
        path = self._commit_path(commit.id)
        path.write_text(json.dumps(commit_to_dict(commit), indent=2), encoding="utf-8")

    def _load_commit(self, commit_id: str) -> Commit:
        path = self._commit_path(commit_id)
        if not path.exists():
            raise KeyError(f"Commit {commit_id!r} not found.")
        return commit_from_dict(json.loads(path.read_text(encoding="utf-8")))

    def _all_commits(self) -> list[Commit]:
        """Load every commit from disk (unordered)."""
        commits = []
        for p in self._commits_dir.glob("*.json"):
            commits.append(commit_from_dict(json.loads(p.read_text(encoding="utf-8"))))
        return commits

    def _expand_path(self, path_or_glob: str) -> list[str]:
        """Expand a path, directory, or glob pattern to a list of relative file paths.

        Raises:
            ValueError: if no files match.
        """
        p = Path(path_or_glob)

        if p.is_dir():
            files = [str(f) for f in p.rglob("*") if f.is_file()]
        else:
            files = [str(Path(f)) for f in _glob.glob(path_or_glob, recursive=True)
                     if Path(f).is_file()]

        if not files:
            raise ValueError(
                f"No files found matching {path_or_glob!r}. "
                "Did you mean a file, directory, or glob pattern?"
            )
        return files

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def track(self, path: str) -> list[str]:
        """Add a file, directory, or glob pattern to tracking.

        Args:
            path: A file path, directory path, or glob pattern.

        Returns:
            The list of file paths that were newly added to tracking.

        Raises:
            ValueError: if no matching files are found.
        """
        files = self._expand_path(path)
        newly_tracked = []
        for f in files:
            abs_f = str(Path(f).resolve())
            if abs_f not in self._state["tracked_files"]:
                self._state["tracked_files"][abs_f] = None  # never committed yet
                newly_tracked.append(abs_f)
        self._save_state()
        return newly_tracked

    def untrack(self, file_path: str) -> None:
        """Remove a file from tracking and garbage-collect its history.

        For every commit that references this file, the associated blob's
        refcount is decremented. Blobs reaching refcount=0 are deleted from disk.

        Raises:
            KeyError: if the file is not tracked.
        """
        if file_path not in self._state["tracked_files"]:
            raise KeyError(f"File {file_path!r} is not tracked.")

        # Collect blobs referenced by this file across all commits.
        all_commits = self._all_commits()
        for commit in all_commits:
            updated_changes = []
            for change in commit.changes:
                if change.path == file_path:
                    if change.blob_hash is not None:
                        self._blob_store.decrement_ref(change.blob_hash)
                    # Drop this FileChange from the commit.
                else:
                    updated_changes.append(change)
            if len(updated_changes) != len(commit.changes):
                commit.changes = updated_changes
                self._save_commit(commit)

        del self._state["tracked_files"][file_path]
        self._save_state()

    def create_commit(self, title: str, note: str) -> Commit:
        """Detect changes in tracked files and create a new commit.

        Args:
            title: Short title for the commit.
            note: Detailed Markdown note (the LLM's 'memory').

        Returns:
            The newly created Commit.

        Raises:
            RuntimeError: if no tracked files have changed.
        """
        changes = compute_diff(self._state["tracked_files"], self._blob_store)
        if not changes:
            raise RuntimeError(
                "No changes detected in tracked files. "
                "Nothing to commit."
            )

        commit = Commit.create(
            title=title,
            note=note,
            parent_id=self._state["head_commit_id"],
            changes=changes,
        )
        self._save_commit(commit)

        # Update tracked_files with the new hashes.
        for change in changes:
            if change.action == "deleted":
                # Keep the file in tracking but mark hash as None
                # (it might come back).
                self._state["tracked_files"][change.path] = None
            else:
                self._state["tracked_files"][change.path] = change.blob_hash

        self._state["head_commit_id"] = commit.id
        self._save_state()
        return commit

    def get_status(self) -> list[FileStatus]:
        """Return the status of all tracked files.

        For each file: current on-disk size and total history size (all
        blobs ever associated with this file across all commits).
        """
        # Build a map: file_path -> set of blob hashes across all commits.
        all_commits = self._all_commits()
        file_blobs: dict[str, set[str]] = {
            p: set() for p in self._state["tracked_files"]
        }
        for commit in all_commits:
            for change in commit.changes:
                if change.path in file_blobs and change.blob_hash is not None:
                    file_blobs[change.path].add(change.blob_hash)

        statuses = []
        for rel_path in self._state["tracked_files"]:
            p = Path(rel_path)
            current_size = p.stat().st_size if p.exists() and p.is_file() else None
            history_size = sum(
                self._blob_store.get_size(h) for h in file_blobs[rel_path]
            )
            statuses.append(
                FileStatus(
                    path=rel_path,
                    current_size=current_size,
                    history_size=history_size,
                )
            )
        return statuses

    def get_commit(self, commit_id: str) -> Commit:
        """Load and return a commit by ID.

        Raises:
            KeyError: if the commit does not exist.
        """
        return self._load_commit(commit_id)

    def get_log(self, limit: int = 20) -> list[Commit]:
        """Return up to `limit` commits in reverse chronological order.

        Traverses the commit chain via parent_id starting from HEAD.
        """
        commits: list[Commit] = []
        current_id = self._state["head_commit_id"]
        while current_id is not None and len(commits) < limit:
            commit = self._load_commit(current_id)
            commits.append(commit)
            current_id = commit.parent_id
        return commits

    def read_file_at_commit(self, file_path: str, commit_id: str) -> bytes:
        """Read the content of a tracked file as it was at a specific commit.

        Scans commit history to find the most recent blob for `file_path`
        at or before `commit_id`.

        Raises:
            KeyError: if the commit or file is not found in history.
        """
        # Walk the chain from the target commit backwards.
        current_id: str | None = commit_id
        while current_id is not None:
            commit = self._load_commit(current_id)
            for change in commit.changes:
                if change.path == file_path and change.blob_hash is not None:
                    return self._blob_store.retrieve(change.blob_hash)
            current_id = commit.parent_id

        raise KeyError(
            f"File {file_path!r} was not found in the history up to commit {commit_id!r}."
        )

