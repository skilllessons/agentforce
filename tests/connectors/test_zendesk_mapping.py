"""to_ticket_row against a recorded Zendesk payload.

The fixture is a verbatim capture of seven real tickets from the sandbox, so
these assert against the shape Zendesk actually sends rather than the shape the
docs describe.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from agentforge.connectors.zendesk.mapping import to_ticket_row

_FIXTURE = Path(__file__).parent / "fixtures" / "zendesk_tickets.json"


@pytest.fixture(scope="module")
def tickets() -> dict[int, dict[str, Any]]:
    payload = json.loads(_FIXTURE.read_text())
    return {t["id"]: t for t in payload["tickets"]}


def test_external_id_is_a_string(tickets: dict[int, dict[str, Any]]) -> None:
    # Mix an int in once and ON CONFLICT (tenant_id, source, external_id) stops
    # matching — silent duplicates, not an error.
    row = to_ticket_row(tickets[7], "local-dev")
    assert row["external_id"] == "7"
    assert isinstance(row["external_id"], str)


def test_body_comes_from_description(tickets: dict[int, dict[str, Any]]) -> None:
    # Zendesk has no `body` field.
    assert to_ticket_row(tickets[7], "local-dev")["body"] == tickets[7]["description"]


def test_group_id_is_stringified(tickets: dict[int, dict[str, Any]]) -> None:
    assert to_ticket_row(tickets[7], "local-dev")["group_external_id"] == "54466266205844"


def test_null_group_id_stays_none(tickets: dict[int, dict[str, Any]]) -> None:
    # str(None) is the four-character string "None", which looks entirely
    # plausible in a TEXT column and is wrong.
    row = to_ticket_row({**tickets[7], "group_id": None}, "local-dev")
    assert row["group_external_id"] is None


@pytest.mark.parametrize(
    ("ticket_id", "expected"),
    [(1, ["zendesk_accelerated_setup"]), (7, [])],
)
def test_tags(
    tickets: dict[int, dict[str, Any]], ticket_id: int, expected: list[str]
) -> None:
    assert to_ticket_row(tickets[ticket_id], "local-dev")["tags"] == expected


def test_timestamps_are_aware_datetimes(tickets: dict[int, dict[str, Any]]) -> None:
    row = to_ticket_row(tickets[7], "local-dev")
    for key in ("external_created_at", "external_updated_at"):
        assert isinstance(row[key], datetime)
        assert row[key].tzinfo is not None


def test_row_carries_no_primary_key(tickets: dict[int, dict[str, Any]]) -> None:
    # The repo mints the nanoid; keeping it out is what makes this deterministic.
    assert "id" not in to_ticket_row(tickets[7], "local-dev")


def test_missing_id_raises(tickets: dict[int, dict[str, Any]]) -> None:
    payload = {k: v for k, v in tickets[7].items() if k != "id"}
    with pytest.raises(KeyError):
        to_ticket_row(payload, "local-dev")


def test_every_fixture_ticket_maps(tickets: dict[int, dict[str, Any]]) -> None:
    rows = [to_ticket_row(t, "local-dev") for t in tickets.values()]
    assert len(rows) == 7
    assert all(r["source"] == "zendesk" for r in rows)
