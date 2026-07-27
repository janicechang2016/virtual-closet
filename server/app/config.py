"""Environment config. Fails fast on missing critical secrets at startup."""
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()  # no-op in prod where Railway injects real env vars


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"Missing required env var {name!r}. Set it in .env (local) or "
            f"Railway Variables (prod). See server/.env.example."
        )
    return val


class Config:
    # Critical — the app refuses to start without these.
    DATABASE_URL: str = _require("DATABASE_URL")
    # APP_SECRET is the reversal guardrail: no auth => no safe public endpoint.
    APP_SECRET: str = _require("APP_SECRET")
    BUDGET_CAP_USD: float = float(os.getenv("BUDGET_CAP_USD", "45"))

    # Browser origins allowed to call this API. Explicit allowlist, never "*" —
    # the bearer token travels in a header and a wildcard would hand it to any
    # page. Comma-separated in Railway Variables to add another.
    CORS_ORIGINS: list = [
        o.strip() for o in os.getenv(
            "CORS_ORIGINS",
            "https://virtual-closet-seven.vercel.app,http://localhost:8765",
        ).split(",") if o.strip()
    ]

    # Paid APIs — optional at startup (unused during the foundation phase).
    FAL_KEY: Optional[str] = os.getenv("FAL_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

    # Object storage (Cloudflare R2).
    R2_ACCOUNT_ID: Optional[str] = os.getenv("R2_ACCOUNT_ID")
    R2_ACCESS_KEY_ID: Optional[str] = os.getenv("R2_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY: Optional[str] = os.getenv("R2_SECRET_ACCESS_KEY")
    R2_BUCKET: str = os.getenv("R2_BUCKET", "virtual-closet")


config = Config()
