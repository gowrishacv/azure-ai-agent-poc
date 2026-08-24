from datetime import UTC, datetime

import pytest

from app.connectors.base import SyncCheckpoint
from app.connectors.sharepoint import (
    SharePointConnector,
    SharePointPage,
    TransientGraphError,
    UnresolvedPermissionError,
)
from app.knowledge.contracts import KnowledgeDocument
from app.knowledge.sync import InMemoryKnowledgeSink, synchronize
from scripts.sync_sharepoint import load_checkpoint, save_checkpoint


class FakeGraphReader:
    def __init__(
        self,
        *,
        pages: dict[str | None, SharePointPage],
        content: dict[str, str],
        permissions: dict[str, list[dict[str, str]]],
        transient_page_failures: int = 0,
    ) -> None:
        self.pages = pages
        self.content = content
        self.permissions = permissions
        self.transient_page_failures = transient_page_failures
        self.page_calls: list[str | None] = []
        self.content_calls: list[str] = []
        self.permission_calls: list[str] = []

    def get_page(self, cursor: str | None) -> SharePointPage:
        self.page_calls.append(cursor)
        if self.transient_page_failures:
            self.transient_page_failures -= 1
            raise TransientGraphError("synthetic throttling")
        return self.pages[cursor]

    def get_content(self, item_id: str) -> str:
        self.content_calls.append(item_id)
        return self.content[item_id]

    def get_permissions(self, item_id: str) -> list[dict[str, str]]:
        self.permission_calls.append(item_id)
        return self.permissions[item_id]


def _item(
    item_id: str,
    *,
    name: str,
    etag: str,
    modified_at: str = "2026-08-24T08:00:00Z",
    deleted: bool = False,
) -> dict[str, object]:
    return {
        "id": item_id,
        "name": name,
        "etag": etag,
        "modified_at": modified_at,
        "deleted": deleted,
    }


def _reader_for_initial_sync() -> FakeGraphReader:
    return FakeGraphReader(
        pages={
            None: SharePointPage(
                items=(_item("item-a", name="Platform policy", etag="v1"),),
                next_cursor="page-2",
            ),
            "page-2": SharePointPage(
                items=(_item("item-b", name="Operations policy", etag="v3"),),
                delta_cursor="delta-1",
            ),
        },
        content={
            "item-a": "Synthetic platform policy",
            "item-b": "Synthetic operations policy",
        },
        permissions={
            "item-a": [{"kind": "group", "id": "platform-engineers"}],
            "item-b": [{"kind": "user", "id": "synthetic-user-001"}],
        },
    )


def test_full_sync_reads_all_pages_and_maps_acl_metadata() -> None:
    reader = _reader_for_initial_sync()
    connector = SharePointConnector(
        reader,
        site_key="synthetic-site",
        drive_key="platform-library",
    )

    batch = connector.collect(full=True)

    assert reader.page_calls == [None, "page-2"]
    assert batch.cursor == "delta-1"
    assert batch.full_sync is True
    assert len(batch.documents) == 2
    assert batch.deleted_ids == ()
    assert batch.source_ids == frozenset(document.id for document in batch.documents)

    first = batch.documents[0]
    assert first.source_type == "sharepoint"
    assert first.source == "sharepoint://synthetic-site/platform-library/item-a"
    assert first.allowed_principals == ("group:platform-engineers",)
    assert first.content == "Synthetic platform policy"


def test_incremental_sync_preserves_id_updates_acl_and_emits_tombstone() -> None:
    initial_connector = SharePointConnector(
        _reader_for_initial_sync(),
        site_key="synthetic-site",
        drive_key="platform-library",
    )
    initial = initial_connector.collect(full=True)
    original = next(document for document in initial.documents if document.title == "Platform policy")

    reader = FakeGraphReader(
        pages={
            "delta-1": SharePointPage(
                items=(
                    _item("item-a", name="Platform policy", etag="v2"),
                    _item("item-b", name="Operations policy", etag="v4", deleted=True),
                ),
                delta_cursor="delta-2",
            )
        },
        content={"item-a": "Synthetic platform policy updated"},
        permissions={"item-a": [{"kind": "role", "id": "AI.Agent.User"}]},
    )
    connector = SharePointConnector(
        reader,
        site_key="synthetic-site",
        drive_key="platform-library",
    )

    batch = connector.collect(cursor="delta-1")

    updated = batch.documents[0]
    assert updated.id == original.id
    assert updated.content_hash != original.content_hash
    assert updated.allowed_principals == ("role:AI.Agent.User",)
    assert batch.deleted_ids == (connector.document_id("item-b"),)
    assert batch.cursor == "delta-2"
    assert reader.content_calls == ["item-a"]
    assert reader.permission_calls == ["item-a"]


def test_unresolved_source_permissions_fail_closed_before_content_is_returned() -> None:
    reader = FakeGraphReader(
        pages={
            None: SharePointPage(
                items=(_item("restricted", name="Restricted", etag="v1"),),
                delta_cursor="delta-restricted",
            )
        },
        content={"restricted": "Must never become searchable"},
        permissions={"restricted": [{"kind": "unresolved", "id": "unknown"}]},
    )
    connector = SharePointConnector(
        reader,
        site_key="synthetic-site",
        drive_key="platform-library",
    )

    with pytest.raises(UnresolvedPermissionError, match="restricted"):
        connector.collect(full=True)

    assert reader.content_calls == []


def test_transient_graph_failures_use_bounded_exponential_retry() -> None:
    delays: list[float] = []
    reader = _reader_for_initial_sync()
    reader.transient_page_failures = 2
    connector = SharePointConnector(
        reader,
        site_key="synthetic-site",
        drive_key="platform-library",
        max_attempts=3,
        base_delay_seconds=0.1,
        sleeper=delays.append,
    )

    batch = connector.collect(full=True)

    assert batch.cursor == "delta-1"
    assert delays == [0.1, 0.2]


def test_sync_is_idempotent_and_full_reconciliation_removes_stale_documents() -> None:
    connector = SharePointConnector(
        _reader_for_initial_sync(),
        site_key="synthetic-site",
        drive_key="platform-library",
    )
    batch = connector.collect(full=True)
    sink = InMemoryKnowledgeSink()

    first_report = synchronize(batch, sink)
    second_report = synchronize(batch, sink)

    assert first_report.upserted == 2
    assert second_report.upserted == 0
    assert second_report.unchanged == 2
    assert len(sink.documents) == 2

    stale = KnowledgeDocument.from_source(
        id="sp-stale-document",
        title="Stale synthetic document",
        content="Synthetic stale content",
        source="sharepoint://synthetic-site/platform-library/stale",
        source_type="sharepoint",
        source_version="v1",
        modified_at=datetime(2026, 8, 24, 7, 0, tzinfo=UTC),
        allowed_principals=["group:platform-engineers"],
    )
    sink.upsert(stale)

    reconciliation_report = synchronize(batch, sink, reconcile=True)

    assert reconciliation_report.deleted == 1
    assert "sp-stale-document" not in sink.documents


def test_checkpoint_and_report_persist_no_document_content_or_cursor_value() -> None:
    checkpoint = SyncCheckpoint(
        source="sharepoint",
        cursor="opaque-delta-token",
        updated_at=datetime(2026, 8, 24, 8, 30, tzinfo=UTC),
    )
    connector = SharePointConnector(
        _reader_for_initial_sync(),
        site_key="synthetic-site",
        drive_key="platform-library",
    )
    batch = connector.collect(full=True)
    report = synchronize(batch, InMemoryKnowledgeSink(), cursor_age_seconds=15)

    checkpoint_json = checkpoint.model_dump_json()
    report_json = report.model_dump_json()

    assert "opaque-delta-token" in checkpoint_json
    assert "content" not in checkpoint_json
    assert "opaque-delta-token" not in report_json
    assert "Synthetic platform policy" not in report_json
    assert report.cursor_age_seconds == 15


def test_checkpoint_file_round_trip_contains_only_cursor_metadata(tmp_path) -> None:
    checkpoint_path = tmp_path / "sharepoint-checkpoint.json"
    checkpoint = SyncCheckpoint(
        source="sharepoint",
        cursor="opaque-delta-token",
        updated_at=datetime(2026, 8, 24, 8, 30, tzinfo=UTC),
    )

    save_checkpoint(checkpoint_path, checkpoint)
    restored = load_checkpoint(checkpoint_path)
    stored = checkpoint_path.read_text(encoding="utf-8")

    assert restored == checkpoint
    assert set(restored.model_dump()) == {"source", "cursor", "updated_at"}
    assert "Synthetic" not in stored
