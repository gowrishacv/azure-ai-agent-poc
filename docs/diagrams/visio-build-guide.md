# Visio and diagrams.net build guide

The editable source is
[`azure-ai-agent-end-to-end.drawio`](azure-ai-agent-end-to-end.drawio). It has
two pages so the architecture remains readable:

1. **End-to-end architecture** — Azure DevOps delivery, application runtime,
   AI/data paths, observability, lifecycle automation, and optional enterprise
   controls.
2. **Connectivity and ports** — the logical flow numbers, protocols, ports,
   identities, trust boundaries, and current-versus-target exposure.

Open the file in [diagrams.net with the Azure library
enabled](https://app.diagrams.net/?splash=0&libs=azure2). The diagram references
the Microsoft Azure icons included in diagrams.net's `azure2` library. It does
not contain copied personal subscription, tenant, resource, or identity values.

To use Microsoft Visio, open the `.drawio` file in diagrams.net and choose
**File → Export as → VSDX**. Review text wrapping and connector labels after
opening the exported file in Visio. SVG, PNG, and PDF are better choices when
an editable Visio file is not required.

## Page setup

- Size: 16:9 landscape.
- Background: off-white `#F7F9FC`.
- Font: Segoe UI.
- Main Azure flow: solid blue `#1877BD`, 2–2.5 pt.
- Supporting/control flow: purple `#7B61A8`, dashed.
- Blocking flow: red `#C63B3B`.
- Keep at least 24 px between shapes and avoid crossing connectors.

## Official icon mapping

The `.drawio` source already uses the corresponding Azure SVGs:

- Azure DevOps;
- Microsoft Entra ID and Managed Identities;
- Azure Storage Accounts for keyless Terraform state;
- Azure Container Apps and Azure Container Registry;
- Microsoft Foundry;
- Azure AI Search;
- Azure Key Vault;
- Private Endpoint and Private DNS Zones;
- Application Insights and Log Analytics;
- Front Door, API Management, Azure Firewall, and Virtual Machine for the
  optional enterprise extension;
- Cost Management and Billing for the budget control.

Terraform is represented by a labelled pipeline stage because it is not an
Azure service. Keep every service name visible, and do not rotate, crop,
recolour, or distort Microsoft product icons. Microsoft publishes the official
[Azure architecture icon guidance and package](https://learn.microsoft.com/azure/architecture/icons/).

## Connectors

### End-to-end architecture page

1. Engineer → Azure DevOps: commit, approve, and run.
2. Azure DevOps → Microsoft Entra ID: OIDC workload identity federation.
3. Pipeline → Azure Resource Manager and remote state: Terraform over HTTPS.
4. Pipeline → regulatory gate: deterministic GDPR/DORA evidence followed by
   optional advisory review of sanitized findings.
5. Pipeline → Container Registry → Container Apps: build, pull, deploy, index,
   and smoke test.
6. User → Container Apps: HTTPS 443; Container Apps forwards internally to the
   FastAPI target port 8000.
7. Container Apps → Foundry: embeddings and grounded chat over HTTPS 443 using
   managed identity.
8. Container Apps → Azure AI Search: hybrid retrieval over HTTPS 443 using
   managed identity.
9. Container Apps → Key Vault: optional retrieval over HTTPS 443 using managed
   identity.
10. Container Apps → Application Insights → Log Analytics: telemetry.
11. Scheduled lifecycle guard → Azure control plane: inventory and destroy only
    tagged, expired development resources.

### Connectivity and ports page

Use [`connectivity-and-ports.md`](connectivity-and-ports.md) as the exact flow
legend. Blue solid connectors are implemented flows, blue dashed connectors
are private-endpoint/DNS paths, purple dashed connectors are controls or
telemetry, and grey dashed connectors are optional enterprise extensions.

Do not draw TCP 8000 as an Internet-open port. HTTPS terminates at Container
Apps ingress, and the managed environment routes internally to the container
target port.

## Important labels

- “Technical evidence — not certification”
- “No source code, Terraform state, secrets, or customer data sent to AI”
- “Managed identity + Azure RBAC”
- “DORA applicability requires financial-sector owner review”
- “Implemented POC” versus “Optional enterprise extension”
- “Budget alerts notify; lifecycle guard performs controlled cleanup”
