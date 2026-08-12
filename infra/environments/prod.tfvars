workload                  = "aiagent"
environment               = "prod"
location                  = "swedencentral"
search_location           = ""
owner                     = "replace-me"
enable_private_networking = true
container_min_replicas    = 1
container_max_replicas    = 3
log_daily_quota_gb        = 1
resource_ttl_hours        = 0
auto_destroy              = false

# Register an Entra API application, then enable these before real use.
require_auth   = false
auth_tenant_id = ""
auth_audience  = ""

# Phase 2.1: populate these after registering the API and SPA in Entra ID.
auth_required_role            = ""
auth_required_scope           = ""
auth_scope                    = ""
ui_client_id                  = ""
enable_document_authorization = false
