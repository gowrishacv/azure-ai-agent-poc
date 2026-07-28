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

## Cost safety toolkit

Three controls are included. They deliberately do not create an always-on
monitoring service:

1. `scripts/destroy-azure-poc.sh` creates a Terraform destroy plan by default.
   Applying the plan requires matching POC tags and an exact subscription-name
   confirmation. Production also requires `--allow-production`.
2. `scripts/create-azure-cost-budget.sh` creates a resource-group budget with
   email alerts at 50%, 80%, and 100%.
3. `azure-pipelines-cost-guard.yml` inventories tagged POC resources every day
   at 06:00 UTC. Scheduled runs are read-only and fail when POC resources are
   found, allowing Azure DevOps run-failure notifications to reach subscribers.
   Destruction is available only through an explicit manual parameter and a
   separate Azure DevOps environment that should have an approval check.

Preview a development destroy:

```bash
./scripts/destroy-azure-poc.sh \
  --environment dev \
  --state-resource-group "$STATE_RG" \
  --state-storage-account "$STATE_ACCOUNT"
```

After reviewing the complete plan, rerun the same command with `--apply`. The
script prints the exact confirmation text to enter.

Create a small monthly budget after deployment:

```bash
RESOURCE_GROUP="$(terraform -chdir=infra output -raw resource_group_name)"

./scripts/create-azure-cost-budget.sh \
  --resource-group "$RESOURCE_GROUP" \
  --amount 20 \
  --email "replace-with-your-email@example.com"
```

Azure Cost Management budgets are evaluated from delayed cost data and only
send notifications; they do not stop resources. The guarded Terraform destroy
remains the reliable way to stop this POC's workload charges.

Create a second Azure DevOps pipeline from
`azure-pipelines-cost-guard.yml`. Keep its scheduled default in inventory-only
mode. For a manual destroy, select `destroyResources: true` and require approval
on the `ai-agent-destroy-dev` or `ai-agent-destroy-prod` environment.

## When to spend more

Enable minimum replicas for latency SLOs, private endpoints for data-boundary
requirements, APIM for centralized quotas/policies, and additional Search
replicas for query availability—not simply because they are common enterprise
components.
