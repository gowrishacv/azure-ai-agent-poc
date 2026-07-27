# Deployment runbook

## 1. Verify regional capacity

Confirm that the selected region supports both model names and versions in the
Foundry catalog. If a deployment returns `SKUNotAvailable` or a quota error,
change the region/model values in the environment tfvars; do not silently
replace the intended model in the pipeline.

## 2. Register providers

Register these resource providers once per subscription:

```bash
for provider in \
  Microsoft.App \
  Microsoft.CognitiveServices \
  Microsoft.ContainerRegistry \
  Microsoft.Insights \
  Microsoft.KeyVault \
  Microsoft.ManagedIdentity \
  Microsoft.Network \
  Microsoft.OperationalInsights \
  Microsoft.Search; do
  az provider register --namespace "$provider"
done
```

The Azure DevOps Plan stage also performs this registration idempotently. It
waits until each provider reaches `Registered` before creating the reviewed
Terraform plan.

## Recover from a soft-deleted Foundry account

Microsoft Foundry accounts use soft delete. Recreating a Terraform-managed
account with the same name fails with `FlagMustBeSetForRestore` while the old
account remains recoverable.

Confirm the exact deleted account before changing it:

```bash
az cognitiveservices account show-deleted \
  --name "<account-name>" \
  --resource-group "<original-resource-group>" \
  --location "<location>" \
  --output table
```

If the deleted account and its data are no longer required, permanently purge
it:

```bash
az cognitiveservices account purge \
  --name "<account-name>" \
  --resource-group "<original-resource-group>" \
  --location "<location>"
```

Purging cannot be undone. The pipeline checks the reviewed Terraform plan for
this conflict and prints the exact purge command, but it never purges
automatically.

## 3. Bootstrap state

Apply `infra/bootstrap`. Grant each pipeline WIF identity `Storage Blob Data
Contributor` on the state storage account. Shared-key access is disabled.

The bootstrap uses AzAPI control-plane resources for the storage account and
container. This is intentional: AzureRM performs a key-based data-plane
readiness probe while creating a storage account, which fails when shared-key
authorization is disabled from creation.

### Recover from the former AzureRM bootstrap

If an earlier apply created the storage account but failed with
`KeyBasedAuthenticationNotPermitted`, update to the current bootstrap and run:

```bash
terraform -chdir=infra/bootstrap init -upgrade

SUBSCRIPTION_ID="$(az account show --query id --output tsv)"
STATE_RG="$(terraform -chdir=infra/bootstrap state show azurerm_resource_group.state | awk -F' = ' '/name / {gsub(/"/, "", $2); print $2}')"
STATE_ACCOUNT="staiagenttf<suffix-shown-in-the-error>"
STATE_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${STATE_RG}/providers/Microsoft.Storage/storageAccounts/${STATE_ACCOUNT}"

terraform -chdir=infra/bootstrap import azapi_resource.state "$STATE_ID"
terraform -chdir=infra/bootstrap apply
```

Use the exact storage account name from the failed apply. Import is necessary
because Azure created the account before its data-plane readiness check failed.

## 4. Configure Azure DevOps

- Create environment-specific WIF service connections.
- Grant resource creation and role-assignment permissions at the smallest
  viable scope.
- Create the three-value variable groups documented in the README.
- Authorize the YAML pipeline to use each protected resource.
- Add approval and branch-control checks to the production environment.
- Set production environment locking to sequential.

The repository includes
`scripts/create-azure-devops-wif-connections.sh` to create the `dev` and `prod`
service connections. It uses separate Entra applications, creates no client
secrets, defaults to preview mode, and refuses to replace mismatched existing
connections or federated credentials.

## 5. Run plan-only

Queue with `apply=false`. Review:

- Model names, versions, SKU, and capacity
- Resource region and naming
- Role assignments
- Whether public access is enabled
- Expected create/change/destroy counts

## 6. Apply and deploy

Queue with `apply=true`. The pipeline applies the published plan, builds in ACR,
updates Container Apps, seeds the index for the public MVP profile, and calls
`/health`.

RBAC propagation can delay the first index load. Retry the stage after several
minutes; do not replace managed identity with an API key.

## 7. Private profile

Use a self-hosted Azure DevOps agent with line of sight to the VNet and private
DNS zones. The hosted agent can still deploy control-plane resources, but it
cannot reach private Search and Foundry data-plane endpoints to seed the index.

## 8. Rollback

Container Apps keeps revisions. For a bad application release, direct traffic
back to a known image/revision. For infrastructure, create a new reviewed
Terraform plan that restores the previous configuration; do not edit state or
apply an old plan after state has changed.
