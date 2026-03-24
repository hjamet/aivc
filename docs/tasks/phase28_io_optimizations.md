# Phase 28: Synchronous I/O Optimization (Batching & Fast Diff)

## 1. Context & Discussion
During Phase 27, users reported that `create_commit` would "freeze indefinitely" on Windows after tracking large directories (e.g., `node_modules`). 

The investigation revealed two critical bottlenecks in the synchronous part of the commit process:
1. **O(N²) JSON I/O**: `BlobStore.store()` was reading and writing the entire `refcounts.json` for *every single file* added. For 10,000 files, this meant 10,000 full rewrites of a growing JSON file, which is lethal on NTFS.
2. **O(N) Redundant Hashing**: `compute_diff` was reading and hashing the content of *every* tracked file to detect changes, even if the file hadn't been touched.

## 2. Affected Files
- `src/aivc/core/blob_store.py`: Added `batch()` context manager and in-memory caching.
- `src/aivc/core/diff.py`: Integrated `mtime` and `size` checks to bypass hashing for unchanged files.
- `src/aivc/core/workspace.py`: Migrated `tracked_files` storage format to include metadata and implemented batching.

## 3. Objectives (Definition of Done)
* **Instantaneous Commits**: `create_commit` must return in less than 1 second for 1,000+ files if few changes occurred.
* **O(1) refcounts write**: The `refcounts.json` file must be written at most once per `create_commit` or `untrack` operation.
* **Metadata-based Diffing**: SHA-256 hashing must only occur for files whose `mtime` or `size` has changed on disk.
* **Seamless Migration**: Existing `workspace.json` files must be automatically upgraded to the new metadata format without user intervention.
