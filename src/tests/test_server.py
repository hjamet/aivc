"""
Tests for the AIVC MCP server tools.

The SemanticEngine is always mocked — no ML dependencies are loaded.
These tests validate the formatting and orchestration logic of each tool.
"""

from __future__ import annotations

import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch


# ---------------------------------------------------------------------------
# Bootstrap: inject a fake SemanticEngine before importing server.py so that
# the module-level initialisation does NOT touch the filesystem or ML stack.
# ---------------------------------------------------------------------------

_FAKE_STORAGE = "/tmp/aivc_test_storage"

# Must be set before importing the server module.
os.environ["AIVC_STORAGE_ROOT"] = _FAKE_STORAGE

# Build a mock SemanticEngine class and patch at import time.
_mock_engine = MagicMock()


def _import_server():
    """Import aivc.server with SemanticEngine fully mocked."""
    import aivc.server as srv
    # Forcibly replace the module-level engine with our mock.
    srv._engine = _mock_engine
    return srv


# We import once for all tests.
_server = _import_server()

# Grab the tool functions directly from the server module.
_create_commit = _server.create_commit
_search_memory = _server.search_memory
_consult_commit = _server.consult_commit
_get_recent = _server.get_recent_commits
_consult_file = _server.consult_file
_read_hist = _server.read_historical_file
_get_status = _server.get_status
_untrack = _server.untrack
_track = _server.track


# ---------------------------------------------------------------------------
# Helpers to build fake domain objects
# ---------------------------------------------------------------------------

def _make_commit(
    commit_id="abc-123",
    title="Do something",
    note="Detailed note.",
    timestamp="2026-03-18T12:00:00+00:00",
    parent_id=None,
    changes=None,
):
    """Build a minimal mock Commit."""
    from aivc.core.commit import Commit, FileChange
    fc = FileChange(
        path="src/foo.py",
        action="modified",
        blob_hash="aaa",
        bytes_added=100,
        bytes_removed=50,
    )
    return Commit(
        id=commit_id,
        title=title,
        note=note,
        timestamp=timestamp,
        parent_id=parent_id,
        changes=changes if changes is not None else [fc],
    )


def _make_search_result(commit_id="abc-123", title="Old commit", score=0.9):
    """Build a minimal mock SearchResult."""
    from aivc.semantic.searcher import SearchResult
    return SearchResult(
        commit_id=commit_id,
        title=title,
        timestamp="2026-03-18T10:00:00+00:00",
        score=score,
        snippet="short snippet",
        file_paths=["src/foo.py", "src/bar.py"],
    )


def _make_file_status(path="src/foo.py", current_size=1024, history_size=4096):
    """Build a minimal mock FileStatus."""
    from aivc.core.workspace import FileStatus
    return FileStatus(path=path, current_size=current_size, history_size=history_size)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreateCommit(unittest.TestCase):
    def setUp(self):
        _mock_engine.reset_mock(return_value=True, side_effect=True)

    def test_returns_commit_id_and_files(self):
        _mock_engine.create_commit.return_value = _make_commit()
        result = _create_commit("Do something", "Detailed note.")
        self.assertIn("abc-123", result)
        self.assertIn("Do something", result)
        self.assertIn("src/foo.py", result)
        self.assertIn("modified", result)

    def test_delegates_to_engine(self):
        _mock_engine.create_commit.return_value = _make_commit()
        _create_commit("T", "N")
        _mock_engine.create_commit.assert_called_once_with("T", "N", consulted_files=[])

    def test_delegates_to_engine_with_consulted(self):
        _mock_engine.create_commit.return_value = _make_commit()
        _create_commit("T", "N", consulted_files=["f1.py"])
        _mock_engine.create_commit.assert_called_once_with("T", "N", consulted_files=["f1.py"])

    def test_runtime_error_propagates(self):
        _mock_engine.create_commit.side_effect = RuntimeError("No changes detected")
        with self.assertRaises(RuntimeError):
            _create_commit("T", "N")

    def test_empty_changes_handled(self):
        _mock_engine.create_commit.return_value = _make_commit(changes=[])
        result = _create_commit("T", "N")
        self.assertIn("no tracked files changed", result)


class TestSearchMemory(unittest.TestCase):
    def setUp(self):
        _mock_engine.reset_mock(return_value=True, side_effect=True)

    def test_returns_commit_list_without_note(self):
        _mock_engine.search.return_value = [_make_search_result()]
        result = _search_memory("find something")
        self.assertIn("abc-123", result)
        self.assertIn("Old commit", result)
        self.assertIn("> short snippet", result)
        # Must NOT contain the full note content
        self.assertNotIn("Detailed note", result)

    def test_includes_aggregated_files(self):
        results = [
            _make_search_result("c1", "C1"),
            _make_search_result("c2", "C2"),
        ]
        _mock_engine.search.return_value = results
        result = _search_memory("find")
        self.assertIn("src/foo.py", result)

    def test_no_results_returns_graceful_message(self):
        _mock_engine.search.return_value = []
        result = _search_memory("nothing")
        self.assertIn("No matching commits", result)

    def test_top_n_capped_at_20(self):
        _mock_engine.search.return_value = []
        _search_memory("x", top_n=100)
        # top_n is capped to 20 before passing to engine
        _mock_engine.search.assert_called_once_with("x", top_n=20, filter_glob="")


class TestConsultCommit(unittest.TestCase):
    def setUp(self):
        _mock_engine.reset_mock(return_value=True, side_effect=True)
        # Default: no child found
        _mock_engine.find_child_commit.return_value = None

    def test_returns_full_note(self):
        _mock_engine.get_commit.return_value = _make_commit(note="# My Work\n\nDetails here.")
        result = _consult_commit("abc-123")
        self.assertIn("# My Work", result)
        self.assertIn("Details here", result)

    def test_renders_file_changes(self):
        _mock_engine.get_commit.return_value = _make_commit()
        result = _consult_commit("abc-123")
        self.assertIn("src/foo.py", result)

    def test_key_error_propagates(self):
        _mock_engine.get_commit.side_effect = KeyError("Commit not found")
        with self.assertRaises(KeyError):
            _consult_commit("bad-id")

    def test_shows_parent_context(self):
        parent = _make_commit(commit_id="p-123", title="Parent commit")
        child = _make_commit(commit_id="c-456", title="Child commit", parent_id="p-123")
        
        def side_effect(cid):
            if cid == "p-123": return parent
            if cid == "c-456": return child
            raise KeyError(cid)
            
        _mock_engine.get_commit.side_effect = side_effect
        
        result = _consult_commit("c-456")
        self.assertIn("⬆️ **Prev** : Parent commit (ID: p-123)", result)

    def test_shows_child_context(self):
        commit = _make_commit(commit_id="c-123", title="My commit")
        child = _make_commit(commit_id="next-456", title="Next commit")
        
        _mock_engine.get_commit.return_value = commit
        _mock_engine.find_child_commit.return_value = child
        
        result = _consult_commit("c-123")
        self.assertIn("⬇️ **Next** : Next commit (ID: next-456)", result)

    def test_no_parent_no_child(self):
        _mock_engine.get_commit.return_value = _make_commit(parent_id=None)
        _mock_engine.find_child_commit.return_value = None
        
        result = _consult_commit("initial-id")
        self.assertNotIn("⬆️ **Prev**", result)
        self.assertNotIn("⬇️ **Next**", result)

    def test_both_parent_and_child(self):
        parent = _make_commit(commit_id="p-1", title="P")
        current = _make_commit(commit_id="curr", title="C", parent_id="p-1")
        child = _make_commit(commit_id="next", title="N")

        def side_effect(cid):
            if cid == "p-1": return parent
            if cid == "curr": return current
            raise KeyError(cid)

        _mock_engine.get_commit.side_effect = side_effect
        _mock_engine.find_child_commit.return_value = child

        result = _consult_commit("curr")
        self.assertIn("⬆️ **Prev** : P (ID: p-1)", result)
        self.assertIn("⬇️ **Next** : N (ID: next)", result)


class TestGetRecentCommits(unittest.TestCase):
    def setUp(self):
        _mock_engine.reset_mock(return_value=True, side_effect=True)

    def test_paginates_correctly(self):
        commits = [_make_commit(commit_id=f"c{i}", title=f"Commit {i}") for i in range(15)]
        _mock_engine.get_log.return_value = commits
        _mock_engine.get_commit_files.return_value = ["src/foo.py"]

        result = _get_recent(limit=5, offset=5)
        self.assertIn("Commit 5", result)
        self.assertNotIn("Commit 0", result)

    def test_empty_range_returns_graceful_message(self):
        _mock_engine.get_log.return_value = []
        result = _get_recent()
        self.assertIn("No commits found", result)

    def test_limit_capped_at_50(self):
        _mock_engine.get_log.return_value = []
        _get_recent(limit=200)
        # Must request offset+50 at most
        _mock_engine.get_log.assert_called_once_with(limit=50)


class TestConsultFile(unittest.TestCase):
    def setUp(self):
        _mock_engine.reset_mock(return_value=True, side_effect=True)

    def test_returns_commit_history(self):
        _mock_engine.get_file_commits.return_value = ["abc-123"]
        _mock_engine.get_commit.return_value = _make_commit()
        result = _consult_file("src/foo.py")
        self.assertIn("src/foo.py", result)
        self.assertIn("Do something", result)

    def test_key_error_propagates(self):
        _mock_engine.get_file_commits.side_effect = KeyError("File not in graph")
        with self.assertRaises(KeyError):
            _consult_file("src/unknown.py")

    def test_empty_commit_list(self):
        _mock_engine.get_file_commits.return_value = []
        result = _consult_file("src/orphan.py")
        self.assertIn("No commits found", result)


class TestReadHistoricalFile(unittest.TestCase):
    def setUp(self):
        _mock_engine.reset_mock(return_value=True, side_effect=True)

    def test_returns_decoded_utf8(self):
        _mock_engine.read_file_at_commit.return_value = b"# Hello World\n"
        result = _read_hist("src/foo.py", "abc-123")
        self.assertEqual(result, "# Hello World\n")

    def test_key_error_propagates(self):
        _mock_engine.read_file_at_commit.side_effect = KeyError("Not found")
        with self.assertRaises(KeyError):
            _read_hist("src/foo.py", "bad-commit")


class TestGetStatus(unittest.TestCase):
    def setUp(self):
        _mock_engine.reset_mock(return_value=True, side_effect=True)

    def test_returns_formatted_table(self):
        _mock_engine.get_status.return_value = [_make_file_status()]
        result = _get_status()
        self.assertIn("src/foo.py", result)
        self.assertIn("1.0 KB", result)  # 1024 bytes
        self.assertIn("4.0 KB", result)  # 4096 bytes

    def test_no_tracked_files(self):
        _mock_engine.get_status.return_value = []
        result = _get_status()
        self.assertIn("No files are currently tracked", result)

    def test_missing_file_shows_missing(self):
        _mock_engine.get_status.return_value = [
            _make_file_status(current_size=None)
        ]
        result = _get_status()
        self.assertIn("missing", result)


class TestUntrack(unittest.TestCase):
    def setUp(self):
        _mock_engine.reset_mock()

    def test_delegates_and_confirms(self):
        _mock_engine.untrack.return_value = None
        result = _untrack(["src/foo.py"])
        _mock_engine.untrack.assert_called_once_with("src/foo.py")
        self.assertIn("src/foo.py", result)

    def test_multiple_paths(self):
        _mock_engine.untrack.return_value = None
        result = _untrack(["src/a.py", "src/b.py"])
        self.assertEqual(_mock_engine.untrack.call_count, 2)
        self.assertIn("2 path(s)", result)

    def test_partial_failure(self):
        _mock_engine.untrack.side_effect = [None, KeyError("Not tracked")]
        result = _untrack(["src/ok.py", "src/unknown.py"])
        self.assertIn("1 path(s)", result)  # 1 success
        self.assertIn("could not be untracked", result)


class TestTrack(unittest.TestCase):
    def setUp(self):
        _mock_engine.reset_mock()

    def test_delegates_and_lists_new_files(self):
        _mock_engine.track.return_value = {"newly_tracked": ["/abs/path/foo.py"], "hidden_skipped": 0}
        result = _track(["src/*.py"])
        _mock_engine.track.assert_called_once_with("src/*.py", [])
        self.assertIn("✅ Tracked 1 new file(s)", result)
        self.assertIn("/abs/path/foo.py", result)

    def test_multiple_paths(self):
        _mock_engine.track.return_value = {"newly_tracked": ["/abs/a.py"], "hidden_skipped": 0}
        result = _track(["src/a.py", "src/b.py"])
        self.assertEqual(_mock_engine.track.call_count, 2)
        self.assertIn("2 new file(s)", result)

    def test_already_tracked_returns_message(self):
        _mock_engine.track.return_value = {"newly_tracked": [], "hidden_skipped": 0}
        result = _track(["src/stable.py"])
        self.assertIn("No new files", result)

    def test_partial_failure(self):
        _mock_engine.track.side_effect = [ValueError("No files found"), {"newly_tracked": ["/ok.py"], "hidden_skipped": 0}]
        result = _track(["nonexistent/*", "real.py"])
        self.assertIn("1 new file(s)", result)
        self.assertIn("had issues", result)


if __name__ == "__main__":
    unittest.main()
