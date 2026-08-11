from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import auth
from app.config import Settings


def bearer_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/ask",
            "headers": [(b"authorization", b"Bearer test-token")],
        }
    )


@pytest.mark.asyncio
async def test_authorize_extracts_search_principals(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "_jwk_client",
        lambda _tenant: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key="key")
        ),
    )
    monkeypatch.setattr(
        auth.jwt,
        "decode",
        lambda *_args, **_kwargs: {
            "oid": "11111111-1111-1111-1111-111111111111",
            "tid": "tenant",
            "groups": ["22222222-2222-2222-2222-222222222222"],
            "roles": ["AI.Agent.User"],
            "scp": "access_as_user",
        },
    )
    settings = Settings(
        require_auth=True,
        auth_tenant_id="tenant",
        auth_audience="api://agent",
        auth_required_role="AI.Agent.User",
        auth_required_scope="access_as_user",
    )

    principal = await auth.authorize(bearer_request(), settings)

    assert principal.authenticated is True
    assert principal.scopes == ("access_as_user",)
    assert principal.search_principals == (
        "group:22222222-2222-2222-2222-222222222222",
        "public",
        "role:AI.Agent.User",
        "user:11111111-1111-1111-1111-111111111111",
    )


@pytest.mark.asyncio
async def test_authorize_rejects_missing_required_role(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "_jwk_client",
        lambda _tenant: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key="key")
        ),
    )
    monkeypatch.setattr(
        auth.jwt,
        "decode",
        lambda *_args, **_kwargs: {"oid": "user-1", "tid": "tenant", "roles": []},
    )
    settings = Settings(
        require_auth=True,
        auth_tenant_id="tenant",
        auth_audience="api://agent",
        auth_required_role="AI.Agent.User",
    )

    with pytest.raises(HTTPException) as caught:
        await auth.authorize(bearer_request(), settings)

    assert caught.value.status_code == 403


@pytest.mark.asyncio
async def test_authorize_rejects_missing_required_scope(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "_jwk_client",
        lambda _tenant: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key="key")
        ),
    )
    monkeypatch.setattr(
        auth.jwt,
        "decode",
        lambda *_args, **_kwargs: {"oid": "user-1", "tid": "tenant", "scp": "other"},
    )
    settings = Settings(
        require_auth=True,
        auth_tenant_id="tenant",
        auth_audience="api://agent",
        auth_required_scope="access_as_user",
    )

    with pytest.raises(HTTPException) as caught:
        await auth.authorize(bearer_request(), settings)

    assert caught.value.status_code == 403


@pytest.mark.asyncio
async def test_anonymous_mode_exposes_only_public_principal() -> None:
    principal = await auth.authorize(Request({"type": "http", "headers": []}), Settings())
    assert principal.search_principals == ("public",)
