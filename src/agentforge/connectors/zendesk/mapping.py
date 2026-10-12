"""Zendesk payload → normalized row shape.

Pure and deterministic: no clock, no I/O, no id generation. That is what lets
these be tested by exact equality against a recorded payload.

The row carries no ``id`` — the repo mints the nanoid. Person foreign keys are
arguments rather than derived here, because a ticket payload carries only
``requester_id`` (the source's integer), not our internal person id.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

SOURCE = "zendesk"


def _opt_str(value: Any) -> str | None:
    """str() an optional id, preserving None.

    ``str(None)`` is the four-character string "None", which looks entirely
    plausible in a TEXT column. ``group_id`` is null on plenty of tickets.
    """
    return None if value is None else str(value)


def _ts(value: str | None) -> datetime | None:
    """Zendesk ISO-8601 (``2026-10-11T00:40:31Z``) → aware datetime."""
    return None if value is None else datetime.fromisoformat(value)


def to_ticket_row(
    ticket: dict[str, Any],
    tenant_id: str,
    requester_person_id: str | None = None,
    assignee_person_id: str | None = None,
) -> dict[str, Any]:
    """Map one Zendesk ticket to a ``tickets`` row, minus the primary key.

    ``ticket["id"]`` is required — a payload without it is a bug worth a
    KeyError, not a silent null. Everything else is optional.

    ``raw`` stays a dict; serializing to JSON is the repo's concern.
    """
    return {
        "tenant_id": tenant_id,
        "source": SOURCE,
        "external_id": str(ticket["id"]),
        "subject": ticket.get("subject"),
        "body": ticket.get("description"),
        "requester_person_id": requester_person_id,
        "assignee_person_id": assignee_person_id,
        "status": ticket.get("status"),
        "priority": ticket.get("priority"),
        "tags": ticket.get("tags") or [],
        "group_external_id": _opt_str(ticket.get("group_id")),
        "external_created_at": _ts(ticket.get("created_at")),
        "external_updated_at": _ts(ticket.get("updated_at")),
        "raw": ticket,
    }
