from typing import Dict, Any, List, Callable
from functools import wraps
from src.core.logger import log


class ToolDefinition:
    def __init__(self, name: str, description: str, handler: Callable,
                 input_schema: Dict = None, read_only: bool = True):
        self.name = name
        self.description = description
        self.handler = handler
        self.input_schema = input_schema or {}
        self.read_only = read_only


class MCPRegistry:

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, name: str, description: str,
                 input_schema: Dict = None, read_only: bool = True) -> Callable:
        def decorator(func: Callable) -> Callable:
            self._tools[name] = ToolDefinition(
                name=name, description=description, handler=func,
                input_schema=input_schema, read_only=read_only,
            )

            @wraps(func)
            async def wrapper(**kwargs):
                log.debug(f"MCP调用: {name}")
                try:
                    return await func(**kwargs)
                except Exception as e:
                    log.error(f"MCP工具 {name} 失败: {e}")
                    raise
            return wrapper
        return decorator

    async def invoke(self, name: str, params: Dict[str, Any] = None) -> Any:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"未注册的工具: {name}")
        return await tool.handler(**(params or {}))

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "read_only": t.read_only}
            for t in self._tools.values()
        ]

    def format_for_llm(self) -> str:
        lines = ["可用工具:"]
        for t in self._tools.values():
            lines.append(f"- {t.name}: {t.description}")
        return "\n".join(lines)


mcp_registry = MCPRegistry()
