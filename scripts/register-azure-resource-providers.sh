#!/usr/bin/env bash
set -euo pipefail

readonly POLL_INTERVAL_SECONDS=10
readonly REGISTRATION_TIMEOUT_SECONDS=900

readonly -a REQUIRED_PROVIDERS=(
  "Microsoft.App"
  "Microsoft.Authorization"
  "Microsoft.CognitiveServices"
  "Microsoft.ContainerRegistry"
  "Microsoft.Insights"
  "Microsoft.KeyVault"
  "Microsoft.ManagedIdentity"
  "Microsoft.Network"
  "Microsoft.OperationalInsights"
  "Microsoft.Resources"
  "Microsoft.Search"
  "Microsoft.Storage"
)

for provider in "${REQUIRED_PROVIDERS[@]}"; do
  state="$(
    az provider show \
      --namespace "$provider" \
      --query registrationState \
      --output tsv
  )"

  if [[ "$state" == "Registered" ]]; then
    printf '%s is already registered.\n' "$provider"
    continue
  fi

  printf 'Registering %s (current state: %s)...\n' "$provider" "$state"
  az provider register \
    --namespace "$provider" \
    --only-show-errors \
    --output none

  deadline=$((SECONDS + REGISTRATION_TIMEOUT_SECONDS))
  while ((SECONDS < deadline)); do
    state="$(
      az provider show \
        --namespace "$provider" \
        --query registrationState \
        --output tsv
    )"

    if [[ "$state" == "Registered" ]]; then
      printf '%s registration completed.\n' "$provider"
      break
    fi

    printf 'Waiting for %s registration (state: %s)...\n' "$provider" "$state"
    sleep "$POLL_INTERVAL_SECONDS"
  done

  if [[ "$state" != "Registered" ]]; then
    printf 'ERROR: %s did not reach Registered within %s seconds.\n' \
      "$provider" "$REGISTRATION_TIMEOUT_SECONDS" >&2
    exit 1
  fi
done
