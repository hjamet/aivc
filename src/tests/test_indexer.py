"""Unit tests for aivc.semantic.indexer.Indexer.

These tests require sentence-transformers and chromadb to be installed.
They are marked with ``requires_ml`` and will be skipped if ML deps are not
available in the current environment. Run inside the venv created by install.sh.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from aivc.core.memory import Memory, FileChange

pytestmark = pytest.mark.requires_ml


def _make_memory(
    memory_id: str = "aaaa-0001",
    title: str = "Test memory",
    note: str = "This is a detailed note about the test memory.",
    file_paths: list[str] | None = None,
) -> Memory:
    """Create a minimal Memory for testing."""
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
    return Memory(
        id=memory_id,
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
# index_memory / is_indexed
# ---------------------------------------------------------------------------

def test_index_memory_and_is_indexed(indexer) -> None:
    memory = _make_memory()
    assert not indexer.is_indexed(memory.id)
    indexer.index_memory(memory)
    assert indexer.is_indexed(memory.id)


def test_index_memory_is_idempotent(indexer) -> None:
    memory = _make_memory()
    indexer.index_memory(memory)
    # Second call must not raise.
    indexer.index_memory(memory)
    assert indexer.is_indexed(memory.id)


def test_index_memory_raises_on_empty_note(indexer) -> None:
    memory = _make_memory(note="   ")
    with pytest.raises(ValueError, match="note is empty"):
        indexer.index_memory(memory)


def test_index_memory_raises_on_empty_id(indexer) -> None:
    memory = _make_memory(memory_id="")
    with pytest.raises(ValueError, match="empty id"):
        indexer.index_memory(memory)


# ---------------------------------------------------------------------------
# remove_memory
# ---------------------------------------------------------------------------

def test_remove_memory(indexer) -> None:
    memory = _make_memory()
    indexer.index_memory(memory)
    indexer.remove_memory(memory.id)
    assert not indexer.is_indexed(memory.id)


def test_remove_memory_raises_if_not_indexed(indexer) -> None:
    with pytest.raises(KeyError, match="not in the index"):
        indexer.remove_memory("nonexistent-id")


# ---------------------------------------------------------------------------
# reindex_all
# ---------------------------------------------------------------------------

def test_reindex_all_replaces_collection(indexer) -> None:
    m1 = _make_memory(memory_id="id-1", title="First")
    m2 = _make_memory(memory_id="id-2", title="Second")
    indexer.index_memory(m1)
    indexer.index_memory(m2)

    m3 = _make_memory(memory_id="id-3", title="Third")
    indexer.reindex_all([m3])

    assert not indexer.is_indexed("id-1")
    assert not indexer.is_indexed("id-2")
    assert indexer.is_indexed("id-3")


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------

def test_query_returns_results(indexer) -> None:
    memory = _make_memory(
        note="Implemented a fast sorting algorithm using quicksort.",
    )
    indexer.index_memory(memory)
    results = indexer.query("sorting algorithm", top_k=5)
    assert len(results) >= 1
    assert results[0]["memory_id"] == memory.id


def test_query_raises_on_empty_index(indexer) -> None:
    with pytest.raises(ValueError, match="index is empty"):
        indexer.query("anything", top_k=5)


def test_query_clamps_top_k_to_collection_size(indexer) -> None:
    memory = _make_memory()
    indexer.index_memory(memory)
    # Asking for top_k=100 when only 1 doc exists must not raise.
    results = indexer.query("test", top_k=100)
    assert len(results) == 1


def test_query_handles_commas_in_file_paths(indexer) -> None:
    """Regression test: commas in filenames must not break parsing."""
    fp = "Notes, Highlights, and More - readwise.md"
    memory = _make_memory(
        memory_id="comma-id",
        title="Memory with comma file",
        file_paths=[fp]
    )
    indexer.index_memory(memory)
    results = indexer.query("comma", top_k=5)
    
    assert len(results) == 1
    assert results[0]["file_paths"] == [fp]
