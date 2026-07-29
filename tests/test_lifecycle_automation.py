from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DESTROY_SCRIPT = REPOSITORY_ROOT / "scripts" / "destroy-azure-poc.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _fake_commands(tmp_path: Path) -> tuple[Path, Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "applied"
    command_log = tmp_path / "commands.log"

    _write_executable(
        bin_dir / "terraform",
        """#!/usr/bin/env bash
set -euo pipefail
command_name="${2:-}"
case "$command_name" in
  init)
    exit 0
    ;;
  state)
    case "${3:-}" in
      list)
        if [[ ! -f "$FAKE_STATE_MARKER" ]]; then
          echo "azurerm_resource_group.this"
        fi
        ;;
      show)
        printf 'resource "azurerm_resource_group" "this" {\\n  name = "rg-aiagent-dev-test"\\n}\\n'
        ;;
    esac
    ;;
  output)
    exit 1
    ;;
  plan)
    for argument in "$@"; do
      if [[ "$argument" == -out=* ]]; then
        : >"${argument#-out=}"
      fi
    done
    ;;
  show)
    echo "Plan: 0 to add, 0 to change, 1 to destroy."
    ;;
  apply)
    : >"$FAKE_STATE_MARKER"
    ;;
  *)
    echo "Unexpected terraform command: $*" >&2
    exit 1
    ;;
esac
""",
    )

    _write_executable(
        bin_dir / "az",
        """#!/usr/bin/env bash
set -euo pipefail
arguments="$*"
if [[ "$arguments" == "account show --query id --output tsv" ]]; then
  echo "subscription-test"
elif [[ "$arguments" == "account show --query name --output tsv" ]]; then
  echo "Test Subscription"
elif [[ "$arguments" == "account show --query tenantId --output tsv" ]]; then
  echo "tenant-test"
elif [[ "$arguments" == group\\ show*tags.purpose* ]]; then
  echo "azure-ai-agent-poc"
elif [[ "$arguments" == group\\ show*tags.environment* ]]; then
  echo "dev"
elif [[ "$arguments" == group\\ show*tags.managed_by* ]]; then
  echo "terraform"
elif [[ "$arguments" == group\\ show*tags.auto_destroy* ]]; then
  echo "true"
elif [[ "$arguments" == group\\ show*tags.expires_on* ]]; then
  echo "$FAKE_EXPIRES_ON"
elif [[ "$arguments" == group\\ show* ]]; then
  exit 0
elif [[ "$arguments" == resource\\ list*Failure\\ Anomalies* ]]; then
  echo "/generated/failure-anomalies"
elif [[ "$arguments" == resource\\ list*Application\\ Insights\\ Smart\\ Detection* ]]; then
  echo "/generated/smart-detection-action-group"
elif [[ "$arguments" == resource\\ delete* ]]; then
  printf '%s\\n' "$arguments" >>"$FAKE_COMMAND_LOG"
elif [[ "$arguments" == "group exists --name rg-aiagent-dev-test" ]]; then
  echo "false"
else
  echo "Unexpected az command: $arguments" >&2
  exit 1
fi
""",
    )

    return bin_dir, marker, command_log


def _environment(
    bin_dir: Path,
    marker: Path,
    command_log: Path,
    expires_on: str,
) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{bin_dir}:{environment['PATH']}",
            "FAKE_STATE_MARKER": str(marker),
            "FAKE_COMMAND_LOG": str(command_log),
            "FAKE_EXPIRES_ON": expires_on,
        }
    )
    return environment


def test_expired_dev_cleanup_removes_generated_resources_and_reports(tmp_path: Path) -> None:
    bin_dir, marker, command_log = _fake_commands(tmp_path)
    report_file = tmp_path / "report.md"

    result = subprocess.run(
        [
            "bash",
            str(DESTROY_SCRIPT),
            "--environment",
            "dev",
            "--state-resource-group",
            "state-rg",
            "--state-storage-account",
            "stateaccount",
            "--state-container",
            "tfstate",
            "--apply",
            "--only-if-expired",
            "--non-interactive",
            "--confirm",
            "DESTROY dev Test Subscription",
            "--report-file",
            str(report_file),
        ],
        cwd=REPOSITORY_ROOT,
        env=_environment(bin_dir, marker, command_log, "2020-01-01T00:00:00Z"),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert marker.exists()
    deleted_resources = command_log.read_text(encoding="utf-8")
    assert "/generated/failure-anomalies" in deleted_resources
    assert "/generated/smart-detection-action-group" in deleted_resources
    report = report_file.read_text(encoding="utf-8")
    assert "Status: **destroyed**" in report
    assert "Remaining Terraform resources: `0`" in report


def test_unexpired_dev_is_retained_without_deleting_resources(tmp_path: Path) -> None:
    bin_dir, marker, command_log = _fake_commands(tmp_path)
    report_file = tmp_path / "report.md"

    result = subprocess.run(
        [
            "bash",
            str(DESTROY_SCRIPT),
            "--environment",
            "dev",
            "--state-resource-group",
            "state-rg",
            "--state-storage-account",
            "stateaccount",
            "--apply",
            "--only-if-expired",
            "--non-interactive",
            "--confirm",
            "DESTROY dev Test Subscription",
            "--report-file",
            str(report_file),
        ],
        cwd=REPOSITORY_ROOT,
        env=_environment(bin_dir, marker, command_log, "2999-01-01T00:00:00Z"),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert not command_log.exists()
    assert "Scheduled cleanup skipped" in result.stdout
    assert "Status: **retained**" in report_file.read_text(encoding="utf-8")


def test_only_dev_opts_into_automatic_expiry_cleanup() -> None:
    dev = (REPOSITORY_ROOT / "infra" / "environments" / "dev.tfvars").read_text(
        encoding="utf-8"
    )
    prod = (REPOSITORY_ROOT / "infra" / "environments" / "prod.tfvars").read_text(
        encoding="utf-8"
    )
    pipeline = (REPOSITORY_ROOT / "azure-pipelines-cost-guard.yml").read_text(
        encoding="utf-8"
    )

    assert "resource_ttl_hours        = 24" in dev
    assert "auto_destroy              = true" in dev
    assert "resource_ttl_hours        = 0" in prod
    assert "auto_destroy              = false" in prod
    assert "eq(variables['Build.Reason'], 'Schedule')" in pipeline
    assert "${{ eq(parameters.environment, 'dev') }}" in pipeline
