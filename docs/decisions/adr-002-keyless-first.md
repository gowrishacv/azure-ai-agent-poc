# ADR-002: Disable service keys and use managed identity

## Status

Accepted

## Context

The demo must illustrate a credible production path. API keys are easy to start
with but require storage, rotation, and leak response.

## Decision

Use a user-assigned managed identity for the app, Azure RBAC for Foundry/Search/
Key Vault/ACR, and Azure DevOps workload identity federation for deployment.
Disable local authentication on Foundry and Search.

## Trade-offs

RBAC propagation can delay first deployment and local developers need Azure CLI
access. This is accepted because the design avoids long-lived credentials and
produces attributable authorization.

## Consequences

- Positive: no model/search keys in application settings or pipeline variables.
- Negative: role design and troubleshooting are more involved.
- Mitigation: identity matrix, readiness checks, and documented propagation
  retry behavior.

