"""Unit tests for the MCP Server Watcher logic."""

import os
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from aivc.server import AIVCWatcherHandler, start_background_watchers, _engine

def test_watcher_handler_ignores_hidden_files():
    mock_engine = MagicMock()
    watched_path = "/home/user/project"
    handler = AIVCWatcherHandler(mock_engine, watched_path)
    
    # Visible file
    event = MagicMock()
    event.is_directory = False
    event.src_path = "/home/user/project/src/main.py"
    handler.on_created(event)
    mock_engine.track.assert_called_with("/home/user/project/src/main.py")
    
    # Hidden file
    mock_engine.reset_mock()
    event.src_path = "/home/user/project/src/.secret"
    handler.on_created(event)
    mock_engine.track.assert_not_called()
    
    # File in hidden dir
    mock_engine.reset_mock()
    event.src_path = "/home/user/project/.git/config"
    handler.on_created(event)
    mock_engine.track.assert_not_called()

@patch("aivc.server._engine")
@patch("aivc.server.Observer")
@patch("os.path.isdir")
def test_start_background_watchers(mock_isdir, mock_observer_cls, mock_engine):
    mock_isdir.return_value = True
    mock_engine.get_watched_dirs.return_value = {
        "/path/to/watch": {"ignores": []}
    }
    
    mock_observer = MagicMock()
    mock_observer_cls.return_value = mock_observer
    
    start_background_watchers()
    
    # Startup sync called
    mock_engine.track.assert_called_with("/path/to/watch")
    # Observer scheduled
    mock_observer.schedule.assert_called()
    # Observer started
    mock_observer.start.assert_called()
