"""
LangGraph每日研报工作流

流程: 调度 -> 采集 -> [舆情|行业|宏观](并行) -> 协调 -> 编撰 -> 审核 -> 推送 -> 反思
"""
import time
import asyncio
from typing import TypedDict, Dict, Any, List, Optional, Annotated
from operator import add
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.core.config import settings
from src.core.logger import log
from src.domain.models import (
    AgentRole, AgentOutput, FinalReport, ReviewStatus, ReportType,
)
from src.agents.collector import collector_agent
from src.agents.sentiment import sentiment_agent
from src.agents.sector import sector_agent
from src.agents.macro import macro_agent
from src.agents.writer import writer_agent
from src.agents.reviewer import reviewer_agent
from src.agents.supervisor import supervisor
from src.push.service import push_service
from src.memory.store import memory_store
from src.reasoning.reflexion import reflexion_engine
from src.evaluation.component_eval import component_evaluator


class WorkflowState(TypedDict):
    symbols: List[str]
    report_type: str
    news_list: List[Dict]
    quotes: Dict[str, Dict]
    data_quality: float
    sentiment_report: Dict
    sector_report: Dict
    macro_report: Dict
    final_report: Dict
    review_result: Dict
    revision_count: int
    messages: Annotated[List[str], add]


async def collect_node(state: WorkflowState) -> Dict[str, Any]:
    """数据采集节点"""
    start = time.time()
    output = await collector_agent.run({
        "symbols": state["symbols"],
        "news_limit": 3,
    })

    component_evaluator.evaluate("collector", {
        "data_quality": output.data_quality,
        "latency": max(0, 1 - (time.time() - start) / 10),
    })

    return {
        "news_list": output.data.get("news_list", []),
        "quotes": output.data.get("quotes", {}),
        "data_quality": output.data_quality,
        "messages": [f"采集完成: 新闻{output.data.get('news_count', 0)}条"],
    }


async def sentiment_node(state: WorkflowState) -> Dict[str, Any]:
    """舆情分析节点"""
    output = await sentiment_agent.run({
        "news_list": state["news_list"],
        "data_quality": state["data_quality"],
    })

    component_evaluator.evaluate("sentiment_agent", {
        "confidence": output.data.get("confidence", 0),
        "data_quality": output.data_quality,
    })

    return {
        "sentiment_report": output.data,
        "messages": [f"舆情分析: {output.data.get('label', 'neutral')}"],
    }


async def sector_node(state: WorkflowState) -> Dict[str, Any]:
    """行业分析节点"""
    output = await sector_agent.run({
        "quotes": state["quotes"],
        "data_quality": state["data_quality"],
    })

    component_evaluator.evaluate("sector_agent", {
        "confidence": output.data.get("confidence", 0),
        "data_quality": output.data_quality,
    })

    return {
        "sector_report": output.data,
        "messages": [f"行业分析: {len(output.data.get('top_sectors', []))}个板块"],
    }


async def macro_node(state: WorkflowState) -> Dict[str, Any]:
    """宏观分析节点"""
    output = await macro_agent.run({
        "news_list": state["news_list"],
        "data_quality": state["data_quality"],
    })

    return {
        "macro_report": output.data,
        "messages": [f"宏观分析: {output.data.get('impact_assessment', 'neutral')}"],
    }


async def coordinate_node(state: WorkflowState) -> Dict[str, Any]:
    """Supervisor协调节点: 合并分析结果"""
    outputs = {
        AgentRole.SENTIMENT: AgentOutput(
            agent_role=AgentRole.SENTIMENT, data=state["sentiment_report"],
            data_quality=state["data_quality"],
        ),
        AgentRole.SECTOR: AgentOutput(
            agent_role=AgentRole.SECTOR, data=state["sector_report"],
            data_quality=state["data_quality"],
        ),
        AgentRole.MACRO: AgentOutput(
            agent_role=AgentRole.MACRO, data=state["macro_report"],
            data_quality=state["data_quality"],
        ),
    }

    merged = supervisor.merge_analysis(outputs)
    return {
        "sentiment_report": merged.get("sentiment_report", state["sentiment_report"]),
        "sector_report": merged.get("sector_report", state["sector_report"]),
        "macro_report": merged.get("macro_report", state["macro_report"]),
        "data_quality": merged.get("data_quality", state["data_quality"]),
        "messages": [f"协调完成: 数据质量{merged.get('data_quality', 0):.0%}"],
    }


async def write_node(state: WorkflowState) -> Dict[str, Any]:
    """编撰节点"""
    output = await writer_agent.run({
        "report_type": state["report_type"],
        "sentiment_report": state["sentiment_report"],
        "sector_report": state["sector_report"],
        "macro_report": state["macro_report"],
        "quotes": state.get("quotes", {}),
    })

    component_evaluator.evaluate("writer_agent", {
        "has_content": 1.0 if output.data.get("body") else 0.0,
    })

    return {
        "final_report": output.data,
        "messages": [f"编撰完成: {output.data.get('title', '')}"],
    }


async def review_node(state: WorkflowState) -> Dict[str, Any]:
    """审核节点"""
    output = await reviewer_agent.run({
        "final_report": state["final_report"],
    })

    return {
        "review_result": output.data,
        "messages": [f"审核结果: {output.data.get('status', 'unknown')}"],
    }


def should_revise(state: WorkflowState) -> str:
    """条件路由: 审核不通过且修改次数未超限则返回编撰"""
    review = state.get("review_result", {})
    revision_count = state.get("revision_count", 0)

    if review.get("status") == ReviewStatus.REVISE.value and revision_count < 2:
        return "revise"
    return "publish"


async def revise_node(state: WorkflowState) -> Dict[str, Any]:
    """修改节点: 增加修改计数后重新编撰"""
    return {
        "revision_count": state.get("revision_count", 0) + 1,
        "messages": [f"返回修改: 第{state.get('revision_count', 0) + 1}次"],
    }


async def publish_node(state: WorkflowState) -> Dict[str, Any]:
    """推送节点"""
    report_data = state.get("final_report", {})
    if not report_data:
        return {"messages": ["无内容可推送"]}

    report = FinalReport(**report_data)

    await push_service.save_local(report)
    await push_service.push(report)

    # 记忆存储
    memory_store.add(
        content=f"{report.title}: {report.summary[:100]}",
        memory_type="report",
        importance=0.7,
    )

    return {"messages": [f"推送完成: {report.title}"]}


async def reflexion_node(state: WorkflowState) -> Dict[str, Any]:
    """反思节点: 记录本次生成质量"""
    report_type = ReportType(state.get("report_type", "closing"))
    review = state.get("review_result", {})
    issues = review.get("issues", [])
    revision_count = state.get("revision_count", 0)

    quality = 1.0
    if issues:
        quality -= len(issues) * 0.15
    if revision_count > 0:
        quality -= revision_count * 0.1
    quality = max(0.0, quality)

    lesson = ""
    if issues:
        lesson = f"问题: {'; '.join(issues[:3])}"

    reflexion_engine.record(
        report_type=report_type,
        quality=quality,
        issues=issues,
        lesson=lesson,
        improvement=review.get("suggestions", [""])[0] if review.get("suggestions") else "",
    )

    return {"messages": [f"反思记录: 质量{quality:.0%}"]}


def build_daily_workflow() -> StateGraph:
    wf = StateGraph(WorkflowState)

    wf.add_node("collect", collect_node)
    wf.add_node("sentiment", sentiment_node)
    wf.add_node("sector", sector_node)
    wf.add_node("macro", macro_node)
    wf.add_node("coordinate", coordinate_node)
    wf.add_node("write", write_node)
    wf.add_node("review", review_node)
    wf.add_node("revise", revise_node)
    wf.add_node("publish", publish_node)
    wf.add_node("reflexion", reflexion_node)

    wf.set_entry_point("collect")

    # 采集后并行进入三个分析节点
    wf.add_edge("collect", "sentiment")
    wf.add_edge("collect", "sector")
    wf.add_edge("collect", "macro")

    # 三个分析节点汇聚到协调节点
    wf.add_edge("sentiment", "coordinate")
    wf.add_edge("sector", "coordinate")
    wf.add_edge("macro", "coordinate")

    # 协调 -> 编撰 -> 审核
    wf.add_edge("coordinate", "write")
    wf.add_edge("write", "review")

    # 审核的条件路由
    wf.add_conditional_edges(
        "review",
        should_revise,
        {"revise": "revise", "publish": "publish"},
    )
    wf.add_edge("revise", "write")

    # 推送 -> 反思 -> 结束
    wf.add_edge("publish", "reflexion")
    wf.add_edge("reflexion", END)

    return wf


checkpointer = MemorySaver()
daily_workflow = build_daily_workflow()
daily_app = daily_workflow.compile(checkpointer=checkpointer)


async def generate_report(
    symbols: List[str] = None,
    report_type: str = "closing",
) -> Dict[str, Any]:
    """执行完整的研报生成工作流"""
    symbols = symbols or settings.WATCH_LIST
    log.warning(f"启动研报生成: {report_type} 监控{len(symbols)}只")

    inputs: WorkflowState = {
        "symbols": symbols,
        "report_type": report_type,
        "news_list": [],
        "quotes": {},
        "data_quality": 0.0,
        "sentiment_report": {},
        "sector_report": {},
        "macro_report": {},
        "final_report": {},
        "review_result": {},
        "revision_count": 0,
        "messages": [],
    }

    config = {"configurable": {"thread_id": f"{report_type}_{int(time.time())}"}}

    start = time.time()
    result = await daily_app.ainvoke(inputs, config=config)
    latency = (time.time() - start) * 1000

    component_evaluator.evaluate("workflow", {
        "latency": max(0, 1 - latency / 30000),
        "data_quality": result.get("data_quality", 0),
    })

    report = result.get("final_report", {})
    log.warning(
        f"研报生成完成: {report.get('title', '')} "
        f"耗时{latency / 1000:.1f}s"
    )

    return result
