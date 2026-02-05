import pytest
from unittest.mock import MagicMock, patch
from src.mailer import Mailer

def test_send_report_empty(mock_config):
    mailer = Mailer(mock_config)
    with patch('smtplib.SMTP_SSL') as mock_smtp:
        mailer.send_report([])
        mock_smtp.assert_not_called()

def test_send_report_success(mock_config):
    mailer = Mailer(mock_config)
    processed_articles = [
        {
            "title": "Article 1",
            "link": "http://example.com/1",
            "source": "Source 1",
            "ai_html": "<p>Summary 1</p>"
        }
    ]
    
    with patch('smtplib.SMTP_SSL') as mock_smtp:
        mock_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_instance
        
        mailer.send_report(processed_articles)
        
        mock_instance.login.assert_called_once_with(mock_config.SENDER, mock_config.SMTP_PASS)
        mock_instance.sendmail.assert_called_once()
        
        # Verify call arguments
        args, kwargs = mock_instance.sendmail.call_args
        assert args[0] == mock_config.SENDER
        assert args[1] == mock_config.RECEIVER
        
        # Verify email structure and content
        import email
        from email.header import decode_header
        msg = email.message_from_string(args[2])
        
        def get_header(header_text):
            decoded_parts = decode_header(header_text)
            return "".join(
                [part.decode(enc or 'utf-8') if isinstance(part, bytes) else part for part, enc in decoded_parts]
            )
            
        assert get_header(msg['Subject']) == f"RSS 智能情报局 - 1 篇新更新"
        assert msg['From'] == mock_config.SENDER
        assert msg['To'] == mock_config.RECEIVER
        
        # Check body for content
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/html':
                    body = part.get_payload(decode=True).decode()
        else:
            body = msg.get_payload(decode=True).decode()
            
        assert "Article 1" in body
        assert "http://example.com/1" in body

def test_send_report_failure(mock_config):
    mailer = Mailer(mock_config)
    processed_articles = [{"title": "Art", "link": "link", "source": "src", "ai_html": "html"}]
    
    with patch('smtplib.SMTP_SSL') as mock_smtp:
        mock_instance = MagicMock()
        mock_instance.login.side_effect = Exception("SMTP Auth Error")
        mock_smtp.return_value.__enter__.return_value = mock_instance
        
        with pytest.raises(Exception) as excinfo:
            mailer.send_report(processed_articles)
        
        assert "SMTP Auth Error" in str(excinfo.value)
