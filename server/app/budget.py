"""Server-side budget hard-stop — Postgres-backed port of scripts/genlog.py.

check_budget() MUST be awaited before any paid API call (fal / SAM 3 / Anthropic).
It raises BudgetExceeded before the spend, exactly like the local genlog. Because the
endpoint is now public, this — not any client — is the authority on spend.
"""
from typing import Dict

from .db import pool

# $/image — kept in sync with genlog.py COST_TABLE. Update when pricing changes.
COST_TABLE: Dict[str, float] = {
    "fal-ai/nano-banana-pro": 0.134,
    "fal-ai/nano-banana-2": 0.039,
    "fal-ai/nano-banana-2/edit": 0.039,
    "fal-ai/flux-2-pro": 0.06,
    "fal-ai/idm-vton": 0.03,
    "fal-ai/face-swap": 0.02,
    "default": 0.134,  # assume worst case for unknown models
}


class BudgetExceeded(RuntimeError):
    pass


def estimate_cost(model: str, n_images: int = 1) -> float:
    return COST_TABLE.get(model, COST_TABLE["default"]) * n_images


async def spend_summary() -> dict:
    async with pool().acquire() as con:
        spent = await con.fetchval(
            "SELECT COALESCE(SUM(cost_usd), 0) FROM generation_log"
        )
        row = await con.fetchrow("SELECT cap_usd, phase FROM budget WHERE id = TRUE")
        by_model = await con.fetch(
            "SELECT model, SUM(cost_usd) AS c, COUNT(*) AS n "
            "FROM generation_log GROUP BY model ORDER BY c DESC"
        )
        count = await con.fetchval("SELECT COUNT(*) FROM generation_log")
    spent = float(spent or 0)
    cap = float(row["cap_usd"]) if row else 0.0
    return {
        "spent_usd": round(spent, 4),
        "cap_usd": cap,
        "remaining_usd": round(cap - spent, 4),
        "phase": row["phase"] if row else None,
        "generations": count,
        "by_model": {r["model"]: round(float(r["c"]), 4) for r in by_model},
    }


async def check_budget(model: str, n_images: int = 1) -> None:
    """Raise BudgetExceeded if the next call would blow the cap."""
    s = await spend_summary()
    est = estimate_cost(model, n_images)
    if s["spent_usd"] + est > s["cap_usd"]:
        raise BudgetExceeded(
            f"Blocked: spent ${s['spent_usd']:.2f} + est ${est:.2f} would exceed "
            f"cap ${s['cap_usd']:.2f}. Raise the cap deliberately (budget.cap_usd)."
        )


async def log_generation(model: str, n_images: int = 1,
                         request_id: str = None, meta: dict = None) -> None:
    """Record a completed paid call. Cost derived from COST_TABLE."""
    import json
    async with pool().acquire() as con:
        await con.execute(
            "INSERT INTO generation_log (model, n_images, cost_usd, request_id, meta) "
            "VALUES ($1, $2, $3, $4, $5)",
            model, n_images, estimate_cost(model, n_images),
            request_id, json.dumps(meta or {}),
        )
