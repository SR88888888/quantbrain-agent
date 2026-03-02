import sqlite3
import uuid
from typing import List, Dict, Any
from datetime import datetime
from contextlib import contextmanager
from src.core.config import settings
from src.core.logger import log
from src.domain.models import ReflexionEntry, ReportType


class ReflexionEngine:
    """反思机制: 记录报告质量,积累经验教训"""

    def __init__(self):
        self.enabled = settings.REFLEXION_ENABLED
        self.db_path = settings.REFLEXION_DB_PATH
        self._init_db()

    def _init_db(self):
        if not self.enabled:
            return
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reflexions (
                    reflexion_id TEXT PRIMARY KEY,
                    report_type TEXT NOT NULL,
                    original_quality REAL DEFAULT 0,
                    issues_found TEXT DEFAULT '[]',
                    lesson_learned TEXT DEFAULT '',
                    improvement TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_refl_type ON reflexions(report_type)"
            )

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def record(
        self,
        report_type: ReportType,
        quality: float,
        issues: List[str],
        lesson: str,
        improvement: str,
    ) -> str:
        if not self.enabled:
            return ""

        rid = str(uuid.uuid4())[:8]
        import json

        with self._conn() as conn:
            conn.execute(
                """INSERT INTO reflexions
                (reflexion_id, report_type, original_quality, issues_found,
                 lesson_learned, improvement, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    rid, report_type.value, quality,
                    json.dumps(issues, ensure_ascii=False),
                    lesson, improvement, datetime.now().isoformat(),
                ),
            )
        log.debug(f"反思记录: {report_type.value} 质量={quality:.2f}")
        return rid

    def get_lessons(self, report_type: ReportType = None, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []

        import json

        with self._conn() as conn:
            if report_type:
                rows = conn.execute(
                    """SELECT * FROM reflexions WHERE report_type = ?
                    ORDER BY created_at DESC LIMIT ?""",
                    (report_type.value, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM reflexions ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()

        results = []
        for row in rows:
            results.append({
                "report_type": row["report_type"],
                "quality": row["original_quality"],
                "issues": json.loads(row["issues_found"]),
                "lesson": row["lesson_learned"],
                "improvement": row["improvement"],
            })
        return results

    def get_context_for_writing(self, report_type: ReportType) -> str:
        """为编撰Agent提供历史经验上下文"""
        lessons = self.get_lessons(report_type, limit=3)
        if not lessons:
            return ""

        parts = ["历史反思经验:"]
        for entry in lessons:
            quality_str = f"质量{entry['quality']:.0%}"
            lesson = entry["lesson"][:60] if entry["lesson"] else "无"
            parts.append(f"- {quality_str}: {lesson}")
        return "\n".join(parts)

    def get_stats(self) -> Dict[str, Any]:
        if not self.enabled:
            return {}

        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM reflexions").fetchone()[0]
            avg_quality = conn.execute(
                "SELECT AVG(original_quality) FROM reflexions"
            ).fetchone()[0] or 0
        return {"total_reflexions": total, "avg_quality": round(avg_quality, 3)}


reflexion_engine = ReflexionEngine()
