"""
Tests for the Dashboard API.
"""

from unittest.mock import MagicMock
from aivc.web.dashboard import DashboardHandler


def test_dashboard_api_graph():
    engine = MagicMock()
    engine.get_file_node_data.return_value = [{"id": "a.py"}]
    engine.get_file_cooccurrences.return_value = [{"source": "a.py", "target": "b.py", "weight": 2}]
    
    handler = DashboardHandler.__new__(DashboardHandler)
    handler.engine = engine
    
    res = handler._api_graph()
    assert "nodes" in res
    assert "edges" in res
    assert res["nodes"][0]["id"] == "a.py"
    assert res["edges"][0]["weight"] == 2


def test_dashboard_api_search():
    engine = MagicMock()
    mock_result = MagicMock()
    mock_result.commit_id = "c1"
    mock_result.title = "test title"
    mock_result.timestamp = "2024-01-01"
    mock_result.score = 0.95
    mock_result.snippet = "snippet text"
    mock_result.file_paths = ["a.py"]
    
    engine.search.return_value = [mock_result]
    
    handler = DashboardHandler.__new__(DashboardHandler)
    handler.engine = engine
    
    res = handler._api_search("query")
    assert len(res) == 1
    assert res[0]["commit_id"] == "c1"
    assert res[0]["title"] == "test title"
    assert res[0]["score"] == 0.95


def test_dashboard_api_search_empty():
    engine = MagicMock()
    handler = DashboardHandler.__new__(DashboardHandler)
    handler.engine = engine
    
    res = handler._api_search("")
    assert res == []
    engine.search.assert_not_called()
