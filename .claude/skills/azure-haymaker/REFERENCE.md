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

## Microsoft Learn References

### Azure CLI Documentation

- [Azure CLI Overview](https://learn.microsoft.com/cli/azure/) - Complete Azure CLI reference
- [Azure CLI Installation Guide](https://learn.microsoft.com/cli/azure/install-azure-cli) - Install on Windows, macOS, Linux
- [Azure CLI Configuration](https://learn.microsoft.com/cli/azure/azure-cli-configuration) - Configuration options and settings
- [Azure CLI Command Reference](https://learn.microsoft.com/cli/azure/reference-index) - Full command index
- [Azure CLI Query with JMESPath](https://learn.microsoft.com/cli/azure/query-azure-cli) - Query and filter output
- [Azure CLI Output Formats](https://learn.microsoft.com/cli/azure/format-output-azure-cli) - JSON, table, YAML outputs

### Terraform Azure Provider Documentation

- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs) - Official provider documentation
- [Azure Provider Authentication](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/guides/azure_cli) - Service principal and managed identity auth
- [Terraform Azure Resource Examples](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources) - Resource-specific examples
- [Terraform on Azure Tutorial](https://learn.microsoft.com/azure/developer/terraform/) - Microsoft Learn Terraform guide
- [Terraform State Management in Azure](https://learn.microsoft.com/azure/developer/terraform/store-state-in-azure-storage) - Remote state with Azure Storage

### Azure Bicep Documentation

- [Azure Bicep Overview](https://learn.microsoft.com/azure/azure-resource-manager/bicep/overview) - Introduction to Bicep
- [Bicep Installation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install) - Install Bicep CLI
- [Bicep Template Structure](https://learn.microsoft.com/azure/azure-resource-manager/bicep/file) - Syntax and file structure
- [Bicep Modules](https://learn.microsoft.com/azure/azure-resource-manager/bicep/modules) - Reusable template modules
- [Bicep Parameters and Variables](https://learn.microsoft.com/azure/azure-resource-manager/bicep/parameters) - Configuration management
- [Bicep Deployment Commands](https://learn.microsoft.com/azure/azure-resource-manager/bicep/deploy-cli) - Deploy with Azure CLI
- [Bicep Resource Reference](https://learn.microsoft.com/azure/templates/) - All Azure resource types

### Azure Resource Management

- [Azure Resource Manager Overview](https://learn.microsoft.com/azure/azure-resource-manager/management/overview) - ARM concepts and architecture
- [Resource Groups](https://learn.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-cli) - Manage resource groups with CLI
- [Resource Tagging](https://learn.microsoft.com/azure/azure-resource-manager/management/tag-resources) - Tag resources for organization
- [Resource Locks](https://learn.microsoft.com/azure/azure-resource-manager/management/lock-resources) - Prevent accidental deletion
- [Azure Resource Graph](https://learn.microsoft.com/azure/governance/resource-graph/) - Query resources at scale

### Azure Identity and Access Management

- [Azure Entra ID Overview](https://learn.microsoft.com/entra/fundamentals/whatis) - Identity platform overview
- [Service Principals](https://learn.microsoft.com/entra/identity-platform/app-objects-and-service-principals) - Application and service principal objects
- [Azure RBAC](https://learn.microsoft.com/azure/role-based-access-control/overview) - Role-based access control
- [Built-in Roles](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles) - Complete role reference
- [Managed Identities](https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/overview) - Passwordless authentication
- [Azure AD CLI Commands](https://learn.microsoft.com/cli/azure/ad) - Entra ID CLI reference

### Azure Key Vault

- [Azure Key Vault Overview](https://learn.microsoft.com/azure/key-vault/general/overview) - Secrets management service
- [Key Vault Best Practices](https://learn.microsoft.com/azure/key-vault/general/best-practices) - Security recommendations
- [Manage Secrets with CLI](https://learn.microsoft.com/azure/key-vault/secrets/quick-create-cli) - Secret operations
- [Key Vault Access Policies](https://learn.microsoft.com/azure/key-vault/general/assign-access-policy) - Configure permissions
- [Key Vault References](https://learn.microsoft.com/azure/app-service/app-service-key-vault-references) - Use in App Service and Functions

### Azure Networking

- [Virtual Networks](https://learn.microsoft.com/azure/virtual-network/virtual-networks-overview) - VNet concepts and architecture
- [Network Security Groups](https://learn.microsoft.com/azure/virtual-network/network-security-groups-overview) - Traffic filtering
- [Virtual Network Peering](https://learn.microsoft.com/azure/virtual-network/virtual-network-peering-overview) - Connect VNets
- [Private Endpoints](https://learn.microsoft.com/azure/private-link/private-endpoint-overview) - Private connectivity to PaaS
- [Load Balancer](https://learn.microsoft.com/azure/load-balancer/load-balancer-overview) - Layer 4 load balancing
- [Application Gateway](https://learn.microsoft.com/azure/application-gateway/overview) - Layer 7 load balancing

### Azure Compute Services

- [Virtual Machines Overview](https://learn.microsoft.com/azure/virtual-machines/) - VM documentation hub
- [VM Sizes](https://learn.microsoft.com/azure/virtual-machines/sizes) - All VM size families
- [Azure App Service](https://learn.microsoft.com/azure/app-service/) - Web app hosting
- [Azure Functions](https://learn.microsoft.com/azure/azure-functions/) - Serverless compute
- [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/) - Serverless containers
- [Azure Kubernetes Service](https://learn.microsoft.com/azure/aks/) - Managed Kubernetes

### Azure Storage

- [Azure Storage Overview](https://learn.microsoft.com/azure/storage/common/storage-introduction) - Storage services overview
- [Blob Storage](https://learn.microsoft.com/azure/storage/blobs/) - Object storage
- [Table Storage](https://learn.microsoft.com/azure/storage/tables/) - NoSQL key-value store
- [Storage Account Management](https://learn.microsoft.com/azure/storage/common/storage-account-overview) - Account types and features

### Azure Databases

- [Azure SQL Database](https://learn.microsoft.com/azure/azure-sql/) - Managed SQL database
- [Azure Database for MySQL](https://learn.microsoft.com/azure/mysql/) - Managed MySQL
- [Azure Database for PostgreSQL](https://learn.microsoft.com/azure/postgresql/) - Managed PostgreSQL
- [Azure Cosmos DB](https://learn.microsoft.com/azure/cosmos-db/) - Globally distributed NoSQL
- [Azure Cache for Redis](https://learn.microsoft.com/azure/azure-cache-for-redis/) - In-memory cache

### Azure Monitoring

- [Azure Monitor Overview](https://learn.microsoft.com/azure/azure-monitor/overview) - Monitoring platform
- [Log Analytics](https://learn.microsoft.com/azure/azure-monitor/logs/log-analytics-overview) - Log querying and analysis
- [Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/app-insights-overview) - Application performance monitoring
- [Azure Alerts](https://learn.microsoft.com/azure/azure-monitor/alerts/alerts-overview) - Automated alerting

### DevOps and CI/CD

- [GitHub Actions for Azure](https://learn.microsoft.com/azure/developer/github/github-actions) - CI/CD with GitHub
- [Azure DevOps](https://learn.microsoft.com/azure/devops/) - Complete DevOps platform
- [Azure Pipelines](https://learn.microsoft.com/azure/devops/pipelines/) - CI/CD pipelines
- [GitHub OIDC with Azure](https://learn.microsoft.com/azure/developer/github/connect-from-azure) - Passwordless authentication

### Azure Security

- [Azure Security Best Practices](https://learn.microsoft.com/azure/security/fundamentals/best-practices-and-patterns) - Security guidance
- [Azure Defender](https://learn.microsoft.com/azure/defender-for-cloud/) - Cloud security posture management
- [Azure Policy](https://learn.microsoft.com/azure/governance/policy/) - Governance and compliance
- [Azure Security Baseline](https://learn.microsoft.com/security/benchmark/azure/overview) - Security recommendations

---

**Reference Version**: 2.0
**Last Updated**: 2025-01-15
**Coverage**: Azure CLI 2.50+, Terraform 1.5+, Bicep 0.20+
**MS Learn Links**: 60+ official Microsoft documentation references
