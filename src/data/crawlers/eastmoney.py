import urllib.request
import urllib.parse
import ssl
import json
import re
import asyncio
import random
from datetime import datetime
from typing import List
from src.core.logger import log
from src.domain.models import NewsItem

ssl._create_default_https_context = ssl._create_unverified_context


class EastmoneyCrawler:

    def __init__(self):
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.timeout = 10

    async def fetch_news(self, symbol: str, limit: int = 5) -> List[NewsItem]:
        return await asyncio.get_event_loop().run_in_executor(
            None, self._fetch_sync, symbol, limit
        )

    def _fetch_sync(self, symbol: str, limit: int) -> List[NewsItem]:
        code = symbol.split(".")[0]
        base_url = "https://search-api-web.eastmoney.com/search/jsonp"

        inner_param = {
            "uid": "",
            "keyword": code,
            "type": ["cmsArticleWebOld"],
            "client": "web",
            "clientType": "web",
            "clientVersion": "curr",
            "param": {
                "cmsArticleWebOld": {
                    "searchScope": "default",
                    "sort": "default",
                    "pageIndex": 1,
                    "pageSize": limit,
                    "preTag": "",
                    "postTag": "",
                }
            },
        }

        query_params = {
            "cb": "jQuery",
            "param": json.dumps(inner_param),
        }
        full_url = f"{base_url}?{urllib.parse.urlencode(query_params)}"

        items = []
        try:
            req = urllib.request.Request(
                full_url,
                headers={
                    "User-Agent": self.user_agent,
                    "Referer": "https://www.eastmoney.com/",
                },
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = response.read()

            text = data.decode("utf-8", "ignore")
            match = re.search(r"jQuery\((.*)\)", text)
            if match:
                js = json.loads(match.group(1))
                articles = js.get("result", {}).get("cmsArticleWebOld", [])
                for art in articles:
                    title = art.get("title", "")
                    title = title.replace("<em>", "").replace("</em>", "")
                    items.append(
                        NewsItem(
                            title=title,
                            url=art.get("url", ""),
                            source="eastmoney",
                            publish_time=datetime.now(),
                        )
                    )
                log.debug(f"东财获取成功: {len(items)}条 {symbol}")
        except Exception as e:
            log.debug(f"东财获取失败 {symbol}: {e}")

        return items


eastmoney_crawler = EastmoneyCrawler()
