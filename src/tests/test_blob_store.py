"""Unit tests for BlobStore."""

import pytest
from pathlib import Path
from aivc.core.blob_store import BlobStore


@pytest.fixture
def store(tmp_path: Path) -> BlobStore:
    return BlobStore(tmp_path / "store")


def test_store_returns_correct_sha256(store: BlobStore) -> None:
    import hashlib
    data = b"hello world"
    hash_ = store.store(data)
    assert hash_ == hashlib.sha256(data).hexdigest()


def test_store_is_idempotent_increments_refcount(store: BlobStore) -> None:
    data = b"same content"
    h1 = store.store(data)
    h2 = store.store(data)
    assert h1 == h2
    assert store.get_refcount(h1) == 2


def test_retrieve_returns_exact_bytes(store: BlobStore) -> None:
    data = b"\x00\xFF\x42some binary"
    hash_ = store.store(data)
    assert store.retrieve(hash_) == data


def test_retrieve_crashes_on_unknown_hash(store: BlobStore) -> None:
    with pytest.raises(KeyError, match="Unknown blob hash"):
        store.retrieve("deadbeef" * 8)


def test_decrement_ref_deletes_blob_at_zero(store: BlobStore) -> None:
    data = b"ephemeral"
    hash_ = store.store(data)
    assert store.exists(hash_)
    store.decrement_ref(hash_)
    assert not store.exists(hash_)


def test_decrement_ref_does_not_delete_shared_blob(store: BlobStore) -> None:
    data = b"shared content"
    hash_ = store.store(data)  # refcount = 1
    store.increment_ref(hash_)  # refcount = 2
    store.decrement_ref(hash_)  # refcount = 1 — blob must still exist
    assert store.exists(hash_)
    assert store.get_refcount(hash_) == 1


def test_decrement_ref_crashes_on_unknown_hash(store: BlobStore) -> None:
    with pytest.raises(KeyError):
        store.decrement_ref("unknown" * 8)


def test_different_content_different_blobs(store: BlobStore) -> None:
    h1 = store.store(b"content A")
    h2 = store.store(b"content B")
    assert h1 != h2
    assert store.get_refcount(h1) == 1
    assert store.get_refcount(h2) == 1


def test_get_size_returns_correct_byte_count(store: BlobStore) -> None:
    data = b"x" * 512
    hash_ = store.store(data)
    assert store.get_size(hash_) == 512


def test_get_size_crashes_on_unknown_hash(store: BlobStore) -> None:
    with pytest.raises(KeyError):
        store.get_size("ghost" * 12)


def test_increment_ref_crashes_on_unknown_hash(store: BlobStore) -> None:
    with pytest.raises(KeyError):
        store.increment_ref("nobody" * 10)
