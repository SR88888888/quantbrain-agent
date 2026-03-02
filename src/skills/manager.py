import json
import time
from typing import Dict, Any, List, Optional
from src.core.config import settings
from src.core.logger import log
from src.domain.models import SkillResult
from src.llm.wrapper import llm_wrapper
from src.skills.definitions import SKILL_DEFINITIONS


class SkillManager:

    def __init__(self):
        self.enabled = settings.SKILL_ENABLED
        self._skills = SKILL_DEFINITIONS
        self._stats = {
            sid: {"calls": 0, "success": 0, "total_latency": 0}
            for sid in self._skills
        }

    def execute(self, skill_id: str, params: Dict[str, Any]) -> SkillResult:
        if not self.enabled:
            return SkillResult(skill_id=skill_id, success=False, error="技能系统已禁用")

        skill = self._skills.get(skill_id)
        if not skill:
            return SkillResult(skill_id=skill_id, success=False, error=f"技能不存在: {skill_id}")

        missing = [p for p in skill["required_params"] if p not in params]
        if missing:
            return SkillResult(skill_id=skill_id, success=False, error=f"缺少参数: {missing}")

        start = time.time()
        self._stats[skill_id]["calls"] += 1

        try:
            prompt = skill["prompt"].format(**params)
            result = llm_wrapper.generate_json(
                prompt,
                system=f"你是{skill['name']}专家,只返回JSON。",
            )

            latency_ms = (time.time() - start) * 1000
            self._stats[skill_id]["total_latency"] += latency_ms

            if not result:
                result = self._fallback(skill_id, params)
                if not result:
                    return SkillResult(
                        skill_id=skill_id, success=False,
                        latency_ms=latency_ms, error="JSON解析失败",
                    )

            validated = self._validate(result, skill["output_schema"])
            self._stats[skill_id]["success"] += 1

            return SkillResult(
                skill_id=skill_id,
                success=True,
                output=validated,
                raw_output=json.dumps(validated, ensure_ascii=False),
                confidence=validated.get("confidence", 0.5),
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return SkillResult(
                skill_id=skill_id, success=False,
                latency_ms=latency_ms, error=str(e),
            )

    def execute_chain(self, skill_ids: List[str], params: Dict[str, Any]) -> List[SkillResult]:
        """链式执行: 前一个Skill的输出注入后一个Skill的参数"""
        results = []
        accumulated = params.copy()

        for skill_id in skill_ids:
            result = self.execute(skill_id, accumulated)
            results.append(result)
            if result.success:
                for key, value in result.output.items():
                    accumulated[f"{skill_id}_{key}"] = value

        return results

    def _validate(self, output: Dict, schema: Dict) -> Dict:
        result = output.copy()

        for key in schema.get("required", []):
            if key not in result:
                result[key] = schema.get("defaults", {}).get(key)

        for key, default in schema.get("defaults", {}).items():
            if key not in result:
                result[key] = default

        if "confidence" in result:
            try:
                result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
            except (ValueError, TypeError):
                result["confidence"] = 0.5

        return result

    def _fallback(self, skill_id: str, params: Dict) -> Optional[Dict]:
        """LLM失败时的规则降级"""
        if skill_id == "sentiment_scoring":
            return {"overall_score": 0, "confidence": 0.3, "keywords": []}

        if skill_id == "trend_analysis":
            change = params.get("change_pct", 0)
            trend = "上升" if change > 1 else ("下降" if change < -1 else "横盘")
            return {"trend": trend, "strength": "中", "confidence": 0.3}

        if skill_id == "news_summarize":
            text = params.get("news_text", "")
            return {"summary": text[:50], "confidence": 0.2, "key_points": []}

        return None

    def get_stats(self) -> Dict[str, Any]:
        stats = {}
        for skill_id, s in self._stats.items():
            if s["calls"] > 0:
                stats[skill_id] = {
                    "calls": s["calls"],
                    "success_rate": round(s["success"] / s["calls"], 3),
                    "avg_latency_ms": round(s["total_latency"] / s["calls"], 1),
                }
        return stats


skill_manager = SkillManager()
