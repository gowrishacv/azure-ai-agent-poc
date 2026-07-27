# Security controls and known gaps

## Implemented controls

| Area | Control |
|---|---|
| Credentials | Workload identity federation in CI; managed identity at runtime |
| Local authentication | Disabled on Foundry and Azure AI Search |
| Authorization | Minimum model-user and search-reader roles for the app |
| Secrets | Key Vault uses RBAC, soft delete, and purge protection |
| Network | HTTPS only; optional private endpoints and private DNS |
| Supply chain | ACR admin account disabled; remote build; non-root container |
| Prompt injection | Retrieved content is delimited and explicitly untrusted |
| Input bounds | Pydantic schema, question limit, bounded search results and output |
| Tool risk | No write tools or model-selected external actions |
| Operations | Health probes, telemetry, low ingestion cap |
| Delivery | PR cannot apply; immutable plan; environment approval support |

## Required before production data

1. Register an Entra API application, set `REQUIRE_AUTH=true`,
   `AUTH_TENANT_ID`, and `AUTH_AUDIENCE`, and validate group/app-role claims for
   each operation. The code contains JWT signature, issuer, and audience
   validation; the POC default leaves it disabled.
2. Add per-document authorization metadata and apply user/group filters to
   every Search request, or use separate indexes for hard security boundaries.
3. Put rate limits at a gateway or application edge. Consider APIM only after
   gateway policies and traffic justify the tier.
4. Add Azure AI Content Safety/Prompt Shields and adversarial evaluation. A
   prompt instruction is not a security boundary.
5. Define telemetry redaction and retention. Do not log prompts, retrieved
   documents, or completions by default.
6. Pin the application image by digest, scan it, generate an SBOM, and enforce
   signed-image admission in the delivery policy.
7. Add Azure Policy, Defender for Cloud, resource locks, diagnostic settings,
   alert rules, and incident ownership.
8. Use separate plan and apply identities. Scope them to pre-created
   environment resource groups where practical.
9. Restrict outbound traffic through the organization's landing-zone firewall
   when arbitrary internet egress is not acceptable.

## Identity matrix

| Identity | Foundry | Search | Key Vault | ACR |
|---|---|---|---|---|
| Application UAMI | OpenAI User | Index Data Reader | Secrets User | Pull |
| Pipeline WIF | OpenAI User | Service Contributor + Data Contributor | Control plane via deployment role | Build via deployment role |
| Foundry project | None in MVP | Index Data Reader | None | None |

The pipeline's data-plane roles exist only so it can create and seed the POC
index. A production indexing workload should have a dedicated identity.

## Threat scenarios

- **Direct prompt injection:** system instructions, input bounds, and no tools
  reduce impact; adversarial tests and content safety remain required.
- **Indirect prompt injection in documents:** sources are marked as untrusted;
  the app never executes instructions from retrieved data.
- **Data overexposure:** not solved by RAG. Implement deterministic retrieval
  authorization before adding mixed-sensitivity documents.
- **Cost exhaustion:** bounded replicas, search result count, output tokens,
  model quota, and the log cap constrain blast radius. Add per-caller quotas.
- **Telemetry leakage:** application logs counts and failures, not content.

