import os
import pytest
from pathlib import Path
from aivc.config import get_storage_root
from aivc.core.commit import Commit, FileChange, commit_to_dict, commit_from_dict
from aivc.core.workspace import Workspace
from aivc.semantic.engine import SemanticEngine

def test_config_storage_root(tmp_path):
    env_var = "AIVC_STORAGE_ROOT"
    old_val = os.environ.get(env_var)
    
    try:
        # Test 1: Env var set
        os.environ[env_var] = str(tmp_path)
        assert get_storage_root() == tmp_path
        
        # Test 2: Env var missing, no fallback
        del os.environ[env_var]
        with pytest.raises(SystemExit):
            get_storage_root(allow_fallback=False)
            
        # Test 3: Env var missing, with fallback
        # (Fallbacks to ~/.aivc/storage by default)
        root = get_storage_root(allow_fallback=True)
        assert root == Path.home() / ".aivc" / "storage"
        
    finally:
        if old_val:
            os.environ[env_var] = old_val
        elif env_var in os.environ:
            del os.environ[env_var]

def test_consulted_file_change_validation():
    # Valid consulted change
    fc = FileChange(path="foo.txt", action="consulted", blob_hash=None, bytes_added=0, bytes_removed=0)
    assert fc.action == "consulted"
    
    # Invalid: consulted with blob_hash
    with pytest.raises(ValueError, match="must have blob_hash=None"):
        FileChange(path="foo.txt", action="consulted", blob_hash="abc", bytes_added=0, bytes_removed=0)

def test_commit_serialization_with_consulted():
    fc = FileChange(path="foo.txt", action="consulted", blob_hash=None, bytes_added=0, bytes_removed=0)
    c = Commit.create(title="Test", note="Note", parent_id=None, changes=[fc])
    
    data = commit_to_dict(c)
    assert data["changes"][0]["action"] == "consulted"
    
    c2 = commit_from_dict(data)
    assert c2.changes[0].action == "consulted"
    assert c2.changes[0].path == "foo.txt"
    # Actually Commit.create doesn't resolve paths, Workspace does.

def test_workspace_create_commit_only_consulted(tmp_path):
    ws = Workspace(tmp_path)
    file_a = tmp_path / "a.txt"
    file_a.write_text("hello")
    
    ws.track(str(file_a))
    # First commit to have a clean state
    ws.create_commit("Initial", "Note")
    
    # Now create a commit with ONLY consulted file
    # We need to make sure compute_diff returns empty
    commit = ws.create_commit("Consulted Only", "Note", consulted_files=[str(file_a)])
    
    assert len(commit.changes) == 1
    assert commit.changes[0].action == "consulted"
    assert commit.changes[0].path == str(file_a.resolve())

def test_workspace_create_commit_mixed(tmp_path):
    ws = Workspace(tmp_path)
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"
    file_a.write_text("hello")
    file_b.write_text("world")
    
    ws.track(str(file_a))
    ws.track(str(file_b))
    
    # Commit b once so it's not "added" anymore
    ws.create_commit("Setup", "Note")
    
    # Now modify a and consult b
    file_a.write_text("modified")
    commit = ws.create_commit("Mixed", "Note", consulted_files=[str(file_b)])
    
    actions = {c.path: c.action for c in commit.changes}
    assert actions[str(file_a.resolve())] == "modified"
    assert actions[str(file_b.resolve())] == "consulted"
    assert len(commit.changes) == 2

def test_workspace_create_commit_untracked_consulted(tmp_path):
    ws = Workspace(tmp_path)
    file_a = tmp_path / "a.txt"
    file_a.write_text("hello")
    
    with pytest.raises(KeyError, match="is not tracked"):
        ws.create_commit("Fail", "Note", consulted_files=[str(file_a)])

def test_semantic_engine_graph_updates(tmp_path):
    engine = SemanticEngine(tmp_path)
    file_a = tmp_path / "a.txt"
    file_a.write_text("hello")
    
    engine.track(str(file_a))
    # Commit with only consulted file
    commit = engine.create_commit("Consulted Only", "Note", consulted_files=[str(file_a)])
    
    # Check graph
    files = engine.get_commit_files(commit.id)
    assert str(file_a.resolve()) in files
    
    commits = engine.get_file_commits(str(file_a.resolve()))
    assert commit.id in commits
