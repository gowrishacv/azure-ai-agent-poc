workload                  = "aiagent"
environment               = "prod"
location                  = "swedencentral"
search_location           = ""
owner                     = "platform-team"
enable_private_networking = true
container_min_replicas    = 1
container_max_replicas    = 5
log_daily_quota_gb        = 2
allowed_cors_origins      = ["https://app.example.com"]
resource_ttl_hours        = 0
auto_destroy              = false

# Phase 2.1: populate these after registering the API and SPA in Entra ID.
require_auth                  = true
auth_tenant_id                = "00000000-0000-0000-0000-000000000000"
auth_audience                 = "00000000-0000-0000-0000-000000000000"
auth_required_role            = "AI.Agent.User"
auth_required_scope           = "access_as_user"
auth_scope                    = "api://00000000-0000-0000-0000-000000000000/access_as_user"
ui_client_id                  = "11111111-1111-1111-1111-111111111111"
enable_document_authorization = true
