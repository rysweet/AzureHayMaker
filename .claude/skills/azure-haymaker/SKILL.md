---
name: azure-haymaker
description: Comprehensive Azure architecture and automation expertise covering all 10 technology areas from Azure Architecture Center. Provides guidance on Azure CLI, Terraform, Bicep, and EntraID administration with progressive disclosure of detailed references.
allowed-tools: [Read, WebFetch, Bash, Grep, Glob]
---

# Azure HayMaker Skill

Comprehensive Azure expertise for deploying, managing, and optimizing Azure infrastructure across all technology areas.

## Core Capabilities

This skill provides expert knowledge in:

### 1. **Azure Technology Areas** (10 domains)
- AI & Machine Learning
- Analytics
- Compute
- Containers
- Databases
- Hybrid + Multicloud
- Identity
- Networking
- Security
- Web Apps

### 2. **Automation Tools**
- **Azure CLI** (`az`) - Primary automation tool
- **Terraform** - Infrastructure as Code
- **Azure Bicep** - Native Azure IaC
- **EntraID Admin** - Identity and access management

### 3. **Architecture Guidance**
- Best practices from Azure Architecture Center
- Well-Architected Framework principles
- Common patterns and anti-patterns
- Cost optimization strategies

## When to Use This Skill

Invoke this skill when you need to:
- Deploy Azure infrastructure using automation
- Design Azure solutions following best practices
- Troubleshoot Azure service issues
- Understand Azure CLI, Terraform, or Bicep syntax
- Configure EntraID/Azure AD identity and access
- Implement scenarios from the Azure Architecture Center

## Quick Reference

### Azure CLI Essentials

```bash
# Login and set subscription
az login
az account set --subscription "subscription-id"

# Resource management
az group create --name rg-name --location eastus
az group delete --name rg-name --yes --no-wait

# Common services
az vm create        # Virtual machines
az aks create       # Kubernetes
az sql server create  # SQL Database
az storage account create  # Storage
```

### Terraform Basics

```hcl
# Provider configuration
provider "azurerm" {
  features {}
}

# Resource group
resource "azurerm_resource_group" "example" {
  name     = "rg-example"
  location = "East US"
}
```

### Bicep Essentials

```bicep
// Resource group (deployment scope)
targetScope = 'subscription'

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'rg-example'
  location: 'eastus'
}
```

## Progressive Disclosure

For detailed information, reference these files as needed:

- **`REFERENCE.md`** - Complete Azure CLI command reference, Terraform resources, Bicep modules
- **`ARCHITECTURE_GUIDE.md`** - Azure HayMaker orchestration service architecture
- **`ENTRA_ID_GUIDE.md`** - EntraID administration, RBAC, identity patterns
- **`TROUBLESHOOTING.md`** - Common issues and solutions

## Technology Area Quick Links

When working with specific areas, Claude will automatically load relevant detailed content:

**AI/ML**: Cognitive Services, Azure OpenAI, Machine Learning workspaces
**Analytics**: Data Factory, Synapse, Stream Analytics, Databricks
**Compute**: VMs, App Service, Functions, VM Scale Sets
**Containers**: AKS, Container Apps, Container Instances
**Databases**: SQL Database, Cosmos DB, MySQL, PostgreSQL, Redis
**Hybrid**: Azure Arc, Site Recovery, Azure Stack, ExpressRoute
**Identity**: Service Principals, RBAC, Entra ID, Conditional Access
**Networking**: VNets, VPN Gateway, Load Balancer, Application Gateway
**Security**: Key Vault, NSGs, Managed Identity, Security Center
**Web Apps**: Static websites, App Service, API Management

## Installation Guides

### Install Azure CLI

**macOS:**
```bash
brew update && brew install azure-cli
```

**Linux (Ubuntu/Debian):**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

**Windows:**
```powershell
# Using winget
winget install Microsoft.AzureCLI
```

### Install Terraform

```bash
# macOS
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
```

### Install Bicep

```bash
# Azure CLI extension
az bicep install

# Or standalone
curl -Lo bicep https://github.com/Azure/bicep/releases/latest/download/bicep-linux-x64
chmod +x ./bicep
sudo mv ./bicep /usr/local/bin/bicep
```

## Common Patterns

### Pattern 1: Resource Group + Service Deployment

```bash
# Variables
RG="rg-myapp"
LOCATION="eastus"
TAGS="Environment=Dev Owner=TeamA"

# Create resource group
az group create --name $RG --location $LOCATION --tags $TAGS

# Deploy service (example: App Service)
az appservice plan create --name plan-myapp --resource-group $RG --sku B1
az webapp create --name webapp-myapp --resource-group $RG --plan plan-myapp

# Cleanup
az group delete --name $RG --yes --no-wait
```

### Pattern 2: Service Principal Creation

```bash
# Create SP with Contributor role
az ad sp create-for-rbac \
  --name "sp-myapp" \
  --role Contributor \
  --scopes /subscriptions/{subscription-id}

# Output includes appId, password, tenant
```

### Pattern 3: Tagging Strategy

```bash
# All resources should be tagged
TAGS="Project=AzureHayMaker Environment=Dev ManagedBy=Automation"

az resource tag --tags $TAGS --ids /subscriptions/.../resourceId
```

## Best Practices

1. **Always use tags** for resource organization and cost tracking
2. **Use variables** for reusable values (resource names, locations)
3. **Implement cleanup** - every deployment should have a teardown procedure
4. **Use unique names** - include timestamps or GUIDs in resource names
5. **Enable monitoring** - Application Insights, Log Analytics for visibility
6. **Follow least privilege** - Minimal permissions for service principals
7. **Use Key Vault** - Never hard-code credentials
8. **Test in dev first** - Validate automation before production

## Error Handling

Common issues and solutions:

**"Resource group not found"**
```bash
# Verify subscription
az account show
# List resource groups
az group list --output table
```

**"Insufficient permissions"**
```bash
# Check your role assignments
az role assignment list --assignee $(az account show --query user.name -o tsv)
```

**"Name already exists"**
```bash
# Use unique suffix
UNIQUE=$(date +%Y%m%d%H%M%S)
NAME="myresource-${UNIQUE}"
```

## Getting Started

1. **Authenticate**: `az login`
2. **Set context**: `az account set --subscription "name"`
3. **Explore**: `az --help` or `az <service> --help`
4. **Deploy**: Start with resource groups, then services
5. **Monitor**: Check Azure Portal or use `az monitor`
6. **Cleanup**: Always delete test resources

## Additional Resources

### Azure HayMaker Documentation
- **[Azure HayMaker Project](https://github.com/rysweet/AzureHayMaker)** - Main repository
- **[Architecture Guide](ARCHITECTURE_GUIDE.md)** - Orchestration service architecture
- **[Scenario Repository](../../../../docs/scenarios/)** - 50+ operational scenarios

### Microsoft Learn Resources
- **[Azure CLI Documentation](https://learn.microsoft.com/cli/azure/)** - Complete CLI reference
- **[Terraform on Azure](https://learn.microsoft.com/azure/developer/terraform/)** - Infrastructure as Code guide
- **[Azure Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)** - Native Azure IaC
- **[Azure Architecture Center](https://learn.microsoft.com/azure/architecture/)** - Architecture patterns
- **[Azure Entra ID](https://learn.microsoft.com/entra/identity/)** - Identity platform
- **[Azure Well-Architected Framework](https://learn.microsoft.com/azure/well-architected/)** - Best practices

---

**Note**: This skill uses progressive disclosure. Detailed references, architecture patterns, and advanced topics are loaded automatically when needed for specific tasks.

**Version**: 2.0 | **Last Updated**: 2025-01-15
