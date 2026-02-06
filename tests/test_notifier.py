import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.notifier import EmailNotifier, TelegramNotifier, send_all_reports

def test_email_notifier_success(mock_config):
    notifier = EmailNotifier(mock_config)
    processed_articles = [
        {"title": "Art 1", "link": "http://ex.com/1", "source": "Src 1", "ai_html": "<p>Sum 1</p>"}
    ]
    
    with patch('smtplib.SMTP_SSL') as mock_smtp_ssl:
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_smtp_ssl.return_value = mock_instance
        
        notifier.send_report(processed_articles)
        
        mock_instance.login.assert_called_once_with(mock_config.SENDER, mock_config.SMTP_PASS)
        mock_instance.sendmail.assert_called_once()

@pytest.mark.asyncio
async def test_telegram_notifier_success(mock_config):
    notifier = TelegramNotifier(mock_config)
    processed_articles = [
        {"title": "Art 1", "link": "http://ex.com/1", "source": "Src 1", "ai_html": "<p>Sum 1</p>"}
    ]
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        await notifier.send_report(processed_articles)
        
        assert mock_post.called
        args, kwargs = mock_post.call_args
        assert "telegram.org" in args[0]
        assert kwargs['json']['chat_id'] == "test_chat_id"
        assert "Art 1" in kwargs['json']['text']

@pytest.mark.asyncio
async def test_telegram_notifier_with_warning(mock_config):
    notifier = TelegramNotifier(mock_config)
    processed_articles = [
        {"title": "Art 1", "link": "http://ex.com/1", "source": "Src 1", "ai_html": "<p>Sum 1</p>"}
    ]
    warning = "AI quota exceeded"
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        await notifier.send_report(processed_articles, warning=warning)
        
        args, kwargs = mock_post.call_args
        assert warning in kwargs['json']['text']

@pytest.mark.asyncio
async def test_send_all_reports(mock_config):
    processed_articles = [{"title": "Art", "link": "link", "source": "src", "ai_html": "html"}]
    warning = "test warning"
    
    with patch('src.notifier.EmailNotifier.send_report') as mock_email, \
         patch('src.notifier.TelegramNotifier.send_report', new_callable=AsyncMock) as mock_tg:
        
        await send_all_reports(mock_config, processed_articles, warning=warning)
        
        mock_email.assert_called_once_with(processed_articles, warning=warning)
        mock_tg.assert_called_once_with(processed_articles, warning=warning)

def test_email_notifier_standby(mock_config):
    notifier = EmailNotifier(mock_config)
    with patch('smtplib.SMTP_SSL') as mock_smtp_ssl:
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_smtp_ssl.return_value = mock_instance
        
        notifier.send_report([])
        
        mock_instance.sendmail.assert_called_once()
        args, _ = mock_instance.sendmail.call_args
        
        import email
        from email.header import decode_header
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
