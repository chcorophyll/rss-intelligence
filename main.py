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
        self.GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
        self.SMTP_PASS = os.getenv("SMTP_PASSWORD", "").strip()
        self.SENDER = os.getenv("SENDER_EMAIL", "").strip()
        self.RECEIVER = os.getenv("RECEIVER_EMAIL", "").strip()
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

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

        # 4. 持久化历史 (Phase 3) 必须在发通知之前进行
        if processed:
            # 标记已处理完成的文章
            rss.mark_as_processed(processed)
            print(f"🏁 任务处理完成：今日成功处理 {len(processed)} 篇文章。")
        
        if quota_exceeded:
            remaining = len(pending_articles) - len(processed)
            warning = f"由于 AI 额度不足，{remaining} 篇文章未处理，已保留至下次运行。"
            print(f"⚠️ {warning}")
        elif not processed:
            print("🏁 任务处理完成：无新动态。")
            warning = None
        else:
            warning = None
            
        rss.save_and_clean()    

        # 5. 发送多渠道报告 (Phase 4)
        try:
            await send_all_reports(cfg, processed, warning=warning)
        except Exception as e:
            print(f"⚠️ 通知环节出现问题（但不影响已处理状态）: {e}")

    except Exception as e:
        print(f"🔥 程序运行期间发生致命错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())