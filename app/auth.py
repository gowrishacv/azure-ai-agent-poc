import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from fastapi import HTTPException, Request, status
from jwt import PyJWKClient

from app.config import Settings

_SAFE_PRINCIPAL = re.compile(r"^[A-Za-z0-9._:@-]{1,160}$")


@dataclass(frozen=True)
class Principal:
    authenticated: bool
    subject: str | None
    tenant_id: str | None
    groups: tuple[str, ...]
    roles: tuple[str, ...]
    scopes: tuple[str, ...]

    @property
    def search_principals(self) -> tuple[str, ...]:
        values = ["public"]
        if self.subject:
            values.append(f"user:{self.subject}")
        values.extend(f"group:{group}" for group in self.groups)
        values.extend(f"role:{role}" for role in self.roles)
        return tuple(sorted(set(values)))


ANONYMOUS_PRINCIPAL = Principal(
    authenticated=False,
    subject=None,
    tenant_id=None,
    groups=(),
    roles=(),
    scopes=(),
)


@lru_cache
def _jwk_client(tenant_id: str) -> PyJWKClient:
    return PyJWKClient(
        f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
        cache_jwk_set=True,
        lifespan=3600,
    )


def _claim_values(claims: dict[str, Any], name: str) -> tuple[str, ...]:
    raw_values = claims.get(name, [])
    if isinstance(raw_values, str):
        raw_values = [raw_values]
    if not isinstance(raw_values, list):
        return ()
    return tuple(
        sorted(
            {
                value
                for value in raw_values
                if isinstance(value, str) and _SAFE_PRINCIPAL.fullmatch(value)
            }
        )
    )


def _scope_values(claims: dict[str, Any]) -> tuple[str, ...]:
    raw_scopes = claims.get("scp", "")
    if not isinstance(raw_scopes, str):
        return ()
    return tuple(
        sorted(
            {
                value
                for value in raw_scopes.split()
                if _SAFE_PRINCIPAL.fullmatch(value)
            }
        )
    )


async def authorize(request: Request, settings: Settings) -> Principal:
    if not settings.require_auth:
        request.state.principal = ANONYMOUS_PRINCIPAL
        return ANONYMOUS_PRINCIPAL
    if not settings.auth_tenant_id or not settings.auth_audience:
        raise HTTPException(status_code=500, detail="Authentication is not configured")
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    token = header.removeprefix("Bearer ").strip()
    try:
        key = _jwk_client(settings.auth_tenant_id).get_signing_key_from_jwt(token)
        claims = jwt.decode(
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

    subject = claims.get("oid") or claims.get("sub")
    if not isinstance(subject, str) or not _SAFE_PRINCIPAL.fullmatch(subject):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token does not contain a valid subject",
        )
    roles = _claim_values(claims, "roles")
    scopes = _scope_values(claims)
    if settings.auth_required_role and settings.auth_required_role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Required application role is missing",
        )
    if settings.auth_required_scope and settings.auth_required_scope not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Required delegated scope is missing",
        )
    principal = Principal(
        authenticated=True,
        subject=subject,
        tenant_id=str(claims.get("tid", settings.auth_tenant_id)),
        groups=_claim_values(claims, "groups"),
        roles=roles,
        scopes=scopes,
    )
    request.state.principal = principal
    return principal
