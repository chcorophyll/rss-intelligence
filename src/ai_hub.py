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

    async def process_articles(self, articles, max_articles):
        """处理文章列表"""
        results = []
        for art in articles[:max_articles]:
            print(f"🤖 正在处理: {art['title']}")
            
            # 清理 HTML 标签
            soup = BeautifulSoup(art['content'], "html.parser")
            text = soup.get_text(separator="\n", strip=True)[:6000]
            
            prompt = (
                "Role: Professional News Editor.\n"
                "Task: \n"
                "1. Summarize the content in 3 concise Chinese sentences.\n"
                "2. Provide a bilingual (English-Chinese) comparison of core insights.\n"
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
                results.append(art)
                
                # 免费版 API 必须设置延迟
                await asyncio.sleep(self.delay)
            except Exception as e:
                print(f"❌ AI 处理失败 [{art['title']}]: {e}")
                continue
                
        return results