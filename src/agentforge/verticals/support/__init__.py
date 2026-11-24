"""Support vertical — M2. Answers from the tenant's own ticket data."""

from agentforge.core.runtime.loop import VerticalConfig
from agentforge.core.tools.protocol import ResearchTool
from agentforge.verticals.support.system_prompt import SYSTEM_PROMPT
from agentforge.verticals.support.tools.ticket_search import ticket_search_tool

TOOLS: list[ResearchTool] = [ticket_search_tool]

SUPPORT_VERTICAL = VerticalConfig(
    vertical="support",
    system_prompt=SYSTEM_PROMPT,
    tools=TOOLS,
)

__all__ = ["SUPPORT_VERTICAL", "SYSTEM_PROMPT", "TOOLS"]
