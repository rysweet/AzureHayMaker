# Azure Troubleshooting Guide

Common issues, error messages, and solutions for Azure deployments.

## Authentication & Authorization Issues

### "The client does not have authorization to perform action"

**Cause**: Insufficient RBAC permissions

**Solution**:
```bash
# Check current role assignments
az role assignment list \
  --assignee $(az account show --query user.name -o tsv) \
  --output table

# If you need Contributor, ask admin to run:
az role assignment create \
  --assignee {your-object-id} \
  --role Contributor \
  --scope /subscriptions/{subscription-id}
```

### "No subscriptions found"

**Cause**: Not logged in or no subscription access

**Solution**:
```bash
# Login
az login

# If using service principal
az login --service-principal \
  --username {app-id} \
  --password {password} \
  --tenant {tenant-id}

# List available subscriptions
az account list --output table

# Set active subscription
az account set --subscription "{name or id}"
```

### "InvalidAuthenticationTokenTenant"

**Cause**: Logged into wrong tenant

**Solution**:
```bash
# Check current tenant
az account show --query tenantId

# Login to specific tenant
az login --tenant {tenant-id}
```

## Resource Creation Issues

### "The resource name is invalid"

**Cause**: Name doesn't meet Azure naming requirements

**Common Rules**:
- Storage accounts: 3-24 chars, lowercase letters and numbers
- Resource groups: 1-90 chars, alphanumeric, underscores, hyphens, periods
- VMs: 1-64 chars (Windows), 1-15 chars for hostname
- Function apps: 2-60 chars, alphanumeric and hyphens

**Solution**: Use valid characters and length
```bash
# Good storage account name
STORAGE_NAME="mystorageacct$(date +%s)"  # Append timestamp

# Bad examples:
# "MyStorageAccount"  # Uppercase not allowed
# "storage_account"   # Underscores not allowed
```

### "StorageAccountAlreadyExists"

**Cause**: Storage account name must be globally unique

**Solution**: Add unique suffix
```bash
UNIQUE_SUFFIX=$(openssl rand -hex 4)
STORAGE_NAME="mystorage${UNIQUE_SUFFIX}"

az storage account create --name $STORAGE_NAME ...
```

### "QuotaExceeded"

**Cause**: Reached subscription limit for resource type

**Check Limits**:
```bash
# Check VM quota
az vm list-usage --location eastus --output table

# Check network quota
az network list-usages --location eastus --output table
```

**Solution**: Request quota increase via Azure Portal or delete unused resources

### "LocationNotAvailableForResourceType"

**Cause**: Service not available in that region

**Solution**:
```bash
# List available locations for resource type
az provider show \
  --namespace Microsoft.Compute \
  --query "resourceTypes[?resourceType=='virtualMachines'].locations"

# Use available location
az vm create --location eastus ...
```

## Networking Issues

### "AddressSpaceOverlap"

**Cause**: VNet address space conflicts with peered VNet

**Solution**: Use non-overlapping CIDR blocks
```bash
# VNet 1: 10.0.0.0/16
# VNet 2: 10.1.0.0/16  (Good - no overlap)
# VNet 3: 10.0.0.0/24  (Bad - overlaps with VNet 1)
```

### "Port already allocated"

**Cause**: NSG rule or Load Balancer already using that port

**Solution**: Use different port or remove conflicting rule
```bash
# List existing NSG rules
az network nsg rule list \
  --resource-group {rg} \
  --nsg-name {nsg-name} \
  --output table
```

### "Cannot connect to VM"

**Diagnostic Steps**:
```bash
# 1. Check VM is running
az vm get-instance-view \
  --resource-group {rg} \
  --name {vm-name} \
  --query instanceView.statuses

# 2. Check NSG rules allow traffic
az network nsg rule list \
  --resource-group {rg} \
  --nsg-name {nsg-name}

# 3. Get public IP
az vm show -d \
  --resource-group {rg} \
  --name {vm-name} \
  --query publicIps -o tsv

# 4. Use serial console (Portal) if SSH/RDP doesn't work
```

## Database Issues

### "Server name already exists"

**Cause**: Azure SQL/MySQL/PostgreSQL server names are globally unique

**Solution**: Add unique suffix
```bash
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
SERVER_NAME="mysqlserver-${UNIQUE_ID}"
```

### "FirewallRuleNotAllowingConnection"

**Solution**: Add firewall rule
```bash
# Allow your IP
MY_IP=$(curl -s ifconfig.me)
az sql server firewall-rule create \
  --resource-group {rg} \
  --server {server-name} \
  --name AllowMyIP \
  --start-ip-address $MY_IP \
  --end-ip-address $MY_IP

# Allow Azure services
az sql server firewall-rule create \
  --resource-group {rg} \
  --server {server-name} \
  --name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### "Password does not meet complexity requirements"

**Requirements**:
- At least 8 characters
- Contains uppercase and lowercase
- Contains numbers
- Contains special characters

**Solution**: Generate strong password
```bash
# Generate random password
PASSWORD="P@ssw0rd$(openssl rand -base64 12 | tr -d '=+/' | cut -c1-8)!"
```

## Container Issues

### "Failed to pull image"

**Cause**: Image doesn't exist or no access to private registry

**Solution for ACR**:
```bash
# Attach ACR to AKS
az aks update \
  --resource-group {rg} \
  --name {aks-name} \
  --attach-acr {acr-name}

# Or use service principal
ACR_ID=$(az acr show --name {acr-name} --query id -o tsv)
SP_PASSWORD=$(az ad sp create-for-rbac \
  --name {sp-name} \
  --role acrpull \
  --scope $ACR_ID \
  --query password -o tsv)
```

### "Insufficient CPU/Memory"

**Cause**: Container resource limits too high for plan

**Solution**: Adjust resource requests/limits
```bash
az containerapp update \
  --name {app-name} \
  --resource-group {rg} \
  --cpu 0.5 \
  --memory 1.0Gi
```

## Storage Issues

### "BlobNotFound"

**Solution**: Verify container and blob exist
```bash
# List containers
az storage container list \
  --account-name {storage-name}

# List blobs
az storage blob list \
  --account-name {storage-name} \
  --container-name {container-name}
```

### "AuthorizationPermissionMismatch"

**Cause**: Lack of RBAC role for storage operations

**Solution**: Assign appropriate role
```bash
# For blob operations
az role assignment create \
  --assignee {user-or-sp-id} \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{storage-name}
```

## Performance Issues

### Slow VM Performance

**Diagnostic**:
```bash
# Check VM size
az vm show \
  --resource-group {rg} \
  --name {vm-name} \
  --query hardwareProfile.vmSize

# Check disk performance
az disk show \
  --resource-group {rg} \
  --name {disk-name} \
  --query sku.name  # Premium_LRS is faster than Standard_LRS
```

**Solution**: Resize VM or upgrade disk
```bash
# Resize VM
az vm resize \
  --resource-group {rg} \
  --name {vm-name} \
  --size Standard_D4s_v3

# Upgrade to Premium SSD
az vm update \
  --resource-group {rg} \
  --name {vm-name} \
  --set storageProfile.osDisk.managedDisk.storageAccountType=Premium_LRS
```

### Database Connection Pool Exhausted

**Solution**: Increase max connections or implement connection pooling
```bash
# For Azure Database for MySQL
az mysql flexible-server parameter set \
  --resource-group {rg} \
  --server-name {server-name} \
  --name max_connections \
  --value 500
```

## Deployment Issues

### "ResourceGroupNotFound"

**Solution**: Create the resource group first
```bash
az group create \
  --name {rg-name} \
  --location {location}
```

### "TemplateDeploymentFailed"

**Diagnostic**:
```bash
# View deployment operations
az deployment group operation list \
  --resource-group {rg} \
  --name {deployment-name}

# Show detailed error
az deployment group show \
  --resource-group {rg} \
  --name {deployment-name} \
  --query properties.error
```

### "ResourceNotFound" (during delete)

**Solution**: Resource may be already deleted or in different RG
```bash
# List all resource groups
az group list --output table

# List resources in RG
az resource list \
  --resource-group {rg} \
  --output table

# Force delete RG even if resources are partially deleted
az group delete \
  --name {rg} \
  --yes \
  --no-wait
```

## Cost Management Issues

### Unexpected Charges

**Diagnostic**:
```bash
# List running VMs
az vm list -d \
  --query "[?powerState=='VM running'].{Name:name, RG:resourceGroup}" \
  --output table

# List storage accounts
az storage account list \
  --query "[].{Name:name, RG:resourceGroup, SKU:sku.name}" \
  --output table

# Check AKS node pools
az aks nodepool list \
  --resource-group {rg} \
  --cluster-name {aks-name} \
  --query "[].{Name:name, Count:count, VM:vmSize}"
```

**Solution**: Stop/deallocate unused resources
```bash
# Deallocate VM (stops billing for compute)
az vm deallocate --resource-group {rg} --name {vm-name}

# Delete unused resources
az group delete --name {unused-rg} --yes --no-wait
```

## Monitoring & Logs

### Enable Diagnostics

```bash
# Enable VM boot diagnostics
az vm boot-diagnostics enable \
  --resource-group {rg} \
  --name {vm-name} \
  --storage {storage-account-uri}

# Enable NSG flow logs
az network watcher flow-log create \
  --resource-group {rg} \
  --nsg {nsg-name} \
  --name flowlog \
  --storage-account {storage-name}
```

### View Activity Logs

```bash
# Recent activities
az monitor activity-log list \
  --resource-group {rg} \
  --start-time 2024-01-01T00:00:00Z \
  --output table

# Filter by operation
az monitor activity-log list \
  --resource-group {rg} \
  --caller {email@domain.com} \
  --output table
```

## Quick Diagnostic Commands

```bash
# 1. Verify you're in the right subscription
az account show

# 2. Check resource exists
az resource list --name {resource-name}

# 3. View resource details
az resource show --ids {resource-id}

# 4. Check tags
az resource show --ids {resource-id} --query tags

# 5. List recent deployments
az deployment group list \
  --resource-group {rg} \
  --query "[?properties.provisioningState=='Failed'].{Name:name, Error:properties.error.message}"
```

## Getting Help

### Azure CLI Help
```bash
# General help
az --help

# Service help
az vm --help
az network --help

# Command help
az vm create --help
```

### Documentation Links
- Azure CLI Docs: https://learn.microsoft.com/cli/azure/
- Azure Status: https://status.azure.com/
- Azure Support: https://azure.microsoft.com/support/

### Support Channels
1. **Azure Portal**: Open support ticket
2. **Stack Overflow**: Tag with [azure] and specific service
3. **Microsoft Q&A**: https://learn.microsoft.com/answers/
4. **GitHub Issues**: For Azure CLI bugs

---

## Microsoft Learn References

### Troubleshooting Guides

- [Azure CLI Troubleshooting](https://learn.microsoft.com/cli/azure/troubleshooting) - Common Azure CLI issues and solutions
- [Azure Resource Manager Troubleshooting](https://learn.microsoft.com/azure/azure-resource-manager/troubleshooting/overview) - Deployment and resource errors
- [Azure Virtual Machines Troubleshooting](https://learn.microsoft.com/azure/virtual-machines/troubleshooting/) - VM connectivity and performance issues
- [Azure Networking Troubleshooting](https://learn.microsoft.com/azure/virtual-network/troubleshoot-vm-connectivity) - Network connectivity problems
- [Azure Storage Troubleshooting](https://learn.microsoft.com/azure/storage/common/storage-monitoring-diagnosing-troubleshooting) - Storage account errors
- [Azure RBAC Troubleshooting](https://learn.microsoft.com/azure/role-based-access-control/troubleshooting) - Permission and access issues
- [Azure Key Vault Troubleshooting](https://learn.microsoft.com/azure/key-vault/general/troubleshooting) - Key Vault access and configuration

### Error Code References

- [Azure Error Codes](https://learn.microsoft.com/rest/api/azure/#error-codes) - Common REST API error codes
- [Resource Manager Error Codes](https://learn.microsoft.com/azure/azure-resource-manager/troubleshooting/common-deployment-errors) - Deployment error reference
- [Virtual Machine Error Codes](https://learn.microsoft.com/azure/virtual-machines/error-codes) - VM-specific error codes
- [Storage Error Codes](https://learn.microsoft.com/rest/api/storageservices/common-rest-api-error-codes) - Storage API errors

### Service-Specific Troubleshooting

- [Azure Functions Troubleshooting](https://learn.microsoft.com/azure/azure-functions/functions-diagnostics) - Function app errors
- [Azure Container Apps Troubleshooting](https://learn.microsoft.com/azure/container-apps/troubleshooting) - Container deployment issues
- [Azure Service Bus Troubleshooting](https://learn.microsoft.com/azure/service-bus-messaging/service-bus-troubleshooting-guide) - Messaging errors
- [Azure SQL Database Troubleshooting](https://learn.microsoft.com/azure/azure-sql/database/troubleshoot-common-errors-issues) - Database connectivity
- [Azure Cosmos DB Troubleshooting](https://learn.microsoft.com/azure/cosmos-db/troubleshoot-common-issues) - NoSQL database errors

### Diagnostic Tools

- [Azure Resource Graph](https://learn.microsoft.com/azure/governance/resource-graph/) - Query and discover resources
- [Azure Monitor](https://learn.microsoft.com/azure/azure-monitor/overview) - Monitoring and diagnostics
- [Azure Activity Log](https://learn.microsoft.com/azure/azure-monitor/essentials/activity-log) - Audit resource operations
- [Azure Network Watcher](https://learn.microsoft.com/azure/network-watcher/network-watcher-monitoring-overview) - Network diagnostics
- [Azure Advisor](https://learn.microsoft.com/azure/advisor/) - Best practice recommendations

### Best Practices

- [Azure Well-Architected Framework](https://learn.microsoft.com/azure/well-architected/) - Design best practices
- [Azure Security Best Practices](https://learn.microsoft.com/azure/security/fundamentals/best-practices-and-patterns) - Security guidance
- [Azure Operational Excellence](https://learn.microsoft.com/azure/well-architected/operational-excellence/) - Operations best practices
- [Azure Cost Optimization](https://learn.microsoft.com/azure/cost-management-billing/costs/cost-optimization-best-practices) - Reduce Azure costs

---

**Guide Version**: 2.0
**Last Updated**: 2025-01-15
**Azure CLI Version**: 2.50+
**MS Learn Links**: 25+ troubleshooting and diagnostic resources
