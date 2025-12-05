resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = false
}

resource "azurerm_log_analytics_workspace" "law" {
  name                = var.log_analytics_name
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_storage_account" "storage" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_key_vault" "kv" {
  name                       = var.keyvault_name
  location                   = var.location
  resource_group_name        = azurerm_resource_group.rg.name
  tenant_id                  = var.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 90

  access_policy {
    tenant_id = var.tenant_id
    object_id = var.client_id

    secret_permissions = [
      "Get",
      "List",
      "Set",
      "Delete",
      "Purge",
      "Recover",
      "Backup",
      "Restore"
    ]
  }
}

data "azurerm_client_config" "current" {}


resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.aks_name
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "${var.aks_name}-dns"

  api_server_access_profile {}

  lifecycle {
    ignore_changes = [
      default_node_pool[0].upgrade_settings,
    ]
  }


  identity {
    type = "SystemAssigned"
  }

  default_node_pool {
    name           = "nodepool1"
    vm_size        = "Standard_B2s_v2"
    node_count     = 2
    vnet_subnet_id = azurerm_subnet.aks_subnet.id
  }

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  }

  network_profile {
    network_plugin     = "azure"
    load_balancer_sku  = "standard"
    network_policy     = "azure"
    service_cidr       = "10.1.0.0/16"
    dns_service_ip     = "10.1.0.10"
  }
}


resource "azurerm_virtual_network" "vnet" {
  name                = "gio-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "aks_subnet" {
  name                 = "aks-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}


resource "azurerm_cognitive_account" "doc_intel" {
  name                = "giobibledoc2032"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "FormRecognizer"
  sku_name            = "S0"
}

#resource "azurerm_key_vault_secret" "doc_intel_endpoint" {
#  name         = "doc-intel-endpoint"
#  value        = azurerm_cognitive_account.doc_intel.endpoint
 # key_vault_id = azurerm_key_vault.kv.id
#}

#resource "azurerm_key_vault_secret" "doc_intel_key" {
 ## name         = "doc-intel-key"
 # value        = azurerm_cognitive_account.doc_intel.primary_access_key
#  key_vault_id = azurerm_key_vault.kv.id
#}

