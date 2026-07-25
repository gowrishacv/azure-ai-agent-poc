variable "location" {
  type    = string
  default = "swedencentral"
}

variable "name_prefix" {
  type    = string
  default = "aiagent"
}

resource "random_string" "suffix" {
  length  = 8
  upper   = false
  special = false
}

resource "azurerm_resource_group" "state" {
  name     = "rg-${var.name_prefix}-tfstate"
  location = var.location
}

resource "azapi_resource" "state" {
  type      = "Microsoft.Storage/storageAccounts@2025-01-01"
  parent_id = azurerm_resource_group.state.id
  name      = "st${var.name_prefix}tf${random_string.suffix.result}"
  location  = var.location

  body = {
    kind = "StorageV2"
    sku = {
      name = "Standard_LRS"
    }
    properties = {
      allowBlobPublicAccess        = false
      allowCrossTenantReplication  = false
      allowSharedKeyAccess         = false
      defaultToOAuthAuthentication = true
      minimumTlsVersion            = "TLS1_2"
      publicNetworkAccess          = "Enabled"
      supportsHttpsTrafficOnly     = true
    }
  }
}

data "azapi_resource" "blob_service" {
  type      = "Microsoft.Storage/storageAccounts/blobServices@2025-01-01"
  parent_id = azapi_resource.state.id
  name      = "default"
}

resource "azapi_resource" "container" {
  type      = "Microsoft.Storage/storageAccounts/blobServices/containers@2025-01-01"
  parent_id = data.azapi_resource.blob_service.id
  name      = "tfstate"

  body = {
    properties = {
      publicAccess = "None"
    }
  }
}

output "resource_group_name" {
  value = azurerm_resource_group.state.name
}

output "storage_account_name" {
  value = azapi_resource.state.name
}

output "container_name" {
  value = azapi_resource.container.name
}
