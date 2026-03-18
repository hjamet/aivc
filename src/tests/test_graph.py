"""Unit tests for aivc.semantic.graph.CooccurrenceGraph (SQLite backend)."""

from __future__ import annotations

import pytest
from pathlib import Path

from aivc.core.commit import Commit, FileChange


def _make_commit(
    commit_id: str,
    title: str = "Commit",
    file_paths: list[str] | None = None,
) -> Commit:
    if file_paths is None:
        file_paths = []
    changes = [
        FileChange(
            path=fp, action="modified", blob_hash="deadbeef",
            bytes_added=10, bytes_removed=5,
        )
        for fp in file_paths
    ]
    return Commit(
        id=commit_id,
        timestamp="2026-01-01T00:00:00+00:00",
        title=title,
        note="note",
        parent_id=None,
        changes=changes,
    )


@pytest.fixture
def graph(tmp_path: Path):
    from aivc.semantic.graph import CooccurrenceGraph
    return CooccurrenceGraph(tmp_path / "storage")


# ---------------------------------------------------------------------------
# add_commit
# ---------------------------------------------------------------------------

def test_add_commit_registers_commit_node(graph) -> None:
    c = _make_commit("c1", file_paths=["a.py", "b.py"])
    graph.add_commit(c)
    # Verify via public API
    assert graph.get_commit_files("c1") == ["a.py", "b.py"] or \
           set(graph.get_commit_files("c1")) == {"a.py", "b.py"}


def test_add_commit_registers_file_nodes(graph) -> None:
    c = _make_commit("c1", file_paths=["a.py", "b.py"])
    graph.add_commit(c)
    assert "c1" in graph.get_file_commits("a.py")
    assert "c1" in graph.get_file_commits("b.py")


def test_add_commit_is_idempotent(graph) -> None:
    c = _make_commit("c1", file_paths=["a.py"])
    graph.add_commit(c)
    graph.add_commit(c)
    # File must still list commit only once.
    assert graph.get_file_commits("a.py").count("c1") == 1


def test_add_commit_persists_to_disk(tmp_path) -> None:
    from aivc.semantic.graph import CooccurrenceGraph
    storage = tmp_path / "storage"
    g1 = CooccurrenceGraph(storage)
    c = _make_commit("c1", file_paths=["a.py"])
    g1.add_commit(c)

    # Load a fresh instance from the same root — data must persist.
    g2 = CooccurrenceGraph(storage)
    assert set(g2.get_commit_files("c1")) == {"a.py"}


# ---------------------------------------------------------------------------
# remove_commit
# ---------------------------------------------------------------------------

def test_remove_commit_deletes_commit_node(graph) -> None:
    c = _make_commit("c1", file_paths=["a.py"])
    graph.add_commit(c)
    graph.remove_commit("c1")
    with pytest.raises(KeyError):
        graph.get_commit_files("c1")


def test_remove_commit_cleans_up_orphan_file_node(graph) -> None:
    c = _make_commit("c1", file_paths=["solo.py"])
    graph.add_commit(c)
    graph.remove_commit("c1")
    # "solo.py" has no remaining commits → must be removed.
    with pytest.raises(KeyError):
        graph.get_file_commits("solo.py")


def test_remove_commit_keeps_shared_file_node(graph) -> None:
    c1 = _make_commit("c1", file_paths=["shared.py", "only_c1.py"])
    c2 = _make_commit("c2", file_paths=["shared.py"])
    graph.add_commit(c1)
    graph.add_commit(c2)
    graph.remove_commit("c1")
    # "shared.py" is still referenced by c2.
    assert "c2" in graph.get_file_commits("shared.py")


def test_remove_commit_raises_if_not_in_graph(graph) -> None:
    with pytest.raises(KeyError, match="not in the graph"):
        graph.remove_commit("nonexistent")


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def test_get_commit_files(graph) -> None:
    c = _make_commit("c1", file_paths=["a.py", "b.py"])
    graph.add_commit(c)
    assert set(graph.get_commit_files("c1")) == {"a.py", "b.py"}


def test_get_file_commits(graph) -> None:
    c1 = _make_commit("c1", file_paths=["a.py"])
    c2 = _make_commit("c2", file_paths=["a.py"])
    graph.add_commit(c1)
    graph.add_commit(c2)
    assert set(graph.get_file_commits("a.py")) == {"c1", "c2"}


def test_get_related_files_basic(graph) -> None:
    c1 = _make_commit("c1", file_paths=["a.py", "b.py", "c.py"])
    c2 = _make_commit("c2", file_paths=["a.py", "b.py"])
    graph.add_commit(c1)
    graph.add_commit(c2)
    related = dict(graph.get_related_files("a.py"))
    # "b.py" appears in both commits alongside "a.py".
    assert related["b.py"] == 2
    # "c.py" appears only in c1.
    assert related.get("c.py", 0) == 1
    # "a.py" itself must not be in results.
    assert "a.py" not in related


def test_get_related_files_raises_for_unknown(graph) -> None:
    with pytest.raises(KeyError):
        graph.get_related_files("nonexistent.py")


# ---------------------------------------------------------------------------
# to_vis_data
# ---------------------------------------------------------------------------

def test_to_vis_data_structure(graph) -> None:
    c = _make_commit("c1", title="My commit", file_paths=["a.py"])
    graph.add_commit(c)
    data = graph.to_vis_data()
    assert "nodes" in data
    assert "edges" in data

    node_ids = {n["id"] for n in data["nodes"]}
    assert "c1" in node_ids
    assert "a.py" in node_ids

    edge_sources = {e["source"] for e in data["edges"]}
    assert "c1" in edge_sources
