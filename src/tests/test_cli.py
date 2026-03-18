"""
Tests for the CLI module.
"""

from unittest.mock import patch, MagicMock
import pytest
import os
import sys

from aivc.cli import main, _format_bytes


@pytest.fixture
def mock_engine():
    with patch("aivc.cli._get_engine") as mock_get:
        engine = MagicMock()
        mock_get.return_value = engine
        yield engine


def test_format_bytes():
    assert _format_bytes(None) == "missing"
    assert _format_bytes(500) == "500 B"
    assert _format_bytes(1024) == "1.0 KB"
    assert _format_bytes(10 * 1024**2) == "10.0 MB"


def test_cli_status(mock_engine, capsys):
    mock_engine.get_status.return_value = []
    with patch("sys.argv", ["aivc", "status"]):
        main()
    captured = capsys.readouterr()
    assert "No files are currently tracked" in captured.out


def test_cli_log(mock_engine, capsys):
    mock_engine.get_log.return_value = []
    with patch("sys.argv", ["aivc", "log"]):
        main()
    captured = capsys.readouterr()
    assert "No commits found" in captured.out


def test_cli_search(mock_engine, capsys):
    mock_engine.search.return_value = []
    with patch("sys.argv", ["aivc", "search", "test query"]):
        main()
    captured = capsys.readouterr()
    assert "No matching commits found" in captured.out


def test_cli_no_env_var(capsys):
    # Tests that omitting AIVC_STORAGE_ROOT exits with error
    with patch.dict(os.environ, clear=True):
        if "AIVC_STORAGE_ROOT" in os.environ:
            del os.environ["AIVC_STORAGE_ROOT"]
            
        with patch("sys.argv", ["aivc", "status"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
    
    # sys.exit prints to standard error if it's passed a string,
    # but when caught by pytest.raises, the string is in the exception value.
    assert "Environment variable 'AIVC_STORAGE_ROOT' is not set" in str(exc_info.value)
