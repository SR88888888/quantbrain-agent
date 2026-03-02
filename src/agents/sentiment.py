import time
from typing import Dict, Any
from src.agents.base import BaseAgent
from src.domain.models import AgentRole, AgentOutput, SentimentReport, NewsItem
from src.reasoning.cot import cot_reasoner
from src.skills.manager import skill_manager
from src.core.logger import log


class SentimentAgent(BaseAgent):
    """舆情分析Agent: 使用CoT逐步分析新闻情绪"""

    def __init__(self):
        super().__init__(AgentRole.SENTIMENT)

    async def run(self, context: Dict[str, Any]) -> AgentOutput:
        start = time.time()
        skills_used = []
        data_quality = context.get("data_quality", 1.0)

        news_data = context.get("news_list", [])
        if not news_data:
            return self._output(
                data=SentimentReport().model_dump(),
                data_quality=0.3,
            )

        news_titles = "\n".join(
            [f"- {n['title']}" for n in news_data[:10] if isinstance(n, dict)]
        )
        # 利用正文内容(由ContentFetcher抓取)做更深入分析
        news_contents_parts = []
        for n in news_data[:8]:
            if not isinstance(n, dict):
                continue
            nc = n.get("content", "")
            if nc and len(nc) > 30:
                news_contents_parts.append(f"[{n['title']}] {nc[:200]}")
            else:
                news_contents_parts.append(f"[{n['title']}] (无正文)")
        news_contents = "\n".join(news_contents_parts)

        # 正文覆盖率影响数据质量
        content_coverage = sum(
            1 for n in news_data if isinstance(n, dict) and len(n.get("content", "")) > 30
        ) / max(len(news_data), 1)
        if content_coverage < 0.3:
            data_quality *= 0.8

        # 使用Skill进行情绪评分
        symbols = list(set(n.get("source", "") for n in news_data))
        skill_result = skill_manager.execute("sentiment_scoring", {
            "symbol": ", ".join(symbols) if symbols else "AI产业链",
            "news_titles": news_titles[:500],
        })

        skill_score = 0
        if skill_result.success:
            skills_used.append("sentiment_scoring")
            skill_score = skill_result.output.get("overall_score", 0)

        # 使用CoT进行深度分析
        analysis_context = f"新闻标题:\n{news_titles}\n\n新闻详情(含正文):\n{news_contents[:800]}"
        conclusion, steps, confidence = cot_reasoner.reason(
            task="判断当前市场舆情方向和热点话题",
            context=analysis_context,
            domain="sentiment_analysis",
        )

        # 关键词提取(规则兜底)
        pos_kw, neg_kw = self._extract_keywords(news_titles)

        # 综合评分
        rule_score = len(pos_kw) * 10 - len(neg_kw) * 10
        overall = (skill_score * 0.6 + rule_score * 0.4) if skill_result.success else rule_score

        if overall > 15:
            label = "positive"
        elif overall < -15:
            label = "negative"
        else:
            label = "neutral"

        report = SentimentReport(
            overall_score=overall,
            label=label,
            hot_topics=self._extract_topics(news_titles),
            positive_keywords=pos_kw,
            negative_keywords=neg_kw,
            news_summary=conclusion,
            confidence=confidence,
            reasoning_chain=steps,
        )

        latency = (time.time() - start) * 1000
        log.debug(f"舆情分析完成: {label} 得分={overall:.0f} 耗时{latency:.0f}ms")

        return self._output(
            data=report.model_dump(),
            reasoning_chain=steps,
            skills_used=skills_used,
            data_quality=data_quality,
        )

    @staticmethod
    def _extract_keywords(text: str):
        pos_kw_map = {
            "突破": 2, "利好": 2, "增长": 1.5, "新高": 2, "获批": 1.5,
            "预增": 2, "上涨": 1, "大模型": 1.5, "发布": 1, "算力": 1,
            "合作": 1, "订单": 2, "国产替代": 2, "自主可控": 1.5,
            "融资": 1, "投产": 2, "流片": 2, "量产": 2,
        }
        neg_kw_map = {
            "下跌": 2, "亏损": 2, "立案": 3, "警示": 2, "减持": 1.5,
            "暴跌": 3, "利空": 2, "制裁": 3, "禁令": 3, "封锁": 2,
            "出口管制": 3, "实体清单": 3, "估值过高": 1.5, "泡沫": 2,
        }

        pos = [kw for kw in pos_kw_map if kw in text]
        neg = [kw for kw in neg_kw_map if kw in text]
        return pos, neg

    @staticmethod
    def _extract_topics(text: str):
        topic_keywords = {
            "大模型": "大模型", "GPT": "大模型", "LLM": "大模型",
            "芯片": "AI芯片", "GPU": "AI芯片", "算力": "AI芯片",
            "寒武纪": "AI芯片", "英伟达": "AI芯片",
            "机器人": "具身智能", "人形机器人": "具身智能",
            "自动驾驶": "智能驾驶", "智能座舱": "智能驾驶",
            "AI安全": "AI安全", "数据安全": "AI安全",
            "信创": "信创", "国产替代": "信创",
            "AIGC": "AIGC", "AI办公": "AIGC",
            "AI应用": "AI应用", "智慧教育": "AI应用",
            "算力中心": "算力基建", "智算": "算力基建",
            "端侧AI": "端侧AI", "边缘计算": "端侧AI",
        }
        found = set()
        for kw, topic in topic_keywords.items():
            if kw in text:
                found.add(topic)
        return list(found)[:5]


sentiment_agent = SentimentAgent()
