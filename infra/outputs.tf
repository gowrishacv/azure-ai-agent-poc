output "resource_group_name" {
  value = azurerm_resource_group.this.name
}

output "container_registry_name" {
  value = module.application.container_registry_name
}

output "container_app_name" {
  value = module.application.container_app_name
}

output "container_app_url" {
  value = "https://${module.application.container_app_fqdn}"
}

output "foundry_account_name" {
  value = module.ai.foundry_account_name
}

output "foundry_endpoint" {
  value = module.ai.foundry_endpoint
}

output "foundry_project_name" {
  value = module.ai.foundry_project_name
}

output "search_service_name" {
  value = module.ai.search_service_name
}

output "search_endpoint" {
  value = module.ai.search_endpoint
}

output "chat_deployment_name" {
  value = module.ai.chat_deployment_name
}

output "embedding_deployment_name" {
  value = module.ai.embedding_deployment_name
}

output "search_index_name" {
  value = "${var.workload}-knowledge"
}

output "private_networking_enabled" {
  value = var.enable_private_networking
}

output "application_identity_client_id" {
  value = module.application.client_id
}

output "deployment_summary" {
  value = {
    profile            = var.enable_private_networking ? "private-poc" : "mvp"
    api_url            = "https://${module.application.container_app_fqdn}"
    local_auth         = "disabled"
    minimum_replicas   = var.container_min_replicas
    apim               = "not deployed"
    private_networking = var.enable_private_networking
  }
}
