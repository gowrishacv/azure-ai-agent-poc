# Cost-conscious defaults

Actual prices depend on region, date, reservations, and consumption. Use the
Azure Pricing Calculator with the intended region before deployment.

| Resource | MVP choice | Main cost lever |
|---|---|---|
| Foundry models | Pay-as-you-go, small chat model, 10K TPM capacity | Tokens and provisioned quota |
| Azure AI Search | One Basic replica/partition | Fixed service uptime |
| Container Apps | Consumption, 0 minimum and 2 maximum replicas | Requests, CPU time, minimum replicas |
| Container Registry | Basic | Stored images and build minutes |
| Log Analytics | 30-day retention, 0.5 GB/day ingestion cap | Telemetry volume and retention |
| Application Insights | Workspace based | Same Log Analytics ingestion |
| Key Vault | Standard | Operations |
| Private endpoints | Off by default | Each endpoint and processed data |
| API Management | Not deployed | Fixed gateway tier and capacity |

## Keep the demo bill bounded

- Destroy the resource group after the article/demo.
- Keep one Search replica and one partition.
- Leave Container Apps minimum replicas at zero.
- Use a small model and cap deployment capacity.
- Load only the included three documents.
- Do not enable private networking merely for screenshots.
- Add Azure Cost Management budgets and alerts outside this sample; budgets
  notify but do not automatically stop resources.
- Remove old ACR image tags after the demo under a deliberate retention policy.

## When to spend more

Enable minimum replicas for latency SLOs, private endpoints for data-boundary
requirements, APIM for centralized quotas/policies, and additional Search
replicas for query availability—not simply because they are common enterprise
components.

