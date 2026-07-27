"""Wear logging — the first domain endpoint this API has ever had.

Everything before this was guardrails (auth, budget) and plumbing (queue). This
is the write path they were built to protect, and the reason the hosted Postgres
earns its keep: a wear happens away from the laptop, so it has to be recordable
from a phone.

Design note worth keeping: `wear_log` references `outfit_id` and nothing else, so
an ad-hoc combination becomes an outfit row before it can be logged. That means
every wear grows the corpus the stylist learns from — a garment-level wear table
would have grown a counter and nothing else.
"""
from datetime import date
from typing import Optional

from .db import pool


class WearError(ValueError):
    """Bad input from the client — surfaces as a 400, never a 500."""


async def _resolve_outfit(con, garment_ids: list) -> tuple:
    """Find the outfit for this exact set of garments, or make one.

    Matching is on the SORTED set, so the same three pieces logged in a different
    tap order are the same outfit rather than a duplicate. Returns
    (outfit_id, created).
    """
    ordered = sorted(set(garment_ids))

    known = await con.fetch("SELECT id FROM garment WHERE id = ANY($1::text[])", ordered)
    if len(known) != len(ordered):
        missing = set(ordered) - {r["id"] for r in known}
        raise WearError(f"unknown garment(s): {', '.join(sorted(missing))}")

    row = await con.fetchrow(
        """
        SELECT id FROM outfit
         WHERE (SELECT array_agg(g ORDER BY g) FROM unnest(garment_ids) g) = $1::text[]
         -- prefer a published look over an ad-hoc one, so wearing something you
         -- have published counts against the look rather than forking a twin
         ORDER BY (source = 'manual') DESC, created_at ASC
         LIMIT 1
        """,
        ordered,
    )
    if row:
        return row["id"], False

    new_id = await con.fetchval(
        """
        INSERT INTO outfit (garment_ids, source, rationale)
        VALUES ($1::text[], 'worn', 'logged as worn')
        RETURNING id
        """,
        ordered,
    )
    return new_id, True


async def log_wear(garment_ids: list, worn_on: Optional[str] = None) -> dict:
    if not garment_ids or not isinstance(garment_ids, list):
        raise WearError("garment_ids must be a non-empty list")
    if len(garment_ids) > 12:
        raise WearError("that is more than twelve garments — probably a mistake")

    day: Optional[date] = None
    if worn_on:
        try:
            day = date.fromisoformat(worn_on)
        except ValueError:
            raise WearError("worn_on must be an ISO date, e.g. 2026-07-26")
        if day > date.today():
            raise WearError("cannot log a wear in the future")

    async with pool().acquire() as con:
        async with con.transaction():
            outfit_id, created = await _resolve_outfit(con, garment_ids)
            wear_id = await con.fetchval(
                """
                INSERT INTO wear_log (outfit_id, worn_on, confirmed_by)
                VALUES ($1, COALESCE($2::date, CURRENT_DATE), 'user')
                RETURNING id
                """,
                outfit_id, day,
            )
            total = await con.fetchval(
                "SELECT count(*) FROM wear_log WHERE outfit_id = $1", outfit_id)

    return {
        "ok": True,
        "wear_id": str(wear_id),
        "outfit_id": str(outfit_id),
        "outfit_created": created,
        "times_worn": total,
    }


async def recent_wears(limit: int = 30) -> dict:
    limit = max(1, min(int(limit), 200))
    async with pool().acquire() as con:
        rows = await con.fetch(
            """
            SELECT w.id, w.worn_on, o.id AS outfit_id, o.garment_ids, o.source
              FROM wear_log w
              JOIN outfit o ON o.id = w.outfit_id
             ORDER BY w.worn_on DESC, w.id DESC
             LIMIT $1
            """,
            limit,
        )
    return {"wears": [{
        "wear_id": str(r["id"]),
        "worn_on": r["worn_on"].isoformat(),
        "outfit_id": str(r["outfit_id"]),
        "garment_ids": list(r["garment_ids"]),
        "source": r["source"],
    } for r in rows]}


async def delete_wear(wear_id: str) -> dict:
    """Undo. Mis-taps are the likeliest input error on a phone, so removing a wear
    has to be as cheap as adding one — the same revisability the feedback logs
    already promise.

    An outfit this logger CREATED and that now has no wears left goes with it.
    Leaving it was the first behaviour and it is wrong: these outfits are destined
    to feed the stylist's corpus, so an orphan is a combination she mis-tapped
    once and undid, quietly teaching the model anyway. Published looks and stylist
    suggestions are never touched — they exist independently of any wear.
    """
    async with pool().acquire() as con:
        async with con.transaction():
            try:
                row = await con.fetchrow(
                    "DELETE FROM wear_log WHERE id = $1::uuid RETURNING outfit_id", wear_id)
            except Exception:
                raise WearError("wear_id must be a uuid")
            if row is None:
                return {"ok": True, "deleted": False, "outfit_removed": False}
            gone = await con.execute(
                """
                DELETE FROM outfit o
                 WHERE o.id = $1 AND o.source = 'worn'
                   AND NOT EXISTS (SELECT 1 FROM wear_log w WHERE w.outfit_id = o.id)
                """,
                row["outfit_id"],
            )
    return {"ok": True, "deleted": True,
            "outfit_removed": gone.split()[-1] == "1"}
