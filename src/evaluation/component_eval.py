import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
from src.core.config import settings
from src.core.logger import log
from src.domain.models import ComponentEvaluation


class ComponentEvaluator:

    def __init__(self):
        self.enabled = settings.COMPONENT_EVAL_ENABLED
        self.log_path = Path(settings.COMPONENT_EVAL_LOG_PATH)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._evaluations: List[ComponentEvaluation] = []

    def evaluate(
        self, component: str, metrics: Dict[str, float], details: str = ""
    ) -> ComponentEvaluation:
        score = sum(metrics.values()) / len(metrics) if metrics else 0

        evaluation = ComponentEvaluation(
            component_name=component,
            eval_type="performance",
            score=score,
            metrics=metrics,
            details=details,
        )

        self._evaluations.append(evaluation)
        self._persist(evaluation)
        return evaluation

    def get_health(self) -> Dict[str, Any]:
        components = {}
        for e in self._evaluations[-200:]:
            components.setdefault(e.component_name, []).append(e.score)

        health = {}
        for name, scores in components.items():
            avg = sum(scores) / len(scores)
            status = "excellent" if avg >= 0.8 else ("good" if avg >= 0.6 else "needs_improvement")
            health[name] = {"score": round(avg, 3), "status": status, "count": len(scores)}

        all_scores = [h["score"] for h in health.values() if h["score"] > 0]
        health["overall"] = {
            "score": round(sum(all_scores) / len(all_scores), 3) if all_scores else 0,
        }
        return health

    def _persist(self, evaluation: ComponentEvaluation):
        if not self.enabled:
            return
        try:
            existing = []
            if self.log_path.exists():
                with open(self.log_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.append(evaluation.model_dump(mode="json"))
            existing = existing[-500:]
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


component_evaluator = ComponentEvaluator()
