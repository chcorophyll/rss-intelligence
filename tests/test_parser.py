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
    # pending_old should be cleaned (old pending are now cleaned too)
    assert "pending_old" not in saved

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
    now = time.time()
    rss.history = {
        "h1": {
            "ts": now - 100,
            "processed": False,
            "data": {"title": "Old", "hash": "h1", "content": "Old Content"}
        },
        "h2": {
            "ts": now - 50,
            "processed": False,
            "data": {"title": "New", "hash": "h2", "content": "New Content"}
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

@pytest.mark.asyncio
async def test_slim_history_payload(mock_config, temp_db, tmp_path):
    txt_file = tmp_path / "feeds.txt"
    txt_file.write_text("http://example.com/feed")
    rss = RSSManager(mock_config, opml="nonexistent.opml", txt=str(txt_file), db=temp_db)
    
    mock_feed = MagicMock()
    mock_feed.feed.get.return_value = "Test Feed"
    mock_feed.entries = [{
        "link": "http://example.com/1",
        "title": "Article 1",
        "content": [{"value": "<h1>HTML Body</h1>"}],
        "summary": "Summary"
    }]
    
    with patch.object(rss, '_fetch_one', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_feed
        pending = await rss.fetch_all()
        
    assert len(pending) == 1
    assert pending[0]["content"] == "<h1>HTML Body</h1>"
    
    rss.save_and_clean()
    
    with open(temp_db, 'r', encoding='utf-8') as f:
        saved_db = json.load(f)
        
    for entry in saved_db.values():
        if "data" in entry:
            assert "content" not in entry["data"]

def test_load_corrupted_history_creates_backup(mock_config, temp_db):
    bad_content = "{invalid_json: true,"
    with open(temp_db, 'w', encoding='utf-8') as f:
        f.write(bad_content)
        
    rss = RSSManager(mock_config, db=temp_db)
    assert rss.history == {}
    bak_path = temp_db + ".bak"
    assert os.path.exists(bak_path)
    with open(bak_path, 'r', encoding='utf-8') as f:
        assert f.read() == bad_content


@pytest.mark.asyncio
async def test_fetch_all_html_fallback_success(mock_config, tmp_path):
    db = tmp_path / "test_fallback.json"
    rss = RSSManager(mock_config, db=str(db))
    
    # 文章处于 pending 且缺少正文
    now = time.time()
    rss.history = {
        "h1": {
            "ts": now - 10,
            "processed": False,
            "data": {"title": "No Content Article", "link": "http://example.com/no-content", "hash": "h1"}
        }
    }
    
    with patch('src.parser.RSSManager._fetch_one', new_callable=AsyncMock) as mock_fetch_one, \
         patch('src.parser.RSSManager._fetch_html_content', new_callable=AsyncMock) as mock_fallback, \
         patch('os.path.exists', return_value=False):
        mock_fetch_one.return_value = None
        mock_fallback.return_value = ("Extracted Article Content", 200)
        
        result = await rss.fetch_all()
        assert len(result) == 1
        assert result[0]['hash'] == "h1"
        assert result[0]['content'] == "Extracted Article Content"
        mock_fallback.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_all_fallback_retry_and_skip(mock_config, tmp_path):
    db = tmp_path / "test_retry.json"
    rss = RSSManager(mock_config, db=str(db))
    
    now = time.time()
    rss.history = {
        "h1_broken": {
            "ts": now - 10,
            "processed": False,
            "retry_count": 0,
            "data": {"title": "Broken Link Article", "link": "http://example.com/broken", "hash": "h1_broken"}
        },
        "h2_valid": {
            "ts": now - 20,
            "processed": False,
            "data": {"title": "Valid Article", "link": "http://example.com/valid", "hash": "h2_valid"}
        }
    }
    
    # 模拟 h1 HTML 抓取超时失败 (status 0)，h2 包含 Feed 正文
    async def mock_fallback_func(session, link):
        if link == "http://example.com/broken":
            return ("", 0)
        return ("Valid Content", 200)
        
    with patch('src.parser.RSSManager._fetch_one', new_callable=AsyncMock) as mock_fetch_one, \
         patch.object(rss, '_fetch_html_content', side_effect=mock_fallback_func), \
         patch('os.path.exists', return_value=False):
        mock_fetch_one.return_value = None
        
        result = await rss.fetch_all()
        
        # h1_broken 抓取失败跳过，顺序补入 h2_valid
        assert len(result) == 1
        assert result[0]['hash'] == "h2_valid"
        assert result[0]['content'] == "Valid Content"
        
        # 检查 h1_broken 的 retry_count 增加了 1，且保留为 processed: False
        assert rss.history["h1_broken"]["retry_count"] == 1
        assert rss.history["h1_broken"]["processed"] is False


@pytest.mark.asyncio
async def test_fetch_all_fallback_max_retry_exceeded(mock_config, tmp_path):
    db = tmp_path / "test_max_retry.json"
    rss = RSSManager(mock_config, db=str(db))
    
    now = time.time()
    rss.history = {
        "h1_max": {
            "ts": now - 10,
            "processed": False,
            "retry_count": 2, # 已经重试2次，本次为第3次
            "data": {"title": "Failing Article", "link": "http://example.com/fail", "hash": "h1_max"}
        }
    }
    
    with patch('src.parser.RSSManager._fetch_one', new_callable=AsyncMock) as mock_fetch_one, \
         patch.object(rss, '_fetch_html_content', return_value=("", 500)), \
         patch('os.path.exists', return_value=False):
        mock_fetch_one.return_value = None
        
        result = await rss.fetch_all()
        
        # 不应返回任何有效文章
        assert len(result) == 0
        # h1_max 因达到 3 次重试被标记为已处理
        assert rss.history["h1_max"]["processed"] is True
        assert "data" not in rss.history["h1_max"]



