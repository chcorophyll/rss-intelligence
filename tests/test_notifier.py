import email
from email.header import decode_header
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.notifier import EmailNotifier, TelegramNotifier, send_all_reports

@pytest.fixture
def sample_articles():
    return [
        {"title": "Art 1", "link": "http://ex.com/1", "source": "Src 1", "ai_html": "<p>Sum 1</p>"}
    ]

def test_email_notifier_success(mock_config, sample_articles):
    notifier = EmailNotifier(mock_config)
    
    with patch('smtplib.SMTP_SSL') as mock_smtp_ssl:
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_smtp_ssl.return_value = mock_instance
        
        notifier.send_report(sample_articles)
        
        mock_instance.login.assert_called_once_with(mock_config.SENDER, mock_config.SMTP_PASS)
        mock_instance.sendmail.assert_called_once()

@pytest.mark.asyncio
async def test_telegram_notifier_success(mock_config, sample_articles):
    notifier = TelegramNotifier(mock_config)
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        await notifier.send_report(sample_articles)
        
        assert mock_post.called
        args, kwargs = mock_post.call_args
        assert "telegram.org" in args[0]
        assert kwargs['json']['chat_id'] == "test_chat_id"
        assert "Art 1" in kwargs['json']['text']

@pytest.mark.asyncio
async def test_telegram_notifier_with_warning(mock_config, sample_articles):
    notifier = TelegramNotifier(mock_config)
    warning = "AI quota exceeded"
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        await notifier.send_report(sample_articles, warning=warning)
        
        assert mock_post.call_count == 2
        header_call_args = mock_post.call_args_list[0]
        assert warning in header_call_args.kwargs['json']['text']

@pytest.mark.asyncio
async def test_telegram_notifier_http_error(mock_config, sample_articles):
    notifier = TelegramNotifier(mock_config)
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad Request")
        mock_post.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(RuntimeError) as exc_info:
            await notifier.send_report(sample_articles)
        assert "Telegram API 响应失败 (400)" in str(exc_info.value)

@pytest.mark.asyncio
async def test_send_all_reports(mock_config, sample_articles):
    warning = "test warning"
    
    with patch('src.notifier.EmailNotifier.send_report') as mock_email, \
         patch('src.notifier.TelegramNotifier.send_report', new_callable=AsyncMock) as mock_tg:
        
        await send_all_reports(mock_config, sample_articles, warning=warning)
        
        mock_email.assert_called_once_with(sample_articles, warning=warning)
        mock_tg.assert_called_once_with(sample_articles, warning=warning)

@pytest.mark.asyncio
async def test_send_all_reports_thread_isolated(mock_config, sample_articles):
    warning = "test warning"
    
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread, \
         patch('src.notifier.TelegramNotifier.send_report', new_callable=AsyncMock) as mock_tg:
        
        await send_all_reports(mock_config, sample_articles, warning=warning)
        
        mock_to_thread.assert_called_once()
        args, kwargs = mock_to_thread.call_args
        assert args[0].__name__ == "send_report"
        assert args[1] == sample_articles
        assert kwargs == {"warning": warning}

def test_email_notifier_standby(mock_config):
    notifier = EmailNotifier(mock_config)
    with patch('smtplib.SMTP_SSL') as mock_smtp_ssl:
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_smtp_ssl.return_value = mock_instance
        
        notifier.send_report([])
        
        mock_instance.sendmail.assert_called_once()
        args, _ = mock_instance.sendmail.call_args
        
        msg = email.message_from_string(args[2])
        
        def get_header(header_text):
            decoded_parts = decode_header(header_text)
            return "".join(
                [part.decode(enc or 'utf-8') if isinstance(part, bytes) else part for part, enc in decoded_parts]
            )
            
        assert "今日暂无新情报" in get_header(msg['Subject'])

@pytest.mark.asyncio
async def test_telegram_notifier_standby(mock_config):
    notifier = TelegramNotifier(mock_config)
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        await notifier.send_report([])
        
        args, kwargs = mock_post.call_args
        assert "今日暂无新情报" in kwargs['json']['text']

@pytest.mark.asyncio
async def test_telegram_html_escaping(mock_config):
    notifier = TelegramNotifier(mock_config)
    processed_articles = [
        {
            "title": "AT&T <Test>",
            "link": "http://ex.com/1",
            "source": "AT&T > Source",
            "ai_html": "<p>Sum 1</p>"
        }
    ]
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        await notifier.send_report(processed_articles)
        
        assert mock_post.called
        args, kwargs = mock_post.call_args
        text = kwargs['json']['text']
        assert "AT&amp;T &lt;Test&gt;" in text
        assert "AT&amp;T &gt; Source" in text

@pytest.mark.asyncio
async def test_telegram_notifier_multi_message_ordering(mock_config):
    notifier = TelegramNotifier(mock_config)
    # Generate large payload to exceed single message size threshold (4000 chars)
    processed_articles = [
        {
            "title": f"Article {i}",
            "link": f"http://ex.com/{i}",
            "source": f"Source {i}",
            "ai_html": f"<p>{'Long Content ' * 100}</p>"
        }
        for i in range(10)
    ]
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        await notifier.send_report(processed_articles)
        
        # 1 Header + at least 2 message chunks
        assert mock_post.call_count >= 3
        # Check call sequence: header first, then chunk 1, then chunk 2
        calls = mock_post.call_args_list
        assert "RSS 智能情报局" in calls[0].kwargs['json']['text']
        assert "Article 0" in calls[1].kwargs['json']['text']



