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

def test_load_history_existing(mock_config, temp_db):
    data = {"hash1": time.time()}
    with open(temp_db, 'w') as f:
        json.dump(data, f)
    
    rss = RSSManager(mock_config, db=temp_db)
    assert rss.history == data

def test_save_and_clean(mock_config, temp_db):
    now = time.time()
    old = now - (40 * 24 * 3600)  # 40 days ago
    data = {"new": now, "old": old}
    
    with open(temp_db, 'w') as f:
        json.dump(data, f)
        
    rss = RSSManager(mock_config, db=temp_db)
    rss.save_and_clean()
    
    with open(temp_db, 'r') as f:
        saved = json.load(f)
    
    assert "new" in saved
    assert "old" not in saved
    assert len(saved) == 1

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
async def test_fetch_all_no_urls(mock_config, tmp_path):
    opml = tmp_path / "sub.opml"
    rss = RSSManager(mock_config, opml=str(opml))
    result = await rss.fetch_all()
    assert result == []
