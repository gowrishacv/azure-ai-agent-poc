from functools import lru_cache

import jwt
from fastapi import HTTPException, Request, status
from jwt import PyJWKClient

from app.config import Settings


@lru_cache
def _jwk_client(tenant_id: str) -> PyJWKClient:
    return PyJWKClient(
        f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
        cache_jwk_set=True,
        lifespan=3600,
    )


async def authorize(request: Request, settings: Settings) -> None:
    if not settings.require_auth:
        return
    if not settings.auth_tenant_id or not settings.auth_audience:
        raise HTTPException(status_code=500, detail="Authentication is not configured")
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    token = header.removeprefix("Bearer ").strip()
    try:
        key = _jwk_client(settings.auth_tenant_id).get_signing_key_from_jwt(token)
        jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            audience=settings.auth_audience,
            issuer=f"https://login.microsoftonline.com/{settings.auth_tenant_id}/v2.0",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
        ) from exc

