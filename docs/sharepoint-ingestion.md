# SharePoint Online ingestion

## Status

Phase 3 work package 2 defines and tests the SharePoint connector contract
locally. It does not yet connect this public repository to a real Microsoft 365
tenant.

The local implementation proves paging, incremental checkpoints, deterministic
document IDs, content hashing, ACL translation, deletion handling, retry
limits, and reconciliation without deploying Azure resources or using real
company documents.

## Data flow

```text
SharePoint Online
  -> dedicated read-only ingestion identity
  -> Microsoft Graph reader
  -> SharePoint connector
  -> normalized KnowledgeDocument + allowed_principals
  -> Azure AI Search upsert/delete adapter

Authenticated application user
  -> API bearer-token validation
  -> ACL-filtered Azure AI Search query
  -> Microsoft Foundry grounded answer with citations
```

The ingestion identity and runtime application identity are separate:

- The ingestion identity may read only the approved SharePoint scope and write
  normalized documents to the Search index.
- The runtime identity queries Search and calls Microsoft Foundry. It does not
  receive Microsoft Graph permissions.
- Neither identity uses a client secret in source code. Prefer workload
  identity federation or a managed identity; use a certificate only when the
  hosting model cannot support federation.

## Permission model

Use the narrowest Microsoft Graph Selected permission supported by the chosen
site, list, library, or item, followed by an explicit permission assignment to
that resource. Granting a Selected consent scope alone does not grant access:

- [Microsoft Graph Selected permissions overview](https://learn.microsoft.com/en-us/graph/permissions-selected-overview)

ACL discovery needs a separate design review. The current Microsoft Graph
permission-list APIs can require broader application permissions than content
read operations, and the returned permission details can depend on caller
ownership:

- [List permissions on a driveItem](https://learn.microsoft.com/en-us/graph/api/driveitem-list-permissions?view=graph-rest-1.0)
- [List permissions on a listItem](https://learn.microsoft.com/en-us/graph/api/listitem-list-permissions?view=graph-rest-1.0)

For this reason, the live pilot must prove that the connector can resolve the
complete effective ACL for every indexed item. If a user, group, link, or
inheritance entry cannot be translated safely, the connector rejects the item.
It never falls back to `public`.

Normalized principals use the existing application contract:

- `public`
- `user:<entra-object-id>`
- `group:<entra-object-id>`
- `role:<app-role-value>`

Tenant identifiers are runtime configuration and must not be committed.

## Synchronization behavior

The connector supports both initial and incremental runs:

1. A full run follows every page, produces stable hashed IDs, and records the
   terminal delta cursor.
2. An incremental run resumes from that opaque cursor.
3. Content and ACL changes produce an idempotent upsert.
4. Source deletions produce tombstones.
5. A periodic full reconciliation deletes indexed documents that no longer
   exist in the source.
6. Transient Graph failures use bounded exponential retry.
7. The checkpoint contains only source name, opaque cursor, and timestamp. It
   never contains document text or access tokens.

Safe operational metadata is limited to counts, duration, cursor age, and an
error category. Document text, permission values, user identifiers, access
tokens, prompts, and model answers are not logged.

## Test locally without Azure

From the repository root:

```bash
.venv/bin/python -m pytest -q tests/test_sharepoint_connector.py
.venv/bin/python -m pytest -q
.venv/bin/ruff check app scripts tests
```

These tests use a synthetic Graph reader and an in-memory Search sink. They
verify:

- full paging and an opaque delta checkpoint;
- create, update, ACL change, and deletion behavior;
- stable IDs and repeat-run idempotency;
- stale-document reconciliation;
- permission failure before content is read;
- bounded retries; and
- privacy-safe sync reports and checkpoint files.

Gate 3 also uses seven synthetic caller personas: anonymous, authenticated
public, explicitly allowed user, group member, app-role holder, disallowed
user, and group-overage user. The tests assert the retrieved source IDs and
capture the final model prompt. This proves that restricted chunks are removed
before prompting, even when a deliberately faulty Search test double returns
every active document.

The runtime applies two authorization checks:

1. Azure AI Search receives the deterministic `allowed_principals` filter.
2. The API validates each returned document's ACL again before prompt assembly.

Malformed returned ACLs and unsafe caller principals fail closed. Group-overage
tokens retain only `public` and the verified `user:<object-id>` principal; they
do not receive group-scoped content until an approved group resolver is added.

No Azure deployment, subscription, Microsoft 365 tenant, or paid service is
required for these checks.

## What local tests do not prove

Local tests cannot prove:

- actual Microsoft Graph consent and selected-resource assignment;
- complete ACL and inheritance resolution in the target tenant;
- Graph delta behavior, throttling, or token acquisition;
- Azure AI Search indexing and deletion against a deployed index;
- private networking, DNS, tenant policies, or production throughput.

## When Azure deployment is required

Deploy only for the controlled live pilot after a data owner and security
approver select one non-sensitive SharePoint library. The pilot requires:

1. A dedicated read-only ingestion workload identity.
2. Explicit Graph access to one approved site or library.
3. A live Graph adapter and a live Azure AI Search sink.
4. An isolated development index and synthetic or approved documents.
5. Proof that inherited, direct, link, removed, and unresolved permissions all
   behave as expected.
6. Proof that unauthorized and deleted documents cannot be retrieved or cited.
7. Monitoring for sync freshness, cursor age, rejected items, and categorized
   failures without content logging.

The live pilot passes only when every expected source document has a complete
ACL mapping, repeat runs are idempotent, deletions reconcile, and the existing
authorization-leakage tests remain green.
