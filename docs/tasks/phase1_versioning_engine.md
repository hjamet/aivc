# Phase 1: Internal Versioning Engine (Core)

## 1. Context & Discussion (Narrative)

> The internal versioning engine is the **absolute foundation** of the AIVC project.
>
> Storage is content-addressable (SHA-256), similar to Git.
> Blobs are immutable, providing native deduplication.
> A file X modified 10 times will create at most 10 blobs if it changes every time.
>
> **Architect's Instruction (Garbage Collection)**:
> The user requested that the `untrack` action also delete a file's entire history
> to free up space.
> Danger warning: Since blobs are deduplicated, a file `A` and a file `B`
> can share the same blob. If we `untrack` A and blindly delete its blobs, 
> we corrupt B's history!
> It is NECESSARY to implement a **Reference Counting (GC)** system. Blobs are only 
> physically deleted from the disk when no more files/commits reference them.

## 2. Concerned Files

- `src/aivc/core/blob_store.py` — Storage (SHA-256 blobs) with Refcounter / GC
- `src/aivc/core/commit.py` — Commit data (Short title + Detailed Markdown)
- `src/aivc/core/diff.py` — Modified file detection
- `src/aivc/core/workspace.py` — Tracking space and history size management
- `src/tests/*`

## 3. Objectives (Definition of Done)

* The system can store immutable blobs (SHA-256).
* The system creates commits with a **Title** and a **Detailed Markdown Note**.
* Implementation of **Garbage Collection (Refcount)** logic: deleting a file's history during an `untrack` must not corrupt any other file.
* The workspace's `get_status` method must compute and expose:
  - The list of watched files
  - The size of each file on the current disk
  - **The history size (exclusive + shared blobs)** consumed by this file.
* **No fallback**: any error must crash cleanly with an explicit message.
