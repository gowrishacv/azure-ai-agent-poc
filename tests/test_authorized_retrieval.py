import pytest

from app.agent import AgentService


def test_authorization_filter_rejects_any_unsafe_principal() -> None:
    with pytest.raises(ValueError, match="invalid search principal"):
        AgentService._authorization_filter(
            (
                "public",
                "group:22222222-2222-2222-2222-222222222222",
                "invalid value') or true",
            )
        )


def test_authorization_filter_can_be_disabled() -> None:
    assert AgentService._authorization_filter(None) is None


def test_authorization_filter_fails_closed_without_valid_principal() -> None:
    with pytest.raises(ValueError):
        AgentService._authorization_filter(("invalid principal",))
