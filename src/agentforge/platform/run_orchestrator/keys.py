"""Redis key naming for the run orchestrator.

One place for queue/channel key strings so producers and consumers never
drift. Format: af:<resource>:<scope>.
"""

from __future__ import annotations


def queue_key(vertical: str) -> str:
    """List key the worker BRPOPs from. One queue per vertical.

    e.g. queue_key("insurance") -> "af:queue:insurance"
    """
    return  f"af:queue:{vertical}"
