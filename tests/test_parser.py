import pytest
import os
import json
import time
from unittest.mock import AsyncMock, patch, MagicMock
from src.parser import RSSManager

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_history.json"
    return str(db_path)

def test_load_history_empty(mock_config, temp_db):
    rss = RSSManager(mock_config, db=temp_db)
    assert rss.history == {}

def test_load_history_migration(mock_config, temp_db):
    data = {
        "legacy_h1": 1000.5,
        "modern_h2": {"ts": 2000.5, "processed": False, "data": {"title": "X"}}
    }
    with open(temp_db, 'w') as f:
        json.dump(data, f)
        
    rss = RSSManager(mock_config, db=temp_db)
    # legacy_h1 should be upgraded
    assert isinstance(rss.history["legacy_h1"], dict)
    assert rss.history["legacy_h1"]["ts"] == 1000.5
    assert rss.history["legacy_h1"]["processed"] is True
    # modern_h2 should be untouched
    assert rss.history["modern_h2"]["processed"] is False

def test_load_history_existing(mock_config, temp_db):
    data = {"hash1": {"ts": time.time(), "processed": True}}
    with open(temp_db, 'w') as f:
        json.dump(data, f)
    
    rss = RSSManager(mock_config, db=temp_db)
    assert rss.history == data

def test_save_and_clean(mock_config, temp_db):
    now = time.time()
    old = now - (10 * 24 * 3600)  # 10 days ago (Retention is 7)
    
    data = {
        "processed_new": {"ts": now, "processed": True},
        "processed_old": {"ts": old, "processed": True},
        "pending_old": {"ts": old, "processed": False, "data": {"title": "X"}}
    }
    
    with open(temp_db, 'w') as f:
        json.dump(data, f)
        
    rss = RSSManager(mock_config, db=temp_db)
    rss.retention_days = 7
    rss.save_and_clean()
    
    with open(temp_db, 'r') as f:
        saved = json.load(f)
    
    # processed_new should stay
    assert "processed_new" in saved
    # processed_old should be cleaned (processed AND old)
    assert "processed_old" not in saved
    # pending_old should stay (not processed)
    assert "pending_old" in saved

@pytest.mark.asyncio
async def test_fetch_one_success(mock_config):
    rss = RSSManager(mock_config)
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text.return_value = "<rss><channel><title>Test</title></channel></rss>"
    
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    with patch('feedparser.parse') as mock_parse:
        mock_parse.return_value = MagicMock()
        result = await rss._fetch_one(mock_session, "http://example.com")
        assert result is not None
        mock_parse.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_all_with_pending(mock_config, tmp_path):
    db = tmp_path / "test.json"
    rss = RSSManager(mock_config, db=str(db))
    
    # 1. Setup history with two pending items
    rss.history = {
        "h1": {
            "ts": 1000,
            "processed": False,
            "data": {"title": "Old", "hash": "h1"}
        },
        "h2": {
            "ts": 2000,
            "processed": False,
            "data": {"title": "New", "hash": "h2"}
        }
    }
    
    # 2. Mock fetch_all to find nothing new
    with patch('src.parser.RSSManager._fetch_one', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = None # Nothing new
        
        # We need to mock OPML loading too
        with patch('os.path.exists', return_value=False):
            result = await rss.fetch_all()
            
            # Should return BOTH pending items, sorted Newest first
            assert len(result) == 2
            assert result[0]['title'] == "New"
            assert result[1]['title'] == "Old"

def test_mark_as_processed(mock_config):
    rss = RSSManager(mock_config)
    rss.history = {
        "h1": {
            "ts": 1000,
            "processed": False,
            "data": {"title": "Old", "hash": "h1"}
        }
    }
    articles = [{"hash": "h1"}]
    rss.mark_as_processed(articles)
    
    assert rss.history["h1"]["processed"] is True
    assert "data" not in rss.history["h1"]
    assert rss.history["h1"]["ts"] > 1000
