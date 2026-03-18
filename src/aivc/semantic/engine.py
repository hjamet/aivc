"""
SemanticEngine: orchestrates Workspace + Indexer + CooccurrenceGraph + Searcher.

This is the single public facade for Phase 2.  It wraps the Phase 1 Workspace
(keeping it pure stdlib) and adds semantic indexing transparently on every
``create_commit`` call.

Option B architecture: Workspace is *owned* by SemanticEngine; the core module
is never aware of ChromaDB or SentenceTransformers.

Lazy Loading: The Indexer (ChromaDB + SentenceTransformer) and Searcher
(CrossEncoder) are only instantiated on first use, keeping ``__init__`` fast
for CLI-style invocations that only need Workspace or Graph features.
"""

from __future__ import annotations

from pathlib import Path

from aivc.core.commit import Commit
from aivc.core.workspace import FileStatus, Workspace
from aivc.semantic.graph import CooccurrenceGraph


class SemanticEngine:
    """High-level facade combining versioning + semantic search.

    Creates and owns:
    - A :class:`~aivc.core.workspace.Workspace` (Phase 1 core) — loaded eagerly
    - A :class:`~aivc.semantic.graph.CooccurrenceGraph` — loaded eagerly (SQLite, fast)
    - An :class:`~aivc.semantic.indexer.Indexer` (ChromaDB) — **lazy**
    - A :class:`~aivc.semantic.searcher.Searcher` (Cross-Encoder) — **lazy**

    All data is stored under ``storage_root``.
    """

    def __init__(self, storage_root: Path) -> None:
        """Initialise the lightweight sub-systems.

        Heavy ML dependencies (sentence-transformers, chromadb) are NOT loaded
        here.  They are loaded lazily on first ``create_commit`` or ``search``
        call.

        Args:
            storage_root: Single root directory for all AIVC data
                          (blobs, commits, ChromaDB, graph SQLite).
        """
        self._storage_root = storage_root
        self._workspace = Workspace(storage_root)
        self._graph = CooccurrenceGraph(storage_root)
        # Lazy — will be initialised on first access.
        self.__indexer = None
        self.__searcher = None

    # ------------------------------------------------------------------
    # Lazy properties for heavy ML components
    # ------------------------------------------------------------------

    @property
    def _indexer(self):
        """Lazy-loaded Indexer (ChromaDB + SentenceTransformer bi-encoder)."""
        if self.__indexer is None:
            from aivc.semantic.indexer import Indexer
            self.__indexer = Indexer(self._storage_root)
        return self.__indexer

    @property
    def _searcher(self):
        """Lazy-loaded Searcher (Cross-Encoder reranking pipeline)."""
        if self.__searcher is None:
            from aivc.semantic.searcher import Searcher
            self.__searcher = Searcher(self._indexer)
        return self.__searcher

    # ------------------------------------------------------------------
    # Commit lifecycle
    # ------------------------------------------------------------------

    def create_commit(self, title: str, note: str) -> Commit:
        """Create a versioning commit and index it semantically.

        1. Delegates to :meth:`Workspace.create_commit` (which detects diffs,
           stores blobs, and persists the commit JSON).
        2. Indexes the commit note in ChromaDB.
        3. Updates the co-occurrence graph.

        Args:
            title: Short commit title.
            note: Detailed Markdown note (the 'memory').

        Returns:
            The newly created :class:`~aivc.core.commit.Commit`.

        Raises:
            RuntimeError: if no tracked files changed (propagated from Workspace).
        """
        # Step 1: core versioning (may raise RuntimeError if no changes)
        commit = self._workspace.create_commit(title, note)

        # Step 2: semantic indexing — triggers lazy load on first call
        self._indexer.index_commit(commit)

        # Step 3: graph update (SQLite, always fast)
        self._graph.add_commit(commit)

        return commit

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 50,
        top_n: int = 5,
    ) -> list:
        """Semantic search over commit notes.

        Args:
            query: Free-text search query.
            top_k: Bi-Encoder recall breadth (capped at 50).
            top_n: Cross-Encoder reranked results to return.

        Returns:
            A list of :class:`~aivc.semantic.searcher.SearchResult` sorted by
            relevance (descending).
        """
        return self._searcher.search(query, top_k=top_k, top_n=top_n)

    # ------------------------------------------------------------------
    # Graph queries
    # ------------------------------------------------------------------

    def get_related_files(
        self, file_path: str, top_n: int = 10
    ) -> list[tuple[str, int]]:
        """Return files frequently committed alongside *file_path*.

        Args:
            file_path: Relative path of the reference file.
            top_n: Maximum number of co-occurring files to return.

        Returns:
            List of ``(file_path, cooccurrence_count)`` sorted descending.
        """
        return self._graph.get_related_files(file_path, top_n=top_n)

    def get_commit_files(self, commit_id: str) -> list[str]:
        """Return file paths that were changed in a given commit."""
        return self._graph.get_commit_files(commit_id)

    def get_file_commits(self, file_path: str) -> list[str]:
        """Return commit IDs that have ever touched *file_path*."""
        return self._graph.get_file_commits(file_path)

    def graph_vis_data(self) -> dict:
        """Return the graph in visualisation format (nodes + edges)."""
        return self._graph.to_vis_data()

    # ------------------------------------------------------------------
    # Workspace pass-throughs
    # ------------------------------------------------------------------

    def track(self, path: str) -> list[str]:
        """Track a file, directory, or glob. See :meth:`Workspace.track`."""
        return self._workspace.track(path)

    def untrack(self, file_path: str) -> None:
        """Untrack a file and GC its blobs. See :meth:`Workspace.untrack`."""
        self._workspace.untrack(file_path)

    def get_status(self) -> list[FileStatus]:
        """Return status of all tracked files. See :meth:`Workspace.get_status`."""
        return self._workspace.get_status()

    def get_log(self, limit: int = 20) -> list[Commit]:
        """Return up to *limit* commits in reverse chronological order."""
        return self._workspace.get_log(limit)

    def get_commit(self, commit_id: str) -> Commit:
        """Load a single commit by ID."""
        return self._workspace.get_commit(commit_id)

    def read_file_at_commit(self, file_path: str, commit_id: str) -> bytes:
        """Read a tracked file as it was at a specific commit."""
        return self._workspace.read_file_at_commit(file_path, commit_id)
