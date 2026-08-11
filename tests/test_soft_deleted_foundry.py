import json
import os
import stat
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY_ROOT / "scripts" / "check-soft-deleted-foundry.sh"
FOUNDRY_ADDRESS = "module.ai.azurerm_cognitive_account.foundry"


def write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def run_check(
    tmp_path: Path,
    plan: dict,
    deleted_accounts: list[dict] | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    plan_json = tmp_path / "plan.json"
    plan_json.write_text(json.dumps(plan), encoding="utf-8")
    deleted_json = tmp_path / "deleted.json"
    deleted_json.write_text(json.dumps(deleted_accounts or []), encoding="utf-8")
    az_marker = tmp_path / "az-called"
    plan_file = tmp_path / "plan.tfplan"
    plan_file.touch()

    write_executable(
        bin_dir / "terraform",
        "#!/usr/bin/env bash\nset -euo pipefail\ncat \"$FAKE_PLAN_JSON\"\n",
    )
    write_executable(
        bin_dir / "az",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "touch \"$FAKE_AZ_MARKER\"\n"
        "cat \"$FAKE_DELETED_JSON\"\n",
    )
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{bin_dir}:{environment['PATH']}",
            "FAKE_PLAN_JSON": str(plan_json),
            "FAKE_DELETED_JSON": str(deleted_json),
            "FAKE_AZ_MARKER": str(az_marker),
        }
    )
    result = subprocess.run(
        ["bash", str(SCRIPT), str(plan_file)],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    return result, az_marker


def planned_resource(values: dict, actions: list[str]) -> dict:
    return {
        "planned_values": {
            "root_module": {
                "child_modules": [
                    {"resources": [{"address": FOUNDRY_ADDRESS, "values": values}]}
                ]
            }
        },
        "resource_changes": [
            {"address": FOUNDRY_ADDRESS, "change": {"actions": actions}}
        ],
    }


def test_first_apply_skips_check_when_generated_identity_is_unknown(tmp_path: Path) -> None:
    result, az_marker = run_check(
        tmp_path,
        planned_resource({"location": "swedencentral"}, ["create"]),
    )

    assert result.returncode == 0
    assert "generated during first apply" in result.stdout
    assert not az_marker.exists()


def test_known_account_checks_deleted_accounts(tmp_path: Path) -> None:
    result, az_marker = run_check(
        tmp_path,
        planned_resource(
            {
                "name": "aif-aiagent-dev-test1",
                "resource_group_name": "rg-aiagent-dev-test1",
                "location": "swedencentral",
            },
            ["create"],
        ),
    )

    assert result.returncode == 0
    assert "No conflicting soft-deleted" in result.stdout
    assert az_marker.exists()


def test_conflicting_deleted_account_fails(tmp_path: Path) -> None:
    account = "aif-aiagent-dev-test1"
    resource_group = "rg-aiagent-dev-test1"
    location = "swedencentral"
    result, _ = run_check(
        tmp_path,
        planned_resource(
            {
                "name": account,
                "resource_group_name": resource_group,
                "location": location,
            },
            ["create"],
        ),
        [
            {
                "name": account,
                "location": location,
                "id": (
                    "/subscriptions/example/resourceGroups/"
                    f"{resource_group}/providers/Microsoft.CognitiveServices/accounts/{account}"
                ),
            }
        ],
    )

    assert result.returncode == 1
    assert "soft-deleted Foundry account blocks" in result.stderr
