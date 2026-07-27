# ADR-004: Separate deterministic evidence from advisory AI review

## Status

Accepted

## Context

The POC needs a GDPR/DORA-oriented Azure DevOps stage without representing an
AI-generated assessment as a legal determination. It must remain inexpensive,
keyless, reviewable, and useful to a solo POC owner.

## Decision

Run deterministic, version-controlled checks as the deployment gate. After
Terraform apply, use the deployed Foundry model to review only sanitized check
results. Publish both machine-readable and human-readable evidence artifacts.

## Rationale

- Deterministic failures are reproducible and suitable for a build gate.
- AI is useful for prioritisation but is not an authorization or compliance
  boundary.
- Running after apply avoids a separate paid compliance model deployment.
- Sanitized input reduces disclosure risk.

## Trade-offs

- A first deployment reaches apply before the regulatory stage.
- Source checks show intended design, not complete runtime effectiveness.
- Human evidence such as DPIA decisions and recovery exercises remains outside
  automation.

## Consequences

- Critical technical failures block application deployment.
- AI failure is recorded but does not override deterministic results.
- Production adoption requires runtime policy evidence, named owners, legal
  review, retention controls, and tested recovery procedures.
