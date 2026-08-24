"""Idempotent application of connector batches to a knowledge index."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.connectors.base import SourceBatch
from app.knowledge.contracts import KnowledgeDocument


class KnowledgeSink(Protocol):
    """Index operations needed by the connector synchronizer."""

    def list_documents(self, source_type: str) -> dict[str, KnowledgeDocument]: ...

    def upsert(self, document: KnowledgeDocument) -> None: ...

    def delete(self, document_id: str) -> None: ...


class SyncReport(BaseModel):
    """Privacy-safe operational metadata suitable for logs and metrics."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    processed: int = Field(ge=0)
    upserted: int = Field(ge=0)
    unchanged: int = Field(ge=0)
    deleted: int = Field(ge=0)
    rejected: int = Field(ge=0, default=0)
    duration_ms: int = Field(ge=0, default=0)
    cursor_age_seconds: int = Field(ge=0, default=0)
    error_category: str | None = None


class InMemoryKnowledgeSink:
    """Deterministic sink used by unit tests and local connector rehearsals."""

    def __init__(self) -> None:
        self.documents: dict[str, KnowledgeDocument] = {}

    def list_documents(self, source_type: str) -> dict[str, KnowledgeDocument]:
        return {
            document_id: document
            for document_id, document in self.documents.items()
            if document.source_type == source_type
        }

    def upsert(self, document: KnowledgeDocument) -> None:
        self.documents[document.id] = document

    def delete(self, document_id: str) -> None:
        self.documents.pop(document_id, None)


def synchronize(
    batch: SourceBatch,
    sink: KnowledgeSink,
    *,
    reconcile: bool = False,
    duration_ms: int = 0,
    cursor_age_seconds: int = 0,
) -> SyncReport:
    """Apply a source batch without duplicates and optionally remove stale items."""

    existing = sink.list_documents(batch.source_type)
    upserted = 0
    unchanged = 0
    deleted = 0

    for document in batch.documents:
        if existing.get(document.id) == document:
            unchanged += 1
            continue
        sink.upsert(document)
        upserted += 1

    ids_to_delete = set(batch.deleted_ids)
    if reconcile:
        if not batch.full_sync:
            raise ValueError("Reconciliation requires a full source sync")
        ids_to_delete.update(set(existing) - set(batch.source_ids))

    for document_id in sorted(ids_to_delete):
        if document_id in existing:
            deleted += 1
        sink.delete(document_id)

    return SyncReport(
        processed=len(batch.documents) + len(batch.deleted_ids),
        upserted=upserted,
        unchanged=unchanged,
        deleted=deleted,
        duration_ms=duration_ms,
        cursor_age_seconds=cursor_age_seconds,
    )
