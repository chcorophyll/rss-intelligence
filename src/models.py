from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Article:
    title: str
    link: str
    source: str
    hash: str
    content: str = ""
    ai_html: Optional[str] = None
    
    def to_dict(self):
        return {
            "title": self.title,
            "link": self.link,
            "source": self.source,
            "hash": self.hash,
            "content": self.content,
            "ai_html": self.ai_html
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            title=data.get("title", ""),
            link=data.get("link", ""),
            source=data.get("source", ""),
            hash=data.get("hash", ""),
            content=data.get("content", ""),
            ai_html=data.get("ai_html")
        )
