output "foundry_account_name" {
  value = azurerm_cognitive_account.foundry.name
}

output "foundry_endpoint" {
  description = "Azure OpenAI data-plane endpoint used for chat and embeddings."
  value       = "https://${azurerm_cognitive_account.foundry.name}.openai.azure.com/"
}

output "foundry_project_name" {
  value = azurerm_cognitive_account_project.this.name
}

output "chat_deployment_name" {
  value = azurerm_cognitive_deployment.chat.name
}

output "embedding_deployment_name" {
  value = azurerm_cognitive_deployment.embedding.name
}

output "search_endpoint" {
  value = "https://${azurerm_search_service.this.name}.search.windows.net"
}

output "search_service_name" {
  value = azurerm_search_service.this.name
}
