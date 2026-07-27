# Visio build guide

Use two pages so the architecture stays readable:

1. **Platform architecture** — Azure services and runtime/data flows.
2. **Regulatory delivery flow** — Azure DevOps stages, evidence, decisions, and
   deployment gating.

The matching SVG files in this directory are clean reference layouts that can
be dragged directly into Visio. Ungroup the SVG if you want to edit individual
vector elements.

## Page setup

- Size: 16:9 landscape.
- Background: off-white `#F7F9FC`.
- Font: Segoe UI.
- Main Azure flow: solid blue `#1877BD`, 2–2.5 pt.
- Supporting/control flow: purple `#7B61A8`, dashed.
- Blocking flow: red `#C63B3B`.
- Keep at least 24 px between shapes and avoid crossing connectors.

## Official icon mapping

Download the official Microsoft Azure SVG package and replace each acronym
badge without resizing or distorting the icon:

- ADO → Azure DevOps;
- TF → Terraform logo or a plain Infrastructure as Code label;
- WIF / ID → Microsoft Entra ID or Managed Identities;
- CA → Azure Container Apps;
- AI → Microsoft Foundry;
- SR → Azure AI Search;
- KV → Azure Key Vault;
- AP → Application Insights;
- CR → Azure Container Registry.

Keep the service name visible below every icon. Do not rotate, crop, recolour,
or distort Microsoft service icons.

Official package:

`https://learn.microsoft.com/azure/architecture/icons/`

## Connectors

### Platform page

1. Azure DevOps → Terraform: pipeline execution.
2. Terraform → WIF: secretless Azure authentication.
3. WIF → GDPR/DORA evidence: deployment identity.
4. Client → Container Apps: HTTPS request.
5. Container Apps → Foundry: chat and embeddings using managed identity.
6. Container Apps → Azure AI Search: retrieval using managed identity.
7. Container Registry → Container Apps: image pull.
8. Container Apps → Application Insights: telemetry.
9. Container Apps → Key Vault: optional secret retrieval.

### Regulatory page

1. Validate → Plan → Approval → Apply.
2. Apply → deterministic GDPR/DORA checks.
3. Critical failure **Yes** → block deployment and retain evidence.
4. Critical failure **No** → sanitize results.
5. Sanitized results → Foundry advisory review.
6. AI review → evidence artifacts.
7. Evidence artifacts → build, deploy, index, and smoke test.
8. DPIA, DORA applicability, and risk acceptance remain human-owned decisions.

## Important labels

- “Technical evidence — not certification”
- “No source code, Terraform state, secrets, or customer data sent to AI”
- “Managed identity + Azure RBAC”
- “DORA applicability requires financial-sector owner review”
