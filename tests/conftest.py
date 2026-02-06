import pytest
import os
import configparser
from unittest.mock import MagicMock

class MockConfig:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.add_section('SYSTEM')
        self.config.set('SYSTEM', 'RetentionDays', '30')
        self.config.set('SYSTEM', 'MaxConcurrency', '10')
        
        self.config.add_section('AI')
        self.config.set('AI', 'ModelName', 'gemini-1.5-flash')
        self.config.add_section('SMTP')
        self.config.set('SMTP', 'Server', 'smtp.example.com')
        self.config.set('SMTP', 'Port', '465')

        self.config.add_section('TELEGRAM')
        self.config.set('TELEGRAM', 'Enabled', 'true')
        
        self.GEMINI_KEY = "test_key"
        self.SMTP_PASS = "test_pass"
        self.SENDER = "sender@example.com"
        self.RECEIVER = "receiver@example.com"
        self.TELEGRAM_BOT_TOKEN = "test_token"
        self.TELEGRAM_CHAT_ID = "test_chat_id"

@pytest.fixture
def mock_config():
    return MockConfig()
