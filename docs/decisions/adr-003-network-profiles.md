# ADR-003: Make private networking an explicit profile

## Status

Accepted

## Context

Private endpoints are important for regulated production workloads but add
hourly cost, DNS dependencies, subnet sizing, and a requirement for
VNet-connected build agents.

## Decision

Default to public service endpoints with local authentication disabled and RBAC
enforced. Offer a single Terraform flag that adds Container Apps VNet
integration plus private endpoints for Foundry, Search, and Key Vault.

## Trade-offs

The MVP does not demonstrate a closed network boundary. The private profile is
more representative but is not the lowest-cost path.

## Consequences

- Positive: the first deployment is approachable; the secure-network pattern is
  still executable.
- Negative: teams might mistake public-plus-RBAC for every production scenario.
- Mitigation: prominent production-gap documentation and separate prod example.

