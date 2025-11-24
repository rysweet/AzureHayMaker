# Scenario Template

## Scenario Name: [Brief Descriptive Name]

### Technology Area
[AI & ML / Analytics / Compute / Containers / Databases / Hybrid+Multicloud / Identity / Networking / Security / Web Apps]

### Company Profile
- **Company Size**: [Small / Mid-size]
- **Industry**: [e.g., Retail, Healthcare, Finance]
- **Use Case**: [Brief description of business need]

### Scenario Description
[2-3 sentences describing what this scenario implements]

### Azure Services Used
- Service 1
- Service 2
- Service 3

### Prerequisites
- Azure subscription with appropriate permissions
- Azure CLI installed and configured
- [Any other tools: terraform, bicep, etc.]

---

## Phase 1: Deployment and Validation

### Deployment Steps

```bash
# Step 1: [Description]
az command here

# Step 2: [Description]
az command or terraform/bicep here

# Continue with all deployment steps...
```

### Validation
```bash
# Verify deployment
az command to check resources
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations

```bash
# Operation 1: [Description]
az command here

# Operation 2: [Description]
az command here

# Continue with operational commands...
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps

```bash
# Step 1: Delete resources
az command to delete

# Step 2: Remove role assignments
az command

# Step 3: Verify cleanup
az command to verify all resources are gone
```

---

## Resource Naming Convention
All resources created in this scenario should be named: `azurehaymaker-[scenario-name]-[unique-id]-[resource-type]`

All resources must be tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Link to Azure documentation 1]
- [Link to Azure documentation 2]
- [Link to automation tool documentation]

---

## Automation Tool
**Recommended**: [Azure CLI / Terraform / Bicep]

**Rationale**: [Why this tool is best for this scenario]

---

## Estimated Duration
- **Deployment**: [X minutes]
- **Operations Phase**: [8 hours minimum]
- **Cleanup**: [X minutes]

---

## Notes
- All operations must be scoped to a single tenant and subscription
- Unique resource names must be used for each run
- No data preservation required - cleanup is complete deletion
