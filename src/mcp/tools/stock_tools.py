"""MCP工具实现: 注册所有可供Agent调用的工具"""

from src.mcp.registry import mcp_registry
from src.data.sources import data_source
from src.memory.store import memory_store
from src.memory.knowledge_graph import knowledge_graph


@mcp_registry.register(
    name="stock_get_quote",
    description="获取股票最新行情数据",
    read_only=True,
)
async def stock_get_quote(symbol: str) -> dict:
    quote = await data_source.fetch_quote(symbol)
    if not quote:
        return {"error": f"无法获取 {symbol} 行情"}
    return quote.model_dump(mode="json")


@mcp_registry.register(
    name="stock_get_news",
    description="获取股票相关新闻",
    read_only=True,
)
async def stock_get_news(symbol: str, limit: int = 5) -> list:
    news_list = await data_source.fetch_news(symbol, limit)
    return [n.model_dump(mode="json") for n in news_list]


@mcp_registry.register(
    name="stock_batch_quotes",
    description="批量获取多只股票行情",
    read_only=True,
)
async def stock_batch_quotes(symbols: list) -> dict:
    quotes = await data_source.fetch_quotes_batch(symbols)
    return {s: q.model_dump(mode="json") for s, q in quotes.items()}


@mcp_registry.register(
    name="knowledge_query",
    description="查询股票知识图谱信息",
    read_only=True,
)
async def knowledge_query(symbol: str) -> dict:
    return knowledge_graph.get_stock_info(symbol)


@mcp_registry.register(
    name="memory_search",
    description="搜索历史记忆",
    read_only=True,
)
async def memory_search_tool(symbol: str = "", memory_type: str = "", limit: int = 10) -> list:
    results = memory_store.search(
        symbol=symbol or None,
        memory_type=memory_type or None,
        limit=limit,
    )
    return [m.model_dump(mode="json") for m in results]


@mcp_registry.register(
    name="memory_add",
    description="添加记忆条目",
    read_only=False,
)
async def memory_add_tool(content: str, memory_type: str = "observation",
                          symbol: str = "", importance: float = 0.5) -> dict:
    mid = memory_store.add(content, memory_type, symbol, importance)
    return {"memory_id": mid}


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
