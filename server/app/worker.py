"""Async job worker. Polls the Postgres queue and dispatches by job type.

Every handler that spends money MUST `await check_budget(...)` first and
`await log_generation(...)` after — the worker is where paid calls actually happen,
so the budget hard-stop lives on this path. No paid handlers exist yet (foundation).
"""
import asyncio

from .db import close_pool, init_pool
from . import queue

POLL_SECONDS = 2.0


async def handle(job: dict) -> dict:
    """Dispatch by job['type']. Extend as phases add real jobs."""
    if job["type"] == "echo":
        return {"echo": job["payload"]}
    # Future: 'ingest', 'tryon', 'attribute_extract' — each budget-gated:
    #   await check_budget(model, n_images); ...call...; await log_generation(...)
    raise ValueError(f"unknown job type: {job['type']}")


async def run() -> None:
    await init_pool()
    print("[worker] started; polling queue")
    try:
        while True:
            job = await queue.claim()
            if job is None:
                await asyncio.sleep(POLL_SECONDS)
                continue
            try:
                result = await handle(job)
                await queue.finish(job["id"], result)
                print(f"[worker] done {job['id']} ({job['type']})")
            except Exception as e:  # noqa: BLE001 — record and move on
                await queue.fail(job["id"], str(e))
                print(f"[worker] failed {job['id']}: {e}")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(run())
