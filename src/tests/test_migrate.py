"""Tests for the commit path migration script."""

import json
import sys
import pytest
from pathlib import Path

# The migration script lives in scripts/ (not a package) — add to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from migrate_commit_paths import (  # noqa: E402
    detect_project_root,
    migrate_commit,
    run_migration,
)


def _make_workspace(storage: Path, tracked_files: dict) -> Path:
    """Create a minimal workspace.json."""
    wp = storage / "workspace.json"
    wp.write_text(json.dumps({
        "tracked_files": tracked_files,
        "head_commit_id": None,
    }), encoding="utf-8")
    return wp


def _make_commit(commits_dir: Path, commit_id: str, paths: list[str]) -> Path:
    """Create a minimal commit JSON with given paths."""
    data = {
        "id": commit_id,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "title": "test commit",
        "note": "test note",
        "parent_id": None,
        "changes": [
            {
                "path": p,
                "action": "added",
                "blob_hash": "deadbeef" + str(i),
                "bytes_added": 100,
                "bytes_removed": 0,
            }
            for i, p in enumerate(paths)
        ],
    }
    fp = commits_dir / f"{commit_id}.json"
    fp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return fp


# ---------------------------------------------------------------------------
# detect_project_root
# ---------------------------------------------------------------------------

def test_detect_project_root(tmp_path: Path) -> None:
    storage = tmp_path / "storage"
    storage.mkdir()
    _make_workspace(storage, {
        "/home/user/project/src/a.py": None,
        "/home/user/project/src/b.py": None,
        "/home/user/project/README.md": None,
    })
    root = detect_project_root(storage / "workspace.json")
    assert root == Path("/home/user/project")


def test_detect_project_root_no_absolute_paths(tmp_path: Path) -> None:
    storage = tmp_path / "storage"
    storage.mkdir()
    _make_workspace(storage, {"relative/path.py": None})
    with pytest.raises(RuntimeError, match="No absolute paths"):
        detect_project_root(storage / "workspace.json")


# ---------------------------------------------------------------------------
# migrate_commit
# ---------------------------------------------------------------------------

def test_migrate_converts_relative_to_absolute(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    commits_dir = tmp_path / "commits"
    commits_dir.mkdir()

    cp = _make_commit(commits_dir, "aaa", ["src/main.py", "README.md"])
    fixed = migrate_commit(cp, project_root)

    assert fixed == 2
    data = json.loads(cp.read_text(encoding="utf-8"))
    for change in data["changes"]:
        assert Path(change["path"]).is_absolute()
        assert change["path"].startswith(str(project_root))


def test_migrate_idempotent(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    commits_dir = tmp_path / "commits"
    commits_dir.mkdir()

    cp = _make_commit(commits_dir, "bbb", ["src/main.py"])
    migrate_commit(cp, project_root)
    content_after_first = cp.read_text(encoding="utf-8")

    fixed = migrate_commit(cp, project_root)
    assert fixed == 0
    assert cp.read_text(encoding="utf-8") == content_after_first


def test_migrate_handles_mnt_c_paths(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    (project_root / "src").mkdir(parents=True)
    (project_root / "src" / "main.py").write_text("x")
    commits_dir = tmp_path / "commits"
    commits_dir.mkdir()

    cp = _make_commit(
        commits_dir, "ccc",
        ["/mnt/c/Users/dev/AppData/project/src/main.py"],
    )
    fixed = migrate_commit(cp, project_root)
    assert fixed == 1
    data = json.loads(cp.read_text(encoding="utf-8"))
    assert data["changes"][0]["path"] == str(project_root / "src" / "main.py")


def test_migrate_dry_run_no_write(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    commits_dir = tmp_path / "commits"
    commits_dir.mkdir()

    cp = _make_commit(commits_dir, "ddd", ["src/app.py"])
    original = cp.read_text(encoding="utf-8")

    fixed = migrate_commit(cp, project_root, dry_run=True)
    assert fixed == 1
    assert cp.read_text(encoding="utf-8") == original  # file unchanged


# ---------------------------------------------------------------------------
# run_migration (integration)
# ---------------------------------------------------------------------------

def test_run_migration_full(tmp_path: Path) -> None:
    storage = tmp_path / "storage"
    storage.mkdir()
    commits_dir = storage / "commits"
    commits_dir.mkdir()

    project_root = tmp_path / "project"
    project_root.mkdir()

    _make_workspace(storage, {
        str(project_root / "src" / "a.py"): None,
        str(project_root / "src" / "b.py"): None,
    })
    _make_commit(commits_dir, "e1", ["src/a.py", "src/b.py"])
    _make_commit(commits_dir, "e2", [str(project_root / "src" / "a.py")])  # already absolute

    results = run_migration(storage)
    assert results["e1.json"] == 2
    assert results["e2.json"] == 0
