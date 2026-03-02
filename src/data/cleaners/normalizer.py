import re
from typing import List
from src.domain.models import NewsItem


def normalize_text(text: str) -> str:
    """标准化文本: 去除多余空白、HTML标签"""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def deduplicate_news(items: List[NewsItem]) -> List[NewsItem]:
    """按标题去重,保留首次出现的"""
    seen = set()
    result = []
    for item in items:
        key = normalize_text(item.title)[:50]
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def filter_low_quality(items: List[NewsItem], min_content_len: int = 20) -> List[NewsItem]:
    """过滤内容过短的新闻"""
    return [
        item for item in items
        if len(item.content) >= min_content_len or len(item.title) >= 10
    ]


def clean_news_batch(items: List[NewsItem]) -> List[NewsItem]:
    """完整清洗流程"""
    for item in items:
        item.title = normalize_text(item.title)
        item.content = normalize_text(item.content)

    items = deduplicate_news(items)
    items = filter_low_quality(items)
    return items
