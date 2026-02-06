import asyncio
import os
import configparser
from dotenv import load_dotenv
from src.parser import RSSManager
from src.ai_hub import IntelligenceHub
from src.notifier import send_all_reports


load_dotenv()


class AppConfig:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join('config', 'config.ini'), encoding='utf-8')
        # 从环境变量获取敏感信息
        self.GEMINI_KEY = os.getenv("GEMINI_API_KEY")
        self.SMTP_PASS = os.getenv("SMTP_PASSWORD")
        self.SENDER = os.getenv("SENDER_EMAIL")
        self.RECEIVER = os.getenv("RECEIVER_EMAIL")
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    def validate(self):
        """检查必要配置是否存在"""
        missing = []
        
        # 基础必填项
        if not self.GEMINI_KEY:
            missing.append("GEMINI_API_KEY")
        
        # 如果启用了邮件
        if self.SENDER or self.RECEIVER or self.SMTP_PASS:
             if not all([self.SENDER, self.RECEIVER, self.SMTP_PASS]):
                 missing.extend([k for k, v in {
                     "SENDER_EMAIL": self.SENDER,
                     "RECEIVER_EMAIL": self.RECEIVER,
                     "SMTP_PASSWORD": self.SMTP_PASS
                 }.items() if not v])

        # 如果启用了 Telegram
        if self.config.getboolean('TELEGRAM', 'Enabled', fallback=False):
            if not self.TELEGRAM_BOT_TOKEN:
                missing.append("TELEGRAM_BOT_TOKEN")
            if not self.TELEGRAM_CHAT_ID:
                missing.append("TELEGRAM_CHAT_ID")

        if missing:
            raise ValueError(f"缺少必要环境变量: {', '.join(missing)}")

async def main():
    try:
        # 1. 初始化配置
        cfg = AppConfig()
        cfg.validate()

        # 2. 获取文章 (Phase 1)
        # fetch_all 现在会返回所有“待处理”文章（包括本次新抓取的和之前遗留的）
        rss = RSSManager(cfg)
        pending_articles = await rss.fetch_all()
        
        # 3. AI 智能处理 (Phase 2)
        processed = []
        quota_exceeded = False
        
        if pending_articles:
            print(f"✅ 准备处理 {len(pending_articles)} 篇待办文章（含历史遗留）。")
            hub = IntelligenceHub(cfg)
            processed, quota_exceeded = await hub.process_articles(pending_articles)
        else:
            print("☕ 暂无待处理文章，将发送系统正常运行状态报告。")

        # 4. 发送多渠道报告并持久化历史 (Phase 3)
        warning = None
        if quota_exceeded:
            warning = "由于 AI 额度不足，未处理文章已安全存入历史，将在下次运行时尝试处理。"
            
        try:
            await send_all_reports(cfg, processed, warning=warning)
        except Exception as e:
            print(f"⚠️ 通知环节出现问题: {e}")
        
        # 处理结果持久化
        if processed:
            # 仅将处理并发送成功的标记为已完成
            rss.mark_as_processed(processed)
            print(f"🏁 任务处理完成：今日成功处理 {len(processed)} 篇文章。")
        elif quota_exceeded:
            print("⚠️ 未能总结任何文章（AI 配额耗尽）。文章已保留，下次运行。")
        else:
            print("🏁 任务处理完成：无新动态。")
        rss.save_and_clean()    

    except Exception as e:
        print(f"🔥 程序运行期间发生致命错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())