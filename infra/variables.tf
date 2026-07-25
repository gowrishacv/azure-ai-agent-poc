variable "workload" {
  description = "Short workload name used in Azure resource names."
  type        = string
  default     = "aiagent"

  validation {
    condition     = can(regex("^[a-z0-9]{2,12}$", var.workload))
    error_message = "workload must contain 2-12 lowercase letters or digits."
  }
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "environment must be dev, test, or prod."
  }
}

variable "location" {
  description = "Azure region. Model availability varies by region."
  type        = string
  default     = "swedencentral"
}

variable "owner" {
  description = "Owner tag."
  type        = string
  default     = "azure-ai-poc"
}

variable "chat_model_name" {
  description = "Model catalog name available in the selected region."
  type        = string
  default     = "gpt-4.1-mini"
}

variable "chat_model_version" {
  description = "Model version available in the selected region."
  type        = string
  default     = "2025-04-14"
}

variable "chat_model_capacity" {
  description = "GlobalStandard capacity in thousands of tokens per minute."
  type        = number
  default     = 10
}

variable "embedding_model_name" {
  type    = string
  default = "text-embedding-3-small"
}

variable "embedding_model_version" {
  type    = string
  default = "1"
}

variable "embedding_dimensions" {
  description = "Must match the deployed embedding model and search index."
  type        = number
  default     = 1536
}

variable "search_sku" {
  description = "Basic supports private endpoints and is the practical POC default. Use free manually when suitable."
  type        = string
  default     = "basic"
}

variable "enable_private_networking" {
  description = "Adds VNet integration and private endpoints for Foundry, Search, and Key Vault."
  type        = bool
  default     = false
}

variable "container_min_replicas" {
  description = "Zero enables scale-to-zero for the POC."
  type        = number
  default     = 0
}

variable "container_max_replicas" {
  type    = number
  default = 2
}

variable "log_retention_days" {
  type    = number
  default = 30
}

variable "log_daily_quota_gb" {
  description = "Safety cap for Log Analytics ingestion."
  type        = number
  default     = 0.5
}

variable "allowed_cors_origins" {
  description = "Explicit browser origins. Empty means no browser CORS access."
  type        = list(string)
  default     = []
}

variable "require_auth" {
  description = "Require Microsoft Entra bearer tokens at the API."
  type        = bool
  default     = false
}

variable "auth_tenant_id" {
  description = "Microsoft Entra tenant ID used for JWT issuer validation."
  type        = string
  default     = ""
}

variable "auth_audience" {
  description = "Application ID URI or client ID expected in the JWT audience."
  type        = string
  default     = ""
}
