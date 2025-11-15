# Azure HayMaker - Complete Reference Guide

This file provides comprehensive command references for Azure CLI, Terraform, and Bicep. It's loaded automatically when detailed syntax is needed.

## Azure CLI Command Reference

### Resource Groups

```bash
# Create
az group create --name <name> --location <location> [--tags key=value]

# List
az group list [--output table|json|yaml]

# Show
az group show --name <name>

# Delete
az group delete --name <name> [--yes] [--no-wait]

# Update tags
az group update --name <name> --tags key=value

# Lock resource group
az lock create --name <lock-name> --resource-group <name> --lock-type CanNotDelete
```

### Virtual Machines

```bash
# Create Linux VM
az vm create \
  --resource-group <rg> \
  --name <vm-name> \
  --image UbuntuLTS \
  --admin-username azureuser \
  --generate-ssh-keys \
  --size Standard_B2s

# Create Windows VM
az vm create \
  --resource-group <rg> \
  --name <vm-name> \
  --image Win2022Datacenter \
  --admin-username azureuser \
  --admin-password <password> \
  --size Standard_D2s_v3

# Start/Stop/Restart
az vm start --resource-group <rg> --name <vm-name>
az vm stop --resource-group <rg> --name <vm-name>
az vm restart --resource-group <rg> --name <vm-name>

# Deallocate (stop billing)
az vm deallocate --resource-group <rg> --name <vm-name>

# Delete
az vm delete --resource-group <rg> --name <vm-name> --yes

# List VMs
az vm list [--resource-group <rg>] --output table

# Get IP address
az vm show -d --resource-group <rg> --name <vm-name> --query publicIps -o tsv
```

### Networking

```bash
# Create VNet
az network vnet create \
  --resource-group <rg> \
  --name <vnet-name> \
  --address-prefix 10.0.0.0/16 \
  --subnet-name <subnet-name> \
  --subnet-prefixes 10.0.1.0/24

# Create subnet
az network vnet subnet create \
  --resource-group <rg> \
  --vnet-name <vnet-name> \
  --name <subnet-name> \
  --address-prefixes 10.0.2.0/24

# Create NSG
az network nsg create \
  --resource-group <rg> \
  --name <nsg-name>

# Create NSG rule
az network nsg rule create \
  --resource-group <rg> \
  --nsg-name <nsg-name> \
  --name AllowSSH \
  --priority 1000 \
  --source-address-prefixes '*' \
  --source-port-ranges '*' \
  --destination-address-prefixes '*' \
  --destination-port-ranges 22 \
  --access Allow \
  --protocol Tcp

# Create public IP
az network public-ip create \
  --resource-group <rg> \
  --name <ip-name> \
  --sku Standard \
  --allocation-method Static

# Create Load Balancer
az network lb create \
  --resource-group <rg> \
  --name <lb-name> \
  --sku Standard \
  --public-ip-address <ip-name>
```

### Storage

```bash
# Create storage account
az storage account create \
  --name <storage-name> \
  --resource-group <rg> \
  --location <location> \
  --sku Standard_LRS \
  --kind StorageV2

# Enable static website
az storage blob service-properties update \
  --account-name <storage-name> \
  --static-website \
  --404-document 404.html \
  --index-document index.html

# Create container
az storage container create \
  --name <container-name> \
  --account-name <storage-name> \
  --account-key <key>

# Upload blob
az storage blob upload \
  --account-name <storage-name> \
  --container-name <container> \
  --name <blob-name> \
  --file <local-file>

# Get connection string
az storage account show-connection-string \
  --name <storage-name> \
  --resource-group <rg>
```

### Azure Kubernetes Service (AKS)

```bash
# Create AKS cluster
az aks create \
  --resource-group <rg> \
  --name <aks-name> \
  --node-count 2 \
  --node-vm-size Standard_D2s_v3 \
  --enable-addons monitoring \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group <rg> --name <aks-name>

# Scale cluster
az aks scale --resource-group <rg> --name <aks-name> --node-count 3

# Upgrade cluster
az aks upgrade --resource-group <rg> --name <aks-name> --kubernetes-version 1.27.0

# Stop/Start (to save costs)
az aks stop --resource-group <rg> --name <aks-name>
az aks start --resource-group <rg> --name <aks-name>
```

### Databases

```bash
# Azure SQL Database
az sql server create \
  --name <server-name> \
  --resource-group <rg> \
  --location <location> \
  --admin-user <admin> \
  --admin-password <password>

az sql db create \
  --resource-group <rg> \
  --server <server-name> \
  --name <db-name> \
  --service-objective S0

# Azure Database for MySQL
az mysql flexible-server create \
  --resource-group <rg> \
  --name <server-name> \
  --location <location> \
  --admin-user <admin> \
  --admin-password <password> \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 8.0

# Cosmos DB
az cosmosdb create \
  --name <account-name> \
  --resource-group <rg> \
  --default-consistency-level Session \
  --locations regionName=<location> failoverPriority=0

az cosmosdb sql database create \
  --account-name <account-name> \
  --resource-group <rg> \
  --name <db-name>
```

### Identity & Access

```bash
# Create service principal
az ad sp create-for-rbac \
  --name <sp-name> \
  --role Contributor \
  --scopes /subscriptions/<sub-id>/resourceGroups/<rg>

# Assign role
az role assignment create \
  --assignee <object-id> \
  --role <role-name> \
  --scope <scope>

# List role assignments
az role assignment list \
  --assignee <object-id> \
  --output table

# Create managed identity
az identity create \
  --name <identity-name> \
  --resource-group <rg>

# Get managed identity details
az identity show \
  --name <identity-name> \
  --resource-group <rg>
```

### Key Vault

```bash
# Create Key Vault
az keyvault create \
  --name <kv-name> \
  --resource-group <rg> \
  --location <location>

# Set secret
az keyvault secret set \
  --vault-name <kv-name> \
  --name <secret-name> \
  --value <secret-value>

# Get secret
az keyvault secret show \
  --vault-name <kv-name> \
  --name <secret-name>

# Grant access
az keyvault set-policy \
  --name <kv-name> \
  --object-id <object-id> \
  --secret-permissions get list
```

### Container Apps

```bash
# Create Container Apps environment
az containerapp env create \
  --name <env-name> \
  --resource-group <rg> \
  --location <location>

# Create Container App
az containerapp create \
  --name <app-name> \
  --resource-group <rg> \
  --environment <env-name> \
  --image <image> \
  --target-port 80 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 5

# Update Container App
az containerapp update \
  --name <app-name> \
  --resource-group <rg> \
  --image <new-image>
```

## Terraform Azure Provider Reference

### Provider Configuration

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}
```

### Common Resources

```hcl
# Resource Group
resource "azurerm_resource_group" "example" {
  name     = "rg-example"
  location = "East US"
  tags     = {
    Environment = "Dev"
    Project     = "AzureHayMaker"
  }
}

# Virtual Network
resource "azurerm_virtual_network" "example" {
  name                = "vnet-example"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name
}

# Subnet
resource "azurerm_subnet" "example" {
  name                 = "subnet-example"
  resource_group_name  = azurerm_resource_group.example.name
  virtual_network_name = azurerm_virtual_network.example.name
  address_prefixes     = ["10.0.1.0/24"]
}

# Storage Account
resource "azurerm_storage_account" "example" {
  name                     = "stexample${random_id.suffix.hex}"
  resource_group_name      = azurerm_resource_group.example.name
  location                 = azurerm_resource_group.example.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# Linux Virtual Machine
resource "azurerm_linux_virtual_machine" "example" {
  name                = "vm-example"
  resource_group_name = azurerm_resource_group.example.name
  location            = azurerm_resource_group.example.location
  size                = "Standard_B2s"
  admin_username      = "azureuser"

  network_interface_ids = [
    azurerm_network_interface.example.id,
  ]

  admin_ssh_key {
    username   = "azureuser"
    public_key = file("~/.ssh/id_rsa.pub")
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "UbuntuServer"
    sku       = "18.04-LTS"
    version   = "latest"
  }
}
```

## Bicep Module Reference

### Basic Syntax

```bicep
// Parameter
param location string = resourceGroup().location
param environmentName string

// Variable
var storageAccountName = 'st${uniqueString(resourceGroup().id)}'

// Resource
resource storageAccount 'Microsoft.Storage/storageAccounts@2021-09-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
  }
  tags: {
    Environment: environmentName
  }
}

// Output
output storageAccountId string = storageAccount.id
output storageAccountName string = storageAccount.name
```

### Common Patterns

```bicep
// Virtual Network
resource vnet 'Microsoft.Network/virtualNetworks@2021-05-01' = {
  name: 'vnet-example'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'subnet1'
        properties: {
          addressPrefix: '10.0.1.0/24'
        }
      }
    ]
  }
}

// App Service Plan + Web App
resource appServicePlan 'Microsoft.Web/serverfarms@2021-03-01' = {
  name: 'plan-example'
  location: location
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
}

resource webApp 'Microsoft.Web/sites@2021-03-01' = {
  name: 'webapp-example'
  location: location
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.9'
    }
  }
}

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2021-11-01-preview' = {
  name: 'kv-example'
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    accessPolicies: []
  }
}
```

## EntraID / Azure AD Commands

```bash
# List users
az ad user list --output table

# Create user
az ad user create \
  --display-name "John Doe" \
  --password <password> \
  --user-principal-name john@domain.com

# Create group
az ad group create \
  --display-name "Developers" \
  --mail-nickname developers

# Add user to group
az ad group member add \
  --group "Developers" \
  --member-id <user-object-id>

# Create app registration
az ad app create --display-name "MyApp"

# Create service principal from app
az ad sp create --id <app-id>

# Assign directory role
az ad directory-role-member add \
  --role "User Administrator" \
  --member-id <object-id>
```

---

**Reference Version**: 1.0
**Last Updated**: 2024
**Coverage**: Azure CLI 2.50+, Terraform 1.5+, Bicep 0.20+
