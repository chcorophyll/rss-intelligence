import asyncio
import os
import hashlib
from src.parser import RSSManager
from src.ai_hub import IntelligenceHub
from src.notifier import send_all_reports
from main import AppConfig

async def debug_single_workflow(target_url):
    print(f"🛠️ Starting Step-by-Step Debug for URL: {target_url}\n")
    
    # 1. Initialize Config
    print("Step 1: Loading Configuration...")
    cfg = AppConfig()
    try:
        cfg.validate()
        print("✅ Config validated successfully.\n")
    except Exception as e:
        print(f"❌ Config validation failed: {e}")
        return

    # 2. Fetch and Parse
    print(f"Step 2: Fetching from {target_url}...")
    rss = RSSManager(cfg, db="debug_history.json")
    # Bypass the OPML logic to test just this URL
    import aiohttp
    import feedparser
    async with aiohttp.ClientSession() as session:
        try:
            feed = await rss._fetch_one(session, target_url)
        except Exception as e:
            print(f"❌ Error during fetch: {e}")
            return

        if not feed:
            print("❌ Failed to fetch or parse the feed (Likely timeout or status code != 200).")
            return
        
        print(f"✅ Feed fetched: {feed.feed.get('title', 'Unknown Source')}")
        
        new_items = []
        for entry in feed.entries[:1]: # Just take the first one for testing
            link = entry.get('link')
            u_hash = hashlib.md5(link.encode()).hexdigest()
            content = ""
            if 'content' in entry:
                content = entry.content[0].value
            elif 'summary' in entry:
                content = entry.summary
            
            item = {
                "title": entry.get('title', 'Untitled'),
                "link": link,
                "content": content,
                "source": feed.feed.get('title', 'Source'),
                "hash": u_hash
            }
            new_items.append(item)
            print(f"📄 Found article: {item['title']}")

    if not new_items:
        print("❌ No articles extracted.")
        return

    # 3. AI Processing
    print("\nStep 3: AI Processing with Gemini...")
    hub = IntelligenceHub(cfg)
    try:
        processed, quota_exceeded = await hub.process_articles(new_items)
    except Exception as e:
        print(f"⚠️ AI request failed: {e}")
        processed = []
    
    if not processed:
        print("💡 Since AI failed or quota was hit, using a fallback mock summary to test notifications...")
        processed = [{
            "title": new_items[0]['title'],
            "link": new_items[0]['link'],
            "source": new_items[0]['source'],
            "ai_html": "<h2>[FALLBACK] News Summary</h2><p>Due to AI quota limits, this is a <i>mock</i> summary used for testing notifications.</p>"
        }]

    if processed:
        print("\n✅ Proceeding to notification step...")
        # Use more descriptive output
        print("-" * 30)
        print(f"标题: {processed[0]['title']}")
        print(f"来源: {processed[0]['source']}")
        print(f"AI 总结预览:\n{processed[0].get('ai_html', 'No AI HTML generated')}")
        print("-" * 30)

        # 4. Notification Step
        print("\nStep 4: Sending Notifications (Email & Telegram)...")
        try:
            await send_all_reports(cfg, processed)
            print("✅ All notifications sent successfully.")
        except Exception as e:
            print(f"❌ Notification failed: {e}")
    else:
        print("\n❌ AI processing failed (see error above).")

if __name__ == "__main__":
    # Use a more reliable URL for testing
    test_url = "https://www.theverge.com/rss/index.xml"
    asyncio.run(debug_single_workflow(test_url))
