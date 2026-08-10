# Azure AI Agent connectivity and ports

This document is the technical legend for
`azure-ai-agent-end-to-end.drawio`. The diagram separates what the Terraform
currently deploys from optional enterprise extensions.

## Implemented flows

| # | Source | Destination | Protocol / port | Identity | Purpose |
|---|---|---|---|---|---|
| 1 | Engineer or application user | Azure DevOps or Container Apps ingress | HTTPS / TCP 443 | Azure DevOps user or optional Entra bearer token | Push/run the pipeline or call `POST /ask`. Container Apps terminates TLS and routes to target port 8000. |
| 2 | Microsoft-hosted Azure DevOps agent | Microsoft Entra ID | HTTPS / TCP 443 | OIDC workload identity federation | Exchange the pipeline OIDC token for an Azure access token; no client secret. |
| 3 | Azure DevOps agent | Azure Resource Manager | HTTPS / TCP 443 | Entra token through `sc-ai-agent-dev` or `sc-ai-agent-prod` | Terraform plan, apply, resource inventory, and guarded destroy. |
| 4 | Azure DevOps agent | Terraform state storage account | HTTPS / TCP 443 | Entra ID + Storage Blob Data Contributor | Read, lock, update, and release `ai-agent/<environment>.tfstate`. Shared-key access is disabled. |
| 5 | Azure DevOps agent | Azure Container Registry | HTTPS / TCP 443 | Entra ID | Submit the ACR remote image build and publish the image. |
| 6 | Container Apps | Azure Container Registry | HTTPS / TCP 443 | User-assigned managed identity + `AcrPull` | Pull the application image. |
| 7 | Container Apps platform | FastAPI container | HTTP / TCP 8000 inside the managed environment | Platform-managed | Route requests and call `/health` and `/ready`. Port 8000 is not opened directly to the Internet. |
| 8 | FastAPI container | Microsoft Entra ID | HTTPS / TCP 443 | User-assigned managed identity | Obtain data-plane tokens for Foundry, Search, and Key Vault. |
| 9 | FastAPI container | Microsoft Foundry / Azure OpenAI endpoint | HTTPS / TCP 443 | Managed identity + Cognitive Services OpenAI User | Create query embeddings and grounded chat completions. |
| 10 | FastAPI container | Azure AI Search | HTTPS / TCP 443 | Managed identity + Search Index Data Reader | Hybrid vector/text retrieval from a bounded set of documents. |
| 11 | FastAPI container | Azure Key Vault | HTTPS / TCP 443 | Managed identity + Key Vault Secrets User | Optional secret retrieval. The current application does not require model or search keys. |
| 12 | FastAPI container | Application Insights ingestion | HTTPS / TCP 443 | Application Insights connection string | Send traces, dependencies, latency, exceptions, and health telemetry. |
| 13 | Application Insights | Log Analytics workspace | Azure-managed ingestion | Azure service integration | Store and query workspace-based telemetry. |
| 14 | Regulatory-evidence job | Microsoft Foundry / Azure OpenAI endpoint | HTTPS / TCP 443 | Pipeline WIF identity | Advisory review of sanitized findings only. Deterministic controls remain authoritative. |
| 15 | Azure DevOps agent | Azure DevOps Pipeline Artifacts | HTTPS / TCP 443 | Pipeline job token | Publish immutable Terraform plan and Markdown/JSON/SHA-256 regulatory evidence. |
| 16 | Scheduled cost guard | Azure Resource Manager / Resource Graph | HTTPS / TCP 443 | Dev WIF service connection | Inventory resources and destroy only expired dev resources tagged `auto_destroy=true`. |

## Private-data-services profile

When `enable_private_networking = true`, Terraform adds a VNet with:

- `snet-container-apps` — `10.42.0.0/23`, delegated to
  `Microsoft.App/environments`;
- `snet-private-endpoints` — `10.42.2.0/24`, private endpoint network policies
  disabled;
- private endpoints for Foundry, Azure AI Search, and Key Vault;
- private DNS zones for `privatelink.cognitiveservices.azure.com`,
  `privatelink.openai.azure.com`, `privatelink.search.windows.net`, and
  `privatelink.vaultcore.azure.net`.

All application data-plane calls still use HTTPS / TCP 443. DNS resolution uses
UDP/TCP 53 through Azure-provided or enterprise DNS. A Microsoft-hosted build
agent cannot reach these private endpoints; indexing must run from a
VNet-connected self-hosted agent.

## Current exposure versus enterprise extension

The current private profile does **not** make the whole application private:

- Container Apps external ingress remains enabled;
- Azure Container Registry public network access remains enabled;
- Log Analytics Internet ingestion and query remain enabled;
- no API Management, Front Door/WAF, Firewall, NAT Gateway, custom DNS resolver,
  or hub-spoke connection is provisioned.

For an enterprise production profile, add Front Door Premium + WAF or an
internal Application Gateway, API Management for authentication/quotas, private
ACR, internal Container Apps ingress, inspected egress, private monitoring
links where required, and a self-hosted agent in an approved management VNet.

## Network-control notes

- Do not open inbound TCP 8000 in an NSG. It is the container target port, not
  a public listener.
- Use service tags and FQDN-aware egress controls instead of hard-coded Azure
  service IP addresses where the selected control supports them.
- Private endpoints do not require opening service public IP ranges; clients
  resolve the service FQDN to a private IP.
- The diagram shows logical flows, not an instruction to bypass Azure Firewall,
  NSGs, proxy, or DNS controls from the target landing zone.
- Regulatory evidence is technical evidence, not certification or legal advice.
