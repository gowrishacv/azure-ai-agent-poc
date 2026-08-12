from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_foundry_child_operations_are_serialized_after_readiness_delay() -> None:
    module = (REPOSITORY_ROOT / "infra/modules/ai/main.tf").read_text(encoding="utf-8")

    assert 'command = "sleep 60"' in module
    assert "depends_on = [terraform_data.foundry_ready]" in module
    assert "depends_on = [azurerm_cognitive_deployment.chat]" in module
    assert "depends_on = [azurerm_cognitive_deployment.embedding]" in module


def test_dev_search_uses_capacity_fallback_region() -> None:
    dev = (REPOSITORY_ROOT / "infra/environments/dev.tfvars").read_text(encoding="utf-8")
    module = (REPOSITORY_ROOT / "infra/modules/ai/main.tf").read_text(encoding="utf-8")

    assert 'search_location           = "westeurope"' in dev
    assert "location                      = var.search_location" in module
