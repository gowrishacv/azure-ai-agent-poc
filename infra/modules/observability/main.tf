resource "azurerm_log_analytics_workspace" "this" {
  name                       = "log-${var.name}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  sku                        = "PerGB2018"
  retention_in_days          = var.retention_days
  daily_quota_gb             = var.daily_quota_gb
  internet_ingestion_enabled = true
  internet_query_enabled     = true
  tags                       = var.tags
}

resource "azurerm_application_insights" "this" {
  name                = "appi-${var.name}"
  location            = var.location
  resource_group_name = var.resource_group_name
  workspace_id        = azurerm_log_analytics_workspace.this.id
  application_type    = "web"
  retention_in_days   = var.retention_days
  tags                = var.tags
}

