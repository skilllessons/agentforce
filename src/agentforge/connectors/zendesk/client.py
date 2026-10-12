"""Zendesk REST client — layer 2.

Returns Zendesk's raw JSON dicts. Knows nothing about `tickets`, `persons`, or
Postgres; that translation is mapping.py's job, which is what lets mapping.py
be tested against a recorded payload with no network.

Auth is OAuth client credentials. API tokens are unavailable on Zendesk
accounts created on or after 2026-07-28.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from agentforge.core.config import get_settings

_TOKEN_SKEW_SECONDS = 60
_DEFAULT_SCOPE = "tickets:read users:read"
_MAX_ATTEMPTS = 4
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
# Cap on an honored Retry-After. Zendesk's incremental-export window resets in
# ~60s; a poller that sleeps longer than that on one header is wedged.
_MAX_RETRY_AFTER = 60.0


def _retry_after(resp: httpx.Response, default: float = 1.0) -> float:
    """Seconds to wait per the Retry-After header, clamped to _MAX_RETRY_AFTER."""
    try:
        return min(max(0.0, float(resp.headers["Retry-After"])), _MAX_RETRY_AFTER)
    except (KeyError, TypeError, ValueError):
        return default


class ZendeskError(Exception):
    """A Zendesk request failed.

    This client raises; it is not a ResearchTool. The tool wrapper that exposes
    Zendesk to the agent loop catches this and returns a ToolResult, which is
    where the never-raise rule applies.
    """

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class ZendeskClient:
    """Async Zendesk client. Use as an async context manager.

        async with ZendeskClient() as zd:
            ticket = await zd.get_ticket(7)
    """

    def __init__(
        self,
        subdomain: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        scope: str = _DEFAULT_SCOPE,
    ) -> None:
        settings = get_settings()
        self._subdomain = subdomain or settings.zendesk_subdomain
        self._client_id = client_id or settings.zendesk_client_id
        self._client_secret = client_secret or settings.zendesk_client_secret
        self._scope = scope

        missing = [
            name
            for name, value in (
                ("zendesk_subdomain", self._subdomain),
                ("zendesk_client_id", self._client_id),
                ("zendesk_client_secret", self._client_secret),
            )
            if not value
        ]
        if missing:
            raise ZendeskError(f"missing Zendesk config: {', '.join(missing)}")

        self._base = f"https://{self._subdomain}.zendesk.com"
        self._http: httpx.AsyncClient | None = None
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> ZendeskClient:
        self._http = httpx.AsyncClient(timeout=_TIMEOUT)
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    def _open_http(self) -> httpx.AsyncClient:
        """The live transport, or a clear error if the client was never opened."""
        if self._http is None:
            raise ZendeskError("client is not open — use `async with ZendeskClient()`")
        return self._http

    # ── auth ────────────────────────────────────────────────────────

    async def _ensure_token(self) -> str:
        """Return a valid bearer token, refreshing if it expires within the skew.

        Hold ``self._lock`` for the whole refresh, and re-check expiry *inside*
        the lock — otherwise every waiter that queued behind the first refresh
        performs a second, redundant one.

        POST ``{base}/oauth/tokens``, form-encoded:
            grant_type=client_credentials, client_id, client_secret, scope

        The response carries ``access_token`` and ``expires_in`` (1800s observed)
        and **no refresh token** — re-running this same POST is the refresh path.

        Set ``self._expires_at = time.monotonic() + expires_in - _TOKEN_SKEW_SECONDS``.
        Monotonic, not wall clock: wall time can jump.

        Non-200 → ZendeskError with the status.
        """
        if self._token is not None and time.monotonic() < self._expires_at:
            return self._token

        async with self._lock:
            # Re-check inside the lock: everyone queued behind the first
            # refresher already has a fresh token and must not fetch another.
            if self._token is not None and time.monotonic() < self._expires_at:
                return self._token

            http = self._open_http()
            resp = await http.post(
                f"{self._base}/oauth/tokens",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": self._scope,
                },
            )
            if resp.status_code != 200:
                raise ZendeskError(
                    f"token request failed: {resp.text[:200]}", resp.status_code
                )

            payload = resp.json()
            token = payload.get("access_token")
            if not token:
                raise ZendeskError("token response had no access_token", resp.status_code)

            expires_in = float(payload.get("expires_in", 1800))
            self._token = token
            self._expires_at = time.monotonic() + expires_in - _TOKEN_SKEW_SECONDS
            return token

    # ── transport ───────────────────────────────────────────────────

    async def _request(self, method: str, path: str, **kw: Any) -> dict[str, Any]:
        """The only place in this module that touches the network.

        Attach ``Authorization: Bearer <token>`` from _ensure_token, then loop up
        to _MAX_ATTEMPTS:

            2xx        → return resp.json()
            401        → clear self._token, refresh, retry ONCE. Once only: a bad
                         secret otherwise becomes a tight loop against Zendesk.
            429        → sleep float(resp.headers["Retry-After"]), retry.
                         Honor the server's number; never substitute your own.
            5xx        → sleep 2**attempt + random.uniform(0, 1), retry. The
                         jitter matters once more than one pod polls.
            other 4xx  → raise immediately; retrying a 404 or 422 is pointless.

        Attempts exhausted → ZendeskError carrying the last status.
        """
        http = self._open_http()
        url = f"{self._base}{path}"
        caller_headers = dict(kw.pop("headers", {}) or {})
        refreshed = False
        last_status: int | None = None
        for attempt in range(_MAX_ATTEMPTS):
            token = await self._ensure_token()
            headers = {**caller_headers, "Authorization": f"Bearer {token}"}
            resp = await http.request(method, url, headers=headers, **kw)
            last_status = resp.status_code
            if resp.is_success:
                return resp.json()

            if resp.status_code == 401 and not refreshed:
                refreshed = True
                self._token = None
                self._expires_at = 0.0
                continue

            if resp.status_code == 429:
                delay = _retry_after(resp)
            elif resp.status_code >= 500:
                delay = 2.0 ** attempt + random.uniform(0, 1)
            else:
                raise ZendeskError(f"{method} {path} -> {resp.status_code}: {resp.text[:200]}", resp.status_code)

            if attempt < _MAX_ATTEMPTS - 1:
                await asyncio.sleep(delay)

        raise ZendeskError(f"{method} {path} failed after {_MAX_ATTEMPTS} attempts", last_status)


    # ── reads ───────────────────────────────────────────────────────

    async def get_ticket(self, ticket_id: int | str) -> dict[str, Any]:
        """GET /api/v2/tickets/{id}.json → the ``ticket`` object."""
        return (await self._request("GET", f"/api/v2/tickets/{ticket_id}.json"))["ticket"]

    async def get_comments(self, ticket_id: int | str) -> list[dict[str, Any]]:
        """GET /api/v2/tickets/{id}/comments.json → the ``comments`` list.

        Not needed for M1. M2 wants it: a ticket's ``description`` is only the
        first comment, not the conversation.
        """
        return (await self._request("GET", f"/api/v2/tickets/{ticket_id}/comments.json"))["comments"]

    async def iter_tickets(
        self, cursor: str | None = None
    ) -> AsyncIterator[tuple[list[dict[str, Any]], str]]:
        """Page through the cursor-based incremental export.

        GET /api/v2/incremental/tickets/cursor.json
            start_time=0        when cursor is None (full backfill)
            cursor=<value>      otherwise

        Yield ``(page["tickets"], page["after_cursor"])`` per page; stop once
        ``page["end_of_stream"]`` is true.

        Three verified behaviours this must respect:
          1. This endpoint is rate-limited at 10 req/min, separately from the
             global 400/min. The 429 branch in _request absorbs it.
          2. ``after_cursor`` advances even when a page returns zero tickets, so
             the caller persists it on every yield — not only on non-empty pages.
          3. The same ticket can appear in two pages. That is by design, and why
             the upsert on (tenant_id, source, external_id) is load-bearing.
        """
        params: dict[str, Any] = {"cursor": cursor} if cursor else {"start_time": 0}
        while True:
            page = await self._request("GET", "/api/v2/incremental/tickets/cursor.json", params=params)
            after = page["after_cursor"]
            yield page.get("tickets", []), after
            if page.get("end_of_stream", True):
                return
            params = {"cursor": after}
