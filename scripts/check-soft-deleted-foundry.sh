#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf 'Usage: %s <terraform-plan-file>\n' "$0" >&2
  exit 2
fi

readonly PLAN_FILE="$1"
readonly FOUNDRY_ADDRESS="module.ai.azurerm_cognitive_account.foundry"

if [[ ! -f "$PLAN_FILE" ]]; then
  printf 'ERROR: Terraform plan file not found: %s\n' "$PLAN_FILE" >&2
  exit 2
fi

plan_json="$(terraform show -json "$PLAN_FILE")"

planned_account="$(
  jq -c --arg address "$FOUNDRY_ADDRESS" '
    first(
      (.planned_values.root_module? // {}) |
      .. |
      objects |
      select(.address? == $address) |
      .values?
    ) // empty
  ' <<<"$plan_json"
)"

planned_actions="$(
  jq -c --arg address "$FOUNDRY_ADDRESS" '
    first(
      .resource_changes[]? |
      select(.address == $address) |
      .change.actions
    ) // []
  ' <<<"$plan_json"
)"

if [[ -z "$planned_account" || "$planned_account" == "null" ]]; then
  printf 'No planned Foundry account was found; skipping soft-delete check.\n'
  exit 0
fi

account_name="$(jq -r '.name // empty' <<<"$planned_account")"
resource_group="$(jq -r '.resource_group_name // empty' <<<"$planned_account")"
location="$(jq -r '.location // empty' <<<"$planned_account")"

if [[ -z "$account_name" || -z "$resource_group" || -z "$location" ]]; then
  if jq -e 'index("create") != null' <<<"$planned_actions" >/dev/null; then
    printf '%s\n' \
      'Planned Foundry account identity is generated during first apply; skipping soft-delete check.'
    exit 0
  fi
  printf 'ERROR: Could not read the planned Foundry account name, resource group, and location.\n' >&2
  exit 1
fi

printf 'Checking for soft-deleted Foundry account %s in %s...\n' \
  "$account_name" "$location"

deleted_accounts="$(
  az cognitiveservices account list-deleted \
  --only-show-errors \
  --output json
)"

if ! jq -e \
  --arg account_name "$account_name" \
  --arg resource_group_fragment "/resourceGroups/${resource_group}/" \
  --arg location "$location" \
  '
    any(
      .[];
      (.name | ascii_downcase) == ($account_name | ascii_downcase) and
      (.location | ascii_downcase) == ($location | ascii_downcase) and
      (.id | ascii_downcase | contains($resource_group_fragment | ascii_downcase))
    )
  ' <<<"$deleted_accounts" >/dev/null; then
  printf 'No conflicting soft-deleted Foundry account was found.\n'
  exit 0
fi

printf '\nERROR: A soft-deleted Foundry account blocks this Terraform plan.\n' >&2
printf 'Account:        %s\n' "$account_name" >&2
printf 'Resource group: %s\n' "$resource_group" >&2
printf 'Location:       %s\n\n' "$location" >&2
printf 'If the deleted account is no longer needed, permanently purge it with:\n\n' >&2
printf 'az cognitiveservices account purge \\\n' >&2
printf '  --name %q \\\n' "$account_name" >&2
printf '  --resource-group %q \\\n' "$resource_group" >&2
printf '  --location %q\n\n' "$location" >&2
printf 'Purging is permanent. Review the target before running the command.\n' >&2
exit 1
