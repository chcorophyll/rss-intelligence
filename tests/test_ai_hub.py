import pytest
import asyncio
from unittest.mock import MagicMock, patch
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
    
    hub.client.models.generate_content.return_value = mock_response
    
    articles = [
        {
            "title": "Test Title",
            "content": "<p>Test Content</p>",
            "link": "http://example.com",
            "source": "Test Source"
        }
    ]
    
    # We need to bypass the actual generate_content call in run_in_executor
    # or ensure it returns what we want.
    with patch('asyncio.get_event_loop') as mock_loop:
        mock_l = MagicMock()
        async def mock_run(*args): return mock_response
        mock_l.run_in_executor = mock_run
        mock_loop.return_value = mock_l
        
        # Also need to mock markdown.markdown
        with patch('markdown.markdown') as mock_md:
            mock_md.return_value = "<html>Summary</html>"
            
            # Reduce delay for testing
            hub.delay = 0
            
            results, quota_exceeded = await hub.process_articles(articles)
            
            assert len(results) == 1
            assert results[0]['ai_html'] == "<html>Summary</html>"
            assert quota_exceeded is False

@pytest.mark.asyncio
async def test_process_articles_failure(mock_config, mock_genai_client):
    hub = IntelligenceHub(mock_config)
    hub.client = MagicMock()
    hub.client.models.generate_content.side_effect = Exception("API Error")
    hub.delay = 0
    
    articles = [{"title": "Fail", "content": "Content"}]
    
    results, quota_exceeded = await hub.process_articles(articles)
    assert results == []
    assert quota_exceeded is False

@pytest.mark.asyncio
async def test_process_articles_quota_exceeded(mock_config, mock_genai_client):
    hub = IntelligenceHub(mock_config)
    hub.client = MagicMock()
    hub.delay = 0
    
    articles = [{"title": "Art 1", "content": "Content 1"}, {"title": "Art 2", "content": "Content 2"}]
    
    # Mocking a 429 error on the second article
    mock_response = MagicMock()
    mock_response.text = "Summary 1"
    
    with patch('asyncio.get_event_loop') as mock_loop:
        mock_l = MagicMock()
        
        # Generator for run_in_executor to simulate success then quota failure
        async def mock_run_gen(*args):
            # The first call (index 0) will succeed, second call (index 1) will fail with 429
            if mock_run_gen.call_count == 0:
                mock_run_gen.call_count += 1
                return mock_response
            raise Exception("429 RESOURCE_EXHAUSTED")
        
        mock_run_gen.call_count = 0
        mock_l.run_in_executor = mock_run_gen
        mock_loop.return_value = mock_l
        
        with patch('markdown.markdown') as mock_md:
            mock_md.return_value = "html"
            results, quota_exceeded = await hub.process_articles(articles)
            
            assert len(results) == 1
            assert quota_exceeded is True
