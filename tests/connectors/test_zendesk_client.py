"""ZendeskClient transport behaviour, against a mocked HTTP layer.

No network. The failure modes that matter here — token refresh, rate limits,
retry bounds, cursor pagination — are exactly the ones a live test cannot
trigger on demand.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest

from agentforge.connectors.zendesk.client import ZendeskClient, ZendeskError

_CREDS = {"subdomain": "testsub", "client_id": "cid", "client_secret": "sec"}


def _token_response() -> httpx.Response:
    return httpx.Response(200, json={"access_token": "tok", "expires_in": 1800})


@pytest.fixture
def make_client() -> Iterator[Callable[[Callable[..., httpx.Response]], ZendeskClient]]:
    """Build a client whose transport is a handler you supply."""
    created: list[ZendeskClient] = []

    def factory(handler: Callable[..., httpx.Response]) -> ZendeskClient:
        client = ZendeskClient(**_CREDS)
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        created.append(client)
        return client

    yield factory


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Collapse backoff so the retry tests don't actually wait ~7 seconds."""

    async def _instant(_seconds: float) -> None:
        return None

    monkeypatch.setattr("agentforge.connectors.zendesk.client.asyncio.sleep", _instant)


# ── config ──────────────────────────────────────────────────────────


def test_missing_config_is_rejected_at_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agentforge.core import config

    monkeypatch.setattr(
        config.get_settings(),
        "zendesk_subdomain",
        None,
        raising=False,
    )
    with pytest.raises(ZendeskError, match="missing Zendesk config"):
        ZendeskClient(subdomain="", client_id="", client_secret="")


@pytest.mark.asyncio
async def test_request_without_opening_the_client_raises() -> None:
    client = ZendeskClient(**_CREDS)
    with pytest.raises(ZendeskError, match="not open"):
        await client.get_ticket(1)


# ── transport ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retries_5xx_then_succeeds(make_client: Any) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/tokens":
            return _token_response()
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, text="boom")
        return httpx.Response(200, json={"ok": True})

    client = make_client(handler)
    assert await client._request("GET", "/api/v2/x.json") == {"ok": True}
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_honors_retry_after_on_429(make_client: Any) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/tokens":
            return _token_response()
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, json={"ok": True})

    client = make_client(handler)
    assert await client._request("GET", "/api/v2/x.json") == {"ok": True}


@pytest.mark.asyncio
async def test_401_refreshes_the_token_once(make_client: Any) -> None:
    tokens = {"n": 0}
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/tokens":
            tokens["n"] += 1
            return _token_response()
        calls["n"] += 1
        return httpx.Response(401) if calls["n"] == 1 else httpx.Response(200, json={"ok": True})

    client = make_client(handler)
    assert await client._request("GET", "/api/v2/x.json") == {"ok": True}
    assert tokens["n"] == 2  # initial fetch + one refresh


@pytest.mark.asyncio
async def test_persistent_401_gives_up(make_client: Any) -> None:
    """A revoked secret must not become a tight refresh loop."""
    tokens = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/tokens":
            tokens["n"] += 1
            return _token_response()
        return httpx.Response(401)

    client = make_client(handler)
    with pytest.raises(ZendeskError) as excinfo:
        await client._request("GET", "/api/v2/x.json")
    assert excinfo.value.status == 401
    assert tokens["n"] == 2


@pytest.mark.asyncio
async def test_404_is_not_retried(make_client: Any) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/tokens":
            return _token_response()
        calls["n"] += 1
        return httpx.Response(404, text="nope")

    client = make_client(handler)
    with pytest.raises(ZendeskError) as excinfo:
        await client._request("GET", "/api/v2/x.json")
    assert excinfo.value.status == 404
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_exhausted_attempts_report_the_last_status(make_client: Any) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/tokens":
            return _token_response()
        return httpx.Response(503)

    client = make_client(handler)
    with pytest.raises(ZendeskError) as excinfo:
        await client._request("GET", "/api/v2/x.json")
    assert excinfo.value.status == 503


# ── reads ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_ticket_unwraps_the_singular_key(make_client: Any) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/tokens":
            return _token_response()
        return httpx.Response(200, json={"ticket": {"id": 7}})

    assert await make_client(handler).get_ticket(7) == {"id": 7}


@pytest.mark.asyncio
async def test_get_comments_unwraps_the_plural_key(make_client: Any) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/tokens":
            return _token_response()
        return httpx.Response(200, json={"comments": [{"id": 1}]})

    assert await make_client(handler).get_comments(7) == [{"id": 1}]


# ── pagination ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_iter_tickets_follows_the_cursor(make_client: Any) -> None:
    """Three pages; the final page's tickets must still be yielded."""
    seen: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/tokens":
            return _token_response()
        params = dict(request.url.params)
        seen.append(params)
        if "start_time" in params:
            body = {"tickets": [{"id": 1}], "after_cursor": "C1", "end_of_stream": False}
        elif params.get("cursor") == "C1":
            body = {"tickets": [{"id": 2}], "after_cursor": "C2", "end_of_stream": False}
        else:
            body = {"tickets": [{"id": 3}], "after_cursor": "C3", "end_of_stream": True}
        return httpx.Response(200, json=body)

    ids: list[int] = []
    cursors: list[str] = []
    async for tickets, after in make_client(handler).iter_tickets():
        ids += [t["id"] for t in tickets]
        cursors.append(after)

    assert ids == [1, 2, 3]
    assert cursors == ["C1", "C2", "C3"]
    assert seen == [{"start_time": "0"}, {"cursor": "C1"}, {"cursor": "C2"}]


@pytest.mark.asyncio
async def test_iter_tickets_resumes_from_a_cursor(make_client: Any) -> None:
    seen: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/tokens":
            return _token_response()
        seen.append(dict(request.url.params))
        return httpx.Response(
            200, json={"tickets": [], "after_cursor": "C9", "end_of_stream": True}
        )

    pages = [
        (tickets, after)
        async for tickets, after in make_client(handler).iter_tickets(cursor="C8")
    ]

    assert seen == [{"cursor": "C8"}]
    # The cursor advances even on an empty page — the caller must persist it.
    assert pages == [([], "C9")]
