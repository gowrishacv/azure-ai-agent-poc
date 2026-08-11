variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "log_analytics_workspace_id" { type = string }
variable "application_insights_string" {
  type      = string
  sensitive = true
}
variable "identity_id" { type = string }
variable "identity_client_id" { type = string }
variable "identity_principal_id" { type = string }
variable "infrastructure_subnet_id" {
  type    = string
  default = null
}
variable "foundry_endpoint" { type = string }
variable "foundry_project_name" { type = string }
variable "chat_deployment_name" { type = string }
variable "embedding_deployment_name" { type = string }
variable "search_endpoint" { type = string }
variable "search_index_name" { type = string }
variable "embedding_dimensions" { type = number }
variable "key_vault_uri" { type = string }
variable "min_replicas" { type = number }
variable "max_replicas" { type = number }
variable "allowed_cors_origins" { type = list(string) }
variable "require_auth" { type = bool }
variable "auth_tenant_id" { type = string }
variable "auth_audience" { type = string }
variable "auth_required_role" { type = string }
variable "auth_required_scope" { type = string }
variable "auth_scope" { type = string }
variable "ui_client_id" { type = string }
variable "enable_document_authorization" { type = bool }
variable "tags" { type = map(string) }
