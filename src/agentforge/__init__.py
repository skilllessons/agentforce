"""AgentForge — Vercel for research agents.

The public entry points live in submodules:

- :mod:`agentforge.core.runtime`     — agent loop, stop conditions
- :mod:`agentforge.core.tools`       — ResearchTool protocol, registry, cache
- :mod:`agentforge.core.llm`         — Anthropic + LiteLLM routers
- :mod:`agentforge.core.schema`      — ResearchOutput, Finding, Source
- :mod:`agentforge.verticals`        — domain-specific tools + prompts
- :mod:`agentforge.platform`         — FastAPI gateway, worker, webhooks
"""

__version__ = "0.1.0"
