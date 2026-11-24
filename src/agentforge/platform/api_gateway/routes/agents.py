from __future__ import annotations

from fastapi import APIRouter

from agentforge.verticals.insurance import INSURANCE_VERTICAL
from agentforge.verticals.support import SUPPORT_VERTICAL

router = APIRouter(prefix="/v1", tags=["agents"])

_VERTICALS = [INSURANCE_VERTICAL,SUPPORT_VERTICAL]


@router.get("/agents")
async def list_agents() -> dict:
    return {
        "verticals":[
            {"id": v.vertical, "tools": [t.name for t in v.tools]}
            for v in _VERTICALS
        ]
    }
