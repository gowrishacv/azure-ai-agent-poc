variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "retention_days" { type = number }
variable "daily_quota_gb" { type = number }
variable "tags" { type = map(string) }

