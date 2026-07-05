"""NAIC_lookup — public NAIC CIS company search + curated MDL-NNN model law index.

CIS HTML is server-rendered with stable column ordering: NAIC #, Company Name,
State of Domicile, Group #, Group Name. We find the results table by header
text rather than by class to stay resilient to small markup tweaks.

Curated model-law index lives in ``data/naic_model_laws.py``. Market-conduct
queries return a structured null with a flag pointing the agent to
``state_DOI_query`` or ``web_search`` (NAIC has no clean public market-conduct
API; better than fake data).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlencode, urljoin

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from agentforge.core.tools.protocol import ToolResult
from agentforge.core.tools.validate import validate_input
from agentforge.verticals.insurance.data.naic_model_laws import (
    NaicModelLaw,
    search_model_laws,
)


class _NaicInput(BaseModel):
    query: str = Field(min_length=2)
    type: Literal["company", "group", "model_regulation", "market_conduct"]


_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "minLength": 2},
        "type": {
            "type": "string",
            "enum": ["company", "group", "model_regulation", "market_conduct"],
        },
    },
    "required": ["query", "type"],
    "additionalProperties": False,
}

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "matches": {"type": "array"},
        "notice": {"type": "string"},
    },
}

_USER_AGENT = os.getenv(
    "AGENTFORGE_USER_AGENT", "AgentForge/0.1 (+https://agentforge.example.com)"
)
_CIS_BASE = "https://eapps.naic.org/cis/"
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


async def _call(input_: dict[str, Any]) -> ToolResult:
    try:
        validated = validate_input(input_, _NaicInput)
    except Exception as e:
        return ToolResult(data=None, error=str(e), retrievedAt=_now_iso())

    retrieved_at = _now_iso()

    try:
        if validated.type in ("company", "group"):
            return await _lookup_company_or_group(validated.query, validated.type, retrieved_at)
        if validated.type == "model_regulation":
            return _lookup_model_regulation(validated.query, retrieved_at)
        return _lookup_market_conduct(validated.query, retrieved_at)
    except httpx.TimeoutException:
        return ToolResult(
            data=None, error="NAIC CIS request timed out after 10s", retrievedAt=retrieved_at
        )
    except Exception as e:
        return ToolResult(data=None, error=str(e), retrievedAt=retrieved_at)


async def _lookup_company_or_group(
    query: str, type_: Literal["company", "group"], retrieved_at: str
) -> ToolResult:
    url = urljoin(_CIS_BASE, "companySearch.do")
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.8",
    }
    body = {"searchType": "company", "companyName": query, "submit": "Search"}

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        resp = await client.post(url, headers=headers, data=body)

    if resp.status_code != 200:
        return ToolResult(
            data=None,
            error=f"NAIC CIS {resp.status_code}: {resp.reason_phrase}",
            retrievedAt=retrieved_at,
        )

    matches = _parse_cis_results(resp.text, group_filter=query if type_ == "group" else None)

    return ToolResult(
        data={
            "matches": matches,
            "notice": "No matches in NAIC CIS" if not matches else None,
        },
        sourceUrl=f"{url}?{urlencode({'companyName': query})}",
        retrievedAt=retrieved_at,
    )


def _parse_cis_results(html: str, *, group_filter: str | None) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict[str, str]] = []

    # Find the table whose first row mentions both "NAIC" and "Company".
    target_table = None
    for table in soup.find_all("table"):
        first_row = table.find("tr")
        if first_row is None:
            continue
        cells = first_row.find_all(["th", "td"])
        header_text = " ".join(c.get_text(" ", strip=True).lower() for c in cells)
        if "naic" in header_text and "company" in header_text:
            target_table = table
            break

    if target_table is None:
        return rows

    for tr in target_table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 5:
            continue

        naic = cells[0].get_text(strip=True)
        if not naic.isdigit():
            continue

        name = cells[1].get_text(strip=True)
        state = cells[2].get_text(strip=True)
        group_code = cells[3].get_text(strip=True)
        group_name = cells[4].get_text(strip=True)

        if group_filter and group_filter.lower() not in group_name.lower():
            continue

        link_el = cells[1].find("a")
        href = link_el.get("href") if link_el else None
        link = (
            urljoin(_CIS_BASE, href)
            if href
            else f"{_CIS_BASE}companySearch.do?{urlencode({'companyName': name})}"
        )

        rows.append(
            {
                "naicCode": naic,
                "name": name,
                "domicileState": state,
                "groupCode": group_code,
                "groupName": group_name,
                "url": link,
            }
        )
    return rows


def _lookup_model_regulation(query: str, retrieved_at: str) -> ToolResult:
    matches = search_model_laws(query, limit=5)
    return ToolResult(
        data={
            "matches": [_to_model_row(m) for m in matches],
            "notice": (
                None
                if matches
                else (
                    "No curated NAIC model law matches; fall back to web_search "
                    "for less common references"
                )
            ),
        },
        sourceUrl="https://content.naic.org/model-laws",
        retrievedAt=retrieved_at,
    )


def _to_model_row(m: NaicModelLaw) -> dict[str, str]:
    return {
        "mdl": m.mdl,
        "name": m.title,
        "summary": m.summary,
        "url": m.url,
        "dataVintage": m.last_reviewed or "curated index",
    }


def _lookup_market_conduct(query: str, retrieved_at: str) -> ToolResult:
    return ToolResult(
        data={
            "matches": [],
            "notice": (
                f"Market conduct exam data is not exposed via a public NAIC API. "
                f'For "{query}", route to state_DOI_query with the relevant state, '
                f"or to web_search for NAIC market-conduct annual reports."
            ),
        },
        sourceUrl="https://content.naic.org/cmte_d_mceh.htm",
        retrievedAt=retrieved_at,
    )


class _NaicLookupTool:
    name = "NAIC_lookup"
    description = (
        "Returns NAIC company codes (via the public CIS at eapps.naic.org), group "
        "affiliations, and references to NAIC model regulations (curated index of MDL-NNN "
        "identifiers). Use for cross-state regulatory questions, company identification, and "
        "locating the canonical model regulation behind a state law. Specify type as "
        "company | group | model_regulation | market_conduct."
    )
    input_schema = _INPUT_SCHEMA
    output_schema = _OUTPUT_SCHEMA
    cache_ttl_seconds = 86_400  # 24h
    estimated_cost_usd = 0.001
    vertical = "insurance"

    async def call(self, input_: dict[str, Any]) -> ToolResult:
        return await _call(input_)


naic_lookup_tool = _NaicLookupTool()
