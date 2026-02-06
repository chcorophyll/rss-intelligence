import asyncio
import os
import aiohttp
from dotenv import load_dotenv

async def test_telegram():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ 错误: 请在 .env 文件中设置 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID")
        return

    print(f"📡 正在尝试向 Chat ID {chat_id} 发送测试消息...")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🎉 *RSS 智能情报局* Telegram 机器人测试成功！\n\n这是一条测试消息。",
        "parse_mode": "MarkdownV2"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    print("✅ 发送成功！请检查您的 Telegram。")
                else:
                    err_text = await resp.text()
                    print(f"❌ 发送失败 ({resp.status}): {err_text}")
        except Exception as e:
            print(f"❌ 发生异常: {e}")

if __name__ == "__main__":
    asyncio.run(test_telegram())
