"""
Indexer: vectorises commit notes and persists them in a local ChromaDB collection.

The text indexed per commit is: ``f"{commit.title}\\n\\n{commit.note}"`` so
that semantic search captures both the short title and the detailed Markdown note.

ChromaDB is initialised with a custom SentenceTransformer embedding function so
that the same model is used consistently at index time and search time (Bi-Encoder
stage) — ensuring correct distance comparisons with the Cross-Encoder stage.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings
from sentence_transformers import SentenceTransformer

if TYPE_CHECKING:
    from aivc.core.commit import Commit

from aivc.config import BI_ENCODER_MODEL

_COLLECTION_NAME = "aivc_commits"


class _SentenceTransformerEF(EmbeddingFunction):
    """ChromaDB-compatible embedding function backed by SentenceTransformers."""

    def __init__(self, model: SentenceTransformer) -> None:
        self._model = model

    @staticmethod
    def name() -> str:
        return "aivc_sentence_transformer"

    def get_config(self) -> dict:
        return {"name": self.name()}

    @staticmethod
    def build_from_config(config: dict) -> "_SentenceTransformerEF":
        return _SentenceTransformerEF(SentenceTransformer(BI_ENCODER_MODEL))

    def __call__(self, input: Documents) -> Embeddings:  # noqa: A002
        return self._model.encode(list(input), convert_to_numpy=True).tolist()


class Indexer:
    """Manages the ChromaDB collection for AIVC commit notes.

    Disk layout under ``storage_root``:
        chromadb/      — ChromaDB persistent database directory
    """

    _CHROMA_DIR = "chromadb"

    def __init__(self, storage_root: Path) -> None:
        """Initialise the ChromaDB client and load the bi-encoder model.

        Args:
            storage_root: Root directory shared with BlobStore / Workspace.
                          ChromaDB data will live in ``storage_root/chromadb/``.

        Raises:
            RuntimeError: if ChromaDB or the bi-encoder model cannot be loaded.
        """
        self._chroma_dir = storage_root / self._CHROMA_DIR
        self._chroma_dir.mkdir(parents=True, exist_ok=True)

        self._model = SentenceTransformer(BI_ENCODER_MODEL)
        self._ef = _SentenceTransformerEF(self._model)

        self._client = chromadb.PersistentClient(path=str(self._chroma_dir))
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _commit_text(commit: "Commit") -> str:
        """Build the text to be vectorised for a given commit."""
        return f"{commit.title}\n\n{commit.note}"

    @staticmethod
    def _commit_metadata(commit: "Commit") -> dict:
        """Build the metadata dict stored alongside the vector."""
        file_paths = [c.path for c in commit.changes if c.action != "deleted"]
        return {
            "commit_id": commit.id,
            "title": commit.title,
            "timestamp": commit.timestamp,
            "machine_id": commit.machine_id,
            # ChromaDB metadata values must be str/int/float/bool.
            # Store file paths as a comma-joined string.
            "file_paths": "\n".join(file_paths),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index_commit(self, commit: "Commit") -> None:
        """Upsert a commit into the vector index.

        Idempotent: calling with the same commit twice is safe.

        Args:
            commit: The commit to index.

        Raises:
            ValueError: if the commit has no id or note.
        """
        if not commit.id:
            raise ValueError("Cannot index a commit with an empty id.")
        if not commit.note.strip():
            raise ValueError(f"Cannot index commit {commit.id!r}: note is empty.")

        text = self._commit_text(commit)
        metadata = self._commit_metadata(commit)

        self._collection.upsert(
            ids=[commit.id],
            documents=[text],
            metadatas=[metadata],
        )

    def remove_commit(self, commit_id: str) -> None:
        """Remove a commit from the index.

        Args:
            commit_id: UUID of the commit to remove.

        Raises:
            KeyError: if the commit is not found in the index.
        """
        if not self.is_indexed(commit_id):
            raise KeyError(f"Commit {commit_id!r} is not in the index.")
        self._collection.delete(ids=[commit_id])

    def is_indexed(self, commit_id: str) -> bool:
        """Return True if the commit is already in the index."""
        result = self._collection.get(ids=[commit_id])
        return len(result["ids"]) > 0

    def reindex_all(self, commits: list["Commit"]) -> None:
        """Clear the collection and re-index all provided commits.

        Useful after a migration or if the index becomes stale.

        Args:
            commits: All commits to (re-)index.
        """
        # Wipe the collection by deleting all existing IDs.
        existing = self._collection.get()
        if existing["ids"]:
            self._collection.delete(ids=existing["ids"])

        for commit in commits:
            self.index_commit(commit)

    def query(
        self,
        query_text: str,
        top_k: int,
        filter_ids: list[str] | None = None,
    ) -> list[dict]:
        """Run a bi-encoder query and return the top-k raw results.

        Args:
            query_text: The search query.
            top_k: Number of results to retrieve.
            filter_ids: Optional list of commit IDs to restrict the search to.

        Returns:
            A list of dicts with keys: ``commit_id``, ``title``,
            ``timestamp``, ``file_paths``, ``document`` (the indexed text).

        Raises:
            ValueError: if the collection is empty.
        """
        count = self._collection.count()
        if count == 0:
            raise ValueError("The index is empty — no commits have been indexed yet.")

        if filter_ids is not None:
            if not filter_ids:
                return []
            effective_k = min(top_k, count, len(filter_ids))
        else:
            effective_k = min(top_k, count)

        kwargs = {
            "query_texts": [query_text],
            "n_results": effective_k,
            "include": ["documents", "metadatas", "distances"],
        }

        if filter_ids is not None:
            kwargs["where"] = {"commit_id": {"$in": filter_ids}}

        results = self._collection.query(**kwargs)

        hits = []
        if not results["documents"] or not results["documents"][0]:
            return hits

        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            file_paths_str = meta.get("file_paths", "")
            hits.append(
                {
                    "commit_id": meta["commit_id"],
                    "title": meta["title"],
                    "timestamp": meta["timestamp"],
                    "machine_id": meta.get("machine_id", ""),
                    "file_paths": [p for p in file_paths_str.split("\n") if p],
                    "document": doc,
                }
            )
        return hits

