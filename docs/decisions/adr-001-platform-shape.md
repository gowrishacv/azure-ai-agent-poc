# ADR-001: Use a modular monolith on Azure Container Apps

## Status

Accepted

## Context

The POC targets a small team, low traffic, a short delivery timeline, and a
cost-sensitive demo. It needs API validation, retrieval, and model calls but no
independent scaling boundary.

## Decision

Use one FastAPI deployment with concrete Azure SDK integrations on Container
Apps Consumption. Keep infrastructure separated into Terraform modules.

## Trade-offs

This gives up independent service deployment and language diversity. Those
benefits do not justify AKS, service discovery, queues, and distributed tracing
for this workload.

## Consequences

- Positive: scale to zero, one deployable artifact, easy local testing.
- Negative: all API functions scale together.
- Mitigation: extract indexing or tool execution only when workload evidence
  shows an independent lifecycle or scaling need.

