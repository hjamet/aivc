"""
CooccurrenceGraph: bipartite graph tracking file ↔ commit relationships.

The graph is persisted as a JSON file in the storage_root.  It is updated
dynamically on every ``add_commit`` / ``remove_commit`` call.

Structure of the JSON file:
{
    "file_nodes": {
        "<file_path>": {
            "commit_ids": ["<uuid>", ...]
        },
        ...
    },
    "commit_nodes": {
        "<uuid>": {
            "title": "...",
            "timestamp": "...",
            "file_paths": ["<file_path>", ...]
        },
        ...
    }
}

Edges are implicit: an edge exists between a file and a commit iff the
commit_id appears in ``file_nodes[file_path]["commit_ids"]``.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aivc.core.commit import Commit

_GRAPH_FILE = "cooccurrence_graph.json"


class CooccurrenceGraph:
    """Bipartite graph of file nodes ↔ commit nodes.

    Persisted as ``{storage_root}/cooccurrence_graph.json``.
    """

    def __init__(self, storage_root: Path) -> None:
        """Load or create the co-occurrence graph.

        Args:
            storage_root: Directory shared with BlobStore / ChromaDB.
        """
        storage_root.mkdir(parents=True, exist_ok=True)
        self._path = storage_root / _GRAPH_FILE
        if self._path.exists():
            self._data = self._load()
        else:
            self._data: dict[str, Any] = {
                "file_nodes": {},
                "commit_nodes": {},
            }
            self._save()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        _required = {"file_nodes", "commit_nodes"}
        missing = _required - raw.keys()
        if missing:
            raise ValueError(
                f"cooccurrence_graph.json is corrupted — missing keys: {missing}."
            )
        return raw

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Public API — Mutation
    # ------------------------------------------------------------------

    def add_commit(self, commit: "Commit") -> None:
        """Register a commit and its file edges in the graph.

        Idempotent: calling with the same commit twice is safe.

        Args:
            commit: The commit to add.
        """
        file_paths = [c.path for c in commit.changes]

        # Register the commit node.
        self._data["commit_nodes"][commit.id] = {
            "title": commit.title,
            "timestamp": commit.timestamp,
            "file_paths": file_paths,
        }

        # Register / update file nodes.
        for fp in file_paths:
            if fp not in self._data["file_nodes"]:
                self._data["file_nodes"][fp] = {"commit_ids": []}
            if commit.id not in self._data["file_nodes"][fp]["commit_ids"]:
                self._data["file_nodes"][fp]["commit_ids"].append(commit.id)

        self._save()

    def remove_commit(self, commit_id: str) -> None:
        """Remove a commit and all its edges from the graph.

        Args:
            commit_id: UUID of the commit to remove.

        Raises:
            KeyError: if the commit_id is not in the graph.
        """
        if commit_id not in self._data["commit_nodes"]:
            raise KeyError(f"Commit {commit_id!r} is not in the graph.")

        file_paths = self._data["commit_nodes"][commit_id]["file_paths"]

        # Remove the commit from each file node's list.
        for fp in file_paths:
            if fp in self._data["file_nodes"]:
                try:
                    self._data["file_nodes"][fp]["commit_ids"].remove(commit_id)
                except ValueError:
                    pass  # already removed — idempotent
                # Clean up orphan file nodes.
                if not self._data["file_nodes"][fp]["commit_ids"]:
                    del self._data["file_nodes"][fp]

        del self._data["commit_nodes"][commit_id]
        self._save()

    # ------------------------------------------------------------------
    # Public API — Queries
    # ------------------------------------------------------------------

    def get_commit_files(self, commit_id: str) -> list[str]:
        """Return the file paths associated with a commit.

        Args:
            commit_id: UUID of the commit.

        Raises:
            KeyError: if the commit is not in the graph.
        """
        if commit_id not in self._data["commit_nodes"]:
            raise KeyError(f"Commit {commit_id!r} is not in the graph.")
        return list(self._data["commit_nodes"][commit_id]["file_paths"])

    def get_file_commits(self, file_path: str) -> list[str]:
        """Return the commit IDs that touched a given file.

        Args:
            file_path: Relative path of the file.

        Raises:
            KeyError: if the file is not in the graph.
        """
        if file_path not in self._data["file_nodes"]:
            raise KeyError(f"File {file_path!r} is not in the graph.")
        return list(self._data["file_nodes"][file_path]["commit_ids"])

    def get_related_files(
        self, file_path: str, top_n: int = 10
    ) -> list[tuple[str, int]]:
        """Return the files most frequently committed alongside ``file_path``.

        Co-occurrence count: for each commit that touches ``file_path``, count
        every other file that appears in the same commit.

        Args:
            file_path: The reference file.
            top_n: Maximum number of related files to return.

        Returns:
            A list of ``(other_file_path, cooccurrence_count)`` sorted
            descending by count.

        Raises:
            KeyError: if the file is not in the graph.
        """
        if file_path not in self._data["file_nodes"]:
            raise KeyError(f"File {file_path!r} is not in the graph.")

        counter: Counter[str] = Counter()
        for commit_id in self._data["file_nodes"][file_path]["commit_ids"]:
            commit_node = self._data["commit_nodes"].get(commit_id)
            if commit_node is None:
                continue
            for other_fp in commit_node["file_paths"]:
                if other_fp != file_path:
                    counter[other_fp] += 1

        return counter.most_common(top_n)

    def to_vis_data(self) -> dict:
        """Export the graph to a visualisation-friendly dict.

        Returns:
            A dict with two lists:
            - ``nodes``: each node has ``id``, ``label``, ``type`` (``"commit"``
              or ``"file"``).
            - ``edges``: each edge has ``source`` (commit_id) and
              ``target`` (file_path).
        """
        nodes = []
        edges = []

        for commit_id, meta in self._data["commit_nodes"].items():
            nodes.append(
                {
                    "id": commit_id,
                    "label": meta["title"],
                    "type": "commit",
                    "timestamp": meta["timestamp"],
                }
            )
            for fp in meta["file_paths"]:
                edges.append({"source": commit_id, "target": fp})

        for fp in self._data["file_nodes"]:
            nodes.append({"id": fp, "label": fp, "type": "file"})

        return {"nodes": nodes, "edges": edges}
