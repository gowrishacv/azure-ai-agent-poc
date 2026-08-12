variable "name" { type = string }
variable "location" { type = string }
variable "search_location" { type = string }
variable "resource_group_name" { type = string }
variable "app_principal_id" { type = string }
variable "deployer_principal_id" { type = string }
variable "chat_model_name" { type = string }
variable "chat_model_version" { type = string }
variable "chat_model_capacity" { type = number }
variable "embedding_model_name" { type = string }
variable "embedding_model_version" { type = string }
variable "search_sku" { type = string }
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
