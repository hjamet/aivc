"""Unit tests for CoreIndex SQLite."""

import pytest
from pathlib import Path
from aivc.core.index import CoreIndex
from aivc.core.commit import Commit, FileChange

@pytest.fixture
def index(tmp_path: Path) -> CoreIndex:
    idx = CoreIndex(tmp_path / "index_storage")
    yield idx
    idx.close()

def test_add_commit_inserts_metadata(index: CoreIndex) -> None:
    fc = FileChange(path="a.py", action="added", blob_hash="h1", bytes_added=10, bytes_removed=0)
    commit = Commit.create(title="Init", note="Note", parent_id=None, changes=[fc])
    
    index.add_commit(commit)
    
    # Verify metadata via find_child (testing lookup)
    # Since it's the first commit, it has no parent. Let's check with a second commit.
    fc2 = FileChange(path="b.py", action="added", blob_hash="h2", bytes_added=20, bytes_removed=0)
    commit2 = Commit.create(title="Next", note="Note 2", parent_id=commit.id, changes=[fc2])
    index.add_commit(commit2)
    
    child = index.find_child(commit.id)
    assert child is not None
    assert child[0] == commit2.id
    assert child[1] == "Next"

def test_add_commit_is_idempotent(index: CoreIndex) -> None:
    fc = FileChange(path="a.py", action="added", blob_hash="h1", bytes_added=10, bytes_removed=0)
    commit = Commit.create(title="Init", note="Note", parent_id=None, changes=[fc])
    
    index.add_commit(commit)
    index.add_commit(commit)  # Should not raise
    
    hashes = index.get_blob_hashes_for_file("a.py")
    assert hashes == {"h1"}

def test_get_blob_hashes_for_file(index: CoreIndex) -> None:
    fc1 = FileChange(path="a.py", action="added", blob_hash="h1", bytes_added=10, bytes_removed=0)
    c1 = Commit.create(title="c1", note="n1", parent_id=None, changes=[fc1])
    index.add_commit(c1)
    
    fc2 = FileChange(path="a.py", action="modified", blob_hash="h2", bytes_added=15, bytes_removed=10)
    c2 = Commit.create(title="c2", note="n2", parent_id=c1.id, changes=[fc2])
    index.add_commit(c2)
    
    hashes = index.get_blob_hashes_for_file("a.py")
    assert hashes == {"h1", "h2"}

def test_remove_file_changes(index: CoreIndex) -> None:
    fc = FileChange(path="a.py", action="added", blob_hash="h1", bytes_added=10, bytes_removed=0)
    commit = Commit.create(title="Init", note="Note", parent_id=None, changes=[fc])
    index.add_commit(commit)
    
    assert index.get_blob_hashes_for_file("a.py") == {"h1"}
    index.remove_file_changes("a.py")
    assert index.get_blob_hashes_for_file("a.py") == set()

def test_get_commits_touching_file(index: CoreIndex) -> None:
    fc = FileChange(path="a.py", action="added", blob_hash="h1", bytes_added=10, bytes_removed=0)
    commit = Commit.create(title="Init", note="Note", parent_id=None, changes=[fc])
    index.add_commit(commit)
    
    commits = index.get_commits_touching_file("a.py")
    assert commits == [commit.id]

def test_migrate_from_json(tmp_path: Path, index: CoreIndex) -> None:
    from aivc.core.commit import commit_to_dict
    import json
    
    commits_dir = tmp_path / "commits"
    commits_dir.mkdir()
    
    fc = FileChange(path="a.py", action="added", blob_hash="h1", bytes_added=10, bytes_removed=0)
    commit = Commit.create(title="JSON Commit", note="Note", parent_id=None, changes=[fc])
    
    (commits_dir / f"{commit.id}.json").write_text(json.dumps(commit_to_dict(commit)))
    
    count = index.migrate_from_json(commits_dir)
    assert count == 1
    
    assert index.get_commits_touching_file("a.py") == [commit.id]
    
    # Second run should skip
    count2 = index.migrate_from_json(commits_dir)
    assert count2 == 0
