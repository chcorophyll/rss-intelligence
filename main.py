import asyncio
import os
import configparser
from dotenv import load_dotenv
from src.parser import RSSManager
from src.ai_hub import IntelligenceHub
from src.mailer import Mailer


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

    def validate(self):
        """检查必要配置是否存在"""
        missing = [k for k, v in {
            "GEMINI_API_KEY": self.GEMINI_KEY,
            "SMTP_PASSWORD": self.SMTP_PASS,
            "SENDER_EMAIL": self.SENDER,
            "RECEIVER_EMAIL": self.RECEIVER
        }.items() if not v]
        if missing:
            raise ValueError(f"缺少必要环境变量: {', '.join(missing)}")

async def main():
    try:
        # 1. 初始化配置
        cfg = AppConfig()
        cfg.validate()

        # 2. 抓取 RSS 内容 (Phase 1)
        rss = RSSManager(cfg)
        new_articles = await rss.fetch_all()
        
        if not new_articles:
            print("☕ 没有发现新文章，任务结束。")
            return

        print(f"✅ 抓取完成，发现 {len(new_articles)} 篇新文章。")

        # 3. AI 智能处理 (Phase 2)
        hub = IntelligenceHub(cfg)
        max_items = cfg.config.getint('SYSTEM', 'MaxArticlesPerRun', fallback=12)
        processed = await hub.process_articles(new_articles, max_items)

        # 4. 发送邮件并持久化历史 (Phase 3)
        if processed:
            try:
                mailer = Mailer(cfg)
                mailer.send_report(processed)
            except Exception as e:
                print(f"⚠️ 邮件发送环节出现问题，但已处理的文章将记入历史记录以节省配额。")
            
            rss.save_and_clean()
            print(f"🏁 任务处理完成（历史记录已更新）。")

    except Exception as e:
        print(f"🔥 程序运行期间发生致命错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())