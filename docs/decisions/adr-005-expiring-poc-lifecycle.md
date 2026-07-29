# ADR-005: Expire development POC environments safely

## Status

Accepted

## Context

The POC uses services with fixed or consumption-based charges. Azure Cost
Management budgets notify after delayed cost ingestion but do not stop
resources. A developer can also interrupt Terraform destroy, leaving a stale
lock, partial state, or Application Insights-generated resources that prevent
resource-group deletion.

## Decision

- Create a fixed `expires_on` tag for dev from a Terraform lifecycle marker.
- Set `auto_destroy=true` only in the dev profile.
- Evaluate expiry every day in a separate Azure DevOps cost-guard pipeline.
- Use the existing WIF identity and remote state for scheduled cleanup.
- Require the destroy script to verify purpose, environment, and management
  tags before any deletion.
- Reject scheduled-expiry mode for test and prod.
- Remove only the two known Application Insights-generated monitoring
  resources before applying the reviewed Terraform destroy plan.
- Publish a lifecycle report and verify that Terraform state and the resource
  group are both gone.

## Rationale

- A fixed TTL bounds forgotten development spend without creating another
  paid monitoring service.
- Terraform remains the owner of workload deletion and state reconciliation.
- Independent checks in Terraform tags, pipeline conditions, and the script
  reduce the effect of a single configuration mistake.
- Keeping the provider's resource-group deletion safeguard enabled prevents
  silent deletion of unknown resources.

## Trade-offs

- Scheduled cleanup needs the Azure DevOps WIF connection and hosted agent to
  be available.
- Environment approvals can pause unattended dev cleanup.
- Auto-created monitoring resource names are provider conventions and need
  regression tests when Azure behavior changes.
- The remote-state storage account and deployment identities remain until a
  separate bootstrap teardown is intentionally performed.

## Consequences

- Dev deployments expire after 24 hours by default.
- Production has no automatic expiry.
- Interrupted destroys can resume even when Terraform outputs are already
  missing.
- Lifecycle reports provide evidence of retained, skipped, failed, or completed
  cleanup.
