output "container_apps_subnet_id" {
  value = azurerm_subnet.container_apps.id
}

output "private_endpoint_subnet_id" {
  value = azurerm_subnet.private_endpoints.id
}

output "private_dns_zone_ids" {
  value = { for key, zone in azurerm_private_dns_zone.this : key => zone.id }
}

