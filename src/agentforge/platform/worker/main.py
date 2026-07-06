"""Worker process entry point — drains the insurance queue with the real LLM.

create_default_router() returns AnthropicRouter when ANTHROPIC_API_KEY is set
(falls back to LiteLLM otherwise). The router is stateless, so it's built once.
"""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from agentforge.core.llm.factory import create_default_router
from agentforge.core.llm.types import LLMRouter
from agentforge.platform.worker.loop import process_one
from agentforge.core.observability import configure_logging
from agentforge.core.observability import get_logger


async def _drain(vertical: str, router: LLMRouter) -> None:
    log = get_logger("worker")
    log.info("worker.started", vertical=vertical)
    while True:
        # process_one blocks up to 5s on an empty queue (BRPOP), then returns
        # None — so this loop stays alive and keeps polling, no busy-spin.
        run_id = await process_one(vertical, router)
        if run_id is not None:
            log.info("run.processed", run_id=run_id)


def main() -> None:
    load_dotenv()
    configure_logging()
    router = create_default_router()
    asyncio.run(_drain("insurance", router))


if __name__ == "__main__":
    main()
