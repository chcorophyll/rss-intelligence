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
            except (json.JSONDecodeError, OSError) as e:
                print(f"⚠️ Failed to load history database ({self.db}): {e}")
                if os.path.exists(self.db):
                    try:
                        os.replace(self.db, self.db + ".bak")
                    except OSError:
                        pass
                return {}
        return {}

    def save_and_clean(self):
        """清理过期条目（已处理或未处理），并保存历史记录"""
        cutoff = time.time() - (self.retention_days * 24 * 3600)
        cleaned = {}
        for h, info in self.history.items():
            ts = info.get('ts', 0)
            # 只保留 retention 窗口内的条目（无论是否处理）
            # 超期的 pending 文章也清理，防止积压无限增长
            if ts > cutoff:
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
        fetched_contents = {}
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
                        content = entry.get('content', [{}])[0].get('value', entry.get('summary', ''))
                        fetched_contents[u_hash] = content
                        
                        # 如果是全新文章，存入历史（不存正文 HTML 减小体积），标记为未处理
                        if u_hash not in self.history:
                            self.history[u_hash] = {
                                "ts": now,
                                "processed": False,
                                "data": {
                                    "title": entry.get('title', 'Untitled'),
                                    "link": link,
                                    "source": source,
                                    "hash": u_hash
                                }
                            }

        # 2. 从历史记录中提取所有待处理 (processed: False) 的文章
        cutoff = time.time() - (self.retention_days * 24 * 3600)
        pending_items = []
        for info in self.history.values():
            if not info.get('processed', False) and 'data' in info:
                if info.get('ts', 0) >= cutoff:
                    pending_items.append(info)
        
        # 按时间从近到远排序 (ts 降序)
        pending_items.sort(key=lambda x: x.get('ts', 0), reverse=True)
        
        if pending_items:
            print(f"📋 窗口内待处理候选文章: {len(pending_items)} 篇（最近 {self.retention_days} 天内）")
        
        # 3. 构造返回列表，确保仅传送当次抓取到非空正文的文章，不足时顺延补足（目标最多 50 篇）
        result = []
        max_batch = 50
        
        async with aiohttp.ClientSession() as session:
            idx = 0
            n = len(pending_items)
            
            while idx < n and len(result) < max_batch:
                # 收集下一批需要进行 HTML 补偿抓取的文章（批次大小为 10）
                batch_candidates = []
                
                while idx < n and len(batch_candidates) < 10 and (len(result) + len(batch_candidates)) < max_batch:
                    item = pending_items[idx]
                    idx += 1
                    item_data = dict(item['data'])
                    u_hash = item_data.get('hash')
                    content = fetched_contents.get(u_hash, item_data.get('content', ''))
                    
                    if content.strip():
                        # 自身或内存已有正文，直接加入结果
                        item_data['content'] = content
                        result.append(item_data)
                    elif item_data.get('link'):
                        # 缺失正文，加入当批等待并发补偿抓取的候选列表
                        batch_candidates.append((item, item_data))
                
                if not batch_candidates:
                    continue
                
                # 并发 Task 集合处理当批补偿抓取
                tasks = [self._fetch_html_content(session, c[1]['link']) for c in batch_candidates]
                responses = await asyncio.gather(*tasks)
                
                for (item, item_data), (fallback_text, status_code) in zip(batch_candidates, responses):
                    if len(result) >= max_batch:
                        break
                        
                    u_hash = item_data.get('hash')
                    if fallback_text.strip():
                        item_data['content'] = fallback_text
                        fetched_contents[u_hash] = fallback_text
                        result.append(item_data)
                    else:
                        current_retries = item.get('retry_count', 0) + 1
                        item['retry_count'] = current_retries
                        
                        # 404/410 确定不可恢复，或重试超过 3 次：标记已失效/已处理
                        if status_code in (404, 410) or current_retries >= 3:
                            print(f"⚠️ 正文确定不可获取 (Status {status_code}, 重试 {current_retries}/3)，标记已失效: {item_data.get('title')}")
                            if u_hash in self.history:
                                self.history[u_hash]['processed'] = True
                                if 'data' in self.history[u_hash]:
                                    del self.history[u_hash]['data']
                        else:
                            print(f"⚠️ 正文补偿抓取失败 (Status {status_code}, 重试 {current_retries}/3)，本次跳过: {item_data.get('title')}")
            
        return result

    async def _fetch_raw(self, session, url):
        """通用底层 HTTP 请求，受信号量限制并统一处理 Header 与超时"""
        if not url:
            return "", 404
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        async with self.semaphore:
            try:
                async with session.get(url, timeout=15, headers=headers) as res:
                    if res.status == 200:
                        return await res.text(), 200
                    else:
                        return "", res.status
            except Exception as e:
                print(f"⚠️ Fetch error for {url}: {e}")
                return "", 0

    async def _fetch_one(self, session, url):
        """带信号量限制的 RSS Feed 单源抓取"""
        text, status = await self._fetch_raw(session, url)
        if status == 200 and text:
            try:
                return feedparser.parse(text)
            except Exception as e:
                print(f"❌ Feed parsing error for {url}: {e}")
                return None
        return None

    async def _fetch_html_content(self, session, link):
        """当 RSS Feed 缺失正文时，发起网页抓取进行补偿"""
        html_text, status = await self._fetch_raw(session, link)
        if status == 200 and html_text.strip():
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_text, 'html.parser')
                for s in soup(['script', 'style', 'nav', 'footer', 'header']):
                    s.decompose()
                main_content = soup.find('article') or soup.find('main') or soup.find('body')
                text = main_content.get_text(separator='\n', strip=True) if main_content else soup.get_text(separator='\n', strip=True)
                return text, 200
            except Exception as e:
                print(f"⚠️ HTML parsing error for {link}: {e}")
                return "", 0
        return "", status

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