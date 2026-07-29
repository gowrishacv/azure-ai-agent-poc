locals {
  base_name = "${var.workload}-${var.environment}-${random_string.suffix.result}"

  lifecycle_tags = merge(
    tomap({
      auto_destroy = var.resource_ttl_hours > 0 ? tostring(var.auto_destroy) : "false"
    }),
    var.resource_ttl_hours > 0 ? tomap({
      expires_on = terraform_data.lifecycle_expiry[0].output
    }) : tomap({})
  )

  tags = merge(
    {
      workload    = var.workload
      environment = var.environment
      owner       = var.owner
      managed_by  = "terraform"
      purpose     = "azure-ai-agent-poc"
    },
    local.lifecycle_tags
  )
}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}
