#!/usr/bin/env bash
#
# Creates these Azure Resource Manager service connections:
#   sc-ai-agent-dev
#   sc-ai-agent-prod
#
# Each connection uses a separate Microsoft Entra app/service principal and
# workload identity federation. No client secret is created.
#
# The script is preview-only unless --apply is supplied.

set -Eeuo pipefail

ORGANIZATION=""
PROJECT=""
SUBSCRIPTION_ID=""
STATE_RESOURCE_GROUP=""
STATE_STORAGE_ACCOUNT=""
DEPLOYMENT_SCOPE=""
APPLY=false
ASSUME_YES=false

usage() {
  cat <<'EOF'
Usage:
  ./scripts/create-azure-devops-wif-connections.sh \
    --organization https://dev.azure.com/<organization> \
    --project <azure-devops-project> \
    --subscription-id <azure-subscription-id> \
    --state-resource-group <terraform-state-resource-group> \
    --state-storage-account <terraform-state-storage-account> \
    [--deployment-scope <azure-resource-id>] \
    [--apply] [--yes]

Behavior:
  Preview mode (default):
    Validates inputs and displays the identities, service connections, and
    Azure role assignments that would be created.

  --apply:
    Creates separate dev/prod Entra applications and service principals,
    Azure DevOps ARM workload-identity service connections, federated
    credentials, and Azure role assignments.

  --yes:
    Suppresses the final interactive confirmation. Use only in controlled
    automation.

Deployment scope:
  Defaults to /subscriptions/<subscription-id>. This is required by the
  repository's default Terraform design because it creates resource groups.
  Pass a narrower existing resource-group scope only if Terraform is changed
  to deploy inside that pre-created resource group.
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_value() {
  local option="$1"
  local value="${2:-}"
  [[ -n "$value" ]] || die "$option requires a value."
}

while (($# > 0)); do
  case "$1" in
    --organization)
      require_value "$1" "${2:-}"
      ORGANIZATION="$2"
      shift 2
      ;;
    --project)
      require_value "$1" "${2:-}"
      PROJECT="$2"
      shift 2
      ;;
    --subscription-id)
      require_value "$1" "${2:-}"
      SUBSCRIPTION_ID="$2"
      shift 2
      ;;
    --state-resource-group)
      require_value "$1" "${2:-}"
      STATE_RESOURCE_GROUP="$2"
      shift 2
      ;;
    --state-storage-account)
      require_value "$1" "${2:-}"
      STATE_STORAGE_ACCOUNT="$2"
      shift 2
      ;;
    --deployment-scope)
      require_value "$1" "${2:-}"
      DEPLOYMENT_SCOPE="$2"
      shift 2
      ;;
    --apply)
      APPLY=true
      shift
      ;;
    --yes)
      ASSUME_YES=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1. Run with --help."
      ;;
  esac
done

for command in az jq; do
  command -v "$command" >/dev/null 2>&1 || die "Required command not found: $command"
done

[[ -n "$ORGANIZATION" ]] || die "--organization is required."
[[ -n "$PROJECT" ]] || die "--project is required."
[[ -n "$SUBSCRIPTION_ID" ]] || die "--subscription-id is required."
[[ -n "$STATE_RESOURCE_GROUP" ]] || die "--state-resource-group is required."
[[ -n "$STATE_STORAGE_ACCOUNT" ]] || die "--state-storage-account is required."

if [[ -z "$DEPLOYMENT_SCOPE" ]]; then
  DEPLOYMENT_SCOPE="/subscriptions/${SUBSCRIPTION_ID}"
fi

az account show >/dev/null 2>&1 || die "Run 'az login' before this script."

if ! az extension show --name azure-devops >/dev/null 2>&1; then
  die "Azure DevOps CLI extension is missing. Install it with: az extension add --name azure-devops"
fi

az account set --subscription "$SUBSCRIPTION_ID"

TENANT_ID="$(az account show --query tenantId --output tsv)"
SUBSCRIPTION_NAME="$(az account show --query name --output tsv)"
PROJECT_ID="$(
  az devops project show \
    --organization "$ORGANIZATION" \
    --project "$PROJECT" \
    --query id \
    --output tsv
)"
STATE_SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${STATE_RESOURCE_GROUP}/providers/Microsoft.Storage/storageAccounts/${STATE_STORAGE_ACCOUNT}"

# Use ARM directly instead of `az storage account show`. Some Azure CLI
# releases select an unsupported Microsoft.Storage API version. The stable
# 2025-01-01 version is also used by the Terraform bootstrap.
STATE_SCOPE="$(
  az rest \
    --method get \
    --url "https://management.azure.com${STATE_SCOPE}?api-version=2025-01-01" \
    --query id \
    --output tsv
)"

[[ -n "$PROJECT_ID" ]] || die "Azure DevOps project was not found or is not accessible."
[[ -n "$STATE_SCOPE" ]] || die "Terraform state storage account was not found."

printf '\nAzure DevOps organization: %s\n' "$ORGANIZATION"
printf 'Azure DevOps project:      %s (%s)\n' "$PROJECT" "$PROJECT_ID"
printf 'Azure subscription:        %s (%s)\n' "$SUBSCRIPTION_NAME" "$SUBSCRIPTION_ID"
printf 'Microsoft Entra tenant:    %s\n' "$TENANT_ID"
printf 'Deployment RBAC scope:     %s\n' "$DEPLOYMENT_SCOPE"
printf 'State RBAC scope:          %s\n\n' "$STATE_SCOPE"

printf 'The script will configure:\n'
for environment in dev prod; do
  printf '  - sc-ai-agent-%s\n' "$environment"
  printf '      identity: ado-sc-ai-agent-%s\n' "$environment"
  printf '      Contributor: %s\n' "$DEPLOYMENT_SCOPE"
  printf '      Role Based Access Control Administrator: %s\n' "$DEPLOYMENT_SCOPE"
  printf '      Storage Blob Data Contributor: %s\n' "$STATE_SCOPE"
done

if [[ "$APPLY" != true ]]; then
  printf '\nPreview complete. Re-run with --apply after reviewing these scopes.\n'
  exit 0
fi

if [[ "$ASSUME_YES" != true ]]; then
  printf '\nType the Azure subscription name to continue: '
  read -r confirmation
  [[ "$confirmation" == "$SUBSCRIPTION_NAME" ]] || die "Confirmation did not match. No changes made."
fi

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/azure-ai-agent-wif.XXXXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

role_assignment_exists() {
  local principal_id="$1"
  local role="$2"
  local scope="$3"
  local count
  count="$(
    az role assignment list \
      --assignee "$principal_id" \
      --role "$role" \
      --scope "$scope" \
      --query 'length(@)' \
      --output tsv
  )"
  [[ "$count" != "0" ]]
}

ensure_role_assignment() {
  local principal_id="$1"
  local role="$2"
  local scope="$3"

  if role_assignment_exists "$principal_id" "$role" "$scope"; then
    printf 'Role already assigned: %s at %s\n' "$role" "$scope"
    return
  fi

  az role assignment create \
    --assignee-object-id "$principal_id" \
    --assignee-principal-type ServicePrincipal \
    --role "$role" \
    --scope "$scope" \
    --output none
  printf 'Assigned role: %s at %s\n' "$role" "$scope"
}

ensure_identity() {
  local display_name="$1"
  local app_id
  local principal_id

  app_id="$(
    az ad app list \
      --display-name "$display_name" \
      --query "[?displayName == '${display_name}'].appId | [0]" \
      --output tsv
  )"

  if [[ -z "$app_id" ]]; then
    app_id="$(
      az ad app create \
        --display-name "$display_name" \
        --sign-in-audience AzureADMyOrg \
        --query appId \
        --output tsv
    )"
    az ad sp create --id "$app_id" --output none
    printf 'Created Entra identity: %s\n' "$display_name" >&2
  else
    if ! az ad sp show --id "$app_id" >/dev/null 2>&1; then
      az ad sp create --id "$app_id" --output none
    fi
    printf 'Using existing Entra identity: %s\n' "$display_name" >&2
  fi

  principal_id="$(az ad sp show --id "$app_id" --query id --output tsv)"
  printf '%s|%s\n' "$app_id" "$principal_id"
}

ensure_service_connection() {
  local connection_name="$1"
  local app_id="$2"
  local config_file="$TMP_DIR/${connection_name}.json"
  local endpoint_id

  endpoint_id="$(
    az devops service-endpoint list \
      --organization "$ORGANIZATION" \
      --project "$PROJECT" \
      --query "[?name == '${connection_name}'].id | [0]" \
      --output tsv
  )"

  if [[ -z "$endpoint_id" ]]; then
    jq -n \
      --arg subscriptionId "$SUBSCRIPTION_ID" \
      --arg subscriptionName "$SUBSCRIPTION_NAME" \
      --arg connectionName "$connection_name" \
      --arg tenantId "$TENANT_ID" \
      --arg appId "$app_id" \
      --arg projectId "$PROJECT_ID" \
      --arg projectName "$PROJECT" \
      '{
        data: {
          subscriptionId: $subscriptionId,
          subscriptionName: $subscriptionName,
          environment: "AzureCloud",
          scopeLevel: "Subscription",
          creationMode: "Manual"
        },
        name: $connectionName,
        type: "AzureRM",
        url: "https://management.azure.com/",
        authorization: {
          parameters: {
            tenantid: $tenantId,
            serviceprincipalid: $appId
          },
          scheme: "WorkloadIdentityFederation"
        },
        isShared: false,
        isReady: true,
        serviceEndpointProjectReferences: [{
          projectReference: {
            id: $projectId,
            name: $projectName
          },
          name: $connectionName
        }]
      }' > "$config_file"

    endpoint_id="$(
      az devops service-endpoint create \
        --organization "$ORGANIZATION" \
        --project "$PROJECT" \
        --service-endpoint-configuration "$config_file" \
        --query id \
        --output tsv
    )"
    printf 'Created service connection: %s\n' "$connection_name" >&2
  else
    local existing_app_id
    local existing_scheme
    existing_app_id="$(
      az devops service-endpoint show \
        --organization "$ORGANIZATION" \
        --project "$PROJECT" \
        --id "$endpoint_id" \
        --query authorization.parameters.serviceprincipalid \
        --output tsv
    )"
    existing_scheme="$(
      az devops service-endpoint show \
        --organization "$ORGANIZATION" \
        --project "$PROJECT" \
        --id "$endpoint_id" \
        --query authorization.scheme \
        --output tsv
    )"

    [[ "$existing_scheme" == "WorkloadIdentityFederation" ]] ||
      die "$connection_name exists but does not use workload identity federation."
    [[ "$existing_app_id" == "$app_id" ]] ||
      die "$connection_name exists but points to a different Entra application."
    printf 'Using existing service connection: %s\n' "$connection_name" >&2
  fi

  printf '%s\n' "$endpoint_id"
}

ensure_federated_credential() {
  local connection_name="$1"
  local app_id="$2"
  local endpoint_id="$3"
  local credential_name="fic-${connection_name}"
  local endpoint_json
  local issuer
  local subject
  local existing_json
  local credential_file="$TMP_DIR/${credential_name}.json"

  endpoint_json="$(
    az devops service-endpoint show \
      --organization "$ORGANIZATION" \
      --project "$PROJECT" \
      --id "$endpoint_id" \
      --output json
  )"
  issuer="$(jq -r '.authorization.parameters.workloadIdentityFederationIssuer // empty' <<<"$endpoint_json")"
  subject="$(jq -r '.authorization.parameters.workloadIdentityFederationSubject // empty' <<<"$endpoint_json")"

  [[ -n "$issuer" ]] || die "Azure DevOps did not return a federation issuer for $connection_name."
  [[ -n "$subject" ]] || die "Azure DevOps did not return a federation subject for $connection_name."

  existing_json="$(
    az ad app federated-credential list \
      --id "$app_id" \
      --query "[?name == '${credential_name}'] | [0]" \
      --output json
  )"

  if [[ -n "$existing_json" && "$existing_json" != "null" && "$existing_json" != "[]" ]]; then
    local existing_issuer
    local existing_subject
    existing_issuer="$(jq -r '.issuer // empty' <<<"$existing_json")"
    existing_subject="$(jq -r '.subject // empty' <<<"$existing_json")"
    [[ "$existing_issuer" == "$issuer" && "$existing_subject" == "$subject" ]] ||
      die "Federated credential $credential_name exists with a different issuer or subject."
    printf 'Federated credential already configured: %s\n' "$credential_name"
    return
  fi

  jq -n \
    --arg name "$credential_name" \
    --arg issuer "$issuer" \
    --arg subject "$subject" \
    '{
      name: $name,
      issuer: $issuer,
      subject: $subject,
      audiences: ["api://AzureADTokenExchange"]
    }' > "$credential_file"

  az ad app federated-credential create \
    --id "$app_id" \
    --parameters "$credential_file" \
    --output none
  printf 'Created federated credential: %s\n' "$credential_name"
}

for environment in dev prod; do
  connection_name="sc-ai-agent-${environment}"
  identity_name="ado-${connection_name}"

  printf '\nConfiguring %s...\n' "$connection_name"
  identity_result="$(ensure_identity "$identity_name")"
  app_id="${identity_result%%|*}"
  principal_id="${identity_result##*|}"

  endpoint_id="$(ensure_service_connection "$connection_name" "$app_id")"
  ensure_federated_credential "$connection_name" "$app_id" "$endpoint_id"

  ensure_role_assignment "$principal_id" "Contributor" "$DEPLOYMENT_SCOPE"
  ensure_role_assignment \
    "$principal_id" \
    "Role Based Access Control Administrator" \
    "$DEPLOYMENT_SCOPE"
  ensure_role_assignment \
    "$principal_id" \
    "Storage Blob Data Contributor" \
    "$STATE_SCOPE"

  az devops service-endpoint show \
    --organization "$ORGANIZATION" \
    --project "$PROJECT" \
    --id "$endpoint_id" \
    --query '{
      name:name,
      scheme:authorization.scheme,
      ready:isReady,
      subscription:data.subscriptionName
    }' \
    --output table
done

printf '\nCompleted. The service connections are not authorized for every pipeline.\n'
printf 'Authorize only the intended pipeline from Azure DevOps service connection security.\n'
