from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    LLM_BASE_URL: str = Field(default="http://localhost:11434")
    MODEL_NAME: str = Field(default="/datadisk/home/lsr/qwen2.5-72b-awq")
    LLM_TIMEOUT: int = Field(default=120)
    LLM_MAX_RETRIES: int = Field(default=3)
    LLM_RETRY_DELAY: float = Field(default=2.0)
    MAX_LLM_CALLS_PER_HOUR: int = Field(default=500)

    DEEP_LAB_URL: str = Field(default="http://192.168.200.1:8002")
    GATEWAY_URL: str = Field(default="http://172.18.0.1:8000")

    CACHE_TTL_SECONDS: int = Field(default=300)

    # 优化点1: 精简为3只核心股票，便于深度分析
    WATCH_LIST: List[str] = Field(default=[
        "002230.SZ",  # 科大讯飞 - AI应用龙头
        "688256.SH",  # 寒武纪 - AI芯片龙头
        "603019.SH",  # 中科曙光 - 算力基础设施
    ])

    FALLBACK_ENABLED: bool = Field(default=True)
    MOCK_DATA_ENABLED: bool = Field(default=True)

    MEMORY_DB_PATH: str = Field(default="data/memory.db")
    MEMORY_MAX_ITEMS: int = Field(default=2000)
    MEMORY_DECAY_FACTOR: float = Field(default=0.95)

    KNOWLEDGE_GRAPH_PATH: str = Field(default="data/knowledge_graph.db")
    KNOWLEDGE_GRAPH_ENABLED: bool = Field(default=True)

    REFLEXION_ENABLED: bool = Field(default=True)
    REFLEXION_DB_PATH: str = Field(default="data/reflexion.db")

    SKILL_ENABLED: bool = Field(default=True)

    SUPERVISOR_ENABLED: bool = Field(default=True)
    SUPERVISOR_CONSENSUS_THRESHOLD: float = Field(default=0.7)

    COT_ENABLED: bool = Field(default=True)
    REACT_MAX_ITERATIONS: int = Field(default=5)

    CONTENT_FETCH_ENABLED: bool = Field(default=True)
    CONTENT_FETCH_TIMEOUT: float = Field(default=8.0)
    CONTENT_MAX_LENGTH: int = Field(default=800)

    REACT_ENABLED: bool = Field(default=True)

    COMPONENT_EVAL_ENABLED: bool = Field(default=True)
    COMPONENT_EVAL_LOG_PATH: str = Field(default="data/component_eval.json")

    PUSH_WECHAT_WEBHOOK: str = Field(default="")
    PUSH_FEISHU_WEBHOOK: str = Field(default="")
    PUSH_EMAIL_SMTP_HOST: str = Field(default="")
    PUSH_EMAIL_SMTP_PORT: int = Field(default=465)
    PUSH_EMAIL_USER: str = Field(default="")
    PUSH_EMAIL_PASSWORD: str = Field(default="")
    PUSH_EMAIL_RECEIVERS: List[str] = Field(default=[])

    # 优化点4: 仅保留早上09:00一次
    SCHEDULE_MORNING: str = Field(default="09:00")
    SCHEDULE_NOON: str = Field(default="11:35")
    SCHEDULE_CLOSING: str = Field(default="15:30")

    TUSHARE_TOKEN: str = Field(default="")
    TUSHARE_API_URL: str = Field(default="http://tushare.nlink.vip")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
