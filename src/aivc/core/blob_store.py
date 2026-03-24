"""
BlobStore: content-addressable storage using SHA-256.

Blobs are immutable binary files stored by their hash.
A JSON-persisted reference counter ensures that blobs are only deleted
from disk when no file or commit references them anymore (GC).
"""

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


class BlobStore:
    """Content-addressable blob storage with reference counting.

    Layout on disk:
        <storage_root>/
            blobs/
                <sha256_hex>     # raw binary blob
            refcounts.json       # {sha256_hex: int}
    """

    _REFCOUNTS_FILE = "refcounts.json"
    _BLOBS_DIR = "blobs"

    def __init__(self, storage_root: Path) -> None:
        self._root = storage_root
        self._blobs_dir = self._root / self._BLOBS_DIR
        self._refcounts_path = self._root / self._REFCOUNTS_FILE

        self._blobs_dir.mkdir(parents=True, exist_ok=True)
        if not self._refcounts_path.exists():
            self._refcounts_path.write_text("{}", encoding="utf-8")
        
        self._batch_mode = False
        self._refcounts_cache: dict[str, int] | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_refcounts(self) -> dict[str, int]:
        if self._batch_mode and self._refcounts_cache is not None:
            return self._refcounts_cache
        return json.loads(self._refcounts_path.read_text(encoding="utf-8"))

    def _save_refcounts(self, refcounts: dict[str, int]) -> None:
        if self._batch_mode:
            self._refcounts_cache = refcounts
            return
        self._refcounts_path.write_text(
            json.dumps(refcounts, indent=2), encoding="utf-8"
        )

    @contextmanager
    def batch(self) -> Generator[None, None, None]:
        """Context manager to batch multiple refcount updates into a single disk write."""
        self._batch_mode = True
        self._refcounts_cache = self._load_refcounts()
        try:
            yield
        finally:
            self._batch_mode = False
            if self._refcounts_cache is not None:
                # Force save to disk at the end of the batch
                self._refcounts_path.write_text(
                    json.dumps(self._refcounts_cache, indent=2), encoding="utf-8"
                )
            self._refcounts_cache = None

    def _blob_path(self, hash_: str) -> Path:
        return self._blobs_dir / hash_

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(self, data: bytes) -> str:
        """Store a blob. Returns its SHA-256 hex digest.

        Idempotent: if the blob already exists only the refcount is incremented.
        """
        hash_ = hashlib.sha256(data).hexdigest()
        blob_path = self._blob_path(hash_)

        if not blob_path.exists():
            blob_path.write_bytes(data)

        refcounts = self._load_refcounts()
        refcounts[hash_] = refcounts.get(hash_, 0) + 1
        self._save_refcounts(refcounts)

        return hash_

    def retrieve(self, hash_: str) -> bytes:
        """Return the raw bytes of a stored blob.

        Raises:
            KeyError: if the hash is unknown.
        """
        blob_path = self._blob_path(hash_)
        if not blob_path.exists():
            raise KeyError(f"Unknown blob hash: {hash_!r}")
        return blob_path.read_bytes()

    def increment_ref(self, hash_: str) -> None:
        """Increment the reference count for a blob.

        Raises:
            KeyError: if the hash is unknown.
        """
        refcounts = self._load_refcounts()
        if hash_ not in refcounts:
            raise KeyError(f"Cannot increment ref for unknown blob: {hash_!r}")
        refcounts[hash_] += 1
        self._save_refcounts(refcounts)

    def decrement_ref(self, hash_: str) -> None:
        """Decrement the reference count. Deletes the blob from disk if it reaches 0.

        Raises:
            KeyError: if the hash is unknown.
            RuntimeError: if the refcount would go below 0.
        """
        refcounts = self._load_refcounts()
        if hash_ not in refcounts:
            raise KeyError(f"Cannot decrement ref for unknown blob: {hash_!r}")
        if refcounts[hash_] <= 0:
            raise RuntimeError(
                f"Refcount for blob {hash_!r} is already {refcounts[hash_]}, "
                "cannot decrement further. Storage is in an inconsistent state."
            )

        refcounts[hash_] -= 1
        if refcounts[hash_] == 0:
            del refcounts[hash_]
            self._blob_path(hash_).unlink()

        self._save_refcounts(refcounts)

    def get_size(self, hash_: str) -> int:
        """Return the size in bytes of a stored blob.

        Raises:
            KeyError: if the hash is unknown.
        """
        blob_path = self._blob_path(hash_)
        if not blob_path.exists():
            raise KeyError(f"Unknown blob hash: {hash_!r}")
        return blob_path.stat().st_size

    def get_refcount(self, hash_: str) -> int:
        """Return the current reference count of a blob.

        Raises:
            KeyError: if the hash is unknown.
        """
        refcounts = self._load_refcounts()
        if hash_ not in refcounts:
            raise KeyError(f"Unknown blob hash: {hash_!r}")
        return refcounts[hash_]

    def exists(self, hash_: str) -> bool:
        """Return True if the blob exists (regardless of refcount)."""
        return self._blob_path(hash_).exists()

