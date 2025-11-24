# Scenario: Azure Migrate Assessment and Discovery

## Technology Area
Hybrid+Multicloud

## Company Profile
- **Company Size**: Large enterprise
- **Industry**: Healthcare
- **Use Case**: Assess on-premises infrastructure for cloud migration readiness

## Scenario Description
Deploy Azure Migrate to discover on-premises infrastructure, assess migration readiness, and create migration plans. Configure assessment tools, analyze dependencies, and generate migration recommendations.

## Azure Services Used
- Azure Migrate (migration assessment and orchestration)
- Azure Migrate: Server Assessment (readiness assessment)
- Azure Migrate: Database Assessment (database evaluation)
- Azure Key Vault (credentials storage)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed
- A unique identifier for this scenario run

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-hybrid-migrate-${UNIQUE_ID}-rg"
LOCATION="eastus"
MIGRATE_PROJECT="azurehaymaker-migrate-${UNIQUE_ID}"
STORAGE_ACCOUNT="azmkrmigrate${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=hybrid-azure-migrate Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Storage Account for migration data
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

# Step 3: Create containers for assessment data
STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

az storage container create \
  --name "discovery-data" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}"

az storage container create \
  --name "assessment-results" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}"

az storage container create \
  --name "migration-artifacts" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}"

# Step 4: Create Key Vault
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 5: Create Azure Migrate Project
az migrate project create \
  --name "${MIGRATE_PROJECT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 6: Get project details
PROJECT_ID=$(az migrate project show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MIGRATE_PROJECT}" \
  --query "id" -o tsv)

# Step 7: Create sample discovery data
cat > /tmp/discovered_servers.json <<EOF
{
  "servers": [
    {
      "id": "server-001",
      "name": "web-server-01",
      "os": "Windows Server 2019",
      "cpu": 8,
      "memory": 32,
      "storage": 500,
      "network": ["10.0.1.10"],
      "applications": ["IIS", ".NET Framework", "SQL Server Express"]
    },
    {
      "id": "server-002",
      "name": "app-server-01",
      "os": "Windows Server 2019",
      "cpu": 16,
      "memory": 64,
      "storage": 1000,
      "network": ["10.0.1.11"],
      "applications": ["App Service", ".NET 4.8", "Custom App"]
    },
    {
      "id": "server-003",
      "name": "db-server-01",
      "os": "Windows Server 2019",
      "cpu": 32,
      "memory": 128,
      "storage": 2000,
      "network": ["10.0.1.12"],
      "applications": ["SQL Server 2019"]
    },
    {
      "id": "server-004",
      "name": "file-server-01",
      "os": "Windows Server 2016",
      "cpu": 4,
      "memory": 16,
      "storage": 5000,
      "network": ["10.0.1.13"],
      "applications": ["File Share", "DFS"]
    }
  ]
}
EOF

# Step 8: Create assessment group
cat > /tmp/assessment_group.json <<EOF
{
  "groupName": "production-servers",
  "groupType": "Default",
  "description": "Production servers for migration assessment",
  "servers": ["server-001", "server-002", "server-003"],
  "properties": {
    "environment": "production",
    "priority": "high"
  }
}
EOF

# Step 9: Create assessment configuration
cat > /tmp/assessment_config.json <<EOF
{
  "assessmentName": "production-assessment",
  "groupName": "production-servers",
  "computeOptions": {
    "isPerformanceBased": true,
    "computeComfort": 1.5,
    "cpuUtilizationPercentile": 95,
    "memoryUtilizationPercentile": 95
  },
  "storageOptions": {
    "storageRedundancy": "LocallyRedundant",
    "discType": "PremiumManagedDisk"
  },
  "networkOptions": {
    "networkSecurityGroupOption": "UserManaged"
  },
  "azureOptions": {
    "azureOfferCode": "MSAZR0003P",
    "currency": "USD",
    "discountPercentage": 0,
    "azureHybridUseBenefit": "Yes"
  }
}
EOF

# Step 10: Store assessment configuration
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "discovered-servers" \
  --value @/tmp/discovered_servers.json

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "assessment-config" \
  --value @/tmp/assessment_config.json

echo ""
echo "=========================================="
echo "Azure Migrate Project: ${MIGRATE_PROJECT}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo "Storage Account: ${STORAGE_ACCOUNT}"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Show Migrate Project
az migrate project show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MIGRATE_PROJECT}"

# Check project status
az migrate project show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MIGRATE_PROJECT}" \
  --query "createdTimestamp" -o tsv

# List projects
az migrate project list \
  --resource-group "${RESOURCE_GROUP}" \
  --output table

# Verify Storage Account
az storage account show \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}"

# List storage containers
az storage container list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --output table

# Check Key Vault
az keyvault show --name "${KEYVAULT}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Create assessment group
echo "To create assessment groups:"
echo "Servers are organized by group for targeted assessment and migration planning"

# Operation 2: Generate migration readiness assessment
cat > /tmp/readiness_assessment.json <<EOF
{
  "assessmentResults": {
    "server-001": {
      "readiness": "Ready",
      "recommendedSize": "Standard_D4s_v3",
      "estimatedMonthlyCost": 200
    },
    "server-002": {
      "readiness": "Ready with Conditions",
      "recommendedSize": "Standard_D8s_v3",
      "estimatedMonthlyCost": 400,
      "conditions": ["Requires Extended Support", "Network bandwidth optimization"]
    },
    "server-003": {
      "readiness": "Ready",
      "recommendedSize": "Standard_E16s_v3",
      "estimatedMonthlyCost": 800,
      "notes": "SQL Server licensing included"
    },
    "server-004": {
      "readiness": "Needs Assessment",
      "recommendedSize": "Standard_D2s_v3",
      "estimatedMonthlyCost": 100,
      "conditions": ["Large storage migration required"]
    }
  }
}
EOF

# Operation 3: Analyze dependencies
cat > /tmp/dependency_analysis.json <<EOF
{
  "dependencies": [
    {
      "source": "web-server-01",
      "target": "app-server-01",
      "protocol": "HTTP",
      "port": 8080,
      "traffic": "High"
    },
    {
      "source": "app-server-01",
      "target": "db-server-01",
      "protocol": "TDS",
      "port": 1433,
      "traffic": "Very High"
    },
    {
      "source": "app-server-01",
      "target": "file-server-01",
      "protocol": "SMB",
      "port": 445,
      "traffic": "Medium"
    }
  ]
}
EOF

# Operation 4: Create migration plan
cat > /tmp/migration_plan.json <<EOF
{
  "phases": [
    {
      "phase": 1,
      "name": "Assessment and Preparation",
      "duration": "2-4 weeks",
      "tasks": [
        "Detailed application assessment",
        "Network design review",
        "Compliance requirements analysis"
      ]
    },
    {
      "phase": 2,
      "name": "Pilot Migration",
      "duration": "1-2 weeks",
      "servers": ["file-server-01"],
      "tasks": [
        "Test migration process",
        "Validate performance",
        "Identify issues"
      ]
    },
    {
      "phase": 3,
      "name": "Production Migration",
      "duration": "3-4 weeks",
      "servers": ["web-server-01", "app-server-01", "db-server-01"],
      "tasks": [
        "Migrate production servers",
        "Cutover traffic",
        "Decommission on-premises"
      ]
    }
  ]
}
EOF

# Operation 5: Monitor assessment progress
az migrate project show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MIGRATE_PROJECT}" \
  --query "createdTimestamp" -o tsv

# Operation 6: Generate cost analysis
echo "Cost Analysis for Migration:"
echo "- Web Server: \$200/month"
echo "- App Server: \$400/month"
echo "- Database Server: \$800/month"
echo "- File Server: \$100/month"
echo "- Total Estimated: \$1,500/month"

# Operation 7: Create replication schedule
cat > /tmp/replication_schedule.json <<EOF
{
  "schedule": {
    "discovery": "Continuous",
    "assessment": "Weekly",
    "costAnalysis": "Monthly",
    "refreshInterval": "24 hours"
  }
}
EOF

# Operation 8: Update project properties
az migrate project update \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MIGRATE_PROJECT}" \
  --tags Environment=production Phase=assessment 2>/dev/null || true

# Operation 9: Export assessment results
az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "assessment-results" \
  --name "readiness-assessment.json" \
  --file /tmp/readiness_assessment.json

# Operation 10: Generate migration report
echo "Azure Migrate Assessment Report Generated"
echo "- Servers Assessed: 4"
echo "- Ready for Migration: 3"
echo "- Needs Assessment: 1"
echo "- Total Estimated Annual Cost: \$18,000"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete Migrate Project
az migrate project delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MIGRATE_PROJECT}" \
  --yes 2>/dev/null || true

# Step 2: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 3: Verify deletion
sleep 60
az group exists --name "${RESOURCE_GROUP}"

# Step 4: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 5: Clean up local files
rm -rf /tmp/discovered_servers.json /tmp/assessment_*.json /tmp/readiness_assessment.json /tmp/dependency_analysis.json /tmp/migration_plan.json /tmp/replication_schedule.json
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-hybrid-migrate-${UNIQUE_ID}-rg`
- Migrate Project: `azurehaymaker-migrate-${UNIQUE_ID}`
- Storage Account: `azmkrmigrate${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Migrate Overview](https://learn.microsoft.com/en-us/azure/migrate/migrate-services-overview)
- [Azure Migrate Appliance](https://learn.microsoft.com/en-us/azure/migrate/migrate-appliance)
- [Server Assessment](https://learn.microsoft.com/en-us/azure/migrate/concepts-assessment-calculation)
- [Dependency Analysis](https://learn.microsoft.com/en-us/azure/migrate/concepts-dependency-visualization)
- [Azure Migrate CLI Reference](https://learn.microsoft.com/en-us/cli/azure/migrate)

---

## Automation Tool
**Recommended**: Azure CLI + Analysis Tools

**Rationale**: Azure CLI manages Migrate project lifecycle while analysis tools process discovery data for comprehensive assessment.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8 hours (with assessments and analysis)
- **Cleanup**: 5 minutes

---

## Notes
- Azure Migrate appliance performs continuous discovery
- Agentless discovery available for VMware environments
- Agent-based discovery for detailed application inventory
- Dependency mapping shows application relationships
- Assessment provides sizing and cost estimates
- All operations scoped to single tenant and subscription
- Supports wave-based migration planning
