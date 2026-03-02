from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime
from enum import Enum


class AgentRole(str, Enum):
    COLLECTOR = "collector"
    SENTIMENT = "sentiment"
    SECTOR = "sector"
    MACRO = "macro"
    WRITER = "writer"
    REVIEWER = "reviewer"
    SUPERVISOR = "supervisor"


class DataSource(str, Enum):
    EASTMONEY = "eastmoney"
    SINA = "sina"
    LIVE = "live"
    MOCK = "mock"
    CACHE = "cache"


class ReportType(str, Enum):
    MORNING = "morning"
    NOON = "noon"
    CLOSING = "closing"
    ALERT = "alert"
    WEEKLY = "weekly"


class PushChannel(str, Enum):
    WECHAT = "wechat"
    EMAIL = "email"
    WEBHOOK = "webhook"
    FEISHU = "feishu"


class ReviewStatus(str, Enum):
    PASS = "pass"
    REVISE = "revise"
    REJECT = "reject"


# ---- 数据采集相关 ----

class NewsItem(BaseModel):
    title: str
    content: str = ""
    source: str = ""
    url: str = ""
    publish_time: datetime = Field(default_factory=datetime.now)
    sentiment: Optional[str] = None


class StockQuote(BaseModel):
    symbol: str
    name: str = ""
    price: float
    change_pct: float
    volume: float
    amount: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open_price: float = 0.0
    pre_close: float = 0.0
    source: DataSource = DataSource.LIVE
    timestamp: datetime = Field(default_factory=datetime.now)


class AnnouncementItem(BaseModel):
    symbol: str
    title: str
    content: str = ""
    ann_type: str = ""
    publish_time: datetime = Field(default_factory=datetime.now)
    importance: float = 0.5


class RawDataBundle(BaseModel):
    """采集Agent的输出: 原始数据包"""
    news_list: List[NewsItem] = Field(default_factory=list)
    quotes: Dict[str, StockQuote] = Field(default_factory=dict)
    announcements: List[AnnouncementItem] = Field(default_factory=list)
    data_quality: float = 1.0
    collected_at: datetime = Field(default_factory=datetime.now)


# ---- 分析Agent相关 ----

class SentimentReport(BaseModel):
    overall_score: float = 0.0
    label: str = "neutral"
    hot_topics: List[str] = Field(default_factory=list)
    positive_keywords: List[str] = Field(default_factory=list)
    negative_keywords: List[str] = Field(default_factory=list)
    news_summary: str = ""
    confidence: float = 0.5
    reasoning_chain: List[str] = Field(default_factory=list)


class SectorReport(BaseModel):
    top_sectors: List[Dict[str, Any]] = Field(default_factory=list)
    abnormal_stocks: List[Dict[str, Any]] = Field(default_factory=list)
    fund_flow_summary: str = ""
    trend_summary: str = ""
    confidence: float = 0.5
    reasoning_chain: List[str] = Field(default_factory=list)


class MacroReport(BaseModel):
    policy_summary: str = ""
    economic_outlook: str = ""
    key_events: List[str] = Field(default_factory=list)
    impact_assessment: str = ""
    confidence: float = 0.5
    reasoning_chain: List[str] = Field(default_factory=list)


# ---- 编撰和审核相关 ----

class FinalReport(BaseModel):
    report_type: ReportType
    title: str = ""
    summary: str = ""
    body: str = ""
    highlights: List[str] = Field(default_factory=list)
    symbols_mentioned: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)


class ReviewResult(BaseModel):
    status: ReviewStatus
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    revised_report: Optional[FinalReport] = None


# ---- Agent通用 ----

class AgentOutput(BaseModel):
    agent_role: AgentRole
    success: bool = True
    data: Dict[str, Any] = Field(default_factory=dict)
    reasoning_chain: List[str] = Field(default_factory=list)
    skills_used: List[str] = Field(default_factory=list)
    data_quality: float = 1.0
    latency_ms: float = 0.0
    error: Optional[str] = None


# ---- Skill相关 ----

class SkillResult(BaseModel):
    skill_id: str
    success: bool
    output: Dict[str, Any] = Field(default_factory=dict)
    raw_output: str = ""
    confidence: float = 0.0
    latency_ms: float = 0.0
    error: Optional[str] = None


# ---- 记忆相关 ----

class MemoryItem(BaseModel):
    memory_id: str
    symbol: str = ""
    memory_type: Literal["decision", "observation", "report", "reflexion"]
    content: str
    importance: float = 0.5
    access_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)


# ---- 反思相关 ----

class ReflexionEntry(BaseModel):
    reflexion_id: str
    report_type: ReportType
    original_quality: float = 0.0
    issues_found: List[str] = Field(default_factory=list)
    lesson_learned: str = ""
    improvement: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


# ---- 评估相关 ----

class ComponentEvaluation(BaseModel):
    component_name: str
    eval_type: str
    score: float
    metrics: Dict[str, float] = Field(default_factory=dict)
    details: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
