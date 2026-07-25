# Article and social-media kit

## Medium angle

**Title:** Your AI Agent Works in the Demo. Now Let’s Deploy It Properly on Azure

**Thesis:** A production AI agent is a cloud workload, not merely a prompt. The
repository shows the smallest useful platform that adds identity, retrieval,
delivery controls, observability, and a path to private networking without
starting with an expensive enterprise topology.

## Suggested article structure

1. Begin with the working playground demo and the questions security asks.
2. Show the repository architecture and explain why it is one service.
3. Demonstrate keyless access: WIF in the pipeline, managed identity at runtime.
4. Walk through Validate → Plan → Approval → Apply → Deploy → Smoke test.
5. Show the RAG request and its structured citations.
6. Toggle the private-network profile and explain the DNS/build-agent trade-off.
7. Compare the MVP with enterprise extensions.
8. Close with the production gaps: API auth, document ACLs, safety evaluation,
   rate limits, and controlled egress.

## Demo sequence

```text
terraform plan
  → inspect identity and role assignments
  → run Azure DevOps pipeline
  → open /health
  → ask "How should production workloads authenticate?"
  → show citation response
  → open Application Insights dependency map
  → show the private-networking flag
```

## LinkedIn draft

I built the POC behind my “AI Agent Landing Zone” idea.

It deploys a production-style Azure AI agent platform with:

- Microsoft Foundry and Azure AI Search
- Managed identity and Azure RBAC—no model or search keys
- Terraform modules and remote state
- Azure DevOps workload identity federation
- Validate, plan, approval, apply, deploy, and smoke-test stages
- A small RAG API with citations and prompt-injection boundaries
- Application Insights and bounded scaling
- An optional private-endpoint profile

The important design choice was what *not* to put in the MVP.

No AKS. No microservices. No database without a persistence requirement. No API
Management tier until centralized quotas and gateway policy justify the cost.

The default is inexpensive and demonstrable. The enterprise controls are
explicit extensions rather than architecture theatre.

#Azure #MicrosoftFoundry #AzureAI #Terraform #AzureDevOps #AIAgents
#CloudArchitecture #PlatformEngineering #ManagedIdentity

