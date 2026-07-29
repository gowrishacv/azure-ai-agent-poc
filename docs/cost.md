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

Four controls are included. They deliberately do not create an additional
always-on monitoring service:

1. `scripts/destroy-azure-poc.sh` creates a Terraform destroy plan by default.
   Applying the plan requires matching POC tags and an exact subscription-name
   confirmation. Production also requires `--allow-production`. The script
   removes only the known alert rule and action group that Application Insights
   creates automatically, then verifies that state and the resource group are
   gone.
2. `scripts/create-azure-cost-budget.sh` creates a resource-group budget with
   email alerts at 50%, 80%, and 100%.
3. `azure-pipelines-cost-guard.yml` inventories tagged POC resources every day
   at 06:00 UTC. It publishes a lifecycle report whenever cleanup runs.
4. The dev Terraform profile sets a fixed `expires_on` tag 24 hours after
   creation and `auto_destroy=true`. A scheduled cost-guard run can destroy
   that expired dev environment. Production defaults to no expiry and can
   never use the scheduled-expiry mode.

The expiry timestamp is fixed when Terraform creates the environment; normal
plans do not move it forward. Changing `resource_ttl_hours` deliberately
replaces the lifecycle marker and calculates a new expiry.

Preview a development destroy:

```bash
./scripts/destroy-azure-poc.sh \
  --environment dev \
  --state-resource-group "$STATE_RG" \
  --state-storage-account "$STATE_ACCOUNT" \
  --report-file .artifacts/lifecycle-preview.md
```

After reviewing the complete plan, rerun the same command with `--apply`. The
script prints the exact confirmation text to enter.

Create a small monthly budget after deployment:

```bash
RESOURCE_GROUP="$(terraform -chdir=infra output -raw resource_group_name)"

./scripts/create-azure-cost-budget.sh \
  --resource-group "$RESOURCE_GROUP" \
  --amount "<monthly-amount-in-your-billing-currency>" \
  --email "replace-with-your-email@example.com"
```

Azure chooses the budget currency from the billing account; the CLI does not
accept a separate currency parameter.

Azure Cost Management budgets are evaluated from delayed cost data and only
send notifications; they do not stop resources. The guarded Terraform destroy
remains the reliable way to stop this POC's workload charges.

Create a second Azure DevOps pipeline from
`azure-pipelines-cost-guard.yml`. Its schedule targets dev. Before enabling
unattended cleanup, verify that the WIF service connection, variable group, POC
tags, backend key, and dev-only TTL match the intended subscription. A manual
destroy uses `destroyResources: true`. Keep an approval check on
`ai-agent-destroy-prod`; scheduled expiry cleanup is rejected for prod by both
the pipeline and destroy script.

If a terminal or pipeline stops during Terraform apply, first confirm that no
other apply is active. Use the lock ID from Terraform's error with
`terraform force-unlock`, then rerun the guarded destroy. Do not use
`-lock=false`. A partial destroy can remove Terraform outputs; the script falls
back to the resource-group object still in state so cleanup can resume safely.

## When to spend more

Enable minimum replicas for latency SLOs, private endpoints for data-boundary
requirements, APIM for centralized quotas/policies, and additional Search
replicas for query availability—not simply because they are common enterprise
components.
