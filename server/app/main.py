"""FastAPI app. /health is open; everything else requires the bearer token.

Foundation scope: this exposes the guardrails (auth + budget) and the async job
plumbing. Real endpoints (ingest, stylist, tryon, insights, graph — v2 §4) land in
later phases and all hang off `require_auth` + `check_budget`.
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .auth import require_auth
from .budget import spend_summary
from .config import config
from .db import close_pool, init_pool
from . import queue, wear


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="Virtual Closet v2", lifespan=lifespan)

# The wear logger runs in a browser on a different origin (the Vercel site), so
# this is the first time anything but curl has called the API. Origins are an
# explicit allowlist, never "*": with credentials in a bearer header, a wildcard
# would let any page a phone visits spend this token.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


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


# ── wear logging (Phase 3) ────────────────────────────────────────────────────
# The first domain endpoint. Everything above is guardrail or plumbing; this is
# the write path they exist to protect.
@app.post("/wear", dependencies=[Depends(require_auth)])
async def post_wear(payload: dict):
    try:
        return await wear.log_wear(payload.get("garment_ids") or [],
                                   payload.get("worn_on"))
    except wear.WearError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/wear", dependencies=[Depends(require_auth)])
async def get_wear(limit: int = 30):
    return await wear.recent_wears(limit)


@app.delete("/wear/{wear_id}", dependencies=[Depends(require_auth)])
async def remove_wear(wear_id: str):
    try:
        return await wear.delete_wear(wear_id)
    except wear.WearError as e:
        raise HTTPException(status_code=400, detail=str(e))
