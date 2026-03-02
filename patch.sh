#!/bin/bash
# QuantBrain v2.1 修改脚本
# 在 ~/quantbrain-agent 目录下执行: bash patch.sh
# ============================================================

cd ~/quantbrain-agent || exit 1
echo "开始应用修改..."

# ============================================================
# 1. .env 追加配置
# ============================================================
cat >> .env << 'EOF'
CONTENT_FETCH_ENABLED=true
REACT_ENABLED=true
EOF
echo "[1/15] .env 追加完成"

# ============================================================
# 2. src/core/config.py - 替换WATCH_LIST
# ============================================================
sed -i '/WATCH_LIST: List\[str\] = Field(default=\[/,/\])/c\
    WATCH_LIST: List[str] = Field(default=[\
        "002230.SZ",  # 科大讯飞 - AI语音/NLP龙头\
        "300474.SZ",  # 景嘉微 - GPU芯片\
        "688111.SH",  # 金山办公 - AI+办公\
        "688047.SH",  # 龙芯中科 - 国产CPU\
        "002415.SZ",  # 海康威视 - AI视觉\
        "688256.SH",  # 寒武纪 - AI芯片\
        "603019.SH",  # 中科曙光 - AI算力\
        "688396.SH",  # 华峰测控 - 半导体测试\
        "300496.SZ",  # 中科创达 - 智能OS/端侧AI\
        "688561.SH",  # 奇安信 - AI安全\
    ])' src/core/config.py

# 在 REACT_MAX_ITERATIONS 后面插入新配置项
sed -i '/REACT_MAX_ITERATIONS: int = Field(default=5)/a\
\
    CONTENT_FETCH_ENABLED: bool = Field(default=True)\
    CONTENT_FETCH_TIMEOUT: float = Field(default=8.0)\
    CONTENT_MAX_LENGTH: int = Field(default=800)\
\
    REACT_ENABLED: bool = Field(default=True)' src/core/config.py

echo "[2/15] config.py 修改完成"

# ============================================================
# 3. src/memory/knowledge_graph.py - 替换种子数据 + 新增方法
# ============================================================

# 用Python脚本做精确替换（sed处理多行Python字典太脆弱）
python3 << 'PYEOF'
import re

filepath = "src/memory/knowledge_graph.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# --- 替换 stocks 字典 ---
old_stocks_pattern = r'(stocks = \{)[^}]+("601857\.SH"[^}]+\}[^}]+\})'
new_stocks = '''stocks = {
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
        }'''

# 找到 stocks = { 到对应闭合 } 的完整区域
start = content.find("        stocks = {", content.find("def _seed_data"))
# 找到stocks字典结束位置(通过找 "with self._conn" 定位)
end = content.find("\n        with self._conn", start)
content = content[:start] + new_stocks + content[end:]

# --- 将 INSERT OR IGNORE 改为 INSERT OR REPLACE ---
content = content.replace(
    "INSERT OR IGNORE INTO stock_knowledge",
    "INSERT OR REPLACE INTO stock_knowledge"
)

# --- 在 _seed_data 的 with self._conn() 块末尾(conn.execute循环后)插入关联关系 ---
insert_marker = '                    ),\n                )\n'
# 找到最后一个这样的marker(在_seed_data方法内)
seed_func_start = content.find("def _seed_data")
seed_func_body = content[seed_func_start:]
last_insert_pos = seed_func_body.rfind(insert_marker)
if last_insert_pos > 0:
    abs_pos = seed_func_start + last_insert_pos + len(insert_marker)
    relations_code = '''
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
'''
    content = content[:abs_pos] + relations_code + content[abs_pos:]

# --- 在 get_all_stocks 方法之前插入两个新方法 ---
get_all_marker = "    def get_all_stocks"
new_methods = '''    def get_related_stocks(self, symbol: str) -> List[Dict[str, Any]]:
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

'''
content = content.replace(get_all_marker, new_methods + "    " + get_all_marker.strip())

# --- 扩展 get_context 添加关联信息 ---
old_context_return = '        return " | ".join(parts)'
new_context_return = '''        # 添加关联信息
        related = self.get_related_stocks(symbol)
        if related:
            rel_str = ", ".join(
                f"{r['name']}({r['relation_type']})" for r in related[:3]
            )
            parts.append(f"关联: {rel_str}")

        return " | ".join(parts)'''
content = content.replace(old_context_return, new_context_return, 1)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("[3/15] knowledge_graph.py 修改完成")
PYEOF

# ============================================================
# 4. src/data/sources.py - 集成ContentFetcher + Mock数据更新
# ============================================================

python3 << 'PYEOF'
filepath = "src/data/sources.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# --- 添加 import ---
old_import = "from src.data.crawlers.sina import SinaCrawler"
new_import = """from src.data.crawlers.sina import SinaCrawler
from src.data.crawlers.content_fetcher import content_fetcher"""
content = content.replace(old_import, new_import)

# --- 替换 MockDataProvider.STOCKS ---
old_mock = '''    STOCKS = {
        "600519.SH": ("贵州茅台", 1485.0),
        "300750.SZ": ("宁德时代", 365.0),
        "601318.SH": ("中国平安", 48.0),
        "600030.SH": ("中信证券", 22.5),
        "601857.SH": ("中国石油", 8.8),
    }'''
new_mock = '''    STOCKS = {
        "002230.SZ": ("科大讯飞", 58.0),
        "300474.SZ": ("景嘉微", 75.0),
        "688111.SH": ("金山办公", 280.0),
        "688047.SH": ("龙芯中科", 95.0),
        "002415.SZ": ("海康威视", 32.0),
        "688256.SH": ("寒武纪", 320.0),
        "603019.SH": ("中科曙光", 52.0),
        "688396.SH": ("华峰测控", 160.0),
        "300496.SZ": ("中科创达", 68.0),
        "688561.SH": ("奇安信", 42.0),
    }'''
content = content.replace(old_mock, new_mock)

# --- 在 collect_all 中，"real_quotes = self.market" 之前插入ContentFetcher调用 ---
old_real = "        real_quotes = self.market.get_stock_quotes(symbols)"
new_fetch_block = '''        # 使用ContentFetcher抓取新闻正文
        if settings.CONTENT_FETCH_ENABLED:
            news_with_urls = [n for n in news_list if n.url and not n.content]
            if news_with_urls:
                log.debug(f"正文抓取: {len(news_with_urls)}条待抓取")
                enriched = await content_fetcher.fetch_batch(news_with_urls)
                url_to_content = {n.url: n.content for n in enriched if n.content}
                for n in news_list:
                    if n.url in url_to_content and not n.content:
                        n.content = url_to_content[n.url]
                fetched_count = sum(1 for n in enriched if n.content)
                log.debug(f"正文抓取完成: {fetched_count}/{len(news_with_urls)}条成功")

        real_quotes = self.market.get_stock_quotes(symbols)'''
content = content.replace(old_real, new_fetch_block)

# --- 改进数据质量计算 ---
old_quality = '''        if len(news_list) >= 10:
            quality = min(quality + 0.3, 1.0)'''
new_quality = '''        content_count = sum(1 for n in news_list if n.content and len(n.content) > 50)
        if content_count >= 5:
            quality = min(quality + 0.2, 1.0)
        if len(news_list) >= 10:
            quality = min(quality + 0.1, 1.0)'''
content = content.replace(old_quality, new_quality)

# --- 在 fetch_news 方法中也使用ContentFetcher ---
old_fetch_news = '''    async def fetch_news(self, symbol, limit=5):
        try:
            return await self.eastmoney.fetch_news(symbol, limit)
        except Exception:
            return []'''
new_fetch_news = '''    async def fetch_news(self, symbol, limit=5):
        try:
            news = await self.eastmoney.fetch_news(symbol, limit)
            if settings.CONTENT_FETCH_ENABLED and news:
                news = await content_fetcher.fetch_batch(news)
            return news
        except Exception:
            return []'''
content = content.replace(old_fetch_news, new_fetch_news)

# --- 添加 settings import ---
if "from src.core.config import settings" not in content:
    content = content.replace(
        "from src.core.logger import log",
        "from src.core.config import settings\nfrom src.core.logger import log"
    )

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("[4/15] sources.py 修改完成")
PYEOF

# ============================================================
# 5. src/data/crawlers/content_fetcher.py - 新建文件
#    (原来写在别处但没被import，现在移到正确位置)
# ============================================================

cat > src/data/crawlers/content_fetcher.py << 'PYEOF'
import httpx
import asyncio
from typing import Optional, List
from src.core.config import settings
from src.core.logger import log
from src.domain.models import NewsItem

CONTENT_SELECTORS = [
    ".zw_body", "#ContentBody", ".article-body", "#artibody",
    ".article", "#article", ".article-content", ".post-content",
]


class ContentFetcher:
    """新闻正文抓取器 - 被DataSourceAggregator.collect_all()实际调用"""

    def __init__(self):
        self.timeout = settings.CONTENT_FETCH_TIMEOUT
        self.max_content_length = settings.CONTENT_MAX_LENGTH
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        }
        self._fetch_count = 0
        self._success_count = 0

    async def fetch_content(self, item: NewsItem) -> NewsItem:
        if not item.url:
            return item
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, headers=self.headers, follow_redirects=True,
            ) as client:
                resp = await client.get(item.url)
                self._fetch_count += 1
                if resp.status_code != 200:
                    return item
                content = self._extract_content(resp.text)
                if content:
                    item.content = content[:self.max_content_length]
                    self._success_count += 1
        except Exception as e:
            log.debug(f"正文抓取失败: {item.url[:50]}... {e}")
        return item

    async def fetch_batch(self, items: List[NewsItem]) -> List[NewsItem]:
        semaphore = asyncio.Semaphore(5)

        async def _limited_fetch(item):
            async with semaphore:
                return await self.fetch_content(item)

        results = await asyncio.gather(
            *[_limited_fetch(item) for item in items], return_exceptions=True,
        )
        return [items[i] if isinstance(r, Exception) else r for i, r in enumerate(results)]

    def _extract_content(self, html: str) -> Optional[str]:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            for selector in CONTENT_SELECTORS:
                node = soup.select_one(selector)
                if node:
                    text = node.get_text(separator="\n", strip=True)
                    if len(text) > 30:
                        return text
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text() for p in paragraphs if len(p.get_text()) > 10)
            return text if text and len(text) > 30 else None
        except ImportError:
            log.warning("bs4未安装,正文提取不可用")
            return None

    def get_stats(self):
        return {
            "total_fetched": self._fetch_count,
            "success_count": self._success_count,
            "success_rate": self._success_count / self._fetch_count if self._fetch_count > 0 else 0,
        }


content_fetcher = ContentFetcher()
PYEOF
echo "[5/15] content_fetcher.py 创建完成"

# ============================================================
# 6. src/agents/sentiment.py - AI产业链关键词 + 利用正文
# ============================================================

python3 << 'PYEOF'
filepath = "src/agents/sentiment.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# --- 替换 _extract_keywords ---
old_kw = '''    @staticmethod
    def _extract_keywords(text: str):
        pos_kw_map = {"增长": 2, "利好": 2, "买入": 1.5, "新高": 2, "获批": 1.5, "预增": 2, "上涨": 1}
        neg_kw_map = {"下跌": 2, "亏损": 2, "立案": 3, "警示": 2, "减持": 1.5, "暴跌": 3, "利空": 2}

        pos = [kw for kw in pos_kw_map if kw in text]
        neg = [kw for kw in neg_kw_map if kw in text]
        return pos, neg'''
new_kw = '''    @staticmethod
    def _extract_keywords(text: str):
        pos_kw_map = {
            "突破": 2, "利好": 2, "增长": 1.5, "新高": 2, "获批": 1.5,
            "预增": 2, "上涨": 1, "大模型": 1.5, "发布": 1, "算力": 1,
            "合作": 1, "订单": 2, "国产替代": 2, "自主可控": 1.5,
            "融资": 1, "投产": 2, "流片": 2, "量产": 2,
        }
        neg_kw_map = {
            "下跌": 2, "亏损": 2, "立案": 3, "警示": 2, "减持": 1.5,
            "暴跌": 3, "利空": 2, "制裁": 3, "禁令": 3, "封锁": 2,
            "出口管制": 3, "实体清单": 3, "估值过高": 1.5, "泡沫": 2,
        }

        pos = [kw for kw in pos_kw_map if kw in text]
        neg = [kw for kw in neg_kw_map if kw in text]
        return pos, neg'''
content = content.replace(old_kw, new_kw)

# --- 替换 _extract_topics ---
old_topics = '''    @staticmethod
    def _extract_topics(text: str):
        topic_keywords = {
            "新能源": "新能源", "锂电": "新能源", "光伏": "新能源",
            "白酒": "消费", "消费": "消费",
            "金融": "金融", "银行": "金融", "保险": "金融",
            "科技": "科技", "芯片": "科技", "AI": "科技",
        }
        found = set()
        for kw, topic in topic_keywords.items():
            if kw in text:
                found.add(topic)
        return list(found)[:5]'''
new_topics = '''    @staticmethod
    def _extract_topics(text: str):
        topic_keywords = {
            "大模型": "大模型", "GPT": "大模型", "LLM": "大模型",
            "芯片": "AI芯片", "GPU": "AI芯片", "算力": "AI芯片",
            "寒武纪": "AI芯片", "英伟达": "AI芯片",
            "机器人": "具身智能", "人形机器人": "具身智能",
            "自动驾驶": "智能驾驶", "智能座舱": "智能驾驶",
            "AI安全": "AI安全", "数据安全": "AI安全",
            "信创": "信创", "国产替代": "信创",
            "AIGC": "AIGC", "AI办公": "AIGC",
            "AI应用": "AI应用", "智慧教育": "AI应用",
            "算力中心": "算力基建", "智算": "算力基建",
            "端侧AI": "端侧AI", "边缘计算": "端侧AI",
        }
        found = set()
        for kw, topic in topic_keywords.items():
            if kw in text:
                found.add(topic)
        return list(found)[:5]'''
content = content.replace(old_topics, new_topics)

# --- 改进分析上下文，利用正文 ---
old_ctx = '''        news_contents = "\\n".join(
            [n.get("content", "")[:100] for n in news_data[:5] if isinstance(n, dict)]
        )'''
new_ctx = '''        # 利用正文内容(由ContentFetcher抓取)做更深入分析
        news_contents_parts = []
        for n in news_data[:8]:
            if not isinstance(n, dict):
                continue
            nc = n.get("content", "")
            if nc and len(nc) > 30:
                news_contents_parts.append(f"[{n['title']}] {nc[:200]}")
            else:
                news_contents_parts.append(f"[{n['title']}] (无正文)")
        news_contents = "\\n".join(news_contents_parts)

        # 正文覆盖率影响数据质量
        content_coverage = sum(
            1 for n in news_data if isinstance(n, dict) and len(n.get("content", "")) > 30
        ) / max(len(news_data), 1)
        if content_coverage < 0.3:
            data_quality *= 0.8'''
content = content.replace(old_ctx, new_ctx)

# --- 更新CoT上下文 ---
old_analysis = '        analysis_context = f"新闻标题:\\n{news_titles}\\n\\n新闻摘要:\\n{news_contents[:300]}"'
new_analysis = '        analysis_context = f"新闻标题:\\n{news_titles}\\n\\n新闻详情(含正文):\\n{news_contents[:800]}"'
content = content.replace(old_analysis, new_analysis)

# --- 更新Skill调用的symbol ---
old_skill_sym = '            "symbol": ", ".join(symbols) if symbols else "综合",'
new_skill_sym = '            "symbol": ", ".join(symbols) if symbols else "AI产业链",'
content = content.replace(old_skill_sym, new_skill_sym)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("[6/15] sentiment.py 修改完成")
PYEOF

# ============================================================
# 7. src/agents/macro.py - AI产业链宏观关键词
# ============================================================

python3 << 'PYEOF'
filepath = "src/agents/macro.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# --- 替换宏观关键词列表 ---
old_kw = '''        macro_keywords = [
            "央行", "利率", "GDP", "CPI", "PMI", "降准", "降息",
            "财政", "货币", "监管", "政策", "外汇", "美联储",
            "关税", "贸易", "出口", "进口", "国务院",
        ]'''
new_kw = '''        macro_keywords = [
            "央行", "利率", "GDP", "CPI", "PMI", "降准", "降息",
            "财政", "货币", "监管", "政策", "外汇", "美联储",
            "关税", "贸易", "出口", "进口", "国务院",
            # AI产业链宏观
            "芯片制裁", "出口管制", "实体清单", "算力", "新基建",
            "人工智能", "AI政策", "科技自立", "信创", "国产替代",
            "半导体", "集成电路", "大基金", "科创板",
            "数字经济", "数据要素", "新质生产力",
            "英伟达", "台积电", "ASML", "光刻机",
        ]'''
content = content.replace(old_kw, new_kw)

# --- 替换影响评估关键词 ---
old_pos = '        positive_kw = ["利好", "宽松", "降息", "刺激", "支持"]'
new_pos = '        positive_kw = ["利好", "宽松", "降息", "刺激", "支持", "突破", "国产替代", "自主可控", "大基金"]'
content = content.replace(old_pos, new_pos)

old_neg = '        negative_kw = ["收紧", "加息", "监管", "限制", "风险"]'
new_neg = '        negative_kw = ["收紧", "加息", "监管", "限制", "风险", "制裁", "封锁", "禁令", "实体清单"]'
content = content.replace(old_neg, new_neg)

# --- 利用正文构建宏观上下文 ---
old_macro_ctx = '''        macro_context = "\\n".join(
            [f"- {n[\'title\']}: {n.get(\'content\', \'\')[:100]}" for n in macro_news[:5]]
        )'''
new_macro_ctx = '''        macro_context_parts = []
        for n in macro_news[:5]:
            title = n.get("title", "")
            nc = n.get("content", "")
            if nc and len(nc) > 30:
                macro_context_parts.append(f"- {title}: {nc[:200]}")
            else:
                macro_context_parts.append(f"- {title}")
        macro_context = "\\n".join(macro_context_parts)'''
content = content.replace(old_macro_ctx, new_macro_ctx)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("[7/15] macro.py 修改完成")
PYEOF

# ============================================================
# 8. src/agents/sector.py - 集成ReAct + 知识图谱关联分析
# ============================================================

python3 << 'PYEOF'
filepath = "src/agents/sector.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# --- 添加 import ---
old_import = "from src.reasoning.cot import cot_reasoner"
new_import = """from src.reasoning.cot import cot_reasoner
from src.reasoning.react import react_engine"""
content = content.replace(old_import, new_import, 1)

# --- 在 CoT分析之前插入产业链分析 ---
old_mock_check = "        # 检查数据源质量"
new_chain_analysis = """        # 使用知识图谱分析产业链联动
        chain_analysis = self._analyze_industry_chain(quotes)

        # 检查数据源质量"""
content = content.replace(old_mock_check, new_chain_analysis)

# --- 扩展分析数据上下文 ---
old_analysis_data = '''        analysis_data = (
            f"板块表现: {self._format_sectors(sector_perf)}\\n"
            f"异动个股: {self._format_abnormal(abnormal)}\\n"
            f"趋势信号: {self._format_trends(trend_results)}"
        )'''
new_analysis_data = '''        analysis_data = (
            f"板块表现: {self._format_sectors(sector_perf)}\\n"
            f"异动个股: {self._format_abnormal(abnormal)}\\n"
            f"趋势信号: {self._format_trends(trend_results)}\\n"
            f"产业链分析: {chain_analysis}"
        )

        # 对异动股票使用ReAct+MCP深度分析
        react_answer = None
        if react_engine.enabled and abnormal:
            top_ab = abnormal[0]
            try:
                react_answer, react_steps = await react_engine.reason_with_mcp(
                    task=f"分析{top_ab.get('name', '')}({top_ab.get('symbol', '')})异动原因",
                    context=f"涨跌幅: {top_ab.get('change_pct', 0):+.2f}%\\n{analysis_data[:500]}",
                )
                if react_answer:
                    analysis_data += f"\\nReAct深度分析: {react_answer[:300]}"
                    skills_used.append("react_reasoning")
            except Exception as e:
                log.debug(f"ReAct分析跳过: {e}")'''
content = content.replace(old_analysis_data, new_analysis_data)

# --- 在 _format_trends 方法之后插入新方法 ---
old_format_trends_end = '''    @staticmethod
    def _format_trends(trends: List[Dict]) -> str:
        return ", ".join(
            f"{t[\'symbol\']}:{t[\'trend\']}" for t in trends[:5]
        )'''
new_with_chain = '''    @staticmethod
    def _format_trends(trends: List[Dict]) -> str:
        return ", ".join(
            f"{t[\'symbol\']}:{t[\'trend\']}" for t in trends[:5]
        )

    def _analyze_industry_chain(self, quotes: Dict[str, Dict]) -> str:
        """利用知识图谱分析产业链联动"""
        chain_signals = []
        for symbol in quotes:
            related = knowledge_graph.get_related_stocks(symbol)
            if not related:
                continue
            info = knowledge_graph.get_stock_info(symbol)
            my_change = quotes[symbol].get("change_pct", 0)
            for rel in related:
                rel_sym = rel["symbol"]
                if rel_sym in quotes:
                    rel_change = quotes[rel_sym].get("change_pct", 0)
                    if abs(my_change - rel_change) > 3:
                        chain_signals.append(
                            f"{info.get(\'name\', symbol)}与{rel.get(\'name\', rel_sym)}"
                            f"({rel.get(\'relation_type\', \'关联\')})走势分化: "
                            f"{my_change:+.2f}% vs {rel_change:+.2f}%"
                        )
                    elif my_change > 2 and rel_change > 2:
                        chain_signals.append(
                            f"{info.get(\'name\', symbol)}与{rel.get(\'name\', rel_sym)}"
                            f"({rel.get(\'relation_type\', \'关联\')})同步走强"
                        )
        if not chain_signals:
            return "产业链整体联动不明显"
        return "; ".join(chain_signals[:5])'''
content = content.replace(old_format_trends_end, new_with_chain)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("[8/15] sector.py 修改完成")
PYEOF

# ============================================================
# 9. src/reasoning/react.py - 新增 reason_with_mcp 方法
# ============================================================

python3 << 'PYEOF'
filepath = "src/reasoning/react.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# --- 添加 REACT_ENABLED 配置 ---
old_init = '''    def __init__(self):
        self.max_iterations = settings.REACT_MAX_ITERATIONS'''
new_init = '''    def __init__(self):
        self.enabled = getattr(settings, "REACT_ENABLED", True)
        self.max_iterations = settings.REACT_MAX_ITERATIONS'''
content = content.replace(old_init, new_init)

# --- 在 reason 方法开头加入enabled检查 ---
old_reason_start = '        steps: List[ThoughtStep] = []'
new_reason_start = '''        if not self.enabled:
            return "ReAct已禁用", []

        steps: List[ThoughtStep] = []'''
content = content.replace(old_reason_start, new_reason_start, 1)

# --- 在 reason 方法之后插入 reason_with_mcp ---
old_build_system = "    def _build_system"
new_mcp_method = '''    async def reason_with_mcp(
        self,
        task: str,
        context: str,
    ) -> "tuple[str, list]":
        """使用MCP注册的工具进行ReAct推理"""
        from src.mcp.registry import mcp_registry

        available_tools = mcp_registry.format_for_llm()

        async def mcp_executor(action_name, params):
            return await mcp_registry.invoke(action_name, params)

        return await self.reason(
            task=task, context=context,
            tool_executor=mcp_executor,
            available_tools=available_tools,
        )

    def _build_system'''
content = content.replace(old_build_system, new_mcp_method, 1)

# --- 添加 to_dict 到 ThoughtStep ---
old_step_class_end = '        self.observation = observation'
new_step_class_end = '''        self.observation = observation

    def to_dict(self):
        return {
            "step": self.step_id, "thought": self.thought,
            "action": self.action, "observation": self.observation[:200],
        }'''
content = content.replace(old_step_class_end, new_step_class_end, 1)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("[9/15] react.py 修改完成")
PYEOF

# ============================================================
# 10. src/mcp/tools/stock_tools.py - 新增MCP工具
# ============================================================

cat >> src/mcp/tools/stock_tools.py << 'PYEOF'


@mcp_registry.register(
    name="stock_fund_flow",
    description="获取个股资金流向(主力净流入、散户流向)",
    read_only=True,
)
async def stock_fund_flow(symbol: str) -> dict:
    return data_source.market.get_stock_fund_flow(symbol)


@mcp_registry.register(
    name="market_overview",
    description="获取市场概览(大盘指数、板块排名、北向资金)",
    read_only=True,
)
async def market_overview() -> dict:
    return data_source.collect_market_context()


@mcp_registry.register(
    name="knowledge_sector_stocks",
    description="按板块查询AI概念股列表",
    read_only=True,
)
async def knowledge_sector_stocks(sector: str) -> list:
    return knowledge_graph.get_sector_stocks(sector)
PYEOF
echo "[10/15] stock_tools.py 追加完成"

# ============================================================
# 11. src/llm/prompt_templates.py - AI产业链专用Prompt
# ============================================================

python3 << 'PYEOF'
filepath = "src/llm/prompt_templates.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# --- 替换 SYSTEM_PROMPTS ---
replacements = {
    '"你是资深金融舆情分析师,拥有10年A股市场经验。"':
        '"你是资深AI产业链舆情分析师,拥有10年TMT行业研究经验。"',
    '"你是资深行业研究员,擅长板块轮动和资金流向分析。"':
        '"你是资深AI产业链研究员,擅长板块轮动和产业链上下游分析。"',
    '"你是宏观策略分析师,擅长政策解读和经济趋势判断。"':
        '"你是宏观策略分析师,尤其擅长AI产业政策和科技出口管制解读。"',
    '"你是顶级券商首席策略分析师,为机构客户撰写深度研报。"':
        '"你是顶级券商TMT首席分析师,为机构客户撰写AI产业链深度研报。"',
}
for old, new in replacements.items():
    content = content.replace(old, new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("[11/15] prompt_templates.py 修改完成")
PYEOF

# ============================================================
# 12. model/finetune/prepare_data.py - AI概念股微调数据
# ============================================================

python3 << 'PYEOF'
filepath = "model/finetune/prepare_data.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# --- 替换 STOCK_LIST ---
old_list = '''STOCK_LIST = [
    "600519.SH", "000858.SZ", "600887.SH", "300750.SZ", "002594.SZ",
    "601318.SH", "600030.SH", "601857.SH", "601398.SH", "000001.SZ",
]'''
new_list = '''STOCK_LIST = [
    ("002230.SZ", "科大讯飞", "AI应用"),
    ("300474.SZ", "景嘉微", "AI芯片"),
    ("688111.SH", "金山办公", "AI应用"),
    ("688047.SH", "龙芯中科", "AI芯片"),
    ("002415.SZ", "海康威视", "AI视觉"),
    ("688256.SH", "寒武纪", "AI芯片"),
    ("603019.SH", "中科曙光", "AI算力"),
    ("688396.SH", "华峰测控", "AI芯片"),
    ("300496.SZ", "中科创达", "AI应用"),
    ("688561.SH", "奇安信", "AI安全"),
]'''
content = content.replace(old_list, new_list)

# --- 更新 generate_analysis_sample 签名和内容 ---
old_sig = 'def generate_analysis_sample(symbol, rsi, change_pct, volume_ratio):'
new_sig = 'def generate_analysis_sample(symbol, name, sector, rsi, change_pct, volume_ratio):'
content = content.replace(old_sig, new_sig)

old_user = '''    user_content = (
        f"请分析股票{symbol}的当前状态:\\n"
        f"RSI={rsi}, 涨跌幅={change_pct:.2f}%, 量比={volume_ratio:.2f}"
    )'''
new_user = '''    user_content = (
        f"请分析AI概念股{name}({symbol})的当前状态:\\n"
        f"所属板块: {sector}\\n"
        f"RSI={rsi}, 涨跌幅={change_pct:.2f}%, 量比={volume_ratio:.2f}"
    )'''
content = content.replace(old_user, new_user)

old_sys = '            {"role": "system", "content": "你是专业A股分析师,擅长技术分析和报告撰写。输出格式为Markdown。"},'
new_sys = '            {"role": "system", "content": "你是专业A股AI产业链分析师,擅长技术分析和产业链研究。输出格式为纯文本,不使用Markdown符号。"},'
content = content.replace(old_sys, new_sys)

# --- 更新main中的循环(适配新的tuple格式) ---
old_loop = '    for idx, symbol in enumerate(STOCK_LIST):'
new_loop = '    for idx, (symbol, name, sector) in enumerate(STOCK_LIST):'
content = content.replace(old_loop, new_loop)

old_call = '                sample = generate_analysis_sample(symbol, rsi, change_pct, volume_ratio)'
new_call = '                sample = generate_analysis_sample(symbol, name, sector, rsi, change_pct, volume_ratio)'
content = content.replace(old_call, new_call)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("[12/15] prepare_data.py 修改完成")
PYEOF

# ============================================================
# 13. model/finetune/train_lora.py - 适配AWQ
# ============================================================

python3 << 'PYEOF'
filepath = "model/finetune/train_lora.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# --- 替换模型路径和配置 ---
content = content.replace('MODEL_PATH = "Qwen3-4B"', 'MODEL_PATH = "/datadisk/home/lsr/qwen2.5-72b-awq"')
content = content.replace('OUTPUT_DIR = "qwen3_finetuned"', 'OUTPUT_DIR = "qwen2.5-72b-awq-lora"')
content = content.replace('MAX_SEQ_LENGTH = 512', 'MAX_SEQ_LENGTH = 1024')
content = content.replace('GRAD_ACCUM_STEPS = 4', 'GRAD_ACCUM_STEPS = 8')

# --- 删除BitsAndBytesConfig(AWQ已量化,不需要) ---
old_bnb = '''    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )'''
content = content.replace(old_bnb, '    # AWQ模型已量化,不需要BitsAndBytesConfig')

# --- 修改模型加载(去掉quantization_config) ---
old_load = '''    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
    )'''
new_load = '''    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
    )'''
content = content.replace(old_load, new_load)

# --- 删除 prepare_model_for_kbit_training(AWQ不需要) ---
content = content.replace(
    '    model = prepare_model_for_kbit_training(model)\n    model.config.use_cache = False',
    '    model.config.use_cache = False\n    if hasattr(model, "gradient_checkpointing_enable"):\n        model.gradient_checkpointing_enable()'
)

# --- 调整LoRA配置 ---
content = content.replace('        r=8,', '        r=16,')
content = content.replace('        lora_alpha=16,', '        lora_alpha=32,')

# --- 清理不需要的import ---
content = content.replace(
    'from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training',
    'from peft import LoraConfig, get_peft_model, TaskType'
)
content = content.replace(
    '    BitsAndBytesConfig,\n',
    ''
)

# --- 修改tokenize格式(使用chat template) ---
old_format = '''    def format_fn(example):
        messages = example["messages"]
        text = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            text += f"<|{role}|>\\n{content}\\n"
        return {"text": text}'''
new_format = '''    def format_fn(example):
        messages = example["messages"]
        try:
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        except Exception:
            text = ""
            for msg in messages:
                role, c = msg["role"], msg["content"]
                text += f"<|im_start|>{role}\\n{c}<|im_end|>\\n"
        return {"text": text}'''
content = content.replace(old_format, new_format)

# --- 修改optim ---
content = content.replace('optim="paged_adamw_8bit"', 'optim="adamw_torch"')

# --- 修改学习率 ---
content = content.replace('learning_rate=2e-4', 'learning_rate=1e-4')

# --- 修改输出提示 ---
old_done = '    print(f"训练完成, 模型保存至: {OUTPUT_DIR}")'
new_done = '''    print(f"训练完成, LoRA适配器保存至: {OUTPUT_DIR}")
    print(f"使用: vllm serve {MODEL_PATH} --enable-lora --lora-modules finance-lora={OUTPUT_DIR}")'''
content = content.replace(old_done, new_done)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("[13/15] train_lora.py 修改完成")
PYEOF

# ============================================================
# 14. model/finetune/merge.py - AWQ不需要合并
# ============================================================

cat > model/finetune/merge.py << 'PYEOF'
"""
AWQ模型 + LoRA 部署说明

AWQ模型不建议直接合并LoRA权重。推荐使用vLLM动态加载:

  vllm serve /datadisk/home/lsr/qwen2.5-72b-awq \
    --enable-lora \
    --lora-modules finance-lora=qwen2.5-72b-awq-lora \
    --max-lora-rank 16

调用时: model="finance-lora" 使用微调版本
"""
import sys
import os


def print_usage():
    print("=" * 60)
    print("Qwen2.5-72B-AWQ + LoRA 推荐部署方式")
    print("=" * 60)
    print()
    print("vllm serve /datadisk/home/lsr/qwen2.5-72b-awq \\")
    print("    --host 0.0.0.0 --port 11434 \\")
    print("    --enable-lora \\")
    print("    --lora-modules finance-lora=qwen2.5-72b-awq-lora \\")
    print("    --max-lora-rank 16")
    print()
    print(".env配置:")
    print("  LLM_BASE_URL=http://localhost:11434")
    print("  MODEL_NAME=/datadisk/home/lsr/qwen2.5-72b-awq")
    print()
    print('使用LoRA: 调用时指定 model="finance-lora"')
    print("=" * 60)


def merge_if_needed():
    """如果确实需要合并(不推荐)"""
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
    except ImportError:
        print("需要: pip install torch transformers peft")
        return

    BASE = "/datadisk/home/lsr/qwen2.5-72b-awq"
    LORA = "qwen2.5-72b-awq-lora"
    OUT = "qwen2.5-72b-merged"

    confirm = input("AWQ模型合并LoRA可能损失精度,确定继续? (yes/no): ")
    if confirm != "yes":
        return

    print("加载模型...")
    tokenizer = AutoTokenizer.from_pretrained(BASE, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        BASE, torch_dtype=torch.float16, device_map="auto", trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(model, LORA)
    model = model.merge_and_unload()
    os.makedirs(OUT, exist_ok=True)
    model.save_pretrained(OUT)
    tokenizer.save_pretrained(OUT)
    print(f"合并完成: {OUT}")


if __name__ == "__main__":
    if "--merge" in sys.argv:
        merge_if_needed()
    else:
        print_usage()
PYEOF
echo "[14/15] merge.py 重写完成"

# ============================================================
# 15. model/serve/inference_api.py - 适配vLLM客户端
# ============================================================

python3 << 'PYEOF'
filepath = "model/serve/inference_api.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# --- 替换整个模型加载逻辑为vLLM客户端模式 ---
# 删除 torch import 和本地模型加载
content = content.replace('import torch\n', '')
content = content.replace('from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig\n', 'import requests as req_lib\n')

content = content.replace('MODEL_PATH = "model/qwen3_merged"', '''VLLM_URL = "http://localhost:11434"
MODEL_NAME = "/datadisk/home/lsr/qwen2.5-72b-awq"''')

# --- 替换ChatRequest ---
old_req = '''class ChatRequest(BaseModel):
    prompt: str
    system: str = "你是专业A股金融分析师,直接输出结论,不要思考过程。"
    max_tokens: int = 1024'''
new_req = '''class ChatRequest(BaseModel):
    prompt: str
    system: str = "你是专业A股AI产业链分析师,直接输出结论,不要思考过程。使用中文。"
    max_tokens: int = 1024
    temperature: float = 0.3
    use_lora: bool = False'''
content = content.replace(old_req, new_req)

# --- 删除全局model/tokenizer和load_model函数 ---
old_globals = '''model = None
tokenizer = None


def load_model():
    global model, tokenizer
    print("加载模型(4-bit量化)...")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
    )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        quantization_config=bnb_config,
        device_map="cuda",
        trust_remote_code=True,
    )
    model.eval()
    print("模型加载完成")


@app.on_event("startup")
def startup():
    load_model()'''
content = content.replace(old_globals, '')

# --- 替换health ---
old_health = '''@app.get("/health")
def health():
    return {"status": "ok", "model": "quant-qwen3-4bit"}'''
new_health = '''@app.get("/health")
def health():
    try:
        resp = req_lib.get(f"{VLLM_URL}/v1/models", timeout=5)
        models = [m.get("id", "") for m in resp.json().get("data", [])] if resp.ok else []
        return {"status": "ok", "vllm": "running", "models": models}
    except Exception as e:
        return {"status": "error", "vllm": str(e)}'''
content = content.replace(old_health, new_health)

# --- 替换generate ---
old_gen = '''@app.post("/generate", response_model=ChatResponse)
def generate(req: ChatRequest):
    messages = [
        {"role": "system", "content": req.system},
        {"role": "user", "content": req.prompt},
    ]

    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(text, return_tensors="pt").to("cuda")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=req.max_tokens,
            temperature=0.1,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    )
    return ChatResponse(content=response)'''
new_gen = '''@app.post("/generate", response_model=ChatResponse)
def generate(req: ChatRequest):
    model = "finance-lora" if req.use_lora else MODEL_NAME
    messages = [
        {"role": "system", "content": req.system},
        {"role": "user", "content": req.prompt},
    ]
    try:
        resp = req_lib.post(
            f"{VLLM_URL}/v1/chat/completions",
            json={"model": model, "messages": messages,
                  "max_tokens": req.max_tokens, "temperature": req.temperature},
            timeout=120,
        )
        if resp.status_code == 200:
            return ChatResponse(content=resp.json()["choices"][0]["message"]["content"])
        return ChatResponse(content=f"vLLM错误: HTTP {resp.status_code}")
    except Exception as e:
        return ChatResponse(content=f"调用失败: {e}")'''
content = content.replace(old_gen, new_gen)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("[15/15] inference_api.py 修改完成")
PYEOF

# ============================================================
echo ""
echo "=========================================="
echo "全部15处修改完成！"
echo "=========================================="
echo ""
echo "修改摘要:"
echo "  [需求1-微调适配] train_lora.py, merge.py, inference_api.py"
echo "  [需求2-AI概念股] config.py, knowledge_graph.py, sources.py, prepare_data.py, prompt_templates.py"
echo "  [需求3-代码串联] content_fetcher.py(新建), sources.py, sentiment.py, sector.py, react.py, stock_tools.py, macro.py"
echo ""
echo "验证: python -c 'from src.core.config import settings; print(settings.WATCH_LIST)'"
echo ""
echo "如需回滚: 备份文件在 ~/quantbrain-agent-backup.tar.gz"
