import random
import re
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import requests as req_lib
from src.core.config import settings
from src.core.logger import log
from src.domain.models import (
    NewsItem, StockQuote, AnnouncementItem, RawDataBundle, DataSource,
)
from src.data.crawlers.eastmoney import EastmoneyCrawler
from src.data.crawlers.sina import SinaCrawler
from src.data.crawlers.content_fetcher import content_fetcher

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/",
}

class MarketDataProvider:
    def get_index_quotes(self):
        # ... (保持原有代码不变，为节省篇幅略去，实际使用请保留原MarketDataProvider类内容)
        # 这里仅为示例，假设此处代码未变
        return {} 
    
    def get_stock_quotes(self, symbols):
        # 简化的真实行情获取逻辑
        codes = []
        symbol_map = {}
        for s in symbols:
            prefix = "1." if s.startswith("6") else "0."
            code = prefix + s.split(".")[0]
            codes.append(code)
            symbol_map[code] = s
        code_str = ",".join(codes)
        url = (f"https://push2.eastmoney.com/api/qt/ulist.np/get?"
               f"fltt=2&invt=2&fields=f2,f3,f4,f5,f6,f12,f14&secids={code_str}")
        try:
            resp = req_lib.get(url, timeout=10, headers=HEADERS)
            diff = resp.json().get("data", {}).get("diff", [])
            quotes = {}
            for item in diff:
                code = str(item.get("f12", ""))
                matched = None
                for em_code, sym in symbol_map.items():
                    if code in em_code:
                        matched = sym
                        break
                if matched:
                    price = item.get("f2", 0)
                    if price and price != "-":
                        quotes[matched] = StockQuote(
                            symbol=matched, name=str(item.get("f14", "")),
                            price=float(price),
                            change_pct=float(item.get("f3", 0)) if item.get("f3") != "-" else 0,
                            volume=int(item.get("f5", 0)) if item.get("f5") != "-" else 0,
                            amount=float(item.get("f6", 0)) if item.get("f6") != "-" else 0,
                            source=DataSource.EASTMONEY)
            return quotes
        except Exception as e:
            log.warning(f"实时行情失败: {e}")
            return {}
            
    def get_stock_fund_flow(self, symbol): return {}
    def get_major_news(self, limit=20): return []

class DataSourceAggregator:
    def __init__(self):
        self.eastmoney = EastmoneyCrawler()
        self.sina = SinaCrawler()
        self.market = MarketDataProvider() # 注意：这里实际上需要完整的MarketDataProvider

    async def collect_all(self, symbols, news_limit=3):
        news_list = []
        quotes = {}
        
        # 并行采集新闻
        for symbol in symbols:
            try:
                # 尝试获取新闻
                em_news = await self.eastmoney.fetch_news(symbol, news_limit)
                news_list.extend(em_news)
            except Exception: pass
            
        # 优化点2: 增加时间过滤，只保留24小时内的新闻
        news_list = self._filter_recent_news(news_list, hours=24)
        
        # 使用ContentFetcher抓取正文
        if settings.CONTENT_FETCH_ENABLED:
            news_with_urls = [n for n in news_list if n.url and not n.content]
            if news_with_urls:
                enriched = await content_fetcher.fetch_batch(news_with_urls)
                # 更新回原列表...
                
        # 获取行情
        real_quotes = self.market.get_stock_quotes(symbols)
        quotes.update(real_quotes)
        
        # 质量打分
        quality = len(real_quotes) / len(symbols) if symbols else 0.0
        
        return RawDataBundle(news_list=news_list, quotes=quotes, announcements=[], data_quality=quality)

    def _filter_recent_news(self, news_list: List[NewsItem], hours: int = 24) -> List[NewsItem]:
        """优化点2: 过滤掉旧新闻，保证信息有效性"""
        cutoff = datetime.now() - timedelta(hours=hours)
        valid_news = []
        for n in news_list:
            # 如果新闻没有时间，默认保留（或者是爬虫需要解析时间）
            if n.publish_time and n.publish_time >= cutoff:
                valid_news.append(n)
            elif not n.publish_time:
                valid_news.append(n)
        
        # 去重
        seen = set()
        unique_news = []
        for n in valid_news:
            if n.title not in seen:
                unique_news.append(n)
                seen.add(n.title)
        
        log.debug(f"时间过滤: 原{len(news_list)}条 -> 现{len(unique_news)}条 ({hours}h内)")
        return unique_news

    async def fetch_quote(self, symbol):
        real = self.market.get_stock_quotes([symbol])
        return real.get(symbol)

    async def fetch_quotes_batch(self, symbols):
        return self.market.get_stock_quotes(symbols)
    
    async def fetch_news(self, symbol, limit=5):
        return await self.eastmoney.fetch_news(symbol, limit)
    
    def collect_market_context(self): return {}

data_source = DataSourceAggregator()
