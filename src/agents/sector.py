import time
from typing import Dict, Any, List
from src.agents.base import BaseAgent
from src.domain.models import AgentRole, AgentOutput, SectorReport, DataSource
from src.reasoning.cot import cot_reasoner
from src.reasoning.react import react_engine
from src.skills.manager import skill_manager
from src.memory.knowledge_graph import knowledge_graph
from src.core.logger import log


class SectorAgent(BaseAgent):
    """行业分析Agent: 分析板块动态、个股异动、资金流向"""

    def __init__(self):
        super().__init__(AgentRole.SECTOR)

    async def run(self, context: Dict[str, Any]) -> AgentOutput:
        start = time.time()
        skills_used = []
        data_quality = context.get("data_quality", 1.0)

        quotes: Dict[str, Dict] = context.get("quotes", {})
        if not quotes:
            return self._output(
                data=SectorReport().model_dump(),
                data_quality=0.3,
            )

        # 板块分类和排名
        sector_perf = self._group_by_sector(quotes)
        abnormal = self._find_abnormal(quotes)

        # 对每只有行情的股票使用Skill做趋势分析
        trend_results = []
        for symbol, q in quotes.items():
            result = skill_manager.execute("trend_analysis", {
                "symbol": symbol,
                "price": q.get("price", 0),
                "change_pct": q.get("change_pct", 0),
                "volume": q.get("volume", 0),
            })
            if result.success:
                skills_used.append("trend_analysis")
                trend_results.append({
                    "symbol": symbol,
                    "trend": result.output.get("trend", "横盘"),
                    "strength": result.output.get("strength", "中"),
                })

        # 使用知识图谱分析产业链联动
        chain_analysis = self._analyze_industry_chain(quotes)

        # 检查数据源质量
        mock_count = sum(1 for q in quotes.values() if q.get("source") == DataSource.MOCK.value)
        if mock_count > len(quotes) * 0.5:
            data_quality *= 0.6

        # CoT深度分析
        analysis_data = (
            f"板块表现: {self._format_sectors(sector_perf)}\n"
            f"异动个股: {self._format_abnormal(abnormal)}\n"
            f"趋势信号: {self._format_trends(trend_results)}\n"
            f"产业链分析: {chain_analysis}"
        )

        # 对异动股票使用ReAct+MCP深度分析
        react_answer = None
        if react_engine.enabled and abnormal:
            top_ab = abnormal[0]
            try:
                react_answer, react_steps = await react_engine.reason_with_mcp(
                    task=f"分析{top_ab.get('name', '')}({top_ab.get('symbol', '')})异动原因",
                    context=f"涨跌幅: {top_ab.get('change_pct', 0):+.2f}%\n{analysis_data[:500]}",
                )
                if react_answer:
                    analysis_data += f"\nReAct深度分析: {react_answer[:300]}"
                    skills_used.append("react_reasoning")
            except Exception as e:
                log.debug(f"ReAct分析跳过: {e}")

        conclusion, steps, confidence = cot_reasoner.reason(
            task="分析今日板块轮动和个股异动情况",
            context=analysis_data,
            domain="sector_analysis",
        )

        report = SectorReport(
            top_sectors=sector_perf[:5],
            abnormal_stocks=abnormal[:5],
            trend_summary=conclusion,
            confidence=confidence,
            reasoning_chain=steps,
        )

        latency = (time.time() - start) * 1000
        log.debug(f"行业分析完成: {len(sector_perf)}个板块 耗时{latency:.0f}ms")

        return self._output(
            data=report.model_dump(),
            reasoning_chain=steps,
            skills_used=list(set(skills_used)),
            data_quality=data_quality,
        )

    def _group_by_sector(self, quotes: Dict[str, Dict]) -> List[Dict]:
        sector_map: Dict[str, List[float]] = {}
        for symbol, q in quotes.items():
            info = knowledge_graph.get_stock_info(symbol)
            sector = info.get("sector", "其他")
            sector_map.setdefault(sector, []).append(q.get("change_pct", 0))

        result = []
        for sector, changes in sector_map.items():
            avg_change = sum(changes) / len(changes) if changes else 0
            result.append({
                "sector": sector,
                "avg_change_pct": round(avg_change, 2),
                "stock_count": len(changes),
            })

        result.sort(key=lambda x: x["avg_change_pct"], reverse=True)
        return result

    @staticmethod
    def _find_abnormal(quotes: Dict[str, Dict]) -> List[Dict]:
        abnormal = []
        for symbol, q in quotes.items():
            change = abs(q.get("change_pct", 0))
            if change > 3:
                abnormal.append({
                    "symbol": symbol,
                    "name": q.get("name", symbol),
                    "change_pct": q.get("change_pct", 0),
                    "reason": "涨幅较大" if q.get("change_pct", 0) > 0 else "跌幅较大",
                })
        abnormal.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
        return abnormal

    @staticmethod
    def _format_sectors(sectors: List[Dict]) -> str:
        return ", ".join(
            f"{s['sector']}({s['avg_change_pct']:+.2f}%)" for s in sectors[:5]
        )

    @staticmethod
    def _format_abnormal(stocks: List[Dict]) -> str:
        return ", ".join(
            f"{s['name']}({s['change_pct']:+.2f}%)" for s in stocks[:5]
        )

    @staticmethod
    def _format_trends(trends: List[Dict]) -> str:
        return ", ".join(
            f"{t['symbol']}:{t['trend']}" for t in trends[:5]
        )

    def _analyze_industry_chain(self, quotes: Dict[str, Dict]) -> str:
        """利用知识图谱分析产业链联动"""
        chain_signals = []
        for symbol in quotes:
            related = knowledge_graph.get_related_stocks(symbol)
            if not related:
                continue
            info = knowledge_graph.get_stock_info(symbol)
            my_change = quotes[symbol].get("change_pct", 0)
            for rel in related:
                rel_sym = rel["symbol"]
                if rel_sym in quotes:
                    rel_change = quotes[rel_sym].get("change_pct", 0)
                    if abs(my_change - rel_change) > 3:
                        chain_signals.append(
                            f"{info.get('name', symbol)}与{rel.get('name', rel_sym)}"
                            f"({rel.get('relation_type', '关联')})走势分化: "
                            f"{my_change:+.2f}% vs {rel_change:+.2f}%"
                        )
                    elif my_change > 2 and rel_change > 2:
                        chain_signals.append(
                            f"{info.get('name', symbol)}与{rel.get('name', rel_sym)}"
                            f"({rel.get('relation_type', '关联')})同步走强"
                        )
        if not chain_signals:
            return "产业链整体联动不明显"
        return "; ".join(chain_signals[:5])


sector_agent = SectorAgent()
