workload                  = "aiagent"
environment               = "prod"
location                  = "swedencentral"
owner                     = "replace-me"
enable_private_networking = true
container_min_replicas    = 1
container_max_replicas    = 3
log_daily_quota_gb        = 1

# Register an Entra API application, then enable these before real use.
require_auth   = false
auth_tenant_id = ""
auth_audience  = ""

