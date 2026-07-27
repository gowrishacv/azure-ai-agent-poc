output "key_vault_id" {
  value = azurerm_key_vault.this.id
}

output "key_vault_uri" {
  value = azurerm_key_vault.this.vault_uri
}

output "application_identity_id" {
  value = azurerm_user_assigned_identity.application.id
}

output "application_client_id" {
  value = azurerm_user_assigned_identity.application.client_id
}

output "application_principal_id" {
  value = azurerm_user_assigned_identity.application.principal_id
}
