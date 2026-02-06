import asyncio
import hashlib
import json
import os
import time
import aiohttp
import feedparser

class RSSManager:
    def __init__(self, cfg, opml="subscriptions.opml", txt="feeds.txt", db="history.json"):
        self.opml = opml
        self.txt = txt
        self.db = db
        self.retention_days = cfg.config.getint('SYSTEM', 'RetentionDays', fallback=30)
        self.semaphore = asyncio.Semaphore(cfg.config.getint('SYSTEM', 'MaxConcurrency', fallback=10))
        self.history = self._load_history()

    def _load_history(self):
        if os.path.exists(self.db):
            try:
                with open(self.db, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_and_clean(self):
        """清理过期条目并保存历史记录"""
        cutoff = time.time() - (self.retention_days * 24 * 3600)
        cleaned = {h: ts for h, ts in self.history.items() if ts > cutoff}
        with open(self.db, 'w', encoding='utf-8') as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)
        self.history = cleaned

    async def fetch_all(self):
        """获取并解析订阅源"""
        urls = []
        if os.path.exists(self.opml):
            from bs4 import BeautifulSoup
            with open(self.opml, 'r', encoding='utf-8') as f:
                # Use xml parser for correct case handling in OPML
                soup = BeautifulSoup(f.read(), 'xml')
                urls = [o.get('xmlUrl') for o in soup.find_all('outline') if o.get('xmlUrl')]
            print(f"✅ Found {len(urls)} URLs in OPML")
        elif os.path.exists(self.txt):
            with open(self.txt, 'r', encoding='utf-8') as f:
                urls = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        
        if not urls:
            return []

        new_items = []
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_one(session, u) for u in urls]
            feeds = await asyncio.gather(*tasks)
            
            for feed in filter(None, feeds):
                source = feed.feed.get('title', 'Unknown Source')
                for entry in feed.entries:
                    link = entry.get('link')
                    if not link: continue
                    
                    u_hash = hashlib.md5(link.encode()).hexdigest()
                    if u_hash not in self.history:
                        content = entry.get('content', [{}])[0].get('value', entry.get('summary', ''))
                        new_items.append({
                            "title": entry.get('title', 'Untitled'),
                            "link": link,
                            "content": content,
                            "source": source,
                            "hash": u_hash
                        })
                        # 暂时存入历史以防止本次运行中重复处理
                        self.history[u_hash] = time.time()
        return new_items

    async def _fetch_one(self, session, url):
        """带信号量限制的单源抓取"""
        async with self.semaphore:
            try:
                async with session.get(url, timeout=10) as res:
                    if res.status == 200:
                        return feedparser.parse(await res.text())
            except:
                pass
            return None