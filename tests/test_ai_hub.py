import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from src.ai_hub import IntelligenceHub

@pytest.fixture
def mock_genai_client():
    with patch('google.genai.Client') as mock:
        yield mock

@pytest.mark.asyncio
async def test_process_articles_success(mock_config, mock_genai_client):
    hub = IntelligenceHub(mock_config)
    hub.client = MagicMock()
    
    mock_response = MagicMock()
    mock_response.text = "## Summary\n* Sentence 1\n* Sentence 2\n* Sentence 3"
    
    hub.client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    
    articles = [
        {
            "title": "Test Title",
            "content": "<p>Test Content</p>",
            "link": "http://example.com",
            "source": "Test Source"
        }
    ]
    
    with patch('markdown.markdown') as mock_md:
        mock_md.return_value = "<html>Summary</html>"
        
        # Reduce delay for testing
        hub.delay = 0
        
        results, quota_exceeded = await hub.process_articles(articles)
        
        assert len(results) == 1
        assert results[0]['ai_html'] == "<html>Summary</html>"
        assert quota_exceeded is False
        hub.client.aio.models.generate_content.assert_called_once()

@pytest.mark.asyncio
async def test_process_articles_failure(mock_config, mock_genai_client):
    hub = IntelligenceHub(mock_config)
    hub.client = MagicMock()
    hub.client.aio.models.generate_content = AsyncMock(side_effect=Exception("API Error"))
    hub.delay = 0
    
    articles = [{"title": "Fail", "content": "Content"}]
    
    results, quota_exceeded = await hub.process_articles(articles)
    assert len(results) == 1
    assert results[0]['title'] == "Fail"
    assert "⚠️ AI 处理失败" in results[0]['ai_html']
    assert quota_exceeded is False

@pytest.mark.asyncio
async def test_process_articles_quota_exceeded(mock_config, mock_genai_client):
    hub = IntelligenceHub(mock_config)
    hub.client = MagicMock()
    hub.delay = 0
    
    articles = [{"title": "Art 1", "content": "Content 1"}, {"title": "Art 2", "content": "Content 2"}]
    
    mock_response = MagicMock()
    mock_response.text = "Summary 1"
    
    hub.client.aio.models.generate_content = AsyncMock(side_effect=[mock_response, Exception("429 RESOURCE_EXHAUSTED")])
    
    with patch('markdown.markdown') as mock_md:
        mock_md.return_value = "html"
        results, quota_exceeded = await hub.process_articles(articles)
        
        assert len(results) == 1
        assert quota_exceeded is True
