import sqlite3
import json
from typing import List, Dict, Any
from datetime import datetime
from contextlib import contextmanager
from src.core.config import settings
from src.core.logger import log


class KnowledgeGraph:

    def __init__(self):
        self.db_path = settings.KNOWLEDGE_GRAPH_PATH
        self.enabled = settings.KNOWLEDGE_GRAPH_ENABLED
        self._init_db()
        self._seed_data()

    def _init_db(self):
        if not self.enabled:
            return
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_knowledge (
                    symbol TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    industry TEXT,
                    sector TEXT,
                    concepts TEXT,
                    characteristics TEXT,
                    market_cap TEXT,
                    updated_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_symbol TEXT NOT NULL,
                    target_symbol TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    UNIQUE(source_symbol, target_symbol, relation_type)
                )
            """)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _seed_data(self):
        if not self.enabled:
            return

        stocks = {
            "002230.SZ": {
                "name": "科大讯飞", "industry": "人工智能", "sector": "AI应用",
                "concepts": ["大模型", "AI语音", "智慧教育", "NLP", "星火大模型"],
                "characteristics": ["AI龙头", "技术壁垒高", "To B+To C双轮驱动"],
                "market_cap": "大盘",
            },
            "300474.SZ": {
                "name": "景嘉微", "industry": "GPU芯片", "sector": "AI芯片",
                "concepts": ["国产GPU", "信创", "军工电子", "芯片设计"],
                "characteristics": ["国产GPU稀缺标的", "军民融合", "高研发投入"],
                "market_cap": "中盘",
            },
            "688111.SH": {
                "name": "金山办公", "industry": "办公软件", "sector": "AI应用",
                "concepts": ["AI办公", "WPS AI", "信创", "AIGC", "国产替代"],
                "characteristics": ["SaaS模式", "用户基数大", "AI赋能增长"],
                "market_cap": "大盘",
            },
            "688047.SH": {
                "name": "龙芯中科", "industry": "CPU芯片", "sector": "AI芯片",
                "concepts": ["国产CPU", "信创", "自主可控", "LoongArch架构"],
                "characteristics": ["自主指令集", "信创核心", "生态建设中"],
                "market_cap": "中盘",
            },
            "002415.SZ": {
                "name": "海康威视", "industry": "智能安防", "sector": "AI视觉",
                "concepts": ["AI视觉", "机器人", "智能制造", "数字化转型"],
                "characteristics": ["全球安防龙头", "研发驱动", "多元化布局"],
                "market_cap": "超大盘",
            },
            "688256.SH": {
                "name": "寒武纪", "industry": "AI芯片", "sector": "AI芯片",
                "concepts": ["AI训练芯片", "推理芯片", "智能计算", "国产替代英伟达"],
                "characteristics": ["纯正AI芯片", "高研发亏损", "国产算力核心"],
                "market_cap": "大盘",
            },
            "603019.SH": {
                "name": "中科曙光", "industry": "服务器/算力", "sector": "AI算力",
                "concepts": ["AI算力", "智算中心", "海光信息", "国产服务器"],
                "characteristics": ["算力基础设施", "参股海光", "政务云龙头"],
                "market_cap": "大盘",
            },
            "688396.SH": {
                "name": "华峰测控", "industry": "半导体设备", "sector": "AI芯片",
                "concepts": ["芯片测试", "半导体设备", "国产替代", "模拟芯片测试"],
                "characteristics": ["半导体测试龙头", "高毛利", "受益AI芯片放量"],
                "market_cap": "中盘",
            },
            "300496.SZ": {
                "name": "中科创达", "industry": "智能操作系统", "sector": "AI应用",
                "concepts": ["端侧AI", "智能座舱", "机器人OS", "边缘计算"],
                "characteristics": ["嵌入式OS龙头", "汽车智能化", "端侧AI先行者"],
                "market_cap": "中盘",
            },
            "688561.SH": {
                "name": "奇安信", "industry": "网络安全", "sector": "AI安全",
                "concepts": ["AI安全", "数据安全", "信创安全", "零信任"],
                "characteristics": ["安全龙头", "高增长", "AI安全新赛道"],
                "market_cap": "大盘",
            },
        }

        with self._conn() as conn:
            for symbol, info in stocks.items():
                conn.execute(
                    """INSERT OR REPLACE INTO stock_knowledge
                    (symbol, name, industry, sector, concepts, characteristics, market_cap, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        symbol, info["name"], info["industry"], info["sector"],
                        json.dumps(info["concepts"], ensure_ascii=False),
                        json.dumps(info["characteristics"], ensure_ascii=False),
                        info["market_cap"], datetime.now().isoformat(),
                    ),
                )

            # 产业链关联关系
            relations = [
                ("688256.SH", "603019.SH", "供应链", 0.9),
                ("002230.SZ", "688111.SH", "AI应用同业", 0.7),
                ("688256.SH", "300474.SZ", "AI芯片同业", 0.8),
                ("688047.SH", "603019.SH", "信创协同", 0.8),
                ("002415.SZ", "300496.SZ", "AI视觉生态", 0.6),
                ("688561.SH", "002230.SZ", "AI安全应用", 0.5),
            ]
            for src, tgt, rel_type, weight in relations:
                conn.execute(
                    """INSERT OR IGNORE INTO stock_relations
                    (source_symbol, target_symbol, relation_type, weight)
                    VALUES (?, ?, ?, ?)""",
                    (src, tgt, rel_type, weight),
                )

    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        if not self.enabled:
            return {}

        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM stock_knowledge WHERE symbol = ?", (symbol,)
            ).fetchone()

        if not row:
            return {}
        return {
            "symbol": row["symbol"],
            "name": row["name"],
            "industry": row["industry"],
            "sector": row["sector"],
            "concepts": json.loads(row["concepts"]) if row["concepts"] else [],
            "characteristics": json.loads(row["characteristics"]) if row["characteristics"] else [],
            "market_cap": row["market_cap"],
        }

    def get_context(self, symbol: str) -> str:
        info = self.get_stock_info(symbol)
        if not info:
            return ""

        parts = [f"{info['name']}({symbol})"]
        if info.get("industry"):
            parts.append(f"行业: {info['industry']}")
        if info.get("sector"):
            parts.append(f"板块: {info['sector']}")
        if info.get("concepts"):
            parts.append(f"概念: {', '.join(info['concepts'][:4])}")
        # 添加关联信息
        related = self.get_related_stocks(symbol)
        if related:
            rel_str = ", ".join(
                f"{r['name']}({r['relation_type']})" for r in related[:3]
            )
            parts.append(f"关联: {rel_str}")

        return " | ".join(parts)

    def get_related_stocks(self, symbol: str) -> List[Dict[str, Any]]:
        """获取产业链关联股票"""
        if not self.enabled:
            return []
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT target_symbol, relation_type, weight FROM stock_relations
                WHERE source_symbol = ?
                UNION
                SELECT source_symbol, relation_type, weight FROM stock_relations
                WHERE target_symbol = ?
                ORDER BY weight DESC""",
                (symbol, symbol),
            ).fetchall()
        results = []
        for row in rows:
            info = self.get_stock_info(row["target_symbol"])
            if info:
                results.append({
                    **info,
                    "relation_type": row["relation_type"],
                    "relation_weight": row["weight"],
                })
        return results

    def get_sector_stocks(self, sector: str) -> List[Dict[str, Any]]:
        """按板块获取AI概念股列表"""
        if not self.enabled:
            return []
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM stock_knowledge WHERE sector = ?", (sector,)
            ).fetchall()
        return [
            {
                "symbol": row["symbol"], "name": row["name"],
                "industry": row["industry"], "sector": row["sector"],
                "concepts": json.loads(row["concepts"]) if row["concepts"] else [],
            }
            for row in rows
        ]

    def get_all_stocks(self) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        with self._conn() as conn:
            rows = conn.execute("SELECT symbol, name, industry, sector FROM stock_knowledge").fetchall()
        return [dict(row) for row in rows]


knowledge_graph = KnowledgeGraph()
