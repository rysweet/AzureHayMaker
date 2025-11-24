# Scenario: Azure Key Vault for Secrets Management

## Technology Area
Security

## Company Profile
- **Company Size**: Small startup
- **Industry**: SaaS / Financial Technology
- **Use Case**: Securely store and manage API keys, connection strings, and sensitive credentials for cloud applications

## Scenario Description
Deploy Azure Key Vault to centrally manage application secrets including API keys, connection strings, and certificates. This scenario covers secret creation, access management, rotation policies, and secure retrieval patterns for applications.

## Azure Services Used
- Azure Key Vault
- Azure Managed Identity
- Azure App Service (for consumption example)
- Azure CLI (for secret management)

## Prerequisites
- Azure subscription with Owner or Contributor role
- Azure CLI installed and configured
- jq (JSON processor) for parsing responses
- Access to create and manage Key Vault resources

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-security-${UNIQUE_ID}-rg"
LOCATION="eastus"
KEY_VAULT_NAME="azurehaymaker-kv-${UNIQUE_ID}"
APP_SERVICE_PLAN="azurehaymaker-asp-${UNIQUE_ID}"
WEB_APP_NAME="azurehaymaker-app-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=security-key-vault Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Azure Key Vault
az keyvault create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${KEY_VAULT_NAME}" \
  --location "${LOCATION}" \
  --enable-rbac-authorization \
  --tags ${TAGS}

# Step 3: Set access policy for current user (legacy model for testing)
CURRENT_USER_OID=$(az ad signed-in-user show --query objectId -o tsv)
az keyvault set-policy \
  --name "${KEY_VAULT_NAME}" \
  --object-id "${CURRENT_USER_OID}" \
  --secret-permissions get list set delete

# Step 4: Create API Key secret
az keyvault secret set \
  --vault-name "${KEY_VAULT_NAME}" \
  --name "api-key" \
  --value "sk-$(openssl rand -hex 32)"

# Step 5: Create Database Connection String secret
az keyvault secret set \
  --vault-name "${KEY_VAULT_NAME}" \
  --name "db-connection-string" \
  --value "Server=myserver.database.windows.net;Database=mydb;User Id=sa;Password=HayMaker$(openssl rand -hex 8)"

# Step 6: Create third-party API credentials secret
az keyvault secret set \
  --vault-name "${KEY_VAULT_NAME}" \
  --name "third-party-api-credentials" \
  --value "{\"username\":\"user123\",\"password\":\"pass$(openssl rand -hex 12)\"}"

# Step 7: Create JWT signing key secret
az keyvault secret set \
  --vault-name "${KEY_VAULT_NAME}" \
  --name "jwt-signing-key" \
  --value "$(openssl rand -base64 32)"

# Step 8: Create App Service Plan
az appservice plan create \
  --name "${APP_SERVICE_PLAN}" \
  --resource-group "${RESOURCE_GROUP}" \
  --sku B1 \
  --is-linux \
  --tags ${TAGS}

# Step 9: Create Web App with identity
az webapp create \
  --resource-group "${RESOURCE_GROUP}" \
  --plan "${APP_SERVICE_PLAN}" \
  --name "${WEB_APP_NAME}" \
  --runtime "PYTHON|3.9" \
  --tags ${TAGS}

# Step 10: Enable system-assigned managed identity on the Web App
az webapp identity assign \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --identities [system]

# Step 11: Get the managed identity object ID
IDENTITY_OID=$(az webapp identity show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --query principalId -o tsv)

# Step 12: Grant Key Vault access to the managed identity
az keyvault set-policy \
  --name "${KEY_VAULT_NAME}" \
  --object-id "${IDENTITY_OID}" \
  --secret-permissions get list

echo "Key Vault Name: ${KEY_VAULT_NAME}"
echo "Web App Name: ${WEB_APP_NAME}"
echo "Managed Identity OID: ${IDENTITY_OID}"
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Key Vault creation
az keyvault show --resource-group "${RESOURCE_GROUP}" --name "${KEY_VAULT_NAME}"

# List all secrets in Key Vault
az keyvault secret list --vault-name "${KEY_VAULT_NAME}" --output table

# Retrieve a specific secret value
az keyvault secret show \
  --vault-name "${KEY_VAULT_NAME}" \
  --name "api-key" \
  --query value -o tsv

# Verify Web App identity
az webapp identity show --resource-group "${RESOURCE_GROUP}" --name "${WEB_APP_NAME}"

# Check Key Vault access policies
az keyvault list-deleted --resource-group "${RESOURCE_GROUP}" || \
  az keyvault show --resource-group "${RESOURCE_GROUP}" --name "${KEY_VAULT_NAME}"

# List all resources in the resource group
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Create a new secret version with a new value
az keyvault secret set \
  --vault-name "${KEY_VAULT_NAME}" \
  --name "api-key" \
  --value "sk-$(openssl rand -hex 32)"

# Operation 2: List all versions of a secret
az keyvault secret list-versions \
  --vault-name "${KEY_VAULT_NAME}" \
  --name "api-key" \
  --output table

# Operation 3: Retrieve a specific secret version by ID
API_KEY_ID=$(az keyvault secret show \
  --vault-name "${KEY_VAULT_NAME}" \
  --name "api-key" \
  --query id -o tsv)

az keyvault secret show --id "${API_KEY_ID}"

# Operation 4: Add tags to a secret
az keyvault secret set \
  --vault-name "${KEY_VAULT_NAME}" \
  --name "db-connection-string" \
  --value "Server=myserver.database.windows.net;Database=mydb;User Id=sa;Password=HayMaker$(openssl rand -hex 8)" \
  --tags environment=production tier=database

# Operation 5: Update Web App settings to reference Key Vault
az webapp config appsettings set \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --settings \
    "@Microsoft.KeyVault(SecretUri=https://${KEY_VAULT_NAME}.vault.azure.net/secrets/api-key/)" \
    "KEYVAULT_URL=https://${KEY_VAULT_NAME}.vault.azure.net/"

# Operation 6: Create certificate in Key Vault (self-signed for testing)
az keyvault certificate create \
  --vault-name "${KEY_VAULT_NAME}" \
  --name "test-certificate" \
  --policy @- << EOF
{
  "issuerParameters": {
    "name": "Self"
  },
  "keyProperties": {
    "exportable": true,
    "keySize": 2048,
    "keyType": "RSA",
    "reuseKey": true
  },
  "lifetimeActions": [
    {
      "action": {
        "actionType": "EmailContacts"
      },
      "trigger": {
        "daysBeforeExpiry": 30
      }
    }
  ],
  "secretProperties": {
    "contentType": "application/x-pkcs12"
  },
  "x509CertificateProperties": {
    "extendedKeyUsage": [
      "1.3.6.1.5.5.7.3.1"
    ],
    "keyUsage": [
      "digitalSignature"
    ],
    "subject": "CN=azurehaymaker.local",
    "validityInMonths": 12
  }
}
EOF

# Operation 7: Audit Key Vault access logs
az monitor activity-log list \
  --resource-group "${RESOURCE_GROUP}" \
  --caller-only \
  --output table

# Operation 8: Set secret expiration policy
az keyvault secret set \
  --vault-name "${KEY_VAULT_NAME}" \
  --name "temp-api-token" \
  --value "token-$(openssl rand -hex 16)" \
  --expires $(date -u -d '+7 days' '+%s')

# Operation 9: Check Key Vault diagnostics settings
az monitor diagnostic-settings list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.KeyVault/vaults/${KEY_VAULT_NAME}" \
  --output table || echo "Diagnostics not yet configured"

# Operation 10: Backup a secret
BACKUP_DIR="/tmp/kv-backup-${UNIQUE_ID}"
mkdir -p "${BACKUP_DIR}"

az keyvault secret backup \
  --vault-name "${KEY_VAULT_NAME}" \
  --name "api-key" \
  --file "${BACKUP_DIR}/api-key.backup"

# Operation 11: Restore a secret from backup
az keyvault secret restore \
  --vault-name "${KEY_VAULT_NAME}" \
  --file "${BACKUP_DIR}/api-key.backup"

# Operation 12: Enable soft delete verification (already enabled by default)
az keyvault show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${KEY_VAULT_NAME}" \
  --query "{enableSoftDelete: properties.enableSoftDelete, softDeleteRetentionInDays: properties.softDeleteRetentionInDays}"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Purge all secrets from Key Vault (optional - soft delete removes immediately)
for SECRET in $(az keyvault secret list --vault-name "${KEY_VAULT_NAME}" --query "[].name" -o tsv); do
  az keyvault secret delete \
    --vault-name "${KEY_VAULT_NAME}" \
    --name "${SECRET}" || true
done

# Step 2: Purge certificates from Key Vault
for CERT in $(az keyvault certificate list --vault-name "${KEY_VAULT_NAME}" --query "[].name" -o tsv); do
  az keyvault certificate delete \
    --vault-name "${KEY_VAULT_NAME}" \
    --name "${CERT}" || true
done

# Step 3: Delete the entire resource group (includes Key Vault, Web App, App Service Plan)
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 4: Wait for deletion to complete
echo "Waiting for resource group deletion..."
sleep 120

# Step 5: Verify deletion
az group exists --name "${RESOURCE_GROUP}"

# Step 6: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 7: Clean up local backup files
rm -rf /tmp/kv-backup-*
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-security-${UNIQUE_ID}-rg`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`
- App Service Plan: `azurehaymaker-asp-${UNIQUE_ID}`
- Web App: `azurehaymaker-app-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Key Vault Overview](https://learn.microsoft.com/en-us/azure/key-vault/general/overview)
- [Key Vault Secret Management](https://learn.microsoft.com/en-us/azure/key-vault/secrets/about-secrets)
- [Managed Identity for Azure Resources](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview)
- [Key Vault Access Control](https://learn.microsoft.com/en-us/azure/key-vault/general/security-features)
- [Key Vault CLI Reference](https://learn.microsoft.com/en-us/cli/azure/keyvault)
- [Key Vault Best Practices](https://learn.microsoft.com/en-us/azure/key-vault/general/security-best-practices)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive Key Vault management capabilities for secret lifecycle management, access policies, and integration with other Azure services. Direct CLI commands enable rapid secret provisioning and audit operations.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8+ hours (with secret rotation, access management, and compliance checks)
- **Cleanup**: 5-10 minutes

---

## Notes
- Key Vault uses RBAC for access control (recommended over legacy access policies)
- Secrets are encrypted at rest and in transit
- Soft delete enabled by default for recovery (retention: 90 days)
- Managed identity eliminates need for credential storage in application code
- All secrets stored with unique IDs for version control and rollback capability
- Operations scoped to single tenant and subscription
- Key Vault integrates with Azure Monitor for comprehensive audit logging
