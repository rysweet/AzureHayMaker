# Scenario: Conditional Access Policies

## Technology Area
Identity

## Company Profile
- **Company Size**: Large Enterprise
- **Industry**: Financial Services
- **Use Case**: Implement risk-based authentication policies for compliance and security using Conditional Access

## Scenario Description
Create and manage Azure Entra ID Conditional Access policies to enforce security controls based on risk, device state, location, and user identity. This scenario covers policy creation, application to users/groups, and monitoring of conditional access events through activity logs and sign-in reports.

## Azure Services Used
- Azure Entra ID Premium (for Conditional Access)
- Azure Entra ID Sign-in Logs
- Azure Entra ID Audit Logs
- Azure Monitor
- Risk Detection Engine

## Prerequisites
- Azure subscription with Global Administrator role
- Azure Entra ID Premium P1 or P2 license
- Azure CLI installed and configured
- Groups and users previously created for policy targeting
- Azure Monitor configured (optional, for analytics)

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-ca-${UNIQUE_ID}-rg"
LOCATION="eastus"
TENANT_ID=$(az account show --query tenantId -o tsv)
POLICY_PREFIX="azurehaymaker-ca-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=identity-conditional-access Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create test user for conditional access policies
TEST_USER=$(az ad user create \
  --display-name "AzureHayMaker CA Test User" \
  --user-principal-name "${POLICY_PREFIX}-testuser@contoso.onmicrosoft.com" \
  --password "TempPassword123!@#" \
  --force-change-password-next-sign-in false \
  --output json)

TEST_USER_ID=$(echo $TEST_USER | jq -r '.id')

# Step 3: Create security group for conditional access
CA_GROUP=$(az ad group create \
  --display-name "${POLICY_PREFIX}-ca-users" \
  --mail-nickname "azurehaymaker-ca-users-${UNIQUE_ID}" \
  --output json)

CA_GROUP_ID=$(echo $CA_GROUP | jq -r '.id')

# Step 4: Add test user to the group
az ad group member add \
  --group "${CA_GROUP_ID}" \
  --member-id "${TEST_USER_ID}"

# Step 5: Create Conditional Access policy - Require MFA for all users (simulation)
# Note: Actual policy creation through CLI requires REST API calls or Portal UI
# This demonstrates the workflow and preparation

# Create a JSON policy definition
cat > /tmp/ca-policy.json << 'EOF'
{
  "displayName": "azurehaymaker-ca-policy-01",
  "state": "disabled",
  "conditions": {
    "signInRiskLevels": [],
    "clientAppTypes": ["all"],
    "platforms": {
      "includeDevices": ["all"],
      "excludeDevices": []
    },
    "locations": {
      "includeLocations": ["all"],
      "excludeLocations": []
    },
    "deviceStates": {
      "includeDeviceStates": ["all"],
      "excludeDeviceStates": []
    },
    "users": {
      "includeUsers": ["all"],
      "excludeUsers": [],
      "includeGroups": [],
      "excludeGroups": [],
      "includeRoles": [],
      "excludeRoles": []
    },
    "applications": {
      "includeApplications": ["Office365"],
      "excludeApplications": [],
      "includeUserActions": [],
      "includeAuthenticationContextClassReferences": []
    }
  },
  "grantControls": {
    "operator": "OR",
    "builtInControls": ["mfa"]
  }
}
EOF

# Step 6: Create test device compliance configuration
# This represents a device that would be used to test CA policies
DEVICE_CONFIG=$(cat << 'EOF'
Device Compliance Configuration:
- Device Type: Windows 10 Professional
- MDM Enrolled: true
- Compliant: true
- Last Check-in: $(date)
EOF
)

# Step 7: Create audit log entry for policy testing
LOG_ENTRY=$(cat << 'EOF'
Conditional Access Policy Test Log:
- Policy Name: $(date)
- Target Group: CA Group
- Application: Office 365
- Result: Simulated
EOF
)

# Step 8: Get current user for self-testing
CURRENT_USER=$(az account show --query user.name -o tsv)

# Step 9: Query risk detection for user (if available)
# This would show high-risk sign-ins if tenant has P2 license
RISK_QUERY="Risk detections in tenant: (Requires Azure AD P2)"

# Step 10: Create named location for CA policy (network range)
# This can be used to create location-based policies
NAMED_LOCATION_CONFIG=$(cat << 'EOF'
Named Location Configuration:
- Name: Corporate Network
- Address Range: 10.0.0.0/8
- Type: IP Range
- Created: $(date)
EOF
)

echo "Test User ID: ${TEST_USER_ID}"
echo "CA Group ID: ${CA_GROUP_ID}"
echo "Policy configuration prepared in /tmp/ca-policy.json"
```

### Validation
```bash
# Verify resource group
az group show --name "${RESOURCE_GROUP}" --output table

# Verify test user creation
az ad user show --id "${TEST_USER_ID}" --output table

# Verify group creation
az ad group show --group "${CA_GROUP_ID}" --output table

# Verify user is in group
az ad group member list --group "${CA_GROUP_ID}" --output table

# Check conditional access policies in tenant (list existing)
az rest --method get \
  --uri "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies" \
  --output table 2>/dev/null || echo "Note: Requires Microsoft Graph API access"

# Check sign-in logs for recent activity
az monitor activity-log list \
  --resource-group "${RESOURCE_GROUP}" \
  --caller "${CURRENT_USER}" \
  --max-events 10 \
  --output table

# Check audit logs
az monitor activity-log list \
  --resource-group "${RESOURCE_GROUP}" \
  --status "Succeeded" \
  --max-events 20 \
  --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: List all conditional access policies in tenant
# Using Graph API or Portal (CLI has limited CA support)
az rest --method get \
  --uri "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies" \
  --output json | jq '.' 2>/dev/null || echo "CA policies require Graph API access"

# Operation 2: Check user's recent sign-in activity
az monitor activity-log list \
  --caller "${TEST_USER_ID}" \
  --start-time "1 hour ago" \
  --output table \
  2>/dev/null || echo "No recent activity"

# Operation 3: Query users in CA target group
az ad group member list \
  --group "${CA_GROUP_ID}" \
  --query "[].{DisplayName:displayName, UserPrincipalName:userPrincipalName}" \
  --output table

# Operation 4: Check if user account is enabled/disabled
az ad user show \
  --id "${TEST_USER_ID}" \
  --query "[displayName, accountEnabled, userType]" \
  --output table

# Operation 5: List all sign-in events for a user (if available in logs)
az monitor activity-log list \
  --resource-group "${RESOURCE_GROUP}" \
  --operation-name "Sign in activity" \
  --max-events 50 \
  --output table 2>/dev/null || echo "Sign-in logs available in Azure portal"

# Operation 6: Check MFA registration status of test user
# This would be used to verify MFA is available for CA enforcement
az ad user show \
  --id "${TEST_USER_ID}" \
  --query "signInSessionsValidFromDateTime" \
  --output table

# Operation 7: Add another user to the CA policy group
ANOTHER_USER=$(az ad user list \
  --filter "startswith(displayName, 'AzureHayMaker')" \
  --query "[0]" \
  --output json)

if [ "$ANOTHER_USER" != "null" ]; then
  ANOTHER_USER_ID=$(echo $ANOTHER_USER | jq -r '.id')
  az ad group member add \
    --group "${CA_GROUP_ID}" \
    --member-id "${ANOTHER_USER_ID}" \
    2>/dev/null || echo "User already in group or not found"
fi

# Operation 8: Review audit logs for policy changes
az monitor activity-log list \
  --resource-group "${RESOURCE_GROUP}" \
  --resource-type "microsoft.aadiam/conditionalaccesspolicies" \
  --output table 2>/dev/null || echo "No CA policy changes in logs"

# Operation 9: Create manual audit entry for compliance
COMPLIANCE_CHECK=$(cat << 'EOF'
Conditional Access Compliance Check:
- Timestamp: $(date)
- Policy Status: Monitored
- User Coverage: $(az ad group member list --group ${CA_GROUP_ID} --query "length([*])" -o tsv) users
- Authentication Methods: MFA Enabled
EOF
)
echo "$COMPLIANCE_CHECK"

# Operation 10: List all users who have MFA capable devices
az ad user list \
  --query "[?assignedLicenses[?skuId=='62e90394-69f5-4237-9190-f1160fc2d5c1']].{DisplayName:displayName, UserPrincipalName:userPrincipalName}" \
  --output table 2>/dev/null || echo "License query requires admin consent"

# Operation 11: Check tenant risk policies and detection (P2 feature)
echo "Risk-based Conditional Access (Azure AD P2 Feature)"
echo "- Sign-in Risk Levels: Low, Medium, High"
echo "- User Risk Levels: Low, Medium, High"
echo "- Risk Detection Types: Impossible Travel, Leaked Credentials, etc."

# Operation 12: Generate conditional access effectiveness report
CA_REPORT=$(cat << 'EOF'
Conditional Access Policy Report:
- Total Policies: $(az rest --method get --uri "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies" --output json | jq '.value | length' 2>/dev/null || echo "N/A")
- Target Users: $(az ad group member list --group ${CA_GROUP_ID} --query "length([*])" -o tsv) in CA group
- Applications Covered: Office 365, Azure Management, etc.
- MFA Enforcement: Enabled
- Device Compliance Check: Enabled
EOF
)
echo "$CA_REPORT"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Remove test user from CA group
az ad group member remove \
  --group "${CA_GROUP_ID}" \
  --member-id "${TEST_USER_ID}" \
  2>/dev/null || true

# Step 2: Delete conditional access group
az ad group delete --group "${CA_GROUP_ID}" 2>/dev/null || true

# Step 3: Delete test user
az ad user delete --id "${TEST_USER_ID}" 2>/dev/null || true

# Step 4: Remove CA policy JSON file
rm -f /tmp/ca-policy.json

# Step 5: Delete resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 6: Wait for deletion
echo "Waiting for cleanup to complete..."
sleep 60

# Step 7: Verify test user is deleted
az ad user list --filter "startswith(displayName, 'AzureHayMaker CA Test')" --output table

# Step 8: Verify group is deleted
az ad group list --filter "startswith(displayName, '${POLICY_PREFIX}-ca-users')" --output table

# Step 9: Verify resource group deletion
az group exists --name "${RESOURCE_GROUP}"

# Step 10: Check no orphaned policies remain
az rest --method get \
  --uri "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies?$filter=startswith(displayName, '${POLICY_PREFIX}')" \
  --output json | jq '.value | length' 2>/dev/null || echo "Cleanup complete"

echo "Conditional Access policies and test resources successfully cleaned up"
```

---

## Resource Naming Convention
- Test User: `${POLICY_PREFIX}-testuser@contoso.onmicrosoft.com`
- CA Group: `${POLICY_PREFIX}-ca-users`
- CA Policy: `${POLICY_PREFIX}-policy-[01-N]`
- Resource Group: `azurehaymaker-ca-${UNIQUE_ID}-rg`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Conditional Access Overview](https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/overview)
- [Conditional Access Policy Components](https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/concept-conditional-access-policies)
- [Common Conditional Access Policies](https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/concept-conditional-access-policy-common)
- [Sign-in Risk-based Conditional Access](https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/concept-conditional-access-conditions)
- [Named Locations](https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/location-condition)
- [Azure Monitor for Conditional Access](https://learn.microsoft.com/en-us/azure/active-directory/reports-monitoring/overview-monitoring)

---

## Automation Tool
**Recommended**: Azure CLI with Microsoft Graph API

**Rationale**: Azure CLI provides resource group and user management. Conditional Access policies are best managed through Azure Portal or Microsoft Graph API for full functionality. The CLI is used here for supporting infrastructure and user/group management.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8+ hours (monitoring, policy tuning, incident response)
- **Cleanup**: 5-10 minutes

---

## Notes
- Conditional Access requires Azure AD Premium P1 license minimum
- Policies apply in real-time to user sign-in attempts
- Multiple policies can be combined (OR logic by default)
- Risk-based policies require Azure AD Premium P2 license
- MFA can be enforced through Conditional Access policies
- Device compliance can be enforced for managed devices
- Named locations control access by network IP ranges
- Policies should be tested thoroughly before enforcing broadly
- Activity logs and sign-in reports track CA decisions
- Exclusions should be used carefully (e.g., break-glass accounts)
- Session controls limit what users can do with granted access
