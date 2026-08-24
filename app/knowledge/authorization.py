"""Fail-closed authorization metadata helpers for indexed knowledge."""

import re
from collections.abc import Sequence

_SAFE_PRINCIPAL = re.compile(r"^(public|(?:user|group|role):[A-Za-z0-9._:@-]{1,160})$")


def normalize_allowed_principals(
    principals: object,
    *,
    document_id: str = "<unknown>",
) -> tuple[str, ...]:
    """Validate, sort, and freeze a document ACL or reject it.

    An absent, empty, malformed, or duplicated ACL is an ingestion failure. This
    prevents a connector bug from silently widening access to indexed content.
    """

    if (
        isinstance(principals, (str, bytes))
        or not isinstance(principals, Sequence)
        or not principals
    ):
        raise ValueError(
            f"Document {document_id!r} must define allowed_principals as a non-empty collection"
        )

    normalized: list[str] = []
    for principal in principals:
        if not isinstance(principal, str) or not _SAFE_PRINCIPAL.fullmatch(principal):
            raise ValueError(f"Document {document_id!r} contains an invalid principal")
        normalized.append(principal)

    if len(set(normalized)) != len(normalized):
        raise ValueError(f"Document {document_id!r} contains a duplicate principal")

    return tuple(sorted(normalized))


def normalize_search_principals(principals: object) -> tuple[str, ...]:
    """Validate caller principals before building a Search ACL expression."""

    try:
        return normalize_allowed_principals(
            principals,
            document_id="<search request>",
        )
    except ValueError as exc:
        raise ValueError("Search request contains an invalid search principal") from exc


def document_is_authorized(
    allowed_principals: object,
    search_principals: tuple[str, ...],
    *,
    document_id: str,
) -> bool:
    """Apply a second, local ACL check to a document returned by Search."""

    try:
        allowed = normalize_allowed_principals(
            allowed_principals,
            document_id=document_id,
        )
    except ValueError:
        return False
    return not set(allowed).isdisjoint(search_principals)
