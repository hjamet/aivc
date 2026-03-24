# Phase 27: Multi-Machine Distinction & Local Path Mapping

## 1. Context & Discussion (Narratif)
During testing of the multi-machine synchronization (Phase 20), it was discovered that WSL and Windows environments frequently share the same hostname, leading to `machine_id` collisions and preventing bidirectional sync. Furthermore, consulting commits created on Windows from a Linux/WSL machine failed to provide local path hints because Windows-style backslashes were not correctly parsed by Linux-native `pathlib.Path`.

This phase introduces automatic WSL detection to guarantee machine uniqueness and a robust cross-platform path mapping heuristic.

## 2. Files Concerned
- `src/aivc/config.py`: WSL detection in `get_machine_id()`.
- `src/aivc/semantic/engine.py`: Robust path mapping in `find_local_equivalent()`.
- `scripts/demo_remote_sync.py`: Verification utility.

## 3. Objectives (Definition of Done)
* **Automatic WSL Distinction**: Systems running under WSL automatically append `-WSL` to their `machine_id` if not manually overridden in config.
* **Cross-Platform Path Hints**: Commits from Windows (using `\`) show correct local path hints (probablement `...` localement) when consulted on Linux/WSL, and vice-versa.
* **Backward Compatibility**: Existing commits without `machine_id` continue to be treated as local.
