"""Shared-secret auth — the load-bearing guardrail for the hosting reversal.

Single-user app, so a long shared secret sent as a bearer token is sufficient and
avoids a user table. Every non-health route depends on require_auth. Constant-time
compare to avoid a timing oracle on the secret.
"""
import hmac

from fastapi import Header, HTTPException, status

from .config import config


async def require_auth(authorization: str = Header(default="")) -> None:
    prefix = "Bearer "
    token = authorization[len(prefix):] if authorization.startswith(prefix) else ""
    if not token or not hmac.compare_digest(token, config.APP_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
