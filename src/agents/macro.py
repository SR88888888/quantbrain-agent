import time
from typing import Dict, Any
from src.agents.base import BaseAgent
from src.domain.models import AgentRole, AgentOutput, MacroReport
from src.reasoning.cot import cot_reasoner
from src.core.logger import log


class MacroAgent(BaseAgent):
    """宏观解读Agent: 解读政策、经济数据、国际形势"""

    def __init__(self):
        super().__init__(AgentRole.MACRO)

    async def run(self, context: Dict[str, Any]) -> AgentOutput:
        start = time.time()
        data_quality = context.get("data_quality", 1.0)

        news_list = context.get("news_list", [])

        # 筛选宏观相关新闻
        macro_news = self._filter_macro_news(news_list)

        if not macro_news:
            report = MacroReport(
                policy_summary="暂无重要宏观政策变化",
                economic_outlook="市场整体平稳运行",
                confidence=0.3,
            )
            return self._output(data=report.model_dump(), data_quality=0.4)

        macro_context_parts = []
        for n in macro_news[:5]:
            title = n.get("title", "")
            nc = n.get("content", "")
            if nc and len(nc) > 30:
                macro_context_parts.append(f"- {title}: {nc[:200]}")
            else:
                macro_context_parts.append(f"- {title}")
        macro_context = "\n".join(macro_context_parts)

        conclusion, steps, confidence = cot_reasoner.reason(
            task="解读当前宏观政策和经济形势对A股的影响",
            context=f"宏观相关新闻:\n{macro_context}",
            domain="macro_analysis",
        )

        key_events = [n["title"] for n in macro_news[:3]]

        report = MacroReport(
            policy_summary=self._extract_policy(conclusion),
            economic_outlook=conclusion,
            key_events=key_events,
            impact_assessment=self._assess_impact(macro_news),
            confidence=confidence,
            reasoning_chain=steps,
        )

        latency = (time.time() - start) * 1000
        log.debug(f"宏观分析完成: {len(macro_news)}条相关新闻 耗时{latency:.0f}ms")

        return self._output(
            data=report.model_dump(),
            reasoning_chain=steps,
            data_quality=data_quality,
        )

    @staticmethod
    def _filter_macro_news(news_list: list) -> list:
        macro_keywords = [
            "央行", "利率", "GDP", "CPI", "PMI", "降准", "降息",
            "财政", "货币", "监管", "政策", "外汇", "美联储",
            "关税", "贸易", "出口", "进口", "国务院",
            # AI产业链宏观
            "芯片制裁", "出口管制", "实体清单", "算力", "新基建",
            "人工智能", "AI政策", "科技自立", "信创", "国产替代",
            "半导体", "集成电路", "大基金", "科创板",
            "数字经济", "数据要素", "新质生产力",
            "英伟达", "台积电", "ASML", "光刻机",
        ]
        result = []
        for n in news_list:
            if not isinstance(n, dict):
                continue
            text = n.get("title", "") + n.get("content", "")
            if any(kw in text for kw in macro_keywords):
                result.append(n)
        return result

    @staticmethod
    def _extract_policy(text: str) -> str:
        if len(text) > 200:
            return text[:200]
        return text

    @staticmethod
    def _assess_impact(news: list) -> str:
        positive_kw = ["利好", "宽松", "降息", "刺激", "支持", "突破", "国产替代", "自主可控", "大基金"]
        negative_kw = ["收紧", "加息", "监管", "限制", "风险", "制裁", "封锁", "禁令", "实体清单"]

        pos = neg = 0
        for n in news:
            text = n.get("title", "")
            for kw in positive_kw:
                pos += text.count(kw)
            for kw in negative_kw:
                neg += text.count(kw)

        if pos > neg:
            return "整体偏利好"
        elif neg > pos:
            return "整体偏谨慎"
        return "影响中性"


macro_agent = MacroAgent()
