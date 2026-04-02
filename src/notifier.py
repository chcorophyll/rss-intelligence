import smtplib
import aiohttp
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailNotifier:
    def __init__(self, cfg):
        self.cfg = cfg

    def send_report(self, processed_articles, warning=None):
        """构建并发送 HTML 格式的每日报告"""
        msg = MIMEMultipart()
        
        if not processed_articles:
            if warning:
                msg['Subject'] = "RSS 智能情报局 - 因额度不足,今日0篇处理"
            else:
                msg['Subject'] = "RSS 智能情报局 - 今日暂无新情报"
        else:
            msg['Subject'] = f"RSS 智能情报局 - {len(processed_articles)} 篇新更新"
            
        msg['From'] = self.cfg.SENDER
        msg['To'] = self.cfg.RECEIVER

        # 构建邮件正文
        body = "<html><body style='font-family: Arial, sans-serif; color: #333; max-width: 800px; margin: 0 auto;'>"
        
        if warning:
            body += f"""
            <div style='background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; padding: 15px; margin-bottom: 20px; border-radius: 4px;'>
                <strong>⚠️ 注意:</strong> {warning}
            </div>
            """

        if not processed_articles:
            body += f"""
            <div style='text-align: center; padding: 50px 20px; color: #666;'>
                <h2 style='color: #1a73e8;'>☕ 今日暂无新情报</h2>
                <p>系统运行正常，所有订阅源均已同步，暂未发现符合条件的更新。</p>
            </div>
            """
        else:
            body += "<h1 style='color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px;'>今日情报摘要</h1>"
            for art in processed_articles:
                body += f"""
                <div style='margin-bottom: 40px; border-left: 4px solid #1a73e8; padding-left: 15px;'>
                    <h2 style='margin-top: 0;'><a href='{art['link']}' style='text-decoration: none; color: #1a73e8;'>{art['title']}</a></h2>
                    <p style='font-size: 0.9em; color: #666;'>来源: {art['source']}</p>
                    <div style='line-height: 1.6;'>{art['ai_html']}</div>
                </div>
                """
        
        body += "</body></html>"
        msg.attach(MIMEText(body, 'html'))

        try:
            host = self.cfg.config.get('SMTP', 'Server')
            port = self.cfg.config.getint('SMTP', 'Port')
            
            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=30)
            else:
                server = smtplib.SMTP(host, port, timeout=30)
                if port == 587:
                    server.starttls()
            
            with server:
                server.login(self.cfg.SENDER, self.cfg.SMTP_PASS)
                server.sendmail(self.cfg.SENDER, self.cfg.RECEIVER, msg.as_string())
            print("邮件报告发送成功！")
        except Exception as e:
            print(f"邮件发送失败: {e}")
            if "EOF" in str(e) or "protocol" in str(e).lower():
                print("💡 诊断提示: 检测到 SSL 握手异常。这通常是因为 Gmail/国外邮箱的 SMTP 服务被网络环境封锁。")
                print("💡 解决建议: 建议更换为国内邮箱（如 QQ、163）的 SMTP 服务，稳定性更高。")
            raise e

class TelegramNotifier:
    def __init__(self, cfg):
        self.cfg = cfg
        self.token = cfg.TELEGRAM_BOT_TOKEN
        self.chat_id = cfg.TELEGRAM_CHAT_ID

    async def send_report(self, processed_articles, warning=None):
        """发送 Telegram 消息报告"""
        if not processed_articles:
            header = "☕ <b>RSS 智能情报局 - 今日暂无新情报</b>\n\n系统运行正常，暂未发现新文章。"
            if warning:
                header += f"\n\n⚠️ <b>注意: {warning}</b>"
            messages = [header]
        else:
            header = f"🚀 <b>RSS 智能情报局 - {len(processed_articles)} 篇新更新</b>\n"
            if warning:
                header += f"\n⚠️ <b>注意: {warning}</b>\n"
            header += "\n"
            
            messages = []
            current_msg = header
            
            for art in processed_articles:
                # AI summary is in HTML, we need to convert or strip it for Telegram
                ai_summary = art.get('ai_html', '')
                
                # Simple HTML to Telegram HTML conversion
                import re
                ai_summary = re.sub(r'<h[1-6]>(.*?)</h[1-6]>', r'<b>\1</b>', ai_summary)
                ai_summary = ai_summary.replace('<p>', '').replace('</p>', '\n')
                ai_summary = ai_summary.replace('<ul>', '').replace('</ul>', '')
                ai_summary = ai_summary.replace('<li>', '• ').replace('</li>', '\n')
                ai_summary = re.sub(r'<(?!/?(b|strong|i|em|u|ins|s|strike|del|a|code|pre)\b)[^>]+>', '', ai_summary)
                
                item_text = f"<b><a href='{art['link']}'>{art['title']}</a></b>\n"
                item_text += f"<i>来源: {art['source']}</i>\n"
                item_text += f"{ai_summary.strip()}\n\n"
                
                if len(current_msg) + len(item_text) > 4000:
                    messages.append(current_msg)
                    current_msg = item_text
                else:
                    current_msg += item_text
            
            messages.append(current_msg)

        async with aiohttp.ClientSession() as session:
            for msg in messages:
                url = f"https://api.telegram.org/bot{self.token}/sendMessage"
                payload = {
                    "chat_id": self.chat_id,
                    "text": msg,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True
                }
                try:
                    async with session.post(url, json=payload) as resp:
                        if resp.status != 200:
                            err_text = await resp.text()
                            print(f"Telegram 发送失败 ({resp.status}): {err_text}")
                        else:
                            print("Telegram 报告发送成功！")
                except Exception as e:
                    print(f"Telegram 发送异常: {e}")

async def send_all_reports(cfg, processed_articles, warning=None):
    """根据配置发送所有启用的通知"""
    tasks = []
    
    # 1. Email (Sync)
    try:
        email_notifier = EmailNotifier(cfg)
        email_notifier.send_report(processed_articles, warning=warning)
    except Exception as e:
        print(f"邮件发送失败，跳过: {e}")

    # 2. Telegram (Async)
    if cfg.config.getboolean('TELEGRAM', 'Enabled', fallback=False):
        tg_notifier = TelegramNotifier(cfg)
        await tg_notifier.send_report(processed_articles, warning=warning)
