# Phase 3 implementation plan

## Outcome

Phase 3 turns the authenticated POC into an enterprise knowledge integration
reference implementation. It adds one ACL-preserving SharePoint Online
ingestion path, a repeatable AI quality gate, and one allowlisted read-only MCP
tool while retaining the existing Azure AI Search grounding path.

The central architecture decision is:

> Azure AI Search remains the authorization-aware retrieval and citation layer.
> MCP is an optional protocol for approved live tools and data; it must not
> bypass Entra authorization, Azure RBAC, or `allowed_principals` filtering.

## Scope

### In scope

- A source-neutral document and authorization contract.
- A SharePoint Online/Microsoft Graph connector behind a feature flag.
- Incremental, idempotent ingestion with update and deletion handling.
- Preservation of user and group authorization metadata in
  `allowed_principals`.
- Synthetic SharePoint fixtures and multi-persona data-leakage tests.
- A versioned evaluation dataset and a blocking quality/safety pipeline stage.
- One read-only MCP client integration and one allowlisted demonstration tool.
- Privacy-safe operational telemetry for ingestion, retrieval, MCP calls, and
  evaluation results.
- Architecture, threat-model, runbook, and deployment documentation.

### Out of scope

- Replacing Azure AI Search with MCP.
- Model-selected write actions or autonomous changes to company systems.
- Broad Microsoft Graph permissions or unrestricted MCP server discovery.
- Persisted chat history or long-term user memory.
- APIM, WAF, private ingress, inspected egress, or multi-region disaster
  recovery in the cost-conscious MVP. These remain enterprise extensions.
- A legal determination of GDPR or DORA compliance.

## Security invariants

These controls must remain true throughout Phase 3:

1. The browser uses Entra authorization code flow with PKCE and no client
   secret.
2. The API validates token signature, issuer, audience, expiry, delegated
   scope, and optional app role.
3. Authorization is deterministic and occurs before prompting.
4. Documents without valid ACL metadata fail closed and are not indexed.
5. Unauthorized chunks never enter the model context.
6. Workloads use managed identity and Azure RBAC; model and Search API keys are
   not introduced.
7. MCP tools are explicitly configured, read-only, schema validated, bounded by
   timeout, and auditable.
8. Prompts, document text, model answers, access tokens, and personal data are
   not written to logs by default.
9. Existing `/config`, `/health`, `/ready`, `/ask`, and `/feedback` contracts
   remain compatible.

## Target architecture

Phase 3 has two distinct data paths.

### Indexed knowledge path

```text
SharePoint Online
  -> dedicated read-only ingestion identity
  -> Microsoft Graph connector
  -> normalized document + ACL contract
  -> chunk, embed, and reconcile
  -> Azure AI Search allowed_principals index
  -> API ACL-filtered hybrid retrieval
  -> Foundry chat completion
  -> cited answer
```

This is the default path for governed documents, ranking, filtering, grounding,
and citations.

### Live tool path

```text
Authenticated user
  -> FastAPI policy/orchestration layer
  -> explicit MCP tool allowlist
  -> schema and authorization validation
  -> read-only MCP server
  -> bounded result returned as untrusted data
  -> answer with source metadata
```

The MCP server is not called directly from the browser or model. The API owns
tool selection policy, authorization, timeouts, result limits, and audit
metadata. The first implementation should use an explicit application rule,
not unrestricted model-selected tools.

## Work packages

### WP1 - Contracts and synthetic fixtures

Create a source-neutral knowledge contract before connecting to a live tenant.

Proposed document fields:

- `id`
- `title`
- `content`
- `source`
- `source_type`
- `source_version`
- `modified_at`
- `content_hash`
- `allowed_principals`
- `is_deleted`

Likely files:

- `app/knowledge/contracts.py`
- `app/knowledge/authorization.py`
- `tests/fixtures/sharepoint/`
- `tests/test_knowledge_contracts.py`

Acceptance criteria:

- Principal values use the existing `public`, `user:`, `group:`, and `role:`
  formats.
- Empty, malformed, duplicated, or unresolved ACLs fail closed.
- Synthetic fixtures cover public, user-only, group-only, changed, deleted,
  and malformed documents.
- No tenant identifiers or real company content are committed.

### WP2 - SharePoint Online ingestion

Add a connector with a dedicated read-only ingestion identity. Keep permission
selection environment-specific and document the least-privilege decision; do
not embed tenant IDs or credentials in the repository.

Likely files:

- `app/connectors/base.py`
- `app/connectors/sharepoint.py`
- `scripts/sync_sharepoint.py`
- `tests/test_sharepoint_connector.py`
- `docs/sharepoint-ingestion.md`
- `docs/decisions/adr-006-enterprise-knowledge-ingestion.md`

Implementation requirements:

- Support a full initial sync and a resumable incremental sync.
- Store only a delta/checkpoint token or equivalent sync cursor, not document
  content, in connector state.
- Use deterministic document IDs and content hashes for idempotency.
- Apply creates, updates, and deletion tombstones to Search.
- Retry transient failures with bounded exponential backoff.
- Reconcile periodically so missed events cannot leave stale documents
  indefinitely.
- Translate source permissions to `allowed_principals` before indexing.
- Reject an item when permissions cannot be resolved safely.
- Separate the ingestion identity from the runtime application identity.

Acceptance criteria:

- A synthetic source create, update, permission change, and deletion produce
  the expected Search operations.
- Re-running the same sync produces no duplicate documents.
- A permission-resolution failure results in no searchable content.
- Logs contain counts, duration, cursor age, and error category only.

### WP3 - Authorization leakage test suite

Build a matrix that proves retrieval isolation independently of model quality.

Implementation status: completed locally. Azure AI Search remains the primary
server-side ACL filter, and the API now performs a second fail-closed ACL check
on every returned document before constructing the model prompt. Group-overage
tokens do not contribute group principals until an approved resolver exists.

Test personas:

- authenticated public user;
- explicitly allowed user;
- disallowed user;
- allowed group member;
- user with a group-overage token;
- user with the optional app role;
- anonymous caller when authentication is required.

Likely files:

- `tests/test_sharepoint_authorization.py`
- `tests/test_retrieval_leakage.py`
- `tests/fixtures/sharepoint/personas.json`

Acceptance criteria:

- Every unauthorized persona receives no restricted document or citation.
- Group-overage remains fail closed until an approved resolution design exists.
- Tests inspect retrieved source IDs so a safe-looking model response cannot
  hide a retrieval leak.
- Existing authentication and authorization tests remain green.

### WP4 - AI evaluation and safety gate

Add a deterministic evaluation stage after Terraform plan and before apply for
code-only checks, plus a deployed evaluation stage before release completion
when infrastructure is applied.

Evaluation dimensions:

- retrieval relevance;
- authorization correctness;
- citation correctness;
- groundedness and refusal when evidence is absent;
- direct and indirect prompt-injection resistance;
- sensitive-data handling;
- latency and bounded token usage.

Likely files:

- `evals/datasets/platform-assistant-v1.jsonl`
- `scripts/evaluate_agent.py`
- `tests/test_evaluation_contract.py`
- `docs/evaluation.md`
- `azure-pipelines.yml`

Acceptance criteria:

- The dataset is versioned and contains no personal or company-confidential
  data.
- Thresholds and failure reasons are explicit and reviewable.
- The pipeline publishes machine-readable JSON and a Markdown summary.
- An authorization leak, missing required citation, or unsafe tool attempt is a
  hard failure.
- Quality-score threshold changes require code review.

### WP5 - Controlled read-only MCP

Introduce MCP after the connector and leakage tests are stable. Start with one
low-risk read-only tool that returns bounded metadata from a synthetic or
non-sensitive source.

Likely files:

- `app/tools/contracts.py`
- `app/tools/mcp_client.py`
- `app/tools/policy.py`
- `tests/test_mcp_policy.py`
- `tests/test_mcp_client.py`
- `docs/mcp.md`
- `docs/decisions/adr-007-rag-and-mcp-responsibilities.md`

Implementation requirements:

- Configure server URL and tool names explicitly per environment.
- Authenticate the workload without a stored client secret where supported.
- Allow only declared read-only tools.
- Validate request and response schemas.
- Bound result size, call count, retries, and execution time.
- Treat MCP output as untrusted data and never execute embedded instructions.
- Record correlation ID, server alias, tool name, duration, result count, and
  outcome; do not log arguments or returned content by default.
- Return a safe error when the tool is unavailable.
- Keep the existing Search path as the default answer path.

Acceptance criteria:

- Unknown server and tool names are rejected before any network call.
- Write-like operations are not present in the tool catalog.
- Invalid schemas, timeout, oversized output, and server failure are covered by
  tests.
- MCP cannot access documents or services outside the caller's approved
  authorization context.
- Disabling the feature flag restores the current Phase 2 behavior.

### WP6 - Operations and evidence

Add privacy-safe operational signals and recovery documentation.

Signals:

- ingestion success/failure and duration;
- sync cursor age and index freshness;
- documents created, updated, deleted, rejected, and quarantined;
- zero-result retrieval rate;
- MCP tool success, timeout, and rejection counts;
- evaluation scores and regression trend;
- model latency and token usage without content logging.

Likely files:

- `docs/runbooks/knowledge-sync.md`
- `docs/runbooks/index-recovery.md`
- `docs/runbooks/mcp-outage.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/diagrams/azure-ai-agent-end-to-end.drawio`
- `compliance/controls/`

Acceptance criteria:

- A failed sync can be retried safely.
- The index can be rebuilt from the approved source.
- MCP outage does not take down the Search-grounded answer path.
- Evidence identifies what was tested without claiming legal compliance.

## Delivery sequence

Use small pull requests with a working baseline after each merge:

1. Contracts and synthetic fixtures.
2. Connector with mocked Graph responses.
3. ACL-preserving indexing and leakage tests.
4. Versioned evaluation gate.
5. One controlled read-only MCP tool.
6. Telemetry, runbooks, architecture, and evidence updates.
7. Optional live SharePoint tenant validation using environment-only
   configuration and approved permissions.

Do not start with a live tenant or broad Graph permissions. Prove the contract,
authorization behavior, and failure modes locally first.

## Validation commands

Run after each work package:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
npm ci --no-audit --no-fund
npm run check
ruff check app scripts tests
pytest -q
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra init -backend=false
terraform -chdir=infra validate
git diff --check
```

Add focused connector, leakage, evaluation, and MCP tests as their work
packages land. A live SharePoint integration test is a separate, explicitly
configured validation and must not be represented as passing from mocked tests.

## Phase 3 definition of done

Phase 3 is complete when:

- an approved SharePoint document is synchronized and returned with a citation;
- a changed permission removes access on the next successful sync;
- a deleted document is no longer retrievable;
- an unauthorized persona cannot retrieve or cite restricted content;
- the evaluation pipeline blocks authorization, citation, and safety
  regressions;
- one read-only MCP tool works through the API policy layer with bounded,
  privacy-safe audit metadata;
- disabling SharePoint and MCP preserves the Phase 2 application behavior;
- architecture, threat model, operational runbooks, and regulatory evidence are
  updated;
- local tests, UI build, Terraform validation, and the Azure DevOps pipeline
  pass.

## Decisions required before live integration

1. Which SharePoint sites and document libraries are in scope?
2. Is ingestion application-only, delegated, or performed by a managed Azure
   job with an approved identity pattern?
3. Which source permissions must map to users, groups, sharing links, and site
   membership?
4. Where will the incremental sync cursor be stored with optimistic locking?
5. What maximum freshness delay is acceptable?
6. Which single read-only MCP use case provides value that indexed retrieval
   does not?
7. Who owns data-source approval, DPIA decisions, incident response, and MCP
   tool approval?

Exact Microsoft Graph permissions and MCP authentication settings must be
selected from current Microsoft documentation during implementation because
they are tenant- and feature-dependent.
