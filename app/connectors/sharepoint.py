"""Fail-closed SharePoint Online connector over a narrow Graph reader contract."""

import hashlib
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, TypeVar

from app.connectors.base import SourceBatch
from app.knowledge.authorization import normalize_allowed_principals
from app.knowledge.contracts import KnowledgeDocument

_T = TypeVar("_T")


class TransientGraphError(RuntimeError):
    """A retryable Microsoft Graph response such as throttling or a 5xx error."""


class UnresolvedPermissionError(ValueError):
    """Raised when an item ACL cannot be translated without widening access."""


@dataclass(frozen=True)
class SharePointPage:
    """One mocked or live Graph page plus its continuation metadata."""

    items: tuple[Mapping[str, object], ...]
    next_cursor: str | None = None
    delta_cursor: str | None = None


class GraphReader(Protocol):
    """Small boundary that keeps Graph transport separate from mapping logic."""

    def get_page(self, cursor: str | None) -> SharePointPage: ...

    def get_content(self, item_id: str) -> str: ...

    def get_permissions(self, item_id: str) -> Sequence[Mapping[str, str]]: ...


class SharePointConnector:
    """Translate SharePoint items and permissions into canonical documents."""

    source_type = "sharepoint"

    def __init__(
        self,
        reader: GraphReader,
        *,
        site_key: str,
        drive_key: str,
        max_attempts: int = 3,
        base_delay_seconds: float = 0.5,
        sleeper: Callable[[float], object] = time.sleep,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if base_delay_seconds < 0:
            raise ValueError("base_delay_seconds cannot be negative")

        self._reader = reader
        self._site_key = site_key
        self._drive_key = drive_key
        self._max_attempts = max_attempts
        self._base_delay_seconds = base_delay_seconds
        self._sleeper = sleeper

    def document_id(self, item_id: str) -> str:
        """Return a stable ID without exposing a tenant or source identifier."""

        key = f"{self._site_key}:{self._drive_key}:{item_id}"
        return f"sp-{hashlib.sha256(key.encode('utf-8')).hexdigest()[:40]}"

    def collect(self, cursor: str | None = None, *, full: bool = False) -> SourceBatch:
        documents: list[KnowledgeDocument] = []
        deleted_ids: list[str] = []
        source_ids: set[str] = set()
        page_cursor = None if full else cursor
        visited_cursors: set[str | None] = set()
        delta_cursor: str | None = None

        while True:
            if page_cursor in visited_cursors:
                raise RuntimeError("SharePoint paging cursor loop detected")
            visited_cursors.add(page_cursor)

            page = self._retry(
                lambda page_cursor=page_cursor: self._reader.get_page(page_cursor)
            )
            for item in page.items:
                item_id = self._required_string(item, "id")
                document_id = self.document_id(item_id)

                if item.get("deleted") is True:
                    deleted_ids.append(document_id)
                    continue

                permissions = self._retry(lambda item_id=item_id: self._reader.get_permissions(item_id))
                allowed_principals = self._map_permissions(item_id, permissions)
                content = self._retry(lambda item_id=item_id: self._reader.get_content(item_id))
                document = KnowledgeDocument.from_source(
                    id=document_id,
                    title=self._required_string(item, "name"),
                    content=content,
                    source=(
                        f"sharepoint://{self._site_key}/{self._drive_key}/{item_id}"
                    ),
                    source_type=self.source_type,
                    source_version=self._required_string(item, "etag"),
                    modified_at=datetime.fromisoformat(
                        self._required_string(item, "modified_at")
                    ),
                    allowed_principals=allowed_principals,
                )
                documents.append(document)
                source_ids.add(document.id)

            if page.next_cursor is not None:
                page_cursor = page.next_cursor
                continue

            delta_cursor = page.delta_cursor
            break

        if not delta_cursor:
            raise RuntimeError("SharePoint sync completed without a delta cursor")

        return SourceBatch(
            source_type=self.source_type,
            documents=tuple(documents),
            deleted_ids=tuple(dict.fromkeys(deleted_ids)),
            source_ids=frozenset(source_ids),
            cursor=delta_cursor,
            full_sync=full,
        )

    def _retry(self, operation: Callable[[], _T]) -> _T:
        for attempt in range(self._max_attempts):
            try:
                return operation()
            except TransientGraphError:
                if attempt + 1 >= self._max_attempts:
                    raise
                self._sleeper(self._base_delay_seconds * (2**attempt))
        raise AssertionError("unreachable retry state")

    @staticmethod
    def _required_string(item: Mapping[str, object], field: str) -> str:
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"SharePoint item requires a non-empty {field}")
        return value.strip()

    @staticmethod
    def _map_permissions(
        item_id: str,
        permissions: Sequence[Mapping[str, str]],
    ) -> tuple[str, ...]:
        principals: list[str] = []
        for permission in permissions:
            kind = permission.get("kind")
            principal_id = permission.get("id")
            if kind == "public" and not principal_id:
                principals.append("public")
            elif kind in {"user", "group", "role"} and principal_id:
                principals.append(f"{kind}:{principal_id}")
            else:
                raise UnresolvedPermissionError(
                    f"SharePoint item {item_id!r} has an unresolved permission"
                )

        try:
            return normalize_allowed_principals(principals, document_id=item_id)
        except ValueError as error:
            raise UnresolvedPermissionError(
                f"SharePoint item {item_id!r} has an unresolved permission"
            ) from error
