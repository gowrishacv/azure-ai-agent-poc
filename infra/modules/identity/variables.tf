variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "tenant_id" { type = string }
variable "private_networking" { type = bool }
variable "private_endpoint_subnet_id" {
  type    = string
  default = null
}
variable "private_dns_zone_ids" {
  type    = map(string)
  default = {}
}
variable "tags" { type = map(string) }

