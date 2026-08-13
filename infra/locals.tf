locals {
  base_name            = "${var.workload}-${var.environment}-${random_string.suffix.result}"
  foundry_account_name = "aif-${local.base_name}-${random_string.foundry_suffix.result}"

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

# Cognitive Services custom subdomains are globally unique and can remain
# reserved after deletion. Keep a separate state-managed suffix so a retained
# Foundry name never forces every workload resource to be renamed.
resource "random_string" "foundry_suffix" {
  length  = 5
  upper   = false
  special = false
}
