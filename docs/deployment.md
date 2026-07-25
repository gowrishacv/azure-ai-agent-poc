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

## 3. Bootstrap state

Apply `infra/bootstrap`. Grant each pipeline WIF identity `Storage Blob Data
Contributor` on the state storage account. Shared-key access is disabled.

## 4. Configure Azure DevOps

- Create environment-specific WIF service connections.
- Grant resource creation and role-assignment permissions at the smallest
  viable scope.
- Create the three-value variable groups documented in the README.
- Authorize the YAML pipeline to use each protected resource.
- Add approval and branch-control checks to the production environment.
- Set production environment locking to sequential.

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

