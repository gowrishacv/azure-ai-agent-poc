"""Normalized document contract shared by knowledge-source connectors."""

import hashlib
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.knowledge.authorization import normalize_allowed_principals


class KnowledgeDocument(BaseModel):
    """Canonical, immutable document passed from connectors to indexing."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9._:-]+$")
    title: str = Field(min_length=1, max_length=512)
    content: str
    source: str = Field(min_length=1, max_length=2048)
    source_type: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")
    source_version: str = Field(min_length=1, max_length=256)
    modified_at: datetime
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    allowed_principals: tuple[str, ...]
    is_deleted: bool = False

    @field_validator("modified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("modified_at must include a timezone")
        return value

    @field_validator("allowed_principals", mode="before")
    @classmethod
    def validate_allowed_principals(cls, value: object) -> tuple[str, ...]:
        return normalize_allowed_principals(value)

    @model_validator(mode="after")
    def validate_content(self) -> Self:
        if not self.is_deleted and not self.content:
            raise ValueError("Active documents require content")

        expected_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        if self.content_hash != expected_hash:
            raise ValueError("content_hash must match the normalized document content")
        return self

    @classmethod
    def from_source(cls, *, content: str, **source_fields: object) -> Self:
        """Build a document while deriving its integrity hash deterministically."""

        return cls(
            content=content,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            **source_fields,
        )
