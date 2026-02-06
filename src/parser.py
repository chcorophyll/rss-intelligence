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
                    raw = json.load(f)
                    
                    # 自动迁移旧格式 (hash: timestamp) -> 新格式 (hash: {ts, processed})
                    upgraded = {}
                    for k, v in raw.items():
                        if isinstance(v, (int, float)):
                            upgraded[k] = {"ts": float(v), "processed": True}
                        else:
                            upgraded[k] = v
                    return upgraded
            except:
                return {}
        return {}

    def save_and_clean(self):
        """清理已处理且过期的条目，并保存历史记录"""
        cutoff = time.time() - (self.retention_days * 24 * 3600)
        cleaned = {}
        for h, info in self.history.items():
            # 只有已处理且时间过期才清理
            is_processed = info.get('processed', False)
            ts = info.get('ts', 0)
            if not is_processed or ts > cutoff:
                cleaned[h] = info
        
        with open(self.db, 'w', encoding='utf-8') as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)
        self.history = cleaned

    async def fetch_all(self):
        """获取源更新，并与历史记录中的待处理文章合并"""
        urls = []
        if os.path.exists(self.opml):
            from bs4 import BeautifulSoup
            with open(self.opml, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'xml')
                urls = [o.get('xmlUrl') for o in soup.find_all('outline') if o.get('xmlUrl')]
            print(f"✅ Found {len(urls)} URLs in OPML")
        elif os.path.exists(self.txt):
            with open(self.txt, 'r', encoding='utf-8') as f:
                urls = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        
        # 1. 抓取 RSS 订阅源并存入历史（标记为未处理）
        if urls:
            async with aiohttp.ClientSession() as session:
                tasks = [self._fetch_one(session, u) for u in urls]
                feeds = await asyncio.gather(*tasks)
                
                now = time.time()
                for feed in filter(None, feeds):
                    source = feed.feed.get('title', 'Unknown Source')
                    for entry in feed.entries:
                        link = entry.get('link')
                        if not link: continue
                        
                        u_hash = hashlib.md5(link.encode()).hexdigest()
                        # 如果是全新文章，存入历史，带上正文，标记为未处理
                        if u_hash not in self.history:
                            content = entry.get('content', [{}])[0].get('value', entry.get('summary', ''))
                            self.history[u_hash] = {
                                "ts": now,
                                "processed": False,
                                "data": {
                                    "title": entry.get('title', 'Untitled'),
                                    "link": link,
                                    "content": content,
                                    "source": source,
                                    "hash": u_hash
                                }
                            }

        # 2. 从历史记录中提取所有待处理 (processed: False) 的文章
        pending_data = []
        for info in self.history.values():
            if not info.get('processed', False) and 'data' in info:
                pending_data.append(info)
        
        # 按时间从近到远排序 (ts 降序)
        pending_data.sort(key=lambda x: x.get('ts', 0), reverse=True)
        
        return [item['data'] for item in pending_data]

    def mark_as_processed(self, articles):
        """将文章标记为已处理，并清除正文以减小体积"""
        now = time.time()
        for art in articles:
            u_hash = art.get('hash')
            if u_hash in self.history:
                self.history[u_hash]['processed'] = True
                self.history[u_hash]['ts'] = now
                # 清除正文数据
                if 'data' in self.history[u_hash]:
                    del self.history[u_hash]['data']

    async def _fetch_one(self, session, url):
        """带信号量限制的单源抓取"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        async with self.semaphore:
            try:
                async with session.get(url, timeout=15, headers=headers, ssl=False) as res:
                    if res.status == 200:
                        return feedparser.parse(await res.text())
                    else:
                        print(f"⚠️ Fetch failed for {url}: Status {res.status}")
            except Exception as e:
                print(f"❌ Fetch error for {url}: {e}")
            return None