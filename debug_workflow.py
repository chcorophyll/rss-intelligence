import asyncio
import os
import hashlib
from src.parser import RSSManager
from src.ai_hub import IntelligenceHub
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
        feed = await rss._fetch_one(session, target_url)
        if not feed:
            print("❌ Failed to fetch or parse the feed.")
            return
        
        print(f"✅ Feed fetched: {feed.feed.get('title', 'Unknown Source')}")
        
        new_items = []
        for entry in feed.entries[:1]: # Just take the first one for testing
            link = entry.get('link')
            u_hash = hashlib.md5(link.encode()).hexdigest()
            content = entry.get('content', [{}])[0].get('value', entry.get('summary', ''))
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
    processed = await hub.process_articles(new_items, 1)
    
    if processed:
        print("\n✅ AI processing success!")
        print(f"摘要内容预览:\n{processed[0].get('ai_html', 'No AI HTML generated')}")
    else:
        print("\n❌ AI processing failed (see error above).")

if __name__ == "__main__":
    # You can change this URL to test any RSS feed
    test_url = "https://simonwillison.net/atom/everything/"
    asyncio.run(debug_single_workflow(test_url))
