terraform {
  required_version = ">= 1.3.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.114.0"
    }
  }

  #Backend remoto en Azure Storage Account
  backend "azurerm" {
    resource_group_name  = "gio-rg"
    storage_account_name = "gioterraformstate2032"
    container_name       = "tfstate"
    key                  = "terraform.tfstate"
  }
}

provider "azurerm" {
  features {}

  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
  client_id       = var.client_id
  client_secret   = var.client_secret
}
