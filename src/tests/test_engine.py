"""Integration tests for aivc.semantic.engine.SemanticEngine.

These tests require sentence-transformers and chromadb to be installed.
They are marked with ``requires_ml`` and will be skipped if ML deps are not
available in the current environment. Run inside the venv created by install.sh.
"""

from __future__ import annotations

import pytest
from pathlib import Path

pytestmark = pytest.mark.requires_ml


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def engine(tmp_path: Path):
    from aivc.semantic.engine import SemanticEngine
    return SemanticEngine(tmp_path / "storage")


# ---------------------------------------------------------------------------
# create_commit → indexes + updates graph
# ---------------------------------------------------------------------------

def test_create_commit_returns_commit(engine, tmp_path) -> None:
    f = tmp_path / "test.py"
    _write(f, "x = 1")
    engine.track(str(f))
    commit = engine.create_commit("First commit", "Initialised x to 1.")
    assert commit.id
    assert commit.title == "First commit"


def test_create_commit_is_indexed(engine, tmp_path) -> None:
    f = tmp_path / "test.py"
    _write(f, "x = 1")
    engine.track(str(f))
    commit = engine.create_commit("Indexed commit", "This note should be vectorised.")
    assert engine._indexer.is_indexed(commit.id)


def test_create_commit_updates_graph(engine, tmp_path) -> None:
    f = tmp_path / "test.py"
    _write(f, "x = 1")
    engine.track(str(f))
    commit = engine.create_commit("Graph commit", "This should appear in the graph.")
    assert commit.id in engine._graph._data["commit_nodes"]


def test_create_commit_raises_if_no_changes(engine, tmp_path) -> None:
    f = tmp_path / "test.py"
    _write(f, "x = 1")
    engine.track(str(f))
    engine.create_commit("First", "Initial note.")
    with pytest.raises(RuntimeError, match="No changes detected"):
        engine.create_commit("Second", "Should fail — nothing changed.")


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def test_search_finds_relevant_commit(engine, tmp_path) -> None:
    f = tmp_path / "sort.py"
    _write(f, "def quicksort(arr): pass")
    engine.track(str(f))
    engine.create_commit(
        "Implement quicksort",
        "Implemented an in-place quicksort algorithm for sorting integer arrays.",
    )
    results = engine.search("sorting algorithm", top_k=10, top_n=1)
    assert len(results) == 1
    assert "sort" in results[0].title.lower() or results[0].score > 0


# ---------------------------------------------------------------------------
# get_related_files
# ---------------------------------------------------------------------------

def test_get_related_files(engine, tmp_path) -> None:
    fa = tmp_path / "a.py"
    fb = tmp_path / "b.py"
    _write(fa, "a = 1")
    _write(fb, "b = 2")
    engine.track(str(fa))
    engine.track(str(fb))
    engine.create_commit("Co-occur commit", "Both a and b changed.")
    related = dict(engine.get_related_files(str(fa)))
    assert str(fb) in related


# ---------------------------------------------------------------------------
# Workspace pass-throughs
# ---------------------------------------------------------------------------

def test_track_and_get_status(engine, tmp_path) -> None:
    f = tmp_path / "x.py"
    _write(f, "x = 42")
    engine.track(str(f))
    statuses = engine.get_status()
    assert any(s.path == str(f) for s in statuses)


def test_get_log_returns_commits(engine, tmp_path) -> None:
    f = tmp_path / "x.py"
    _write(f, "x = 1")
    engine.track(str(f))
    engine.create_commit("Log test", "First entry in log.")
    log = engine.get_log()
    assert len(log) == 1
    assert log[0].title == "Log test"
