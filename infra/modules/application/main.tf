resource "azurerm_container_registry" "this" {
  name                          = substr(replace("cr${var.name}", "-", ""), 0, 50)
  resource_group_name           = var.resource_group_name
  location                      = var.location
  sku                           = "Basic"
  admin_enabled                 = false
  public_network_access_enabled = true
  anonymous_pull_enabled        = false
  tags                          = var.tags
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.this.id
  role_definition_name = "AcrPull"
  principal_id         = var.identity_principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_container_app_environment" "this" {
  name                       = "cae-${var.name}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  log_analytics_workspace_id = var.log_analytics_workspace_id
  infrastructure_subnet_id   = var.infrastructure_subnet_id
  tags                       = var.tags
}

resource "azurerm_container_app" "this" {
  name                         = "ca-${var.name}"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [var.identity_id]
  }

  registry {
    server   = azurerm_container_registry.this.login_server
    identity = var.identity_id
  }

  ingress {
    external_enabled           = true
    target_port                = 8000
    allow_insecure_connections = false

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    container {
      name   = "api"
      image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "AZURE_CLIENT_ID"
        value = var.identity_client_id
      }
      env {
        name  = "AZURE_AI_ENDPOINT"
        value = var.foundry_endpoint
      }
      env {
        name  = "AZURE_AI_PROJECT_NAME"
        value = var.foundry_project_name
      }
      env {
        name  = "AZURE_OPENAI_CHAT_DEPLOYMENT"
        value = var.chat_deployment_name
      }
      env {
        name  = "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        value = var.embedding_deployment_name
      }
      env {
        name  = "AZURE_SEARCH_ENDPOINT"
        value = var.search_endpoint
      }
      env {
        name  = "AZURE_SEARCH_INDEX"
        value = var.search_index_name
      }
      env {
        name  = "EMBEDDING_DIMENSIONS"
        value = tostring(var.embedding_dimensions)
      }
      env {
        name  = "AZURE_KEY_VAULT_URI"
        value = var.key_vault_uri
      }
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = var.application_insights_string
      }
      env {
        name  = "ALLOWED_CORS_ORIGINS"
        value = join(",", var.allowed_cors_origins)
      }
      env {
        name  = "REQUIRE_AUTH"
        value = tostring(var.require_auth)
      }
      env {
        name  = "AUTH_TENANT_ID"
        value = var.auth_tenant_id
      }
      env {
        name  = "AUTH_AUDIENCE"
        value = var.auth_audience
      }

      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health"
      }

      readiness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/ready"
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].container[0].image
    ]

    precondition {
      condition = !var.require_auth || (
        length(var.auth_tenant_id) > 0 && length(var.auth_audience) > 0
      )
      error_message = "auth_tenant_id and auth_audience are required when require_auth is true."
    }
  }

  depends_on = [azurerm_role_assignment.acr_pull]
}
