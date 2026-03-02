import urllib.request
import ssl
import asyncio
import random
from datetime import datetime
from typing import List
from src.core.logger import log
from src.domain.models import NewsItem

ssl._create_default_https_context = ssl._create_unverified_context


class SinaCrawler:

    def __init__(self):
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        self.timeout = 10

    async def fetch_news(self, symbol: str, limit: int = 5) -> List[NewsItem]:
        return await asyncio.get_event_loop().run_in_executor(
            None, self._fetch_sync, symbol, limit
        )

    def _fetch_sync(self, symbol: str, limit: int) -> List[NewsItem]:
        parts = symbol.split(".")
        if len(parts) == 2:
            code = parts[1].lower() + parts[0]
        else:
            code = ("sh" + symbol) if symbol.startswith("6") else ("sz" + symbol)

        url = (
            f"https://vip.stock.finance.sina.com.cn/corp/go.php/"
            f"vCB_AllNewsStock/symbol/{code}.phtml"
        )

        items = []
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Referer": "https://finance.sina.com.cn/",
                },
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = response.read()

            text = data.decode("gbk", "ignore")

            try:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(text, "lxml")
                for link in soup.select("div.datelist ul a")[:limit]:
                    title = link.get_text().strip()
                    href = link.get("href", "")
                    if title:
                        items.append(
                            NewsItem(
                                title=title,
                                url=href,
                                source="sina",
                                publish_time=datetime.now(),
                            )
                        )
                log.debug(f"新浪获取成功: {len(items)}条 {symbol}")
            except ImportError:
                log.warning("bs4未安装,新浪爬虫不可用")
        except Exception as e:
            log.debug(f"新浪获取失败 {symbol}: {e}")

        return items


sina_crawler = SinaCrawler()
