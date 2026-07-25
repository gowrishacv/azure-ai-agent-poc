# Architecture

## Design goal

Demonstrate how an Azure AI prototype becomes a governed cloud workload without
turning a POC into a costly microservice platform. Expected scale is fewer than
1,000 users, a small document set, and a small engineering team.

## Runtime flow

```mermaid
sequenceDiagram
    actor User
    participant API as Container Apps API
    participant Search as Azure AI Search
    participant Foundry as Microsoft Foundry
    participant Monitor as Application Insights

    User->>API: POST /ask
    API->>API: Validate length and token
    API->>Foundry: Create query embedding (managed identity)
    API->>Search: Hybrid vector/text search (managed identity)
    Search-->>API: Top bounded documents
    API->>API: Mark sources as untrusted data
    API->>Foundry: Grounded prompt + sources
    Foundry-->>API: Answer with citation markers
    API-->>User: Answer + structured citations
    API-->>Monitor: Latency/dependency telemetry
```

The API does not expose arbitrary tools or write actions. That is deliberate:
adding an agent tool expands the identity's authority and requires its own
schema validation, allowlist, timeout, audit trail, and—when consequential—a
human approval step.

## Trust boundaries

```mermaid
flowchart TB
    subgraph Internet["Untrusted network"]
      User["Client input"]
    end
    subgraph App["Application trust boundary"]
      API["FastAPI<br/>validation + auth hook"]
      MI["User-assigned identity"]
    end
    subgraph Data["Azure service boundary"]
      Search["AI Search<br/>untrusted retrieved text"]
      Foundry["Foundry models"]
      KV["Key Vault"]
    end
    User --> API
    API --> MI
    MI -->|"RBAC: read only"| Search
    MI -->|"RBAC: model user"| Foundry
    MI -.->|"RBAC: secrets user"| KV
```

The model is never an authorization decision point. Azure RBAC controls service
access; future document-level access must be applied as deterministic search
filters before content reaches the model.

## Deployment flow

```mermaid
flowchart LR
    C["Commit / PR"] --> V["Validate<br/>lint, test, terraform validate"]
    V --> P["Plan<br/>WIF + remote state"]
    P --> A{"Apply requested?<br/>Environment approval"}
    A -->|No| Stop["Review only"]
    A -->|Yes| I["Apply immutable plan"]
    I --> B["ACR remote build"]
    B --> D["Container App update"]
    D --> X["Index sample data"]
    X --> H["Health smoke test"]
```

The plan file is the artifact applied later in the same run. Production uses an
Azure DevOps environment approval and sequential locking.

## Profiles

### MVP

- Foundry, Search, and Key Vault have public endpoints.
- Local/key authentication is disabled for Foundry and Search.
- Azure RBAC and managed identity remain mandatory.
- Container Apps scales to zero.
- This is the recommended article/demo profile.

### Private POC

Set `enable_private_networking = true`:

- Container Apps environment joins a delegated subnet.
- Foundry, Search, and Key Vault public access is disabled.
- Private endpoints and required private DNS zones are created.
- Indexing must execute from a VNet-connected build agent.

This profile proves the network pattern. It does not include enterprise hub
connectivity, Azure Firewall egress inspection, custom DNS forwarders, or
private ACR; those depend on the organization's landing zone.

## Deliberately excluded from the MVP

- API Management: valuable for quotas, model routing, and policy enforcement,
  but a fixed gateway tier is difficult to justify for a small POC.
- Cosmos DB: no conversation persistence is required.
- Service Bus: the request flow is synchronous and short-lived.
- AKS: Container Apps provides the needed scale-to-zero and identity features.
- Agent write tools: the demo is read-only by design.

