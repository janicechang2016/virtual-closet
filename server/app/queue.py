"""Postgres-backed job queue. No Redis needed at this scale.

enqueue() from request handlers; the worker claims one job at a time with
FOR UPDATE SKIP LOCKED so multiple workers never grab the same job.
"""
import json
from typing import Optional

from .db import pool


async def enqueue(job_type: str, payload: dict) -> str:
    async with pool().acquire() as con:
        job_id = await con.fetchval(
            "INSERT INTO job_queue (type, payload) VALUES ($1, $2) RETURNING id",
            job_type, json.dumps(payload),
        )
    return str(job_id)


async def claim() -> Optional[dict]:
    """Atomically claim the oldest queued job. Returns None if the queue is empty."""
    async with pool().acquire() as con:
        row = await con.fetchrow(
            """
            UPDATE job_queue SET status = 'running', locked_at = now(),
                   attempts = attempts + 1, updated_at = now()
            WHERE id = (
                SELECT id FROM job_queue WHERE status = 'queued'
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED LIMIT 1
            )
            RETURNING id, type, payload
            """
        )
    if row is None:
        return None
    return {"id": str(row["id"]), "type": row["type"], "payload": row["payload"]}


async def finish(job_id: str, result: dict) -> None:
    async with pool().acquire() as con:
        await con.execute(
            "UPDATE job_queue SET status='done', result=$2, updated_at=now() WHERE id=$1",
            job_id, json.dumps(result),
        )


async def fail(job_id: str, error: str) -> None:
    async with pool().acquire() as con:
        await con.execute(
            "UPDATE job_queue SET status='error', error=$2, updated_at=now() WHERE id=$1",
            job_id, error,
        )


async def get_job(job_id: str) -> Optional[dict]:
    async with pool().acquire() as con:
        row = await con.fetchrow(
            "SELECT id, type, status, result, error FROM job_queue WHERE id = $1", job_id
        )
    if row is None:
        return None
    return {
        "id": str(row["id"]), "type": row["type"], "status": row["status"],
        "result": row["result"], "error": row["error"],
    }
