"""Tool registry: ResearchTool protocol, ToolResult, validation, Redis cache."""

from agentforge.core.tools.cache import hash_input, with_cache
from agentforge.core.tools.protocol import ResearchTool, ToolResult
from agentforge.core.tools.redis_client import close_redis, get_redis
from agentforge.core.tools.registry import ToolRegistry
from agentforge.core.tools.validate import ValidationError, validate_input

__all__ = [
    "ResearchTool",
    "ToolRegistry",
    "ToolResult",
    "ValidationError",
    "close_redis",
    "get_redis",
    "hash_input",
    "validate_input",
    "with_cache",
]
