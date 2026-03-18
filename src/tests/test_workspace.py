"""Unit tests for the Workspace orchestrator."""

import pytest
from pathlib import Path
from aivc.core.workspace import Workspace, FileStatus


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    return Workspace(tmp_path / "aivc_storage")


def _write(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


# ---------------------------------------------------------------------------
# track()
# ---------------------------------------------------------------------------

def test_track_single_file(tmp_path: Path, ws: Workspace) -> None:
    f = _write(tmp_path / "src" / "main.py", b"main")
    newly = ws.track(str(f))
    assert str(f) in newly


def test_track_directory_expands_recursively(tmp_path: Path, ws: Workspace) -> None:
    _write(tmp_path / "pkg" / "a.py", b"a")
    _write(tmp_path / "pkg" / "sub" / "b.py", b"b")
    newly = ws.track(str(tmp_path / "pkg"))
    assert len(newly) == 2


def test_track_glob_pattern(tmp_path: Path, ws: Workspace) -> None:
    _write(tmp_path / "x.py", b"x")
    _write(tmp_path / "y.py", b"y")
    _write(tmp_path / "z.txt", b"z")
    newly = ws.track(str(tmp_path / "*.py"))
    paths = [Path(p).name for p in newly]
    assert "x.py" in paths
    assert "y.py" in paths
    assert "z.txt" not in paths


def test_track_no_match_crashes(tmp_path: Path, ws: Workspace) -> None:
    with pytest.raises(ValueError, match="No files found"):
        ws.track(str(tmp_path / "nonexistent.py"))


def test_track_same_file_twice_not_duplicated(tmp_path: Path, ws: Workspace) -> None:
    f = _write(tmp_path / "dup.py", b"content")
    ws.track(str(f))
    newly_second = ws.track(str(f))
    assert newly_second == []
    # Only one entry in state
    status = ws.get_status()
    assert sum(1 for s in status if s.path == str(f)) == 1


# ---------------------------------------------------------------------------
# create_commit()
# ---------------------------------------------------------------------------

def test_create_commit_basic_cycle(tmp_path: Path, ws: Workspace) -> None:
    f = _write(tmp_path / "app.py", b"v1")
    ws.track(str(f))
    commit = ws.create_commit("Initial", "## v1\n\nFirst commit.")
    assert commit.title == "Initial"
    assert len(commit.changes) == 1
    assert commit.changes[0].action == "added"
    assert commit.parent_id is None


def test_create_commit_second_links_to_first(tmp_path: Path, ws: Workspace) -> None:
    f = _write(tmp_path / "app.py", b"v1")
    ws.track(str(f))
    c1 = ws.create_commit("v1", "First.")
    f.write_bytes(b"v2")
    c2 = ws.create_commit("v2", "Second.")
    assert c2.parent_id == c1.id


def test_create_commit_no_changes_crashes(tmp_path: Path, ws: Workspace) -> None:
    f = _write(tmp_path / "app.py", b"stable")
    ws.track(str(f))
    ws.create_commit("Initial", "First commit.")
    # Nothing changed — second commit must crash.
    with pytest.raises(RuntimeError, match="No changes detected"):
        ws.create_commit("Empty", "Nothing to save.")


def test_create_commit_modified_file(tmp_path: Path, ws: Workspace) -> None:
    f = _write(tmp_path / "app.py", b"v1")
    ws.track(str(f))
    ws.create_commit("v1", "First.")
    f.write_bytes(b"v2 - much longer content here")
    commit = ws.create_commit("v2", "Modified.")
    assert commit.changes[0].action == "modified"
    assert commit.changes[0].bytes_added > 0
    assert commit.changes[0].bytes_removed > 0


# ---------------------------------------------------------------------------
# untrack() + GC
# ---------------------------------------------------------------------------

def test_untrack_removes_file_from_tracking(tmp_path: Path, ws: Workspace) -> None:
    f = _write(tmp_path / "a.py", b"content")
    ws.track(str(f))
    ws.create_commit("add a", "note")
    ws.untrack(str(f))
    statuses = ws.get_status()
    assert all(s.path != str(f) for s in statuses)


def test_untrack_unknown_file_crashes(ws: Workspace) -> None:
    with pytest.raises(KeyError):
        ws.untrack("not_tracked.py")


def test_untrack_gc_exclusive_blob(tmp_path: Path, ws: Workspace) -> None:
    """Untracking a file with a unique blob must delete that blob from disk."""
    f = _write(tmp_path / "solo.py", b"unique content abc")
    ws.track(str(f))
    commit = ws.create_commit("add solo", "note")
    blob_hash = commit.changes[0].blob_hash
    blob_path = (ws._root / "blobs" / blob_hash)
    assert blob_path.exists()

    ws.untrack(str(f))
    assert not blob_path.exists(), "Blob must be deleted when refcount reaches 0"


def test_untrack_gc_shared_blob_preserved(tmp_path: Path, ws: Workspace) -> None:
    """Two files with identical content share a blob. Untracking one must NOT delete it."""
    content = b"shared identical content"
    fa = _write(tmp_path / "a.py", content)
    fb = _write(tmp_path / "b.py", content)
    ws.track(str(fa))
    ws.track(str(fb))
    commit = ws.create_commit("add both", "note")

    hashes = {c.path: c.blob_hash for c in commit.changes}
    assert hashes[str(fa)] == hashes[str(fb)], "Shared content must yield the same blob hash"
    shared_hash = hashes[str(fa)]

    ws.untrack(str(fa))
    blob_path = ws._root / "blobs" / shared_hash
    assert blob_path.exists(), "Shared blob must survive after untracking one referencing file"


# ---------------------------------------------------------------------------
# get_status()
# ---------------------------------------------------------------------------

def test_get_status_reports_current_and_history_sizes(tmp_path: Path, ws: Workspace) -> None:
    f = _write(tmp_path / "size.py", b"x" * 100)
    ws.track(str(f))
    ws.create_commit("v1", "note")
    f.write_bytes(b"y" * 200)
    ws.create_commit("v2", "note")

    statuses = ws.get_status()
    st = next(s for s in statuses if s.path == str(f))
    assert st.current_size == 200
    assert st.history_size >= 100  # at least the old blob


def test_get_status_none_for_deleted_file(tmp_path: Path, ws: Workspace) -> None:
    f = _write(tmp_path / "gone.py", b"content")
    ws.track(str(f))
    ws.create_commit("add", "note")
    f.unlink()
    statuses = ws.get_status()
    st = next(s for s in statuses if s.path == str(f))
    assert st.current_size is None


# ---------------------------------------------------------------------------
# get_log() & get_commit()
# ---------------------------------------------------------------------------

def test_get_log_returns_commits_in_reverse_order(tmp_path: Path, ws: Workspace) -> None:
    f = _write(tmp_path / "log.py", b"v1")
    ws.track(str(f))
    c1 = ws.create_commit("c1", "note")
    f.write_bytes(b"v2")
    c2 = ws.create_commit("c2", "note")
    f.write_bytes(b"v3")
    c3 = ws.create_commit("c3", "note")

    log = ws.get_log()
    assert [c.id for c in log] == [c3.id, c2.id, c1.id]


def test_get_commit_crashes_on_unknown_id(ws: Workspace) -> None:
    with pytest.raises(KeyError):
        ws.get_commit("00000000-0000-0000-0000-000000000000")


# ---------------------------------------------------------------------------
# read_file_at_commit()
# ---------------------------------------------------------------------------

def test_read_file_at_commit_returns_correct_content(tmp_path: Path, ws: Workspace) -> None:
    f = _write(tmp_path / "hist.py", b"version 1")
    ws.track(str(f))
    c1 = ws.create_commit("v1", "note")
    f.write_bytes(b"version 2")
    ws.create_commit("v2", "note")

    content_at_c1 = ws.read_file_at_commit(str(f), c1.id)
    assert content_at_c1 == b"version 1"


def test_read_file_at_commit_crashes_if_not_found(tmp_path: Path, ws: Workspace) -> None:
    f = _write(tmp_path / "other.py", b"content")
    ws.track(str(f))
    c = ws.create_commit("add", "note")
    with pytest.raises(KeyError):
        ws.read_file_at_commit("nonexistent.py", c.id)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def test_workspace_persists_and_reloads(tmp_path: Path) -> None:
    """Recreating a Workspace from the same storage_root must restore state."""
    storage = tmp_path / "storage"
    ws1 = Workspace(storage)
    f = _write(tmp_path / "persist.py", b"data")
    ws1.track(str(f))
    c = ws1.create_commit("Initial", "note")

    ws2 = Workspace(storage)
    log = ws2.get_log()
    assert len(log) == 1
    assert log[0].id == c.id
