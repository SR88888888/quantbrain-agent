from typing import List, Tuple
from src.core.config import settings
from src.core.logger import log
from src.llm.wrapper import llm_wrapper
from src.llm.output_parser import (
    extract_reasoning_steps,
    extract_conclusion,
    calculate_reasoning_confidence,
)
from src.llm.prompt_templates import COT_TEMPLATES, SYSTEM_PROMPTS


class ChainOfThought:
    """思维链推理器: 让LLM逐步分析,输出可追溯的推理过程"""

    def __init__(self):
        self.enabled = settings.COT_ENABLED

    def reason(
        self,
        task: str,
        context: str,
        domain: str = "sentiment_analysis",
    ) -> Tuple[str, List[str], float]:
        if not self.enabled:
            return "CoT已禁用", [], 0.5

        cot_template = COT_TEMPLATES.get(domain, COT_TEMPLATES["sentiment_analysis"])
        system_key = domain.split("_")[0] if "_" in domain else domain
        system_prompt = SYSTEM_PROMPTS.get(system_key, SYSTEM_PROMPTS["sentiment"])

        # 将上下文注入模板
        if "{context}" in cot_template:
            prompt = cot_template.format(context=context)
        else:
            prompt = f"{cot_template}\n\n背景信息:\n{context}\n\n任务: {task}"

        response = llm_wrapper.generate(
            prompt, system=system_prompt, max_tokens=2048
        )

        if not response:
            return "分析未完成", [], 0.3

        steps = extract_reasoning_steps(response)
        conclusion = extract_conclusion(response)
        confidence = calculate_reasoning_confidence(steps)

        log.debug(f"CoT完成: {len(steps)}步, 置信度={confidence:.2f}")
        return conclusion, steps, confidence


cot_reasoner = ChainOfThought()