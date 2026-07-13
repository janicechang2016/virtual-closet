#!/usr/bin/env python3
"""Generation logger + cost meter for the virtual closet.

Every image-API call is appended to logs/generations.jsonl. The budget cap
(logs/budget.json) is a HARD stop: check_budget() raises before any call
that would exceed it.

Usage as a library:
    from genlog import log_generation, check_budget, spend_summary
Usage as a CLI:
    python3 scripts/genlog.py summary
    python3 scripts/genlog.py set-cap 25.00
"""
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "generations.jsonl"
BUDGET = ROOT / "logs" / "budget.json"

# $/image, from plan §6 — update when fal pricing changes.
COST_TABLE = {
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


def _read_budget():
    if BUDGET.exists():
        return json.loads(BUDGET.read_text())
    return {"cap_usd": 25.00, "phase": "unset"}


def spend_summary():
    total, by_model, count = 0.0, {}, 0
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            c = e.get("cost_usd", 0.0)
            total += c
            count += 1
            by_model[e.get("model", "?")] = by_model.get(e.get("model", "?"), 0.0) + c
    b = _read_budget()
    return {
        "spent_usd": round(total, 4),
        "cap_usd": b["cap_usd"],
        "remaining_usd": round(b["cap_usd"] - total, 4),
        "generations": count,
        "by_model": {k: round(v, 4) for k, v in by_model.items()},
    }


def estimate_cost(model, n_images=1):
    return COST_TABLE.get(model, COST_TABLE["default"]) * n_images


def check_budget(model, n_images=1):
    """Raise BudgetExceeded if the next call would blow the cap."""
    s = spend_summary()
    est = estimate_cost(model, n_images)
    if s["spent_usd"] + est > s["cap_usd"]:
        raise BudgetExceeded(
            f"Blocked: spent ${s['spent_usd']:.2f} + est ${est:.2f} would exceed "
            f"cap ${s['cap_usd']:.2f}. Raise the cap deliberately with: "
            f"python3 scripts/genlog.py set-cap <usd>"
        )
    return est


def log_generation(model, prompt, purpose, ref_images=None, output_path=None,
                   cost_usd=None, seed=None, request_id=None, outcome="pending-qa",
                   parent_render=None, extra=None):
    entry = {
        "id": uuid.uuid4().hex[:12],
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "purpose": purpose,  # avatar-candidate | avatar-edit | character-sheet | tryon | tryon-edit | smoke-test
        "prompt": prompt,
        "ref_images": ref_images or [],
        "output_path": str(output_path) if output_path else None,
        "cost_usd": cost_usd if cost_usd is not None else estimate_cost(model),
        "seed": seed,
        "request_id": request_id,
        "outcome": outcome,      # pending-qa | pass | auto-retry | needs-user | failed
        "parent_render": parent_render,  # id of render this is an edit of
        "feedback": [],
    }
    if extra:
        entry.update(extra)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry["id"]


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if cmd == "summary":
        print(json.dumps(spend_summary(), indent=2))
    elif cmd == "set-cap":
        b = _read_budget()
        b["cap_usd"] = float(sys.argv[2])
        BUDGET.write_text(json.dumps(b, indent=2))
        print(f"Cap set to ${b['cap_usd']:.2f}")
    else:
        sys.exit(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
