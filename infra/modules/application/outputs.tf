output "container_registry_name" {
  value = azurerm_container_registry.this.name
}

output "container_app_name" {
  value = azurerm_container_app.this.name
}

output "container_app_fqdn" {
  value = azurerm_container_app.this.ingress[0].fqdn
}

output "principal_id" {
  value = var.identity_id
}

output "client_id" {
  value = var.identity_client_id
}

