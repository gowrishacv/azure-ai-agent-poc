import pytest

from app.agent import AgentService


def test_authorization_filter_uses_only_safe_principals() -> None:
    result = AgentService._authorization_filter(
        (
            "public",
            "group:22222222-2222-2222-2222-222222222222",
            "invalid value') or true",
        )
    )
    assert result == (
        "allowed_principals/any(principal: search.in(principal, "
        "'group:22222222-2222-2222-2222-222222222222,public', ','))"
    )


def test_authorization_filter_can_be_disabled() -> None:
    assert AgentService._authorization_filter(None) is None


def test_authorization_filter_fails_closed_without_valid_principal() -> None:
    with pytest.raises(ValueError):
        AgentService._authorization_filter(("invalid principal",))
