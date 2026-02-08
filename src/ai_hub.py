import asyncio
from google import genai
from bs4 import BeautifulSoup
import markdown

class IntelligenceHub:
    def __init__(self, cfg):
        # 初始化最新的 Google GenAI 客户端
        self.client = genai.Client(api_key=cfg.GEMINI_KEY)
        self.model_name = cfg.config.get('AI', 'ModelName', fallback='gemini-1.5-flash')
        self.delay = cfg.config.getint('AI', 'RequestDelay', fallback=4)
        self.concurrency = cfg.config.getint('AI', 'Concurrency', fallback=2)

    async def process_articles(self, articles):
        """并行处理所有文章列表，支持配额异常捕获"""
        results = []
        self.quota_exceeded = False
        
        # 使用信号量控制并发，从配置中读取
        sem = asyncio.Semaphore(self.concurrency) 
        
        async def _worker(art):
            if self.quota_exceeded:
                return None
            
            async with sem:
                res = await self._process_one(art)
                if res:
                    results.append(res)
                return res

        # 创建所有任务
        tasks = [_worker(art) for art in articles]
        await asyncio.gather(*tasks)
                
        return results, self.quota_exceeded

    async def _process_one(self, art):
        """处理单篇文章"""
        print(f"🤖 正在处理: {art['title']}")
        
        # 清理 HTML 标签
        soup = BeautifulSoup(art['content'], "html.parser")
        text = soup.get_text(separator="\n", strip=True)[:6000]
        
        prompt = (
            "Role: Professional Bilingual News Editor.\n"
            "Task: Analyze the provided content and output a structured report strictly in the following Markdown format:\n\n"
            "## 1. 速览 (Summary)\n"
            "- [Point 1: Concise summary in Chinese]\n"
            "- [Point 2: Concise summary in Chinese]\n"
            "- [Point 3: Concise summary in Chinese]\n\n"
            "## 2. 深度 (Insights)\n"
            "| Key Insight (English) | 核心观点 (Chinese) |\n"
            "| :--- | :--- |\n"
            "| [Key point 1 in English] | [Key point 1 in Chinese] |\n"
            "| [Key point 2 in English] | [Key point 2 in Chinese] |\n"
            "| [Key point 3 in English] | [Key point 3 in Chinese] |\n\n"
            "Constraints:\n"
            "- Ensure the Chinese summary captures 100% of the core value.\n"
            "- The table must track the original English phrasing against the Chinese interpretation.\n"
            f"Title: {art['title']}\n"
            f"Content: {text}"
        )
        
        try:
            # 使用 loop 包装同步的 SDK 调用
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.client.models.generate_content(
                    model=self.model_name, 
                    contents=prompt
                )
            )
            
            # 获取生成文本并转为 HTML
            art['ai_html'] = markdown.markdown(response.text)
            
            # 免费版 API 必须设置延迟以防 RPM 限制
            await asyncio.sleep(self.delay)
            return art

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if not self.quota_exceeded:
                    print(f"⚠️ AI 配额已耗尽，停止后续处理。")
                    self.quota_exceeded = True
            else:
                print(f"❌ AI 处理失败 [{art['title']}]: {e}")
            return None