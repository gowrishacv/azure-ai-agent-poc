"""Shared source-connector contracts and checkpoint metadata."""

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.knowledge.contracts import KnowledgeDocument


class SyncCheckpoint(BaseModel):
    """Opaque source cursor persisted without document content."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    source: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")
    cursor: str = Field(min_length=1, max_length=8192)
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("updated_at must include a timezone")
        return value


class SourceBatch(BaseModel):
    """One connector result ready for deterministic indexing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_type: str
    documents: tuple[KnowledgeDocument, ...] = ()
    deleted_ids: tuple[str, ...] = ()
    source_ids: frozenset[str] = frozenset()
    cursor: str
    full_sync: bool = False


class KnowledgeSourceConnector(Protocol):
    """Minimal interface implemented by every enterprise source connector."""

    def collect(self, cursor: str | None = None, *, full: bool = False) -> SourceBatch: ...

