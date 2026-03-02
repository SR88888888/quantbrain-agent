import httpx
import asyncio
from typing import Optional, List
from src.core.config import settings
from src.core.logger import log
from src.domain.models import NewsItem

CONTENT_SELECTORS = [
    ".zw_body", "#ContentBody", ".article-body", "#artibody",
    ".article", "#article", ".article-content", ".post-content",
]


class ContentFetcher:
    """新闻正文抓取器 - 被DataSourceAggregator.collect_all()实际调用"""

    def __init__(self):
        self.timeout = settings.CONTENT_FETCH_TIMEOUT
        self.max_content_length = settings.CONTENT_MAX_LENGTH
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        }
        self._fetch_count = 0
        self._success_count = 0

    async def fetch_content(self, item: NewsItem) -> NewsItem:
        if not item.url:
            return item
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, headers=self.headers, follow_redirects=True,
            ) as client:
                resp = await client.get(item.url)
                self._fetch_count += 1
                if resp.status_code != 200:
                    return item
                content = self._extract_content(resp.text)
                if content:
                    item.content = content[:self.max_content_length]
                    self._success_count += 1
        except Exception as e:
            log.debug(f"正文抓取失败: {item.url[:50]}... {e}")
        return item

    async def fetch_batch(self, items: List[NewsItem]) -> List[NewsItem]:
        semaphore = asyncio.Semaphore(5)

        async def _limited_fetch(item):
            async with semaphore:
                return await self.fetch_content(item)

        results = await asyncio.gather(
            *[_limited_fetch(item) for item in items], return_exceptions=True,
        )
        return [items[i] if isinstance(r, Exception) else r for i, r in enumerate(results)]

    def _extract_content(self, html: str) -> Optional[str]:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            for selector in CONTENT_SELECTORS:
                node = soup.select_one(selector)
                if node:
                    text = node.get_text(separator="\n", strip=True)
                    if len(text) > 30:
                        return text
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text() for p in paragraphs if len(p.get_text()) > 10)
            return text if text and len(text) > 30 else None
        except ImportError:
            log.warning("bs4未安装,正文提取不可用")
            return None

    def get_stats(self):
        return {
            "total_fetched": self._fetch_count,
            "success_count": self._success_count,
            "success_rate": self._success_count / self._fetch_count if self._fetch_count > 0 else 0,
        }


content_fetcher = ContentFetcher()
