"""FastAPI app. /health is open; everything else requires the bearer token.

Foundation scope: this exposes the guardrails (auth + budget) and the async job
plumbing. Real endpoints (ingest, stylist, tryon, insights, graph — v2 §4) land in
later phases and all hang off `require_auth` + `check_budget`.
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from .auth import require_auth
from .budget import spend_summary
from .db import close_pool, init_pool
from . import queue


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="Virtual Closet v2", lifespan=lifespan)


@app.get("/health")
async def health():
    """Open, unauthenticated — for Railway health checks only. No data leaves here."""
    return {"status": "ok"}


@app.get("/budget", dependencies=[Depends(require_auth)])
async def budget():
    return await spend_summary()


@app.get("/jobs/{job_id}", dependencies=[Depends(require_auth)])
async def job_status(job_id: str):
    job = await queue.get_job(job_id)
    return job or {"error": "not found"}


# Example of the async pattern every future generation endpoint follows:
# enqueue a job, return its id, poll /jobs/{id}. Nothing blocks the request.
@app.post("/jobs/echo", dependencies=[Depends(require_auth)])
async def enqueue_echo(payload: dict):
    job_id = await queue.enqueue("echo", payload)
    return {"job_id": job_id}
