"""Unit tests for aivc.semantic.indexer.Indexer.

These tests require sentence-transformers and chromadb to be installed.
They are marked with ``requires_ml`` and will be skipped if ML deps are not
available in the current environment. Run inside the venv created by install.sh.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from aivc.core.commit import Commit, FileChange

pytestmark = pytest.mark.requires_ml


def _make_commit(
    commit_id: str = "aaaa-0001",
    title: str = "Test commit",
    note: str = "This is a detailed note about the test commit.",
    file_paths: list[str] | None = None,
) -> Commit:
    """Create a minimal Commit for testing."""
    if file_paths is None:
        file_paths = ["src/foo.py"]

    changes = [
        FileChange(
            path=fp,
            action="added",
            blob_hash="abc123",
            bytes_added=100,
            bytes_removed=0,
        )
        for fp in file_paths
    ]
    return Commit(
        id=commit_id,
        timestamp="2026-01-01T00:00:00+00:00",
        title=title,
        note=note,
        parent_id=None,
        changes=changes,
    )


@pytest.fixture
def indexer(tmp_path: Path):
    """Return a fresh Indexer backed by a tmp_path storage root."""
    from aivc.semantic.indexer import Indexer
    return Indexer(tmp_path / "storage")


# ---------------------------------------------------------------------------
# index_commit / is_indexed
# ---------------------------------------------------------------------------

def test_index_commit_and_is_indexed(indexer) -> None:
    commit = _make_commit()
    assert not indexer.is_indexed(commit.id)
    indexer.index_commit(commit)
    assert indexer.is_indexed(commit.id)


def test_index_commit_is_idempotent(indexer) -> None:
    commit = _make_commit()
    indexer.index_commit(commit)
    # Second call must not raise.
    indexer.index_commit(commit)
    assert indexer.is_indexed(commit.id)


def test_index_commit_raises_on_empty_note(indexer) -> None:
    commit = _make_commit(note="   ")
    with pytest.raises(ValueError, match="note is empty"):
        indexer.index_commit(commit)


def test_index_commit_raises_on_empty_id(indexer) -> None:
    commit = _make_commit(commit_id="")
    with pytest.raises(ValueError, match="empty id"):
        indexer.index_commit(commit)


# ---------------------------------------------------------------------------
# remove_commit
# ---------------------------------------------------------------------------

def test_remove_commit(indexer) -> None:
    commit = _make_commit()
    indexer.index_commit(commit)
    indexer.remove_commit(commit.id)
    assert not indexer.is_indexed(commit.id)


def test_remove_commit_raises_if_not_indexed(indexer) -> None:
    with pytest.raises(KeyError, match="not in the index"):
        indexer.remove_commit("nonexistent-id")


# ---------------------------------------------------------------------------
# reindex_all
# ---------------------------------------------------------------------------

def test_reindex_all_replaces_collection(indexer) -> None:
    c1 = _make_commit(commit_id="id-1", title="First")
    c2 = _make_commit(commit_id="id-2", title="Second")
    indexer.index_commit(c1)
    indexer.index_commit(c2)

    c3 = _make_commit(commit_id="id-3", title="Third")
    indexer.reindex_all([c3])

    assert not indexer.is_indexed("id-1")
    assert not indexer.is_indexed("id-2")
    assert indexer.is_indexed("id-3")


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------

def test_query_returns_results(indexer) -> None:
    commit = _make_commit(
        note="Implemented a fast sorting algorithm using quicksort.",
    )
    indexer.index_commit(commit)
    results = indexer.query("sorting algorithm", top_k=5)
    assert len(results) >= 1
    assert results[0]["commit_id"] == commit.id


def test_query_raises_on_empty_index(indexer) -> None:
    with pytest.raises(ValueError, match="index is empty"):
        indexer.query("anything", top_k=5)


def test_query_clamps_top_k_to_collection_size(indexer) -> None:
    commit = _make_commit()
    indexer.index_commit(commit)
    # Asking for top_k=100 when only 1 doc exists must not raise.
    results = indexer.query("test", top_k=100)
    assert len(results) == 1
