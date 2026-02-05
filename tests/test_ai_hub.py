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
            
            results = await hub.process_articles(articles, 1)
            
            assert len(results) == 1
            assert results[0]['ai_html'] == "<html>Summary</html>"

@pytest.mark.asyncio
async def test_process_articles_failure(mock_config, mock_genai_client):
    hub = IntelligenceHub(mock_config)
    hub.client = MagicMock()
    hub.client.models.generate_content.side_effect = Exception("API Error")
    hub.delay = 0
    
    articles = [{"title": "Fail", "content": "Content"}]
    
    results = await hub.process_articles(articles, 1)
    assert results == []
