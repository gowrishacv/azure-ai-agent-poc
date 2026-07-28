#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Create or update a monthly Azure Cost Management budget for the POC resource group.

Usage:
  ./scripts/create-azure-cost-budget.sh \
    --resource-group RG \
    --amount 20 \
    --email you@example.com \
    [--budget-name ai-agent-poc-monthly]

Budget alerts notify at 50%, 80%, and 100%. Azure budgets do not stop resources.
EOF
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

resource_group=""
amount="20"
email=""
budget_name="ai-agent-poc-monthly"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --resource-group)
      [[ $# -ge 2 ]] || fail "--resource-group requires a value"
      resource_group="$2"
      shift 2
      ;;
    --amount)
      [[ $# -ge 2 ]] || fail "--amount requires a value"
      amount="$2"
      shift 2
      ;;
    --email)
      [[ $# -ge 2 ]] || fail "--email requires a value"
      email="$2"
      shift 2
      ;;
    --budget-name)
      [[ $# -ge 2 ]] || fail "--budget-name requires a value"
      budget_name="$2"
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

[[ -n "$resource_group" ]] || fail "--resource-group is required"
[[ "$amount" =~ ^[0-9]+([.][0-9]{1,2})?$ ]] || fail "--amount must be a positive number"
[[ "$email" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]] ||
  fail "--email is not valid"
command -v az >/dev/null 2>&1 || fail "Azure CLI is required"

az group show --name "$resource_group" >/dev/null

start_date="$(date -u +%Y-%m-01)"
end_date="2035-12-31"
notifications="$(
  printf '{"Actual50":{"enabled":true,"operator":"GreaterThanOrEqualTo","contact-emails":["%s"],"contact-groups":[],"contact-roles":[],"threshold":50},"Actual80":{"enabled":true,"operator":"GreaterThanOrEqualTo","contact-emails":["%s"],"contact-groups":[],"contact-roles":[],"threshold":80},"Actual100":{"enabled":true,"operator":"GreaterThanOrEqualTo","contact-emails":["%s"],"contact-groups":[],"contact-roles":[],"threshold":100}}' \
    "$email" "$email" "$email"
)"
time_period="$(
  printf '{"start-date":"%s","end-date":"%s"}' "$start_date" "$end_date"
)"

common_args=(
  --resource-group "$resource_group"
  --budget-name "$budget_name"
  --amount "$amount"
  --category Cost
  --time-grain Monthly
  --time-period "$time_period"
  --notifications "$notifications"
)

if az consumption budget show-with-rg \
  --resource-group "$resource_group" \
  --budget-name "$budget_name" >/dev/null 2>&1; then
  etag="$(
    az consumption budget show-with-rg \
      --resource-group "$resource_group" \
      --budget-name "$budget_name" \
      --query eTag \
      --output tsv
  )"
  az consumption budget update-with-rg "${common_args[@]}" --e-tag "$etag"
  printf 'Updated budget: %s\n' "$budget_name"
else
  az consumption budget create-with-rg "${common_args[@]}"
  printf 'Created budget: %s\n' "$budget_name"
fi

printf 'Monthly amount: %s\nAlerts: %s at 50%%, 80%%, and 100%%\n' "$amount" "$email"
printf 'Reminder: budget alerts notify; they do not stop or delete Azure resources.\n'
