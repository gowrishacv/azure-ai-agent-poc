# ADR-006: Preserve source authorization during enterprise knowledge ingestion

## Status

Accepted for the local connector contract. Live Microsoft 365 and Azure
integration remains a controlled pilot.

## Context

Phase 2 retrieves indexed documents only after applying the API's deterministic
`allowed_principals` filter. Phase 3 must ingest SharePoint Online documents
without weakening that boundary.

A connector that copies content without complete source permissions can expose
restricted documents to the wrong employee. A model prompt is not an
authorization control, and a safe-looking answer does not prove that retrieval
was safe.

## Decision

1. Keep Azure AI Search as the indexed retrieval and citation layer. MCP does
   not replace authorization-aware retrieval.
2. Use a dedicated read-only ingestion identity that is separate from the
   runtime application managed identity.
3. Prefer a Microsoft Graph Selected permission with an explicit assignment to
   the approved site, list, library, or item.
4. Review ACL-enumeration permissions separately because Graph permission-list
   APIs can require broader read permissions than the selected content scope.
5. Require complete deterministic translation to `public`, `user:`, `group:`,
   or `role:` principals before reading and indexing document content.
6. Reject unresolved, empty, duplicated, or malformed permissions. Do not
   widen access and do not fall back to `public`.
7. Use stable hashed document IDs and content hashes for repeatable upserts.
8. Persist only an opaque delta cursor and timestamp as connector state.
9. Apply deletion tombstones and run periodic full reconciliation to remove
   stale indexed content.
10. Log only counts, duration, cursor age, and error category.
11. Keep tenant IDs, resource IDs, tokens, credentials, and real company
    documents outside the public repository.

## Consequences

### Benefits

- Authorization remains enforceable before model prompting.
- Repeat synchronization does not create duplicate documents.
- Permission failures stop ingestion instead of silently widening access.
- Deleted or missed source changes are eventually removed by reconciliation.
- Connector logic can be tested locally without Azure or Microsoft 365 cost.

### Trade-offs

- ACL inheritance and sharing links make the live Graph adapter more complex.
- A Selected permission may not be sufficient for every ACL-enumeration API.
  Any broader read permission requires explicit security approval and scope
  validation.
- Local mocks cannot prove tenant-specific Graph, SharePoint, Search, network,
  or policy behavior. A controlled live pilot is still required.
- Fail-closed behavior can temporarily reduce search coverage when source ACLs
  cannot be resolved.

## Validation

The local acceptance suite covers full and incremental paging, stable IDs,
content and ACL updates, deletion tombstones, reconciliation, bounded retries,
permission failure before content retrieval, checkpoint privacy, and
privacy-safe operational reports.

