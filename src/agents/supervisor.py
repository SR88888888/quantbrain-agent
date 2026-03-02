from typing import Dict, Any, List
from src.domain.models import AgentRole, AgentOutput
from src.core.logger import log


class Supervisor:
    """Supervisor协调器: 分配任务、汇总结果、解决冲突"""

    AGENT_WEIGHTS = {
        AgentRole.SENTIMENT: 0.30,
        AgentRole.SECTOR: 0.35,
        AgentRole.MACRO: 0.20,
        AgentRole.WRITER: 0.10,
        AgentRole.REVIEWER: 0.05,
    }

    def merge_analysis(self, outputs: Dict[AgentRole, AgentOutput]) -> Dict[str, Any]:
        """合并多个分析Agent的结果"""
        merged = {
            "data_quality": 0.0,
            "all_reasoning_chains": {},
            "all_skills_used": [],
        }

        total_weight = 0.0
        weighted_quality = 0.0

        for role, output in outputs.items():
            weight = self.AGENT_WEIGHTS.get(role, 0.2)
            if output.success:
                weighted_quality += output.data_quality * weight
                total_weight += weight

            merged[f"{role.value}_report"] = output.data
            if output.reasoning_chain:
                merged["all_reasoning_chains"][role.value] = output.reasoning_chain
            merged["all_skills_used"].extend(output.skills_used)

        merged["data_quality"] = weighted_quality / total_weight if total_weight > 0 else 0.0
        merged["all_skills_used"] = list(set(merged["all_skills_used"]))

        return merged

    def resolve_conflicts(self, sentiment_label: str, sector_trend: str) -> str:
        """解决舆情和行业分析之间的冲突"""
        if sentiment_label == "positive" and "上升" in sector_trend:
            return "多方共振,信号一致"
        if sentiment_label == "negative" and "下降" in sector_trend:
            return "空方共振,信号一致"
        if sentiment_label != sector_trend:
            return "信号分歧,建议关注"
        return "信号中性"

    def should_revise(self, review_data: Dict) -> bool:
        """根据审核结果判断是否需要返回修改"""
        status = review_data.get("status", "pass")
        return status == "revise"


supervisor = Supervisor()
