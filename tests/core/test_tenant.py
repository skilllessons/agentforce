import asyncio

from agentforge.core.runtime.tenant import current_tenant, get_tenant


def test_default_is_none() -> None:
    assert get_tenant() is None


async def test_visible_inside_gather_and_cleared_after_reset() -> None:
    token = current_tenant.set("acme")
    try:
        seen = await asyncio.gather(_read(), _read())
        assert seen == ["acme", "acme"]
    finally:
        current_tenant.reset(token)
    assert get_tenant() is None


async def _read() -> str | None:
    await asyncio.sleep(0)
    return get_tenant()
