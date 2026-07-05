"""Insurance vertical — Phase 1 MVP."""

from agentforge.core.runtime.loop import VerticalConfig
from agentforge.verticals.insurance.system_prompt import SYSTEM_PROMPT
from agentforge.verticals.insurance.tools.iso_forms_search import iso_forms_search_tool
from agentforge.verticals.insurance.tools.naic_lookup import naic_lookup_tool
from agentforge.verticals.insurance.tools.policy_doc_parse import policy_doc_parse_tool
from agentforge.verticals.insurance.tools.state_doi_query import state_doi_query_tool
from agentforge.verticals.insurance.tools.web_search import web_search_tool

TOOLS = [
    web_search_tool,
    state_doi_query_tool,
    naic_lookup_tool,
    policy_doc_parse_tool,
    iso_forms_search_tool,
]

INSURANCE_VERTICAL = VerticalConfig(
    vertical="insurance",
    system_prompt=SYSTEM_PROMPT,
    tools=TOOLS,
)

__all__ = ["INSURANCE_VERTICAL", "SYSTEM_PROMPT", "TOOLS"]
