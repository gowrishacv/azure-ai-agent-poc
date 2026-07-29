#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Safely preview or destroy one Azure AI Agent POC environment.

Usage:
  ./scripts/destroy-azure-poc.sh \
    --environment dev \
    --state-resource-group RG \
    --state-storage-account ACCOUNT \
    [--state-container tfstate] \
    [--apply] \
    [--allow-production] \
    [--only-if-expired] \
    [--report-file PATH] \
    [--non-interactive --confirm "DESTROY dev SUBSCRIPTION_NAME"]

Safety behavior:
  - The default action creates and displays a destroy plan only.
  - The resource group tags must identify this POC before apply is allowed.
  - Production requires --allow-production.
  - Scheduled expiry cleanup is restricted to dev and requires auto_destroy=true.
  - Known Application Insights-generated alert resources are removed before apply.
  - Apply requires the exact subscription-name confirmation.
EOF
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

environment=""
state_resource_group="${TF_STATE_RESOURCE_GROUP:-}"
state_storage_account="${TF_STATE_STORAGE_ACCOUNT:-}"
state_container="${TF_STATE_CONTAINER:-tfstate}"
apply=false
allow_production=false
only_if_expired=false
non_interactive=false
confirmation=""
report_file=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment)
      [[ $# -ge 2 ]] || fail "--environment requires a value"
      environment="$2"
      shift 2
      ;;
    --state-resource-group)
      [[ $# -ge 2 ]] || fail "--state-resource-group requires a value"
      state_resource_group="$2"
      shift 2
      ;;
    --state-storage-account)
      [[ $# -ge 2 ]] || fail "--state-storage-account requires a value"
      state_storage_account="$2"
      shift 2
      ;;
    --state-container)
      [[ $# -ge 2 ]] || fail "--state-container requires a value"
      state_container="$2"
      shift 2
      ;;
    --apply)
      apply=true
      shift
      ;;
    --allow-production)
      allow_production=true
      shift
      ;;
    --only-if-expired)
      only_if_expired=true
      shift
      ;;
    --report-file)
      [[ $# -ge 2 ]] || fail "--report-file requires a value"
      report_file="$2"
      shift 2
      ;;
    --non-interactive)
      non_interactive=true
      shift
      ;;
    --confirm)
      [[ $# -ge 2 ]] || fail "--confirm requires a value"
      confirmation="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

[[ "$environment" =~ ^(dev|test|prod)$ ]] ||
  fail "--environment must be dev, test, or prod"
[[ -n "$state_resource_group" ]] || fail "Terraform state resource group is required"
[[ -n "$state_storage_account" ]] || fail "Terraform state storage account is required"
[[ -n "$state_container" ]] || fail "Terraform state container is required"

if [[ "$environment" == "prod" && "$apply" == true && "$allow_production" != true ]]; then
  fail "Production destruction also requires --allow-production"
fi

if [[ "$only_if_expired" == true ]]; then
  [[ "$environment" == "dev" ]] ||
    fail "--only-if-expired is restricted to the dev environment"
  [[ "$apply" == true ]] ||
    fail "--only-if-expired requires --apply"
fi

require_command az
require_command terraform

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd "$script_dir/.." && pwd)"
terraform_dir="$repository_root/infra"
tfvars_file="$terraform_dir/environments/${environment}.tfvars"
backend_key="ai-agent/${environment}.tfstate"

[[ -f "$tfvars_file" ]] || fail "Terraform variables file not found: $tfvars_file"

write_report() {
  local status="$1"
  local detail="$2"
  local remaining="${3:-unknown}"

  [[ -n "$report_file" ]] || return 0
  mkdir -p "$(dirname "$report_file")"
  {
    printf '# Azure AI Agent POC lifecycle report\n\n'
    printf -- '- Generated: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf -- '- Environment: `%s`\n' "$environment"
    printf -- '- Resource group: `%s`\n' "${resource_group_name:-not available}"
    printf -- '- Terraform state key: `%s`\n' "$backend_key"
    printf -- '- Status: **%s**\n' "$status"
    printf -- '- Remaining Terraform resources: `%s`\n\n' "$remaining"
    printf '%s\n' "$detail"
  } >"$report_file"
}

resource_group_from_state() {
  terraform -chdir="$terraform_dir" state show -no-color azurerm_resource_group.this \
    2>/dev/null |
    sed -n 's/^[[:space:]]*name[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' |
    head -n 1
}

collect_generated_monitoring_resources() {
  local resource_group="$1"
  local resource_id=""

  generated_monitoring_ids=()

  while IFS= read -r resource_id; do
    [[ -n "$resource_id" ]] && generated_monitoring_ids+=("$resource_id")
  done < <(
    az resource list \
      --resource-group "$resource_group" \
      --query "[?contains(type, 'smartDetectorAlertRules') && starts_with(name, 'Failure Anomalies - ')].id" \
      --output tsv
  )

  while IFS= read -r resource_id; do
    [[ -n "$resource_id" ]] && generated_monitoring_ids+=("$resource_id")
  done < <(
    az resource list \
      --resource-group "$resource_group" \
      --query "[?type=='microsoft.insights/actiongroups' && name=='Application Insights Smart Detection'].id" \
      --output tsv
  )
}

delete_generated_monitoring_resources() {
  local resource_id=""

  for resource_id in "${generated_monitoring_ids[@]}"; do
    printf 'Deleting generated monitoring resource: %s\n' "$resource_id"
    az resource delete --ids "$resource_id"
  done
}

subscription_id="$(az account show --query id --output tsv)"
subscription_name="$(az account show --query name --output tsv)"
tenant_id="$(az account show --query tenantId --output tsv)"

[[ -n "$subscription_id" && -n "$subscription_name" ]] ||
  fail "No active Azure CLI subscription. Run az login and az account set first."

printf 'Azure subscription: %s (%s)\n' "$subscription_name" "$subscription_id"
printf 'Microsoft Entra tenant: %s\n' "$tenant_id"
printf 'Environment: %s\n' "$environment"
printf 'State: %s/%s/%s/%s\n' \
  "$state_resource_group" "$state_storage_account" "$state_container" "$backend_key"

export ARM_SUBSCRIPTION_ID="$subscription_id"
export ARM_TENANT_ID="$tenant_id"
export ARM_USE_AZUREAD=true

terraform -chdir="$terraform_dir" init -reconfigure \
  -backend-config="resource_group_name=$state_resource_group" \
  -backend-config="storage_account_name=$state_storage_account" \
  -backend-config="container_name=$state_container" \
  -backend-config="key=$backend_key" \
  -backend-config="use_azuread_auth=true"

state_count="$(terraform -chdir="$terraform_dir" state list | sed '/^[[:space:]]*$/d' | wc -l | tr -d ' ')"
if [[ "$state_count" == "0" ]]; then
  write_report "already empty" "No Terraform-managed workload resources remain." "0"
  printf 'No Terraform-managed resources remain in %s.\n' "$backend_key"
  exit 0
fi

resource_group_name="$(
  terraform -chdir="$terraform_dir" output -raw resource_group_name 2>/dev/null || true
)"
if [[ -z "$resource_group_name" ]]; then
  resource_group_name="$(resource_group_from_state || true)"
fi

if [[ -n "$resource_group_name" ]] &&
  az group show --name "$resource_group_name" >/dev/null 2>&1; then
  purpose_tag="$(
    az group show --name "$resource_group_name" --query "tags.purpose" --output tsv
  )"
  environment_tag="$(
    az group show --name "$resource_group_name" --query "tags.environment" --output tsv
  )"
  managed_by_tag="$(
    az group show --name "$resource_group_name" --query "tags.managed_by" --output tsv
  )"
  auto_destroy_tag="$(
    az group show --name "$resource_group_name" --query "tags.auto_destroy" --output tsv
  )"
  expires_on_tag="$(
    az group show --name "$resource_group_name" --query "tags.expires_on" --output tsv
  )"

  [[ "$purpose_tag" == "azure-ai-agent-poc" ]] ||
    fail "Resource group $resource_group_name does not have the expected purpose tag"
  [[ "$environment_tag" == "$environment" ]] ||
    fail "Resource group environment tag does not match $environment"
  [[ "$managed_by_tag" == "terraform" ]] ||
    fail "Resource group $resource_group_name is not tagged as Terraform-managed"

  printf 'Verified resource group: %s\n' "$resource_group_name"

  if [[ "$only_if_expired" == true ]]; then
    [[ "$auto_destroy_tag" == "true" ]] || {
      write_report "retained" "Scheduled cleanup skipped because auto_destroy is not true." "$state_count"
      printf 'Scheduled cleanup skipped: auto_destroy is not true.\n'
      exit 0
    }
    [[ "$expires_on_tag" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] ||
      fail "Scheduled cleanup requires an expires_on UTC tag"
    current_time="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    if [[ "$expires_on_tag" > "$current_time" ]]; then
      write_report "retained" "Scheduled cleanup skipped because the environment has not expired." "$state_count"
      printf 'Scheduled cleanup skipped: expires_on=%s, now=%s.\n' \
        "$expires_on_tag" "$current_time"
      exit 0
    fi
    printf 'Environment expired at %s and is eligible for scheduled cleanup.\n' "$expires_on_tag"
  fi

  collect_generated_monitoring_resources "$resource_group_name"
  printf 'Known generated monitoring resources to remove before apply: %s\n' \
    "${#generated_monitoring_ids[@]}"
else
  [[ "$only_if_expired" != true ]] ||
    fail "Scheduled cleanup stopped because the Terraform resource group could not be verified"
  printf 'WARNING: Terraform output resource group is missing; checking remaining state only.\n'
  generated_monitoring_ids=()
fi

plan_file="$(mktemp "${TMPDIR:-/tmp}/ai-agent-${environment}-destroy.XXXXXX")"
cleanup() {
  case "$plan_file" in
    "${TMPDIR:-/tmp}"/ai-agent-"$environment"-destroy.*)
      rm -f -- "$plan_file"
      ;;
  esac
}
trap cleanup EXIT

terraform -chdir="$terraform_dir" plan \
  -destroy \
  -var-file="$tfvars_file" \
  -out="$plan_file"

terraform -chdir="$terraform_dir" show -no-color "$plan_file"

if [[ "$apply" != true ]]; then
  write_report "preview only" "A destroy plan was created; no resources were deleted." "$state_count"
  printf '\nDRY RUN ONLY. Nothing was deleted.\n'
  printf 'Review the plan, then rerun the same command with --apply.\n'
  exit 0
fi

expected_confirmation="DESTROY ${environment} ${subscription_name}"
if [[ "$non_interactive" == true ]]; then
  [[ "$confirmation" == "$expected_confirmation" ]] ||
    fail "Non-interactive confirmation must exactly equal: $expected_confirmation"
else
  printf '\nType exactly: %s\n> ' "$expected_confirmation"
  read -r confirmation
  [[ "$confirmation" == "$expected_confirmation" ]] ||
    fail "Confirmation did not match. No resources were deleted."
fi

delete_generated_monitoring_resources

set +e
terraform -chdir="$terraform_dir" apply -auto-approve "$plan_file"
apply_status=$?
set -e

if [[ "$apply_status" -ne 0 ]]; then
  remaining_after_failure="$(
    terraform -chdir="$terraform_dir" state list 2>/dev/null |
      sed '/^[[:space:]]*$/d' |
      wc -l |
      tr -d ' '
  )"
  write_report \
    "failed" \
    "Terraform apply failed. Review the pipeline log and rerun the guarded destroy." \
    "$remaining_after_failure"
  exit "$apply_status"
fi

remaining_count="$(
  terraform -chdir="$terraform_dir" state list | sed '/^[[:space:]]*$/d' | wc -l | tr -d ' '
)"
if [[ "$remaining_count" != "0" ]]; then
  write_report "incomplete" "Terraform state still contains resources." "$remaining_count"
  fail "Destroy completed with $remaining_count resources still present in Terraform state"
fi

if [[ -n "$resource_group_name" ]] &&
  az group exists --name "$resource_group_name" | grep -q '^true$'; then
  write_report "incomplete" "Terraform state is empty but the resource group still exists." "0"
  fail "Terraform state is empty but resource group still exists: $resource_group_name"
fi

write_report "destroyed" "Destroy completed and both Terraform state and resource-group deletion were verified." "0"
printf 'Destroy verified. No workload resources remain for %s.\n' "$environment"
printf 'The Terraform state account and Azure DevOps identities were intentionally retained.\n'
