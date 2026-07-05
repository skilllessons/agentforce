"""Per-vertical tool registry."""

from __future__ import annotations

from collections.abc import Iterable

from agentforge.core.tools.protocol import ResearchTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ResearchTool] = {}

    def register(self, tool: ResearchTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def register_all(self, tools: Iterable[ResearchTool]) -> None:
        for t in tools:
            self.register(t)

    def get(self, name: str) -> ResearchTool | None:
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def list(self, vertical: str | None = None) -> list[ResearchTool]:
        all_tools = list(self._tools.values())
        if vertical is None:
            return all_tools
        return [t for t in all_tools if t.vertical is None or t.vertical == vertical]
