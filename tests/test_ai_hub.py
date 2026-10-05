import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from src.ai_hub import IntelligenceHub
from src.models import Article

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
        Article(
            title="Test Title",
            content="<p>Test Content</p>",
            link="http://example.com",
            source="Test Source",
            hash="h1"
        )
    ]
    
    with patch('markdown.markdown') as mock_md:
        mock_md.return_value = "<html>Summary</html>"
        
        # Reduce delay for testing
        hub.delay = 0
        
        results, quota_exceeded = await hub.process_articles(articles)
        
        assert len(results) == 1
        assert results[0].ai_html == "<html>Summary</html>"
        assert quota_exceeded is False
        hub.client.aio.models.generate_content.assert_called_once()

@pytest.mark.asyncio
async def test_process_articles_failure(mock_config, mock_genai_client):
    hub = IntelligenceHub(mock_config)
    hub.client = MagicMock()
    hub.client.aio.models.generate_content = AsyncMock(side_effect=Exception("API Error"))
    hub.delay = 0
    
    articles = [Article(title="Fail", content="Content", link="", source="", hash="h1")]
    
    results, quota_exceeded = await hub.process_articles(articles)
    assert len(results) == 1
    assert results[0].title == "Fail"
    assert "⚠️ AI 处理失败" in results[0].ai_html
    assert quota_exceeded is False

@pytest.mark.asyncio
async def test_process_articles_quota_exceeded(mock_config, mock_genai_client):
    hub = IntelligenceHub(mock_config)
    hub.client = MagicMock()
    hub.delay = 0
    
    # 模拟并发数，以便第一个抛错时其他的可以被取消
    hub.concurrency = 2
    
    articles = [
        Article(title="Art 1", content="Content 1", link="", source="", hash="h1"),
        Article(title="Art 2", content="Content 2", link="", source="", hash="h2"),
        Article(title="Art 3", content="Content 3", link="", source="", hash="h3")
    ]
    
    mock_response = MagicMock()
    mock_response.text = "Summary 1"
    
    async def mock_generate(*args, **kwargs):
        content = kwargs.get('contents', '')
        if "Content 1" in content:
            # Art 1 触发 429
            raise Exception("429 RESOURCE_EXHAUSTED")
        else:
            # 其他文章模拟耗时任务，如果未被取消将卡主
            await asyncio.sleep(0.5)
            return mock_response
            
    hub.client.aio.models.generate_content = AsyncMock(side_effect=mock_generate)
    
    with patch('markdown.markdown') as mock_md:
        mock_md.return_value = "html"
        
        import time
        start_t = time.time()
        results, quota_exceeded = await hub.process_articles(articles)
        end_t = time.time()
        
        # 验证结果
        assert quota_exceeded is True
        
        # 验证秒级取消：如果不取消，Art 2 和 Art 3 会 sleep 0.5 秒。
        # 由于取消机制，应该非常快完成，这里断言总时间远小于 0.5 秒。
        assert (end_t - start_t) < 0.2
