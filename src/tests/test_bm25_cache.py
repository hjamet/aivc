import pytest
import sqlite3
import json
from pathlib import Path
from aivc.search.bm25_cache import BM25Cache

def test_bm25_cache_init(tmp_path):
    storage_root = tmp_path / "storage"
    cache = BM25Cache(storage_root)
    
    assert (storage_root / "bm25_cache.db").exists()
    
    # Check table exists
    with sqlite3.connect(storage_root / "bm25_cache.db") as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_cache'")
        assert cursor.fetchone() is not None

def test_bm25_cache_get_corpus(tmp_path):
    storage_root = tmp_path / "storage"
    cache = BM25Cache(storage_root)
    
    # Create dummy files
    file1 = tmp_path / "file1.txt"
    file1.write_text("hello world")
    
    file2 = tmp_path / "file2.txt"
    file2.write_text("python is awesome")
    
    # Initial run (cache miss)
    corpus, paths = cache.get_corpus([str(file1), str(file2)])
    assert len(corpus) == 2
    assert corpus[0] == ["hello", "world"]
    assert corpus[1] == ["python", "is", "awesome"]
    assert len(paths) == 2
    
    # Check that entries are in DB
    with sqlite3.connect(storage_root / "bm25_cache.db") as conn:
        cursor = conn.execute("SELECT path, tokens_json FROM file_cache")
        rows = cursor.fetchall()
        assert len(rows) == 2
        
    # Modify file1
    file1.write_text("hello updated world")
    corpus, paths = cache.get_corpus([str(file1), str(file2)])
    assert corpus[0] == ["hello", "updated", "world"]
    
    with sqlite3.connect(storage_root / "bm25_cache.db") as conn:
        cursor = conn.execute("SELECT tokens_json FROM file_cache WHERE path = ?", (str(file1),))
        row = cursor.fetchone()
        assert "updated" in row[0]

def test_bm25_cache_garbage_collection(tmp_path):
    storage_root = tmp_path / "storage"
    cache = BM25Cache(storage_root)
    
    file1 = tmp_path / "file1.txt"
    file1.write_text("test")
    
    cache.get_corpus([str(file1)])
    
    with sqlite3.connect(storage_root / "bm25_cache.db") as conn:
        assert conn.execute("SELECT count(*) FROM file_cache").fetchone()[0] == 1
        
    # Run with empty tracked files list -> should cleanup
    cache.get_corpus([])
    
    with sqlite3.connect(storage_root / "bm25_cache.db") as conn:
        assert conn.execute("SELECT count(*) FROM file_cache").fetchone()[0] == 0
