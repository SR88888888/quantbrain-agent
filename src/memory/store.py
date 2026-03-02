import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from src.core.config import settings
from src.core.logger import log
from src.domain.models import MemoryItem


class MemoryStore:

    def __init__(self):
        self.db_path = settings.MEMORY_DB_PATH
        self.max_items = settings.MEMORY_MAX_ITEMS
        self.decay_factor = settings.MEMORY_DECAY_FACTOR
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL DEFAULT '',
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mem_symbol ON memories(symbol)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mem_type ON memories(memory_type)"
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

    def add(
        self,
        content: str,
        memory_type: str = "observation",
        symbol: str = "",
        importance: float = 0.5,
    ) -> str:
        mid = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        with self._conn() as conn:
            conn.execute(
                """INSERT INTO memories
                (memory_id, symbol, memory_type, content, importance, access_count, created_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
                (mid, symbol, memory_type, content, importance, now, now),
            )

        self._enforce_limit()
        return mid

    def search(
        self,
        symbol: str = None,
        memory_type: str = None,
        limit: int = 10,
    ) -> List[MemoryItem]:
        query = "SELECT * FROM memories WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)

        query += " ORDER BY importance DESC, last_accessed DESC LIMIT ?"
        params.append(limit)

        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._to_item(row) for row in rows]

    def get_context(self, symbol: str = "", max_chars: int = 500) -> str:
        memories = self.search(symbol=symbol or None, limit=8)
        if not memories:
            return ""

        parts = []
        length = 0
        for mem in memories:
            part = f"[{mem.memory_type}] {mem.content}"
            if length + len(part) > max_chars:
                break
            parts.append(part)
            length += len(part)
        return "\n".join(parts)

    def decay_importance(self):
        with self._conn() as conn:
            conn.execute(
                "UPDATE memories SET importance = importance * ?",
                (self.decay_factor,),
            )
            conn.execute("DELETE FROM memories WHERE importance < 0.01")

    def _to_item(self, row: sqlite3.Row) -> MemoryItem:
        return MemoryItem(
            memory_id=row["memory_id"],
            symbol=row["symbol"],
            memory_type=row["memory_type"],
            content=row["content"],
            importance=row["importance"],
            access_count=row["access_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_accessed=datetime.fromisoformat(row["last_accessed"]),
        )

    def _enforce_limit(self):
        with self._conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            if count > self.max_items:
                excess = count - self.max_items
                conn.execute(
                    """DELETE FROM memories WHERE memory_id IN (
                        SELECT memory_id FROM memories ORDER BY importance ASC LIMIT ?
                    )""",
                    (excess,),
                )

    def stats(self) -> Dict[str, Any]:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            avg = conn.execute("SELECT AVG(importance) FROM memories").fetchone()[0] or 0
        return {"total": total, "avg_importance": round(avg, 3)}


memory_store = MemoryStore()
