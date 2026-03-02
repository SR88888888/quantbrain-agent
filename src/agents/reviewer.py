import time
from typing import Dict, Any
from src.agents.base import BaseAgent
from src.domain.models import AgentRole, AgentOutput, ReviewResult, ReviewStatus
from src.reasoning.cot import cot_reasoner
from src.core.logger import log


class ReviewerAgent(BaseAgent):
    """质量审核Agent: 事实核查、逻辑校验、表述规范"""

    def __init__(self):
        super().__init__(AgentRole.REVIEWER)

    async def run(self, context: Dict[str, Any]) -> AgentOutput:
        start = time.time()

        report_data = context.get("final_report", {})
        body = report_data.get("body", "")
        title = report_data.get("title", "")

        if not body:
            return self._output(
                data=ReviewResult(status=ReviewStatus.REJECT, issues=["报告内容为空"]).model_dump(),
            )

        # CoT逐步审核
        review_context = f"报告标题: {title}\n\n报告内容:\n{body[:1500]}"
        conclusion, steps, confidence = cot_reasoner.reason(
            task="审核此金融研报的质量,检查事实、逻辑、表述",
            context=review_context,
            domain="quality_review",
        )

        # 规则检查
        rule_issues = self._rule_check(body)

        # 合并问题
        all_issues = rule_issues
        if "需修改" in conclusion or "问题" in conclusion:
            all_issues.append(f"审核意见: {conclusion[:100]}")

        # 判断审核结果
        if len(all_issues) == 0:
            status = ReviewStatus.PASS
        elif len(all_issues) <= 2:
            status = ReviewStatus.REVISE
        else:
            status = ReviewStatus.REVISE

        result = ReviewResult(
            status=status,
            issues=all_issues,
            suggestions=[conclusion[:200]] if conclusion else [],
        )

        latency = (time.time() - start) * 1000
        log.debug(f"审核完成: {status.value}, {len(all_issues)}个问题, 耗时{latency:.0f}ms")

        return self._output(
            data=result.model_dump(),
            reasoning_chain=steps,
        )

    @staticmethod
    def _rule_check(body: str) -> list:
        issues = []

        if len(body) < 50:
            issues.append("报告内容过短")
        if len(body) > 5000:
            issues.append("报告内容过长")

        sensitive_words = ["保证收益", "稳赚不赔", "内幕", "必涨"]
        for word in sensitive_words:
            if word in body:
                issues.append(f"包含敏感表述: {word}")

        if body.count("。") < 2 and len(body) > 100:
            issues.append("缺少标点断句")

        return issues


reviewer_agent = ReviewerAgent()
