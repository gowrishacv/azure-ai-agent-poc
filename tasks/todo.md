# Phase 3 checklist

## Gate 0 - Confirm scope

- [ ] Select the first SharePoint site and library for the live pilot.
- [ ] Name the data owner and security approver.
- [ ] Define acceptable content freshness and retention.
- [ ] Select one read-only MCP use case.
- [ ] Confirm that no write tools are in Phase 3.

## Gate 1 - Contracts and fixtures

- [x] Add the normalized enterprise document contract.
- [x] Add strict `allowed_principals` validation.
- [x] Add synthetic SharePoint documents and personas.
- [x] Cover create, update, ACL change, deletion, and malformed ACL cases.
- [x] Confirm fixtures contain no real tenant or personal data.

## Gate 2 - SharePoint connector

- [x] Add a source connector interface.
- [x] Implement mocked SharePoint/Graph list and content reads.
- [x] Implement incremental cursor handling.
- [x] Implement idempotent content hashing and upsert behavior.
- [x] Implement deletion tombstones and reconciliation.
- [x] Map source permissions to `allowed_principals`.
- [x] Fail closed when ACL resolution is incomplete.
- [x] Document the dedicated ingestion identity and least privilege.

## Gate 3 - Authorization proof

- [x] Add public, user, group, role, disallowed, overage, and anonymous personas.
- [x] Assert retrieved source IDs, not only generated answer text.
- [x] Prove unauthorized chunks never reach the prompt builder.
- [x] Preserve current Entra, JWT, API, and Search authorization tests.

## Gate 4 - Evaluation pipeline

- [ ] Add a versioned, synthetic evaluation dataset.
- [ ] Score retrieval, citations, grounding, refusal, and latency.
- [ ] Add direct and indirect prompt-injection cases.
- [ ] Add sensitive-data and authorization-leak cases.
- [ ] Publish JSON and Markdown evaluation artifacts.
- [ ] Add explicit blocking thresholds to Azure DevOps.

## Gate 5 - Controlled MCP

- [ ] Add MCP configuration behind a disabled-by-default feature flag.
- [ ] Add an explicit server and tool allowlist.
- [ ] Add one read-only tool with strict schemas.
- [ ] Add timeout, retry, result-size, and call-count limits.
- [ ] Treat tool output as untrusted data.
- [ ] Log metadata only: correlation ID, alias, tool, duration, count, outcome.
- [ ] Reject unknown, write-like, invalid, or oversized calls.
- [ ] Prove MCP cannot bypass Entra, RBAC, or document ACL enforcement.

## Gate 6 - Operations and handoff

- [ ] Add sync-health, cursor-age, freshness, rejection, and MCP metrics.
- [ ] Add knowledge-sync, index-recovery, and MCP-outage runbooks.
- [ ] Update architecture, security, connectivity, and ADR documents.
- [ ] Update GDPR/DORA technical evidence without making compliance claims.
- [ ] Validate the disable/rollback path to Phase 2 behavior.

## Final verification

- [ ] `npm ci --no-audit --no-fund`
- [ ] `npm run check`
- [ ] `ruff check app scripts tests`
- [ ] `pytest -q`
- [ ] `terraform -chdir=infra fmt -check -recursive`
- [ ] `terraform -chdir=infra init -backend=false`
- [ ] `terraform -chdir=infra validate`
- [ ] `git diff --check`
- [ ] Azure DevOps plan-only run passes.
- [ ] Approved dev deployment and deployed evaluation pass.
- [ ] Authorized SharePoint document returns a citation.
- [ ] Unauthorized and deleted documents cannot be retrieved.
- [ ] Read-only MCP failure does not break Search-grounded answers.
