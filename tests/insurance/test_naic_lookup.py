"""NAIC_lookup port — same coverage as the TS suite."""

from __future__ import annotations

import httpx
import pytest

from agentforge.verticals.insurance.tools.naic_lookup import naic_lookup_tool

CIS_HTML_TWO_HITS = """
<html><body>
  <table>
    <tr><th>NAIC #</th><th>Company Name</th><th>State of Domicile</th><th>Group #</th><th>Group Name</th></tr>
    <tr>
      <td>16322</td>
      <td><a href="/cis/companyDetail.do?cocode=16322">Acme Mutual Insurance Co</a></td>
      <td>IA</td>
      <td>0150</td>
      <td>Acme Group</td>
    </tr>
    <tr>
      <td>22667</td>
      <td><a href="/cis/companyDetail.do?cocode=22667">Beta Casualty Co</a></td>
      <td>NY</td>
      <td>0931</td>
      <td>Beta Holdings</td>
    </tr>
  </table>
</body></html>
"""

CIS_HTML_NO_HITS = """
<html><body>
  <table>
    <tr><th>NAIC #</th><th>Company Name</th><th>State of Domicile</th><th>Group #</th><th>Group Name</th></tr>
    <tr><td colspan="5">No companies match your search.</td></tr>
  </table>
</body></html>
"""


@pytest.fixture
def mock_cis(monkeypatch: pytest.MonkeyPatch):
    """Patch httpx.AsyncClient.post to return a controllable fake response."""
    state: dict[str, httpx.Response] = {}

    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *exc) -> None:
            return None

        async def post(self, url: str, **kwargs) -> httpx.Response:
            response = state.get("response")
            if response is None:
                raise RuntimeError("no fake response set")
            if isinstance(response, BaseException):
                raise response
            return response

    monkeypatch.setattr("agentforge.verticals.insurance.tools.naic_lookup.httpx.AsyncClient",
                        _FakeClient)
    return state


def _resp(text: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, text=text, request=httpx.Request("POST", "http://x"))


async def test_parses_company_results(mock_cis):
    mock_cis["response"] = _resp(CIS_HTML_TWO_HITS)
    result = await naic_lookup_tool.call({"query": "Acme", "type": "company"})
    assert result.error is None
    matches = result.data["matches"]
    assert len(matches) == 2
    assert matches[0] == {
        "naicCode": "16322",
        "name": "Acme Mutual Insurance Co",
        "domicileState": "IA",
        "groupCode": "0150",
        "groupName": "Acme Group",
        "url": "https://eapps.naic.org/cis/companyDetail.do?cocode=16322",
    }


async def test_group_filter(mock_cis):
    mock_cis["response"] = _resp(CIS_HTML_TWO_HITS)
    result = await naic_lookup_tool.call({"query": "Beta", "type": "group"})
    matches = result.data["matches"]
    assert len(matches) == 1
    assert matches[0]["groupName"] == "Beta Holdings"


async def test_empty_hits_returns_notice(mock_cis):
    mock_cis["response"] = _resp(CIS_HTML_NO_HITS)
    result = await naic_lookup_tool.call({"query": "Nonexistent", "type": "company"})
    assert result.data["matches"] == []
    assert "no matches" in result.data["notice"].lower()


async def test_5xx_returns_structured_error(mock_cis):
    mock_cis["response"] = _resp("upstream error", status=503)
    result = await naic_lookup_tool.call({"query": "Acme", "type": "company"})
    assert result.data is None
    assert "503" in result.error


async def test_timeout_returns_structured_error(mock_cis):
    mock_cis["response"] = httpx.TimeoutException("aborted")
    result = await naic_lookup_tool.call({"query": "Acme", "type": "company"})
    assert result.data is None
    assert "timed out" in result.error.lower()


async def test_model_regulation_anti_concurrent_causation():
    result = await naic_lookup_tool.call(
        {"query": "NAIC anti-concurrent causation property", "type": "model_regulation"}
    )
    assert result.error is None
    matches = result.data["matches"]
    assert matches[0]["mdl"] == "MDL-880"
    assert "anti-concurrent" in matches[0]["name"].lower()


async def test_model_regulation_credit_scoring():
    result = await naic_lookup_tool.call(
        {
            "query": "NAIC model regulations governing credit scoring in personal lines underwriting",
            "type": "model_regulation",
        }
    )
    assert result.data["matches"][0]["mdl"] == "MDL-275"


async def test_market_conduct_returns_notice():
    result = await naic_lookup_tool.call(
        {"query": "examination triggers", "type": "market_conduct"}
    )
    assert result.data["matches"] == []
    assert (
        "state_DOI_query" in result.data["notice"]
        or "web_search" in result.data["notice"]
    )


def test_cache_ttl_contract():
    assert naic_lookup_tool.cache_ttl_seconds == 86_400
