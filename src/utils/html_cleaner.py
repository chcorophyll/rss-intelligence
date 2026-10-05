import re
from bs4 import BeautifulSoup

def clean_to_text(html_content: str, max_len: int = 6000) -> str:
    """清理 HTML 标签，返回纯文本"""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    return text[:max_len]

def sanitize_telegram_html(html_content: str) -> str:
    """清理非法的 Telegram HTML 标签"""
    if not html_content:
        return ""
    
    ai_summary = html_content
    ai_summary = re.sub(r'<h[1-6]>(.*?)</h[1-6]>', r'<b>\1</b>', ai_summary)
    ai_summary = ai_summary.replace('<p>', '').replace('</p>', '\n')
    ai_summary = ai_summary.replace('<ul>', '').replace('</ul>', '')
    ai_summary = ai_summary.replace('<li>', '• ').replace('</li>', '\n')
    
    # 仅保留 Telegram 支持的标签
    ai_summary = re.sub(r'<(?!/?(b|strong|i|em|u|ins|s|strike|del|a|code|pre)\b)[^>]+>', '', ai_summary)
    
    return ai_summary
