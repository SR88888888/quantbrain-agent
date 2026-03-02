import time
from datetime import datetime
from typing import Dict, Any, List
from src.agents.base import BaseAgent
from src.domain.models import AgentRole, AgentOutput, FinalReport, ReportType
from src.reasoning.cot import cot_reasoner
from src.reasoning.reflexion import reflexion_engine
from src.llm.wrapper import llm_wrapper
from src.core.config import settings
from src.core.logger import log
from src.push.service import clean_body

# 优化点1 & 3: 优化Prompt，强制进行深度关联分析
DEEP_REPORT_PROMPT = (
    "你是顶级券商的TMT行业首席分析师。请基于以下数据，撰写一份高质量的《AI产业链晨报》。\n\n"
    "【舆情面】\n{sentiment_section}\n\n"
    "【板块面】\n{sector_section}\n\n"
    "【宏观面】\n{macro_section}\n\n"
    "【核心个股数据】\n{stock_section}\n\n"
    "【历史复盘】\n{reflexion_context}\n\n"
    "日期: {date}\n\n"
    "写作要求(必须严格遵守):\n"
    "1. **拒绝废话**: 不要写“建议投资者关注”、“值得期待”这种套话。每一句都要有信息量。\n"
    "2. **深度个股分析**: 必须对列表中的每一只核心个股进行具体分析。\n"
    "   - 格式: 股票名称(代码): [涨跌] [量能评价] [核心逻辑]\n"
    "   - 逻辑必须结合今日新闻、资金流向和技术形态。例如：“受X消息刺激，放量突破年线”。\n"
    "3. **数据支撑**: 所有的观点必须带数据（如涨跌幅、RSI值、资金净流入额）。\n"
    "4. **排版清晰**: 使用纯文本，段落之间空行。标题使用“一、”、“二、”。\n"
    "5. **篇幅控制**: 全文1000-1500字，短小精悍。\n"
    "6. **操作思路**: 结尾给出明确的今日策略（进攻/防守/观望）。\n\n"
    "请直接输出研报正文。"
)

class WriterAgent(BaseAgent):
    """内容编撰Agent"""

    def __init__(self):
        super().__init__(AgentRole.WRITER)

    async def run(self, context: Dict[str, Any]) -> AgentOutput:
        start = time.time()

        report_type = ReportType(context.get("report_type", "morning"))
        sentiment_data = context.get("sentiment_report", {})
        sector_data = context.get("sector_report", {})
        macro_data = context.get("macro_report", {})
        quotes_data = context.get("quotes", {})

        # 获取历史反思
        reflexion_ctx = reflexion_engine.get_context_for_writing(report_type)

        # 构建各部分内容
        sentiment_section = self._build_sentiment_section(sentiment_data)
        sector_section = self._build_sector_section(sector_data)
        macro_section = self._build_macro_section(macro_data)
        # 优化点1: 动态构建Config中配置的股票列表
        stock_section = self._build_stock_section(quotes_data)

        today = datetime.now().strftime("%Y-%m-%d")

        prompt = DEEP_REPORT_PROMPT.format(
            sentiment_section=sentiment_section,
            sector_section=sector_section,
            macro_section=macro_section,
            stock_section=stock_section,
            reflexion_context=reflexion_ctx or "无",
            date=today,
        )

        system_prompt = "你是专业严肃的金融分析师，风格犀利，数据驱动。"
        
        body = llm_wrapper.generate(
            prompt, system=system_prompt, max_tokens=2500
        )

        body = clean_body(body)

        # 生成摘要
        summary = self._generate_summary(body)
        
        # 提取高亮要点
        highlights = self._extract_highlights(sentiment_data, sector_data)

        report = FinalReport(
            report_type=report_type,
            title=f"QuantBrain早报 ({today})",
            summary=summary,
            body=body,
            highlights=highlights,
        )

        latency = (time.time() - start) * 1000
        log.debug(f"编撰完成 耗时{latency:.0f}ms")

        return self._output(data=report.model_dump(mode="json"))

    def _build_stock_section(self, quotes: dict) -> str:
        """构建配置清单中的股票行情摘要"""
        # 优化点1: 仅分析配置表中的股票
        targets = settings.WATCH_LIST
        if not quotes:
            return "暂无实时行情数据。"
        
        lines = []
        for symbol in targets:
            q = quotes.get(symbol)
            if q:
                price = q.get("price", 0)
                chg = q.get("change_pct", 0)
                vol = q.get("volume", 0)
                # 尝试获取关联的新闻标题（如果quotes里混入了新闻数据的话，这里简化处理）
                # 实际生产中应从context传入个股新闻
                lines.append(
                    f"{q.get('name')}({symbol}): 现价{price} 涨跌{chg:+.2f}% "
                    f"成交{int(vol/100)}手"
                )
            else:
                lines.append(f"股票 {symbol} 暂无行情")
        
        return "\n".join(lines)

    def _build_sentiment_section(self, data: Dict) -> str:
        if not data: return "暂无数据"
        return f"情绪评分: {data.get('overall_score', 0)}\n综述: {data.get('news_summary', '')}"

    def _build_sector_section(self, data: Dict) -> str:
        if not data: return "暂无数据"
        top = [f"{s['sector']}{s['avg_change_pct']:+.2f}%" for s in data.get('top_sectors', [])[:3]]
        return f"领涨板块: {', '.join(top)}\n趋势: {data.get('trend_summary', '')}"

    def _build_macro_section(self, data: Dict) -> str:
        if not data: return "暂无数据"
        return f"关键事件: {'; '.join(data.get('key_events', []))}\n影响: {data.get('impact_assessment', '')}"

    def _generate_summary(self, body: str) -> str:
        if len(body) < 100: return "暂无摘要"
        prompt = f"请用一句话概括以下研报的核心观点(50字内):\n{body[:1000]}"
        return llm_wrapper.generate(prompt, max_tokens=100)

    @staticmethod
    def _extract_highlights(sentiment, sector) -> List[str]:
        hl = []
        if sentiment.get("label") == "positive": hl.append("市场情绪回暖")
        if sector.get("top_sectors"):
            s = sector["top_sectors"][0]
            hl.append(f"{s['sector']}领涨")
        return hl

writer_agent = WriterAgent()
