---
title: "Windows 365 Cloud PC Provisioning for Knowledge Workers"
description: "Provision and manage Windows 365 Cloud PCs for rich desktop telemetry in knowledge worker simulations"
last_updated: 2025-11-26
doc_type: explanation
owner: knowledge-worker-framework
---

# Windows 365 Cloud PC Provisioning

> **Note**: This document describes the Windows 365 Cloud PC provisioning feature for the Knowledge Worker Activity Framework. Implementation is in progress. See [ARCHITECTURE.md](./ARCHITECTURE.md) for overall framework design.

## Overview

Windows 365 Cloud PCs provide fully managed Windows 11 desktops in the cloud. The Knowledge Worker Framework uses Cloud PCs as endpoints for high-value worker simulations, enabling rich desktop telemetry collection including Windows event logs, process execution history, and user behavior analytics.

## When to Use Cloud PCs vs CLI Containers

The Knowledge Worker Framework supports a **hybrid endpoint strategy** for cost optimization:

| Endpoint Type   | Use Case                       | Telemetry Richness | Cost      |
| --------------- | ------------------------------ | ------------------ | --------- |
| Cloud PC        | High-value workers (10-20%)    | Full desktop logs  | $$$ (High)|
| CLI Container   | Scale workers (80-90%)         | API activity only  | $ (Low)   |

### Cloud PC Advantages

**Rich Telemetry**:
- Full Windows Security Event logs (4624, 4625, 4688, etc.)
- Process execution with command-line arguments
- File system activity (MFT, USN journal)
- Registry modifications
- Network connections with process correlation
- Authentication events (Kerberos, NTLM)

**Realistic Desktop Behavior**:
- Real browser sessions with DOM activity
- Desktop application launches (Outlook, Teams, Edge)
- Background services and scheduled tasks
- Real user profile creation and modification

**Security Product Testing**:
- EDR agent compatibility
- DLP policy validation
- Conditional Access enforcement
- Desktop MFA flows

### CLI Container Advantages

**Cost Efficiency**:
- Run 100+ workers for the cost of 10 Cloud PCs
- Pay only during execution (Azure Container Apps consumption plan)
- No Windows licensing required

**Scale**:
- Spin up 300 workers in parallel
- Minimal resource footprint per worker
- Fast provisioning (seconds vs. minutes)

**Sufficient for API-Level Telemetry**:
- Email send/receive events
- Teams message delivery
- Document access logs
- Calendar event creation

### Hybrid Strategy Example

For a 100-worker simulation:

```python
# 15 high-value Cloud PC workers (executives, admins, targets)
cloud_pc_workers = [
    "CEO", "CFO", "IT Admin", "Security Analyst",
    "HR Director", "Finance Manager", ...
]  # 15 total

# 85 scale workers in containers (general employees)
container_workers = [
    "Engineering Team (20)",
    "Sales Team (25)",
    "Marketing Team (20)",
    "Operations Team (20)"
]  # 85 total
```

**Cost comparison** (USD/month estimate):
- 15 Cloud PCs × $31/month = **$465**
- 85 Container workers × $2/month = **$170**
- **Total: $635/month** vs. **$3,100** for all Cloud PCs

---

## Architecture

### Provisioning Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ KnowledgeWorkerOrchestrator                                     │
│                                                                 │
│  1. Determine endpoint strategy (Cloud PC vs Container)        │
│  2. For Cloud PC workers:                                      │
│     ├── Create provisioning policy (or reuse existing)         │
│     ├── Provision Cloud PCs via Graph API                      │
│     ├── Wait for provisioning (90-minute timeout)              │
│     └── Assign to worker agents                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ Windows365CloudPCManager                                        │
│                                                                 │
│  • ensure_provisioning_policy()                                │
│  • provision_cloud_pc(worker, policy_id)                       │
│  • wait_for_provisioning(worker, timeout)                      │
│  • get_cloud_pc(worker)                                        │
│  • delete_cloud_pc(cloud_pc_id)                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ Microsoft Graph API (Beta)                                      │
│                                                                 │
│  • /deviceManagement/virtualEndpoint/provisioningPolicies      │
│  • /deviceManagement/virtualEndpoint/cloudPCs                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Resource Naming

Cloud PCs follow HayMaker's tag-based resource tracking:

```python
# Cloud PC naming pattern
cloudpc_name = f"kw-{run_id[:8]}-{random:5}"
# Example: kw-abc12345-fx9p2

# Provisioning policy name
policy_name = f"HayMaker-KnowledgeWorker-Policy"

# Tags (Graph API custom properties)
tags = {
    "haymaker_run_id": run_id,
    "haymaker_scenario": "knowledge-worker",
    "worker_id": worker.worker_id,
    "endpoint_type": "cloud_pc"
}
```

---

## Setup and Configuration

### Prerequisites

1. **Windows 365 License**
   - Windows 365 Enterprise subscription
   - Sufficient license allocation for worker count
   - See [Windows 365 pricing](https://www.microsoft.com/windows-365/enterprise/pricing)

2. **Azure AD Permissions**
   - `CloudPC.ReadWrite.All` (Graph API)
   - `DeviceManagementManagedDevices.ReadWrite.All`
   - `Directory.ReadWrite.All` (for user assignment)

3. **Network Configuration**
   - Azure Virtual Network (if using Azure Network Connection)
   - Hybrid AD join configuration (if required)
   - Intune enrollment configured

4. **Graph API Client**
   - App registration with certificate authentication
   - Certificate stored in Azure Key Vault
   - Mounted to Container Apps via secret volume

### Initial Setup

#### 1. Configure Graph API Client

```python
# In orchestrator setup
from azure.identity import CertificateCredential
from msgraph import GraphServiceClient

# Certificate from Key Vault mount
cert_path = "/secrets/m365-app-cert.pem"

credential = CertificateCredential(
    tenant_id="your-tenant-id",
    client_id="your-app-id",
    certificate_path=cert_path,
)

graph_client = GraphServiceClient(credential)
```

#### 2. Create Provisioning Policy

```python
from azure_haymaker.knowledge_worker.endpoints.cloud_pc import Windows365CloudPCManager

# Initialize manager
cloudpc_manager = Windows365CloudPCManager(
    graph_client=graph_client,
    run_id="abc12345-def6-7890-ghij-klmnopqrstuv"
)

# Create or reuse policy
policy_id = await cloudpc_manager.ensure_provisioning_policy(
    display_name="HayMaker-KnowledgeWorker-Policy",
    image_id="MicrosoftWindowsDesktop_windows-ent-cpc_win11-22h2-ent-cpc-m365",
    sku_id="CPC_S_2C_4GB_64GB"  # 2 vCPU, 4GB RAM, 64GB storage
)

print(f"Policy ID: {policy_id}")
# Output: Policy ID: 12345678-1234-1234-1234-123456789abc
```

#### 3. Provision Cloud PC for Worker

```python
from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity, WorkerPersona, EndpointType

# Define worker identity
worker = WorkerIdentity(
    worker_id="kw-abc12345-exec-001",
    display_name="Alex Executive",
    user_principal_name="alex.executive@tenant.onmicrosoft.com",
    department="executive",
    persona=WorkerPersona.EXECUTIVE,
    endpoint_type=EndpointType.CLOUD_PC,
    endpoint_id="",  # Will be set after provisioning
)

# Provision Cloud PC
cloud_pc_id = await cloudpc_manager.provision_cloud_pc(
    worker=worker,
    policy_id=policy_id
)

print(f"Cloud PC provisioning initiated: {cloud_pc_id}")
# Output: Cloud PC provisioning initiated: cloudpc-kw-abc12345-exec-001
```

#### 4. Wait for Provisioning

```python
# Wait for Cloud PC to be ready (90-minute timeout)
success = await cloudpc_manager.wait_for_provisioning(
    worker=worker,
    timeout_minutes=90
)

if success:
    # Get Cloud PC details
    pc_info = await cloudpc_manager.get_cloud_pc(worker)
    print(f"Cloud PC ready: {pc_info['display_name']}")
    print(f"Status: {pc_info['status']}")
    print(f"Managed Device ID: {pc_info['managed_device_id']}")
else:
    print(f"Provisioning failed or timed out")
```

**Expected output**:
```
Cloud PC ready: kw-abc12345-fx9p2
Status: provisioned
Managed Device ID: 87654321-4321-4321-4321-210987654321
```

---

## API Reference

### `Windows365CloudPCManager`

Main class for managing Windows 365 Cloud PCs.

#### Constructor

```python
Windows365CloudPCManager(
    graph_client: GraphServiceClient,
    run_id: str
)
```

**Parameters**:
- `graph_client`: Microsoft Graph API client with Cloud PC permissions
- `run_id`: HayMaker run ID for resource tagging

**Example**:
```python
manager = Windows365CloudPCManager(
    graph_client=my_graph_client,
    run_id="abc12345-def6-7890-ghij-klmnopqrstuv"
)
```

#### Methods

##### `ensure_provisioning_policy()`

Create or retrieve existing provisioning policy.

```python
async def ensure_provisioning_policy(
    display_name: str | None = None,
    image_id: str | None = None,
    sku_id: str | None = None,
) -> str
```

**Parameters**:

| Parameter      | Type      | Required | Default                   | Description                |
| -------------- | --------- | -------- | ------------------------- | -------------------------- |
| `display_name` | str       | No       | "HayMaker-KnowledgeWorker-Policy" | Policy display name |
| `image_id`     | str       | No       | Win11 22H2 M365 image     | Gallery image ID           |
| `sku_id`       | str       | No       | "CPC_S_2C_4GB_64GB"       | Cloud PC SKU               |

**Returns**: `str` - Policy ID

**Raises**:
- `Exception`: If policy creation fails

**Example**:
```python
policy_id = await manager.ensure_provisioning_policy(
    display_name="CustomPolicy",
    sku_id="CPC_M_4C_16GB_256GB"  # Larger SKU
)
# Returns: "98765432-8765-8765-8765-876543210987"
```

##### `provision_cloud_pc()`

Provision a Cloud PC for a worker.

```python
async def provision_cloud_pc(
    worker: WorkerIdentity,
    policy_id: str,
) -> str
```

**Parameters**:

| Parameter   | Type           | Required | Description                      |
| ----------- | -------------- | -------- | -------------------------------- |
| `worker`    | WorkerIdentity | Yes      | Worker identity to assign PC to  |
| `policy_id` | str            | Yes      | Provisioning policy ID           |

**Returns**: `str` - Cloud PC ID (or placeholder during async provisioning)

**Raises**:
- `Exception`: If provisioning initiation fails

**Example**:
```python
cloud_pc_id = await manager.provision_cloud_pc(
    worker=my_worker,
    policy_id=policy_id
)
# Returns: "cloudpc-kw-abc12345-exec-001"
```

**Graph API Call**:
```http
POST /deviceManagement/virtualEndpoint/provisioningPolicies/{id}/assignments
Content-Type: application/json

{
  "target": {
    "@odata.type": "#microsoft.graph.groupAssignmentTarget",
    "groupId": "user-group-id"
  }
}
```

##### `wait_for_provisioning()`

Wait for Cloud PC to reach "provisioned" status.

```python
async def wait_for_provisioning(
    worker: WorkerIdentity,
    timeout_minutes: int | None = None,
) -> bool
```

**Parameters**:

| Parameter         | Type           | Required | Default | Description                   |
| ----------------- | -------------- | -------- | ------- | ----------------------------- |
| `worker`          | WorkerIdentity | Yes      | -       | Worker identity               |
| `timeout_minutes` | int            | No       | 90      | Timeout in minutes            |

**Returns**: `bool` - True if provisioned successfully, False if timeout or error

**Example**:
```python
success = await manager.wait_for_provisioning(
    worker=my_worker,
    timeout_minutes=120  # Extended timeout
)

if success:
    print("Cloud PC ready!")
else:
    print("Provisioning failed")
```

**Polling behavior**:
- Check interval: 60 seconds
- Monitors status field: "provisioning", "provisioned", "failed"
- Returns immediately on "provisioned" or "failed"

##### `get_cloud_pc()`

Retrieve Cloud PC information for a worker.

```python
async def get_cloud_pc(
    worker: WorkerIdentity,
) -> dict[str, Any] | None
```

**Parameters**:

| Parameter | Type           | Required | Description    |
| --------- | -------------- | -------- | -------------- |
| `worker`  | WorkerIdentity | Yes      | Worker identity|

**Returns**: `dict[str, Any]` - Cloud PC info dictionary or None if not found

**Example**:
```python
pc_info = await manager.get_cloud_pc(my_worker)

if pc_info:
    print(f"Display Name: {pc_info['display_name']}")
    print(f"Status: {pc_info['status']}")
    print(f"Device ID: {pc_info['managed_device_id']}")
else:
    print("No Cloud PC found")
```

**Response structure**:
```python
{
    "id": "cloudpc-id",
    "display_name": "kw-abc12345-fx9p2",
    "status": "provisioned",
    "user_principal_name": "alex.executive@tenant.onmicrosoft.com",
    "managed_device_id": "device-id-in-intune"
}
```

##### `delete_cloud_pc()`

Delete a Cloud PC.

```python
async def delete_cloud_pc(
    cloud_pc_id: str,
) -> bool
```

**Parameters**:

| Parameter     | Type | Required | Description      |
| ------------- | ---- | -------- | ---------------- |
| `cloud_pc_id` | str  | Yes      | Cloud PC ID      |

**Returns**: `bool` - True if deleted successfully

**Example**:
```python
success = await manager.delete_cloud_pc("cloudpc-kw-abc12345-exec-001")
# Returns: True
```

**Graph API Call**:
```http
DELETE /deviceManagement/virtualEndpoint/cloudPCs/{id}
```

##### `list_cloud_pcs_for_run()`

List all Cloud PCs for the current run.

```python
async def list_cloud_pcs_for_run() -> list[dict[str, Any]]
```

**Returns**: `list[dict[str, Any]]` - List of Cloud PC info dictionaries

**Example**:
```python
cloud_pcs = await manager.list_cloud_pcs_for_run()

for pc in cloud_pcs:
    print(f"{pc['display_name']}: {pc['status']}")

# Output:
# kw-abc12345-fx9p2: provisioned
# kw-abc12345-kq8r1: provisioning
# kw-abc12345-mp3t7: provisioned
```

---

## Hybrid Endpoint Strategy Implementation

### Orchestrator Decision Logic

```python
# In KnowledgeWorkerOrchestrator

def determine_endpoint_type(worker_identity: WorkerIdentity) -> EndpointType:
    """Determine endpoint type based on worker characteristics.

    Cloud PCs are assigned to:
    - Executives and leadership (high-value targets)
    - IT administrators (privileged access)
    - Security analysts (security tool testing)
    - Specific investigation targets

    CLI Containers are assigned to:
    - General employees (engineering, sales, marketing)
    - Scale workers (bulk activity generation)
    """

    high_value_personas = {
        WorkerPersona.EXECUTIVE,
        WorkerPersona.IT_ADMIN,
        WorkerPersona.SECURITY_ANALYST,
    }

    if worker_identity.persona in high_value_personas:
        return EndpointType.CLOUD_PC

    # Random sampling: 10% of other workers get Cloud PCs
    import random
    if random.random() < 0.10:
        return EndpointType.CLOUD_PC

    return EndpointType.CLI_CONTAINER
```

### Batch Provisioning Example

```python
async def provision_endpoints(
    workers: list[WorkerIdentity],
    graph_client: GraphServiceClient,
    run_id: str,
):
    """Provision endpoints for all workers using hybrid strategy."""

    # Separate workers by endpoint type
    cloud_pc_workers = [w for w in workers if w.endpoint_type == EndpointType.CLOUD_PC]
    container_workers = [w for w in workers if w.endpoint_type == EndpointType.CLI_CONTAINER]

    print(f"Provisioning {len(cloud_pc_workers)} Cloud PCs...")
    print(f"Provisioning {len(container_workers)} CLI containers...")

    # Provision Cloud PCs (parallel with concurrency limit)
    cloudpc_manager = Windows365CloudPCManager(graph_client, run_id)
    policy_id = await cloudpc_manager.ensure_provisioning_policy()

    # Provision in batches of 10 (Graph API rate limiting)
    batch_size = 10
    for i in range(0, len(cloud_pc_workers), batch_size):
        batch = cloud_pc_workers[i:i+batch_size]

        # Provision batch
        tasks = [
            cloudpc_manager.provision_cloud_pc(worker, policy_id)
            for worker in batch
        ]
        await asyncio.gather(*tasks)

        print(f"Provisioned batch {i//batch_size + 1}/{(len(cloud_pc_workers)-1)//batch_size + 1}")

    # Wait for all Cloud PCs to be ready
    print("Waiting for Cloud PCs to provision (up to 90 minutes)...")
    wait_tasks = [
        cloudpc_manager.wait_for_provisioning(worker)
        for worker in cloud_pc_workers
    ]
    results = await asyncio.gather(*wait_tasks)

    success_count = sum(results)
    print(f"{success_count}/{len(cloud_pc_workers)} Cloud PCs provisioned successfully")

    # Provision CLI containers (fast, parallel)
    print("Provisioning CLI containers...")
    # Container provisioning is fast and handled separately
    # See ARCHITECTURE.md for container provisioning details
```

---

## Monitoring and Status

### Provisioning Status Tracking

```python
# Check provisioning progress
cloud_pcs = await cloudpc_manager.list_cloud_pcs_for_run()

status_counts = {}
for pc in cloud_pcs:
    status = pc['status']
    status_counts[status] = status_counts.get(status, 0) + 1

print("Cloud PC Status:")
for status, count in status_counts.items():
    print(f"  {status}: {count}")
```

**Example output**:
```
Cloud PC Status:
  provisioned: 12
  provisioning: 2
  failed: 1
```

### Common Status Values

| Status        | Meaning                                    | Action                       |
| ------------- | ------------------------------------------ | ---------------------------- |
| `provisioning`| Cloud PC is being created                  | Wait (normal, up to 90 min)  |
| `provisioned` | Cloud PC is ready                          | Assign to worker agent       |
| `failed`      | Provisioning failed                        | Check logs, retry            |
| `error`       | Unexpected error                           | Contact support              |
| `deprovisioning` | Cloud PC is being deleted               | Wait for cleanup             |

---

## Cleanup and Resource Management

### Cleanup During Normal Shutdown

```python
# In KnowledgeWorkerOrchestrator cleanup phase
async def cleanup_cloud_pcs(run_id: str):
    """Delete all Cloud PCs for this run."""

    cloudpc_manager = Windows365CloudPCManager(graph_client, run_id)

    # List all Cloud PCs for this run
    cloud_pcs = await cloudpc_manager.list_cloud_pcs_for_run()

    print(f"Cleaning up {len(cloud_pcs)} Cloud PCs...")

    # Delete in parallel
    delete_tasks = [
        cloudpc_manager.delete_cloud_pc(pc['id'])
        for pc in cloud_pcs
    ]
    results = await asyncio.gather(*delete_tasks, return_exceptions=True)

    success_count = sum(1 for r in results if r is True)
    print(f"Deleted {success_count}/{len(cloud_pcs)} Cloud PCs")
```

### Force Cleanup (Tag-Based)

```python
# Tag-based cleanup for orphaned resources
async def force_cleanup_by_run_id(run_id: str):
    """Force delete all Cloud PCs for a run, even if orphaned."""

    # Query all Cloud PCs
    all_cloud_pcs = await graph_client.device_management.virtual_endpoint.cloud_p_cs.get()

    # Filter by naming pattern
    run_prefix = f"kw-{run_id[:8]}"
    matching_pcs = [
        pc for pc in (all_cloud_pcs.value or [])
        if pc.display_name and run_prefix in pc.display_name
    ]

    print(f"Found {len(matching_pcs)} Cloud PCs with run ID {run_id}")

    # Delete all
    for pc in matching_pcs:
        await cloudpc_manager.delete_cloud_pc(pc.id)
        print(f"Deleted: {pc.display_name}")
```

---

## Troubleshooting

### Provisioning Timeout

**Symptom**: `wait_for_provisioning()` returns False after 90 minutes.

**Causes**:
1. Network connectivity issues
2. Image not available in tenant
3. License quota exceeded
4. Azure AD join configuration error

**Solution**:
```python
# Check Cloud PC status manually
pc_info = await cloudpc_manager.get_cloud_pc(worker)

if pc_info:
    print(f"Current status: {pc_info['status']}")

    # Check Azure Portal for detailed error
    # Navigate to: Microsoft Intune > Devices > Windows 365 > All Cloud PCs
    # Select the PC and view "Provisioning details"
else:
    print("Cloud PC not found - provisioning may not have started")
```

### Graph API Permission Errors

**Symptom**: `403 Forbidden` or `Insufficient privileges` errors.

**Solution**:
```bash
# Verify app registration has required permissions
az ad app permission list --id <app-id>

# Required permissions:
# - CloudPC.ReadWrite.All
# - DeviceManagementManagedDevices.ReadWrite.All
# - Directory.ReadWrite.All

# Add missing permissions
az ad app permission add \
  --id <app-id> \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions <permission-id>=Role

# Grant admin consent
az ad app permission admin-consent --id <app-id>
```

### License Quota Exceeded

**Symptom**: Provisioning fails with "quota exceeded" message.

**Solution**:
1. Check available licenses in Microsoft 365 admin center
2. Reduce number of Cloud PC workers in configuration
3. Use hybrid strategy with more CLI containers

```python
# Adjust worker allocation
total_workers = 100
cloud_pc_ratio = 0.10  # Reduce from 0.20 to 0.10

cloud_pc_count = int(total_workers * cloud_pc_ratio)  # 10 instead of 20
container_count = total_workers - cloud_pc_count       # 90 instead of 80
```

### Cloud PC Not Appearing in Graph API

**Symptom**: `get_cloud_pc()` returns None immediately after provisioning.

**Cause**: Provisioning is asynchronous and PC object creation is delayed.

**Solution**:
```python
# Wait a few seconds before first status check
await cloudpc_manager.provision_cloud_pc(worker, policy_id)

# Give Graph API time to create object
await asyncio.sleep(30)

# Now start polling
success = await cloudpc_manager.wait_for_provisioning(worker)
```

---

## Cost Optimization

### SKU Selection

| SKU ID               | vCPU | RAM   | Storage | USD/Month* | Use Case                |
| -------------------- | ---- | ----- | ------- | ---------- | ----------------------- |
| `CPC_S_2C_4GB_64GB`  | 2    | 4 GB  | 64 GB   | $31        | General workers         |
| `CPC_M_4C_16GB_128GB`| 4    | 16 GB | 128 GB  | $66        | Power users             |
| `CPC_L_8C_32GB_256GB`| 8    | 32 GB | 256 GB  | $131       | Development workstations|

*Approximate pricing. See [Windows 365 pricing](https://www.microsoft.com/windows-365/enterprise/pricing) for current rates.

**Recommendation**: Use smallest SKU (`CPC_S_2C_4GB_64GB`) for knowledge worker simulations. Workers only perform M365 API calls and don't need high compute power.

### Cost Calculation Example

```python
# Cost analysis for 100-worker deployment

# Scenario 1: All Cloud PCs
all_cloudpc_cost = 100 * 31  # $3,100/month

# Scenario 2: Hybrid (15% Cloud PCs)
hybrid_cost = (15 * 31) + (85 * 2)  # $465 + $170 = $635/month

# Savings
savings = all_cloudpc_cost - hybrid_cost  # $2,465/month (79.5% reduction)

print(f"All Cloud PCs: ${all_cloudpc_cost:,}/month")
print(f"Hybrid strategy: ${hybrid_cost:,}/month")
print(f"Savings: ${savings:,}/month ({savings/all_cloudpc_cost*100:.1f}%)")
```

**Output**:
```
All Cloud PCs: $3,100/month
Hybrid strategy: $635/month
Savings: $2,465/month (79.5%)
```

---

## Best Practices

### 1. Pre-provision Policies

Create provisioning policies once and reuse across runs:

```python
# Create policy at tenant setup time
policy_id = await cloudpc_manager.ensure_provisioning_policy(
    display_name="HayMaker-Standard-Policy"
)

# Store in configuration
config["cloudpc_policy_id"] = policy_id

# Reuse in subsequent runs
await cloudpc_manager.provision_cloud_pc(worker, config["cloudpc_policy_id"])
```

### 2. Implement Timeout Handling

Don't block indefinitely on provisioning:

```python
# Use reasonable timeouts
success = await cloudpc_manager.wait_for_provisioning(
    worker=worker,
    timeout_minutes=90  # Maximum wait time
)

if not success:
    # Fall back to container endpoint
    logger.warning(f"Cloud PC provisioning timeout for {worker.worker_id}, using container")
    worker.endpoint_type = EndpointType.CLI_CONTAINER
    # Continue with container provisioning
```

### 3. Monitor Provisioning in Parallel

Don't provision serially:

```python
# Bad: Serial provisioning (slow)
for worker in cloud_pc_workers:
    await cloudpc_manager.provision_cloud_pc(worker, policy_id)
    await cloudpc_manager.wait_for_provisioning(worker)  # Blocks for 90 min each

# Good: Parallel provisioning (fast)
# Start all provisioning requests
provision_tasks = [
    cloudpc_manager.provision_cloud_pc(w, policy_id)
    for w in cloud_pc_workers
]
await asyncio.gather(*provision_tasks)

# Wait for all in parallel
wait_tasks = [
    cloudpc_manager.wait_for_provisioning(w)
    for w in cloud_pc_workers
]
results = await asyncio.gather(*wait_tasks)  # All wait simultaneously
```

### 4. Tag Resources for Cleanup

Always use run_id in naming for cleanup:

```python
# Naming includes run_id
cloudpc_name = f"kw-{run_id[:8]}-{random_suffix}"

# Enables cleanup by run_id
cloud_pcs = await list_all_cloud_pcs()
for pc in cloud_pcs:
    if f"kw-{run_id[:8]}" in pc.display_name:
        await delete_cloud_pc(pc.id)
```

### 5. Implement Health Checks

Verify Cloud PCs are functional before assigning work:

```python
async def verify_cloud_pc_ready(worker: WorkerIdentity) -> bool:
    """Verify Cloud PC is fully functional."""

    pc_info = await cloudpc_manager.get_cloud_pc(worker)

    if not pc_info or pc_info['status'] != 'provisioned':
        return False

    # Additional checks (if available via Graph API):
    # - Intune enrollment complete
    # - Network connectivity established
    # - User signed in at least once

    return True
```

---

## Related Documentation

- [Knowledge Worker Framework Architecture](./ARCHITECTURE.md) - Overall framework design
- [Endpoint Strategy](./ARCHITECTURE.md#6-endpoint-strategy) - Detailed endpoint comparison
- [Resource Tracking and Cleanup](./ARCHITECTURE.md#8-resource-tracking-and-cleanup) - Cleanup guarantees
- [Microsoft Graph Cloud PC API](https://learn.microsoft.com/graph/api/resources/cloudpc) - Official API reference

---

## Appendix: Graph API Endpoints Used

### Provisioning Policies

```http
# List policies
GET /deviceManagement/virtualEndpoint/provisioningPolicies

# Create policy
POST /deviceManagement/virtualEndpoint/provisioningPolicies
Content-Type: application/json

{
  "displayName": "HayMaker-KnowledgeWorker-Policy",
  "description": "Policy for HayMaker knowledge worker Cloud PCs",
  "provisioningType": "dedicated",
  "imageId": "MicrosoftWindowsDesktop_windows-ent-cpc_win11-22h2-ent-cpc-m365",
  "imageType": "gallery",
  "cloudPcNamingTemplate": "kw-%RAND:5%",
  "microsoftManagedDesktop": {
    "type": "starterManaged",
    "profile": "CPC_S_2C_4GB_64GB"
  },
  "domainJoinConfiguration": {
    "type": "azureADJoin"
  }
}

# Get policy
GET /deviceManagement/virtualEndpoint/provisioningPolicies/{id}

# Delete policy
DELETE /deviceManagement/virtualEndpoint/provisioningPolicies/{id}
```

### Cloud PCs

```http
# List Cloud PCs
GET /deviceManagement/virtualEndpoint/cloudPCs

# List Cloud PCs for user
GET /deviceManagement/virtualEndpoint/cloudPCs?$filter=userPrincipalName eq 'user@tenant.com'

# Get Cloud PC
GET /deviceManagement/virtualEndpoint/cloudPCs/{id}

# Delete Cloud PC
DELETE /deviceManagement/virtualEndpoint/cloudPCs/{id}

# Reprovision Cloud PC
POST /deviceManagement/virtualEndpoint/cloudPCs/{id}/reprovision
```

### Rate Limits

Microsoft Graph API rate limits for Cloud PC operations:

- **Read operations**: 600 requests per minute per app
- **Write operations**: 200 requests per minute per app
- **Provisioning operations**: 10 concurrent per tenant

**Recommendation**: Batch provisioning in groups of 10 with delays between batches.

```python
# Implement rate limiting
async def provision_with_rate_limit(
    workers: list[WorkerIdentity],
    policy_id: str,
    batch_size: int = 10,
    delay_seconds: int = 60,
):
    """Provision Cloud PCs with rate limiting."""

    for i in range(0, len(workers), batch_size):
        batch = workers[i:i+batch_size]

        # Provision batch
        tasks = [provision_cloud_pc(w, policy_id) for w in batch]
        await asyncio.gather(*tasks)

        # Delay between batches (except for last batch)
        if i + batch_size < len(workers):
            await asyncio.sleep(delay_seconds)
```
