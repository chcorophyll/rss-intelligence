import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class Mailer:
    def __init__(self, cfg):
        self.cfg = cfg

    def send_report(self, processed_articles):
        """构建并发送 HTML 格式的每日报告"""
        if not processed_articles:
            return

        msg = MIMEMultipart()
        msg['Subject'] = f"RSS 智能情报局 - {len(processed_articles)} 篇新更新"
        msg['From'] = self.cfg.SENDER
        msg['To'] = self.cfg.RECEIVER

        # 构建邮件正文
        body = "<html><body style='font-family: Arial, sans-serif; color: #333; max-width: 800px; margin: 0 auto;'>"
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