locals {
  chat_deployment_name      = "chat"
  embedding_deployment_name = "embedding"
}

resource "azurerm_cognitive_account" "foundry" {
  name                          = var.foundry_account_name
  location                      = var.location
  resource_group_name           = var.resource_group_name
  kind                          = "AIServices"
  sku_name                      = "S0"
  custom_subdomain_name         = var.foundry_account_name
  project_management_enabled    = true
  local_auth_enabled            = false
  public_network_access_enabled = !var.private_networking
  tags                          = var.tags

  identity {
    type = "SystemAssigned"
  }
}

resource "terraform_data" "foundry_ready" {
  triggers_replace = [azurerm_cognitive_account.foundry.id]

  provisioner "local-exec" {
    command = "sleep 60"
  }
}

resource "azurerm_cognitive_account_project" "this" {
  name                 = "project-${var.name}"
  cognitive_account_id = azurerm_cognitive_account.foundry.id
  location             = var.location
  display_name         = "Azure AI Agent POC"
  description          = "Keyless Microsoft Foundry project deployed by Terraform."
  tags                 = var.tags

  identity {
    type = "SystemAssigned"
  }

  depends_on = [azurerm_cognitive_deployment.embedding]
}

resource "azurerm_cognitive_deployment" "chat" {
  name                 = local.chat_deployment_name
  cognitive_account_id = azurerm_cognitive_account.foundry.id

  model {
    format  = "OpenAI"
    name    = var.chat_model_name
    version = var.chat_model_version
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.chat_model_capacity
  }

  depends_on = [terraform_data.foundry_ready]
}

resource "azurerm_cognitive_deployment" "embedding" {
  name                 = local.embedding_deployment_name
  cognitive_account_id = azurerm_cognitive_account.foundry.id

  model {
    format  = "OpenAI"
    name    = var.embedding_model_name
    version = var.embedding_model_version
  }

  sku {
    name     = "GlobalStandard"
    capacity = 10
  }

  depends_on = [azurerm_cognitive_deployment.chat]
}

resource "azurerm_search_service" "this" {
  name                          = "srch-${var.name}"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  sku                           = var.search_sku
  replica_count                 = 1
  partition_count               = 1
  local_authentication_enabled  = false
  public_network_access_enabled = !var.private_networking
  tags                          = var.tags

  identity {
    type = "SystemAssigned"
  }

  lifecycle {
    precondition {
      condition     = !var.private_networking || var.search_sku != "free"
      error_message = "The private-network profile requires a paid Azure AI Search tier."
    }
  }
}

resource "azurerm_role_assignment" "app_foundry_user" {
  scope                = azurerm_cognitive_account.foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = var.app_principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "app_search_reader" {
  scope                = azurerm_search_service.this.id
  role_definition_name = "Search Index Data Reader"
  principal_id         = var.app_principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "project_search_reader" {
  scope                = azurerm_search_service.this.id
  role_definition_name = "Search Index Data Reader"
  principal_id         = azurerm_cognitive_account_project.this.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "deployer_foundry_user" {
  scope                = azurerm_cognitive_account.foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = var.deployer_principal_id
}

resource "azurerm_role_assignment" "deployer_search_service_contributor" {
  scope                = azurerm_search_service.this.id
  role_definition_name = "Search Service Contributor"
  principal_id         = var.deployer_principal_id
}

resource "azurerm_role_assignment" "deployer_search_data_contributor" {
  scope                = azurerm_search_service.this.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = var.deployer_principal_id
}

resource "azurerm_private_endpoint" "foundry" {
  count = var.private_networking ? 1 : 0

  name                = "pep-foundry-${var.name}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-foundry-${var.name}"
    private_connection_resource_id = azurerm_cognitive_account.foundry.id
    subresource_names              = ["account"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name = "default"
    private_dns_zone_ids = [
      var.private_dns_zone_ids.cognitive,
      var.private_dns_zone_ids.openai
    ]
  }
}

resource "azurerm_private_endpoint" "search" {
  count = var.private_networking ? 1 : 0

  name                = "pep-search-${var.name}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-search-${var.name}"
    private_connection_resource_id = azurerm_search_service.this.id
    subresource_names              = ["searchService"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [var.private_dns_zone_ids.search]
  }
}
