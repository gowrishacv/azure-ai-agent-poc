from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_foundry_child_operations_are_serialized_after_readiness_delay() -> None:
    module = (REPOSITORY_ROOT / "infra/modules/ai/main.tf").read_text(encoding="utf-8")

    assert 'command = "sleep 60"' in module
    assert "depends_on = [terraform_data.foundry_ready]" in module
    assert "depends_on = [azurerm_cognitive_deployment.chat]" in module
    assert "depends_on = [azurerm_cognitive_deployment.embedding]" in module


def test_workload_and_search_are_colocated_in_west_europe() -> None:
    dev = (REPOSITORY_ROOT / "infra/environments/dev.tfvars").read_text(encoding="utf-8")
    prod = (REPOSITORY_ROOT / "infra/environments/prod.tfvars").read_text(encoding="utf-8")
    variables = (REPOSITORY_ROOT / "infra/variables.tf").read_text(encoding="utf-8")
    bootstrap = (REPOSITORY_ROOT / "infra/bootstrap/main.tf").read_text(encoding="utf-8")
    module = (REPOSITORY_ROOT / "infra/modules/ai/main.tf").read_text(encoding="utf-8")

    assert 'location                  = "westeurope"' in dev
    assert 'location                  = "westeurope"' in prod
    assert 'default     = "westeurope"' in variables
    assert 'default = "westeurope"' in bootstrap
    assert "search_location" not in variables
    assert "location                      = var.location" in module


def test_foundry_uses_an_independent_state_managed_global_name() -> None:
    locals_tf = (REPOSITORY_ROOT / "infra/locals.tf").read_text(encoding="utf-8")
    root_module = (REPOSITORY_ROOT / "infra/main.tf").read_text(encoding="utf-8")
    ai_module = (REPOSITORY_ROOT / "infra/modules/ai/main.tf").read_text(
        encoding="utf-8"
    )

    assert 'resource "random_string" "foundry_suffix"' in locals_tf
    assert 'foundry_account_name = "aif-${local.base_name}-${random_string.foundry_suffix.result}"' in locals_tf
    assert "foundry_account_name       = local.foundry_account_name" in root_module
    assert "name                          = var.foundry_account_name" in ai_module
    assert "custom_subdomain_name         = var.foundry_account_name" in ai_module


def test_key_vault_uses_an_independent_state_managed_global_name() -> None:
    locals_tf = (REPOSITORY_ROOT / "infra/locals.tf").read_text(encoding="utf-8")
    root_module = (REPOSITORY_ROOT / "infra/main.tf").read_text(encoding="utf-8")
    identity_module = (
        REPOSITORY_ROOT / "infra/modules/identity/main.tf"
    ).read_text(encoding="utf-8")

    assert 'resource "random_string" "key_vault_suffix"' in locals_tf
    assert 'random_string.key_vault_suffix.result' in locals_tf
    assert "key_vault_name      = local.key_vault_name" in root_module
    assert "name                          = var.key_vault_name" in identity_module
