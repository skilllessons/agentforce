from __future__ import annotations
from contextlib import asynccontextmanager


import uvicorn
from fastapi import FastAPI

from agentforge.core.db.client import close_db, get_pool
from agentforge.core.observability import configure_logging, get_logger
from agentforge.core.tools.redis_client import close_redis
from agentforge.platform.api_gateway.routes import agents, runs



log = get_logger("api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    configure_logging()
    await get_pool()          # warm the DB pool at boot, not on first request
    log.info("api.startup")
    yield  # ← server serves requests here
    # --- shutdown ---
    await close_db()
    await close_redis()
    log.info("api.shutdown")

app = FastAPI(
    title="AgentForge API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(runs.router)
app.include_router(agents.router)

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)


