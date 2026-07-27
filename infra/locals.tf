locals {
  base_name = "${var.workload}-${var.environment}-${random_string.suffix.result}"

  tags = {
    workload    = var.workload
    environment = var.environment
    owner       = var.owner
    managed_by  = "terraform"
    purpose     = "azure-ai-agent-poc"
  }
}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

