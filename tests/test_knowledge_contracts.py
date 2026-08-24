import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.knowledge.authorization import normalize_allowed_principals
from app.knowledge.contracts import KnowledgeDocument

FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "sharepoint"


def _load_fixture(name: str) -> list[dict]:
    return json.loads((FIXTURE_DIRECTORY / name).read_text(encoding="utf-8"))


def test_sharepoint_scenarios_create_normalized_documents() -> None:
    for scenario in _load_fixture("scenarios.json"):
        source = scenario["document"]

        document = KnowledgeDocument.from_source(
            source_type="sharepoint",
            **source,
        )

        assert list(document.allowed_principals) == scenario["expected_principals"]
        assert (
            document.content_hash == hashlib.sha256(source["content"].encode("utf-8")).hexdigest()
        )
        assert document.modified_at.tzinfo is not None


def test_deleted_document_can_use_empty_content() -> None:
    document = KnowledgeDocument.from_source(
        id="sp-deleted-001",
        title="Deleted synthetic document",
        content="",
        source="sharepoint://synthetic/sites/platform/deleted-001",
        source_type="sharepoint",
        source_version="9",
        modified_at=datetime(2026, 8, 24, 8, 0, tzinfo=UTC),
        allowed_principals=["group:platform-engineers"],
        is_deleted=True,
    )

    assert document.is_deleted is True
    assert document.content_hash == hashlib.sha256(b"").hexdigest()


def test_active_document_rejects_empty_content() -> None:
    with pytest.raises(ValidationError, match="Active documents require content"):
        KnowledgeDocument.from_source(
            id="sp-active-001",
            title="Active synthetic document",
            content="",
            source="sharepoint://synthetic/sites/platform/active-001",
            source_type="sharepoint",
            source_version="1",
            modified_at="2026-08-24T08:00:00Z",
            allowed_principals=["public"],
        )


def test_document_rejects_naive_modified_timestamp() -> None:
    with pytest.raises(ValidationError, match="modified_at must include a timezone"):
        KnowledgeDocument.from_source(
            id="sp-active-001",
            title="Active synthetic document",
            content="Synthetic content",
            source="sharepoint://synthetic/sites/platform/active-001",
            source_type="sharepoint",
            source_version="1",
            modified_at="2026-08-24T08:00:00",
            allowed_principals=["public"],
        )


def test_document_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        KnowledgeDocument.from_source(
            id="sp-active-001",
            title="Active synthetic document",
            content="Synthetic content",
            source="sharepoint://synthetic/sites/platform/active-001",
            source_type="sharepoint",
            source_version="1",
            modified_at="2026-08-24T08:00:00Z",
            allowed_principals=["public"],
            tenant_secret="must-not-be-accepted",
        )


def test_malformed_acl_fixtures_fail_closed() -> None:
    for scenario in _load_fixture("malformed-acls.json"):
        with pytest.raises(ValueError):
            normalize_allowed_principals(
                scenario["allowed_principals"],
                document_id=scenario["scenario"],
            )


def test_acl_normalization_rejects_string_instead_of_collection() -> None:
    with pytest.raises(ValueError, match="non-empty collection"):
        normalize_allowed_principals("public", document_id="wrong-shape")


def test_synthetic_personas_cover_authorization_boundaries() -> None:
    personas = _load_fixture("personas.json")

    assert {persona["persona"] for persona in personas} == {
        "anonymous",
        "authorized-group-member",
        "authorized-role-holder",
        "authorized-user",
        "disallowed-user",
        "group-overage-user",
        "public-user",
    }
    for persona in personas:
        assert "tenant_id" not in persona
        assert tuple(persona["expected_principals"]) == normalize_allowed_principals(
            persona["expected_principals"],
            document_id=persona["persona"],
        )
