import time
from typing import Dict, Any, List
from src.agents.base import BaseAgent
from src.domain.models import AgentRole, AgentOutput
from src.data.sources import data_source
from src.data.cleaners.normalizer import clean_news_batch
from src.core.logger import log


class CollectorAgent(BaseAgent):
    """数据采集Agent: 从多源采集新闻、行情、公告"""

    def __init__(self):
        super().__init__(AgentRole.COLLECTOR)

    async def run(self, context: Dict[str, Any]) -> AgentOutput:
        symbols: List[str] = context.get("symbols", [])
        news_limit: int = context.get("news_limit", 3)
        start = time.time()

        if not symbols:
            return self._error_output("未指定股票列表")

        try:
            bundle = await data_source.collect_all(symbols, news_limit)

            cleaned_news = clean_news_batch(bundle.news_list)
            bundle.news_list = cleaned_news

            latency = (time.time() - start) * 1000
            log.debug(
                f"采集完成: 新闻{len(cleaned_news)}条, "
                f"行情{len(bundle.quotes)}只, 耗时{latency:.0f}ms"
            )

            return self._output(
                data={
                    "news_list": [n.model_dump(mode="json") for n in cleaned_news],
                    "quotes": {s: q.model_dump(mode="json") for s, q in bundle.quotes.items()},
                    "announcements": [a.model_dump(mode="json") for a in bundle.announcements],
                    "news_count": len(cleaned_news),
                    "quote_count": len(bundle.quotes),
                },
                data_quality=bundle.data_quality,
            )

        except Exception as e:
            log.error(f"采集Agent异常: {e}")
            return self._error_output(str(e))


collector_agent = CollectorAgent()
