data "azurerm_client_config" "current" {}

resource "terraform_data" "lifecycle_expiry" {
  count = var.resource_ttl_hours > 0 ? 1 : 0

  input            = timeadd(timestamp(), format("%dh", var.resource_ttl_hours))
  triggers_replace = [var.resource_ttl_hours]

  lifecycle {
    ignore_changes = [input]
  }
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.base_name}"
  location = var.location
  tags     = local.tags

  lifecycle {
    precondition {
      condition     = !var.auto_destroy || var.resource_ttl_hours > 0
      error_message = "auto_destroy requires resource_ttl_hours to be greater than zero."
    }
  }
}

module "network" {
  source = "./modules/network"
  count  = var.enable_private_networking ? 1 : 0

  name                = local.base_name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}

module "observability" {
  source = "./modules/observability"

  name                = local.base_name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  retention_days      = var.log_retention_days
  daily_quota_gb      = var.log_daily_quota_gb
  tags                = local.tags
}

module "identity" {
  source = "./modules/identity"

  name                = local.base_name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  private_networking  = var.enable_private_networking
  private_endpoint_subnet_id = var.enable_private_networking ? (
    module.network[0].private_endpoint_subnet_id
  ) : null
  private_dns_zone_ids = var.enable_private_networking ? {
    key_vault = module.network[0].private_dns_zone_ids.key_vault
  } : {}
  tags = local.tags
}

module "ai" {
  source = "./modules/ai"

  name                       = local.base_name
  location                   = var.location
  resource_group_name        = azurerm_resource_group.this.name
  app_principal_id           = module.identity.application_principal_id
  deployer_principal_id      = data.azurerm_client_config.current.object_id
  chat_model_name            = var.chat_model_name
  chat_model_version         = var.chat_model_version
  chat_model_capacity        = var.chat_model_capacity
  embedding_model_name       = var.embedding_model_name
  embedding_model_version    = var.embedding_model_version
  search_sku                 = var.search_sku
  private_networking         = var.enable_private_networking
  private_endpoint_subnet_id = var.enable_private_networking ? module.network[0].private_endpoint_subnet_id : null
  private_dns_zone_ids       = var.enable_private_networking ? module.network[0].private_dns_zone_ids : {}
  tags                       = local.tags
}

module "application" {
  source = "./modules/application"

  name                        = local.base_name
  location                    = var.location
  resource_group_name         = azurerm_resource_group.this.name
  log_analytics_workspace_id  = module.observability.log_analytics_workspace_id
  application_insights_string = module.observability.application_insights_connection_string
  identity_id                 = module.identity.application_identity_id
  identity_client_id          = module.identity.application_client_id
  identity_principal_id       = module.identity.application_principal_id
  infrastructure_subnet_id    = var.enable_private_networking ? module.network[0].container_apps_subnet_id : null
  foundry_endpoint            = module.ai.foundry_endpoint
  foundry_project_name        = module.ai.foundry_project_name
  chat_deployment_name        = module.ai.chat_deployment_name
  embedding_deployment_name   = module.ai.embedding_deployment_name
  search_endpoint             = module.ai.search_endpoint
  search_index_name           = "${var.workload}-knowledge"
  embedding_dimensions        = var.embedding_dimensions
  key_vault_uri               = module.identity.key_vault_uri
  min_replicas                = var.container_min_replicas
  max_replicas                = var.container_max_replicas
  allowed_cors_origins        = var.allowed_cors_origins
  require_auth                = var.require_auth
  auth_tenant_id              = var.auth_tenant_id
  auth_audience               = var.auth_audience
  tags                        = local.tags
}
