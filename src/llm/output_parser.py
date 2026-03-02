import re
from typing import List, Optional, Dict, Any


def extract_reasoning_steps(response: str) -> List[str]:
    """从LLM响应中提取思维链步骤"""
    steps = []

    patterns = [
        r"步骤\s*\d+[:：]\s*(.+?)(?=步骤\s*\d+[:：]|结论[:：]|$)",
        r"\d+[\.、]\s*(.+?)(?=\d+[\.、]|结论|$)",
        r"[-*]\s+(.+?)(?=[-*]\s+|$)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            step = match.strip()
            if step and len(step) > 5:
                steps.append(step)
        if steps:
            break

    if not steps:
        paragraphs = [
            p.strip() for p in response.split("\n")
            if p.strip() and len(p.strip()) > 10
        ]
        steps = paragraphs[:8]

    return steps


def extract_conclusion(response: str) -> str:
    """从LLM响应中提取结论"""
    patterns = [
        r"结论[:：]\s*(.+?)$",
        r"最终[结建][论议][:：]\s*(.+?)$",
        r"综[上合]所述[:，,]\s*(.+?)$",
        r"总结[:：]\s*(.+?)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()[:500]

    if len(response) > 50:
        return response.strip()[:500]

    lines = response.strip().split("\n")
    return lines[-1].strip()[:500] if lines else ""


def extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    """从文本中提取JSON块"""
    cleaned = re.sub(r"^```json\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return __import__("json").loads(cleaned)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return __import__("json").loads(match.group())
        except Exception:
            pass
    return None


def calculate_reasoning_confidence(steps: List[str]) -> float:
    """根据推理步骤质量计算置信度"""
    if not steps:
        return 0.3

    base_score = min(len(steps) / 5.0, 1.0) * 0.4

    quality_indicators = ["因此", "所以", "说明", "表明", "意味着", "可以判断", "分析", "影响"]
    quality_score = 0.0
    for step in steps:
        for indicator in quality_indicators:
            if indicator in step:
                quality_score += 0.05
    quality_score = min(quality_score, 0.4)

    avg_length = sum(len(s) for s in steps) / len(steps)
    length_score = min(avg_length / 80, 0.2)

    return min(base_score + quality_score + length_score, 1.0)