---
title: "Windows VM Fallback Strategy for Knowledge Workers"
description: "Automatic cascading fallback from Cloud PC to Windows VM to Container for resilient endpoint provisioning"
last_updated: 2025-11-27
doc_type: explanation
owner: knowledge-worker-framework
related_issue: "#120"
---

# Windows VM Fallback Strategy

> **Feature**: Cascade fallback system ensuring endpoint provisioning always succeeds through Windows 365 Cloud PC → Azure Windows VM → CLI Container progression.

## Overview

The Knowledge Worker Framework implements a three-tier cascade fallback strategy for endpoint provisioning. When Windows 365 Cloud PC provisioning fails (due to quota limits, licensing, or service unavailability), the system automatically provisions an Azure Windows VM as a fallback. If VM provisioning also fails, the system falls back to a CLI container endpoint.

This ensures that knowledge worker simulations never fail due to infrastructure issues, while maintaining the richest possible telemetry for each worker.

### Computer Use Agent Support

Windows VMs provide identical desktop capabilities to Cloud PCs for Computer Use Agent testing, including:
- Browser automation (Chrome, Edge, Firefox)
- Desktop application interaction
- GUI-based workflows (Outlook Desktop, Teams Desktop)
- RDP-based agent connectivity

This fallback enables testing without requiring Windows 365 licenses.

## Quick Start

The cascade fallback is automatic and requires no code changes:

```python
from azure_haymaker.knowledge_worker import KnowledgeWorkerOrchestrator

# Initialize orchestrator
orchestrator = KnowledgeWorkerOrchestrator(
    subscription_id="your-subscription-id",
    resource_group="haymaker-rg",
    run_id="abc12345-def6-7890-ghij-klmnopqrstuv"
)

# Provision worker with automatic fallback
worker = await orchestrator.provision_worker(
    worker_id="kw-exec-001",
    display_name="Alex Executive",
    persona=WorkerPersona.EXECUTIVE,
    preferred_endpoint=EndpointType.CLOUD_PC  # Will fallback if unavailable
)

print(f"Provisioned: {worker.endpoint_type}")
# Output: Provisioned: EndpointType.WINDOWS_VM (fallback applied)
```

## Contents

- [Fallback Cascade Architecture](#fallback-cascade-architecture)
- [Windows VM Manager API](#windows-vm-manager-api)
- [Configuration](#configuration)
- [Usage Patterns](#usage-patterns)
- [Monitoring and Logging](#monitoring-and-logging)
- [Troubleshooting](#troubleshooting)
- [Cost Estimation](#cost-estimation)
- [Security Best Practices](#security-best-practices)
- [Examples](#examples)

---

## Fallback Cascade Architecture

### Cascade Decision Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ EndpointManager.provision_endpoint(worker)                      │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ Try Cloud PC Provisioning      │
         └────────────────────────────────┘
                          │
           ┌──────────────┴───────────────┐
           │ Success?                     │
           └──────────────┬───────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │ YES                                │ NO
        ▼                                    ▼
┌──────────────┐              ┌──────────────────────────────┐
│ Return       │              │ Log: Cloud PC failed         │
│ Cloud PC     │              │ Reason: [quota/timeout/etc]  │
└──────────────┘              └──────────────┬───────────────┘
                                              │
                              ┌───────────────▼───────────────┐
                              │ Try Windows VM Provisioning   │
                              └───────────────┬───────────────┘
                                              │
                               ┌──────────────┴───────────────┐
                               │ Success?                     │
                               └──────────────┬───────────────┘
                                              │
                        ┌─────────────────────┼─────────────────┐
                        │ YES                                    │ NO
                        ▼                                        ▼
                ┌──────────────┐              ┌──────────────────────────────┐
                │ Return       │              │ Log: Windows VM failed       │
                │ Windows VM   │              │ Reason: [quota/network/etc]  │
                └──────────────┘              └──────────────┬───────────────┘
                                                              │
                                              ┌───────────────▼───────────────┐
                                              │ Try Container Provisioning    │
                                              │ (Always succeeds)             │
                                              └───────────────┬───────────────┘
                                                              │
                                                              ▼
                                                      ┌──────────────┐
                                                      │ Return       │
                                                      │ Container    │
                                                      └──────────────┘
```

### Management Capabilities by Endpoint Type

| Endpoint Type   | Management Capabilities                              | Fallback Priority |
| --------------- | ---------------------------------------------------- | ----------------- |
| Cloud PC        | Fully managed, no VM maintenance, full desktop       | 1 (Preferred)     |
| Windows VM      | Self-managed, requires patching, full desktop        | 2 (Fallback)      |
| CLI Container   | API activity only (no desktop/browser)               | 3 (Final fallback)|

### When Each Fallback Triggers

**Cloud PC → Windows VM**:
- Windows 365 subscription not available (PRIMARY reason)
- Cloud PC quota exceeded (license limit)
- Provisioning timeout (>90 minutes)
- Graph API service unavailable
- Policy configuration error

**Windows VM → Container**:
- Azure subscription quota exceeded (vCPU/VM limits)
- Network security group misconfiguration
- Public IP allocation failure
- VM provisioning timeout (>30 minutes)

---

## Windows VM Manager API

### `WindowsVMManager`

Manages Azure Windows VM provisioning for knowledge worker endpoints.

#### Constructor

```python
WindowsVMManager(
    subscription_id: str,
    resource_group: str,
    location: str,
    run_id: str,
    vm_size: str = "Standard_D2s_v3"
)
```

**Parameters**:

| Parameter         | Type | Required | Description                        |
| ----------------- | ---- | -------- | ---------------------------------- |
| `subscription_id` | str  | Yes      | Azure subscription ID              |
| `resource_group`  | str  | Yes      | Resource group for VM resources    |
| `location`        | str  | Yes      | Azure region (e.g., "eastus")      |
| `run_id`          | str  | Yes      | HayMaker run ID for tagging        |
| `vm_size`         | str  | No       | VM size (default: Standard_D2s_v3) |

**Example**:

```python
from azure_haymaker.knowledge_worker.endpoints.windows_vm import WindowsVMManager

vm_manager = WindowsVMManager(
    subscription_id="12345678-1234-1234-1234-123456789abc",
    resource_group="haymaker-rg",
    location="eastus",
    run_id="abc12345-def6-7890-ghij-klmnopqrstuv"
)
```

#### Methods

##### `provision_vm()`

Provision a Windows Server VM for a worker.

```python
async def provision_vm(
    worker: WorkerIdentity
) -> dict[str, str]
```

**Parameters**:

| Parameter | Type           | Required | Description    |
| --------- | -------------- | -------- | -------------- |
| `worker`  | WorkerIdentity | Yes      | Worker identity|

**Returns**: `dict[str, str]` with keys:
- `vm_name`: Azure VM resource name
- `public_ip`: VM public IP address
- `admin_username`: Administrator username (always "azureuser")
- `admin_password`: Auto-generated secure password
- `rdp_port`: RDP port (always "3389")
- `winrm_http_port`: WinRM HTTP port (always "5985")
- `winrm_https_port`: WinRM HTTPS port (always "5986")

**Example**:

```python
from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity, WorkerPersona

worker = WorkerIdentity(
    worker_id="kw-exec-001",
    display_name="Alex Executive",
    persona=WorkerPersona.EXECUTIVE,
    endpoint_type=EndpointType.WINDOWS_VM,
    endpoint_id=""
)

vm_details = await vm_manager.provision_vm(worker)

print(f"VM Name: {vm_details['vm_name']}")
print(f"Public IP: {vm_details['public_ip']}")
print(f"RDP: {vm_details['admin_username']}@{vm_details['public_ip']}:3389")
print(f"Password: {vm_details['admin_password']}")
```

**Output**:
```
VM Name: kw-abc12345-exec-001-vm
Public IP: 20.12.34.56
RDP: azureuser@20.12.34.56:3389
Password: K9mP$x2Qr7!vN8zL4wT
```

**Provisioned Resources**:
- Virtual Machine (Standard_D2s_v3 - 2 vCPU, 8GB RAM)
- Network Interface
- Public IP Address
- Network Security Group (RDP + WinRM rules)
- OS Disk (128GB Standard SSD)

##### `delete_vm()`

Delete a Windows VM and all associated resources.

```python
async def delete_vm(
    vm_name: str
) -> bool
```

**Parameters**:

| Parameter | Type | Required | Description       |
| --------- | ---- | -------- | ----------------- |
| `vm_name` | str  | Yes      | Azure VM name     |

**Returns**: `bool` - True if deleted successfully

**Example**:

```python
success = await vm_manager.delete_vm("kw-abc12345-exec-001-vm")
# Returns: True
```

**Deleted Resources**:
- Virtual Machine
- OS Disk
- Network Interface
- Public IP Address
- Network Security Group

##### `get_vm_status()`

Get provisioning status of a VM.

```python
async def get_vm_status(
    vm_name: str
) -> str
```

**Parameters**:

| Parameter | Type | Required | Description   |
| --------- | ---- | -------- | ------------- |
| `vm_name` | str  | Yes      | Azure VM name |

**Returns**: `str` - Provisioning state

**Example**:

```python
status = await vm_manager.get_vm_status("kw-abc12345-exec-001-vm")
print(f"Status: {status}")
# Output: Status: Succeeded
```

**Possible Status Values**:

| Status       | Meaning                          | Action                      |
| ------------ | -------------------------------- | --------------------------- |
| `Creating`   | VM is being provisioned          | Wait (5-10 minutes typical) |
| `Succeeded`  | VM is ready                      | Proceed with worker setup   |
| `Failed`     | Provisioning failed              | Check error, retry, or fallback |
| `Deleting`   | VM is being deleted              | Wait for cleanup            |
| `NotFound`   | VM does not exist                | Check VM name               |

##### `list_vms_for_run()`

List all VMs for the current run.

```python
async def list_vms_for_run() -> list[dict[str, str]]
```

**Returns**: `list[dict[str, str]]` - List of VM details dictionaries

**Example**:

```python
vms = await vm_manager.list_vms_for_run()

for vm in vms:
    print(f"{vm['vm_name']}: {vm['public_ip']} ({vm['status']})")

# Output:
# kw-abc12345-exec-001-vm: 20.12.34.56 (Succeeded)
# kw-abc12345-exec-002-vm: 20.12.34.57 (Creating)
# kw-abc12345-admin-001-vm: 20.12.34.58 (Succeeded)
```

##### `verify_computer_use_ready()`

Verify that VM is ready for Computer Use Agent connectivity.

```python
async def verify_computer_use_ready(
    vm_details: dict[str, str]
) -> dict[str, bool]
```

**Parameters**:

| Parameter    | Type          | Required | Description         |
| ------------ | ------------- | -------- | ------------------- |
| `vm_details` | dict[str, str]| Yes      | VM details from provision_vm() |

**Returns**: `dict[str, bool]` with verification results:
- `rdp_accessible`: RDP port (3389) is reachable
- `edge_installed`: Microsoft Edge browser available
- `chrome_installed`: Google Chrome browser available
- `desktop_ready`: Desktop Experience GUI available

**Example**:

```python
vm_details = await vm_manager.provision_vm(worker)

# Wait for Computer Use Agent readiness
readiness = await vm_manager.verify_computer_use_ready(vm_details)

print(f"Computer Use Readiness:")
print(f"  RDP Accessible: {readiness['rdp_accessible']}")
print(f"  Edge Installed: {readiness['edge_installed']}")
print(f"  Chrome Installed: {readiness['chrome_installed']}")
print(f"  Desktop Ready: {readiness['desktop_ready']}")

if all(readiness.values()):
    print("✅ VM ready for Computer Use Agent")
else:
    print("⚠️  VM not fully ready, waiting...")
```

**Output**:
```
Computer Use Readiness:
  RDP Accessible: True
  Edge Installed: True
  Chrome Installed: True
  Desktop Ready: True
✅ VM ready for Computer Use Agent
```

---

## Configuration

### VM Specifications

Windows VMs are provisioned with the following default configuration:

| Setting               | Value                                    | Notes                            |
| --------------------- | ---------------------------------------- | -------------------------------- |
| **VM Size**           | `Standard_D2s_v3`                        | 2 vCPU, 8GB RAM                  |
| **OS Image**          | Windows Server 2022 Datacenter           | Desktop Experience edition       |
| **OS Disk**           | 128GB Standard SSD                       | Sufficient for logs and telemetry|
| **Admin Username**    | `azureuser`                              | Fixed for consistency            |
| **Admin Password**    | Auto-generated (20 chars)                | Secure random password           |
| **Networking**        | Public IP + NSG                          | Internet-accessible              |
| **Ports**             | 3389 (RDP), 5985 (WinRM HTTP), 5986 (WinRM HTTPS) | For remote management |

### Browser Configuration

Windows VMs are provisioned with:
- Microsoft Edge (pre-installed with Windows Server 2022)
- Chrome (installed via custom script extension)
- Playwright dependencies for browser automation

### Network Security Group Rules

```python
# NSG rules automatically created
nsg_rules = [
    {
        "name": "AllowRDP",
        "priority": 1000,
        "protocol": "Tcp",
        "source": "*",
        "destination_port": "3389",
        "access": "Allow"
    },
    {
        "name": "AllowWinRMHTTP",
        "priority": 1010,
        "protocol": "Tcp",
        "source": "*",
        "destination_port": "5985",
        "access": "Allow"
    },
    {
        "name": "AllowWinRMHTTPS",
        "priority": 1020,
        "protocol": "Tcp",
        "source": "*",
        "destination_port": "5986",
        "access": "Allow"
    }
]
```

**Security Note**: By default, RDP and WinRM are open to the internet for development convenience. For production, restrict source IPs:

```python
# Production NSG configuration
vm_manager = WindowsVMManager(
    subscription_id=subscription_id,
    resource_group=resource_group,
    location=location,
    run_id=run_id,
    allowed_source_ips=["203.0.113.0/24"]  # Your organization's IP range
)
```

### Resource Tagging

All VM resources are tagged for cleanup:

```python
tags = {
    "haymaker_run_id": "abc12345-def6-7890-ghij-klmnopqrstuv",
    "haymaker_scenario": "knowledge-worker",
    "worker_id": "kw-exec-001",
    "endpoint_type": "windows_vm",
    "managed_by": "azure-haymaker",
    "auto_cleanup": "true"
}
```

---

## Usage Patterns

### Pattern 1: Automatic Fallback (Recommended)

Let the EndpointManager handle fallback automatically:

```python
from azure_haymaker.knowledge_worker import EndpointManager

endpoint_mgr = EndpointManager(
    subscription_id=subscription_id,
    resource_group=resource_group,
    location=location,
    run_id=run_id
)

# Attempt Cloud PC, fallback to VM if needed
worker = await endpoint_mgr.provision_endpoint(
    worker_identity=worker,
    preferred_type=EndpointType.CLOUD_PC
)

# Check what was actually provisioned
print(f"Provisioned endpoint: {worker.endpoint_type}")
# Output: Provisioned endpoint: EndpointType.WINDOWS_VM (fallback applied)
```

### Pattern 2: Explicit VM Provisioning

Directly provision a Windows VM without attempting Cloud PC:

```python
from azure_haymaker.knowledge_worker.endpoints.windows_vm import WindowsVMManager

vm_manager = WindowsVMManager(
    subscription_id=subscription_id,
    resource_group=resource_group,
    location=location,
    run_id=run_id
)

# Provision VM directly
vm_details = await vm_manager.provision_vm(worker)

# Update worker with VM details
worker.endpoint_type = EndpointType.WINDOWS_VM
worker.endpoint_id = vm_details['vm_name']
worker.endpoint_metadata = vm_details
```

### Pattern 3: Batch Provisioning with Fallback

Provision multiple workers with automatic fallback:

```python
async def provision_workers_with_fallback(
    workers: list[WorkerIdentity],
    endpoint_mgr: EndpointManager
) -> dict[EndpointType, int]:
    """Provision workers with automatic fallback tracking."""

    endpoint_counts = {
        EndpointType.CLOUD_PC: 0,
        EndpointType.WINDOWS_VM: 0,
        EndpointType.CLI_CONTAINER: 0
    }

    # Provision all workers in parallel
    provision_tasks = [
        endpoint_mgr.provision_endpoint(w, EndpointType.CLOUD_PC)
        for w in workers
    ]

    provisioned_workers = await asyncio.gather(*provision_tasks)

    # Count endpoint types
    for worker in provisioned_workers:
        endpoint_counts[worker.endpoint_type] += 1

    # Report fallback statistics
    print(f"Endpoint Distribution:")
    print(f"  Cloud PCs: {endpoint_counts[EndpointType.CLOUD_PC]}")
    print(f"  Windows VMs: {endpoint_counts[EndpointType.WINDOWS_VM]}")
    print(f"  Containers: {endpoint_counts[EndpointType.CLI_CONTAINER]}")

    return endpoint_counts

# Usage
endpoint_distribution = await provision_workers_with_fallback(
    workers=all_workers,
    endpoint_mgr=endpoint_manager
)
```

**Example Output**:
```
Endpoint Distribution:
  Cloud PCs: 12
  Windows VMs: 3
  Containers: 0
```

### Pattern 4: Testing Windows VM Provisioning

Test VM provisioning in isolation:

```python
async def test_vm_provisioning():
    """Test VM provisioning and connectivity."""

    from azure_haymaker.knowledge_worker.endpoints.windows_vm import WindowsVMManager

    vm_manager = WindowsVMManager(
        subscription_id=subscription_id,
        resource_group="haymaker-test-rg",
        location="eastus",
        run_id="test-run-12345"
    )

    # Create test worker
    test_worker = WorkerIdentity(
        worker_id="test-worker-001",
        display_name="Test Worker",
        persona=WorkerPersona.EXECUTIVE,
        endpoint_type=EndpointType.WINDOWS_VM,
        endpoint_id=""
    )

    # Provision VM
    print("Provisioning VM...")
    vm_details = await vm_manager.provision_vm(test_worker)

    print(f"VM provisioned successfully!")
    print(f"  Name: {vm_details['vm_name']}")
    print(f"  Public IP: {vm_details['public_ip']}")
    print(f"  Username: {vm_details['admin_username']}")
    print(f"  Password: {vm_details['admin_password']}")

    # Wait for VM to be ready
    print("Waiting for VM to be ready...")
    while True:
        status = await vm_manager.get_vm_status(vm_details['vm_name'])
        print(f"  Status: {status}")

        if status == "Succeeded":
            break
        elif status == "Failed":
            raise Exception("VM provisioning failed")

        await asyncio.sleep(30)

    print("VM is ready for testing!")

    # Test RDP connectivity (requires rdp client)
    print(f"\nTest RDP connection:")
    print(f"  rdp://{vm_details['admin_username']}@{vm_details['public_ip']}:3389")

    # Cleanup
    print("\nCleaning up...")
    await vm_manager.delete_vm(vm_details['vm_name'])
    print("VM deleted successfully")

# Run test
await test_vm_provisioning()
```

---

## Monitoring and Logging

### Fallback Decision Logging

Every fallback decision is logged with reason:

```python
# Example logs from EndpointManager
2025-11-27 10:15:23 INFO [kw-exec-001] Attempting Cloud PC provisioning
2025-11-27 10:15:45 WARN [kw-exec-001] Cloud PC provisioning failed: License quota exceeded (15/15 used)
2025-11-27 10:15:45 INFO [kw-exec-001] Falling back to Windows VM provisioning
2025-11-27 10:18:32 INFO [kw-exec-001] Windows VM provisioned successfully: kw-abc12345-exec-001-vm
2025-11-27 10:18:32 INFO [kw-exec-001] Endpoint: EndpointType.WINDOWS_VM (fallback level: 1)
```

### Fallback Metrics

Track fallback statistics for monitoring:

```python
from azure_haymaker.knowledge_worker.telemetry import FallbackMetrics

# Collect fallback metrics
metrics = FallbackMetrics(run_id=run_id)

# After provisioning all workers
fallback_stats = metrics.get_fallback_statistics()

print(f"Fallback Statistics:")
print(f"  Total workers: {fallback_stats['total_workers']}")
print(f"  Cloud PC success: {fallback_stats['cloud_pc_success']} ({fallback_stats['cloud_pc_success_rate']:.1%})")
print(f"  VM fallback: {fallback_stats['vm_fallback']} ({fallback_stats['vm_fallback_rate']:.1%})")
print(f"  Container fallback: {fallback_stats['container_fallback']} ({fallback_stats['container_fallback_rate']:.1%})")
print(f"\nFallback Reasons:")
for reason, count in fallback_stats['fallback_reasons'].items():
    print(f"  {reason}: {count}")
```

**Example Output**:
```
Fallback Statistics:
  Total workers: 15
  Cloud PC success: 12 (80.0%)
  VM fallback: 3 (20.0%)
  Container fallback: 0 (0.0%)

Fallback Reasons:
  Cloud PC quota exceeded: 3
```

### Azure Monitor Integration

VM provisioning emits Application Insights events:

```python
# Custom events logged to Application Insights
{
  "event_name": "WindowsVMProvisioned",
  "properties": {
    "run_id": "abc12345-def6-7890-ghij-klmnopqrstuv",
    "worker_id": "kw-exec-001",
    "vm_name": "kw-abc12345-exec-001-vm",
    "vm_size": "Standard_B2s",
    "location": "eastus",
    "provisioning_duration_seconds": 187,
    "fallback_from": "cloud_pc",
    "fallback_reason": "quota_exceeded"
  }
}
```

**Query in Application Insights**:
```kusto
customEvents
| where name == "WindowsVMProvisioned"
| where timestamp > ago(1d)
| summarize count() by tostring(customDimensions.fallback_reason)
| order by count_ desc
```

---

## Troubleshooting

### Issue: VM Provisioning Timeout

**Symptom**: VM status stuck in "Creating" state for >30 minutes.

**Causes**:
1. Azure capacity issues in region
2. Subscription quota reached
3. Network configuration error

**Solution**:

```python
# Check VM status
status = await vm_manager.get_vm_status(vm_name)
print(f"Current status: {status}")

# If stuck, check Azure Portal for detailed error:
# Navigate to: Resource Group > VM > Activity Log

# Try alternative region
vm_manager_backup = WindowsVMManager(
    subscription_id=subscription_id,
    resource_group=resource_group,
    location="westus2",  # Alternative region
    run_id=run_id
)

vm_details = await vm_manager_backup.provision_vm(worker)
```

### Issue: RDP Connection Refused

**Symptom**: Cannot connect to VM via RDP after provisioning.

**Causes**:
1. NSG rules not yet applied
2. Windows Firewall blocking RDP
3. VM still booting

**Solution**:

```python
# Wait for VM to be fully ready (not just "Succeeded" status)
import asyncio

async def wait_for_rdp_ready(vm_details: dict, timeout_minutes: int = 10):
    """Wait for RDP port to be accessible."""

    import socket

    start_time = asyncio.get_event_loop().time()
    timeout_seconds = timeout_minutes * 60

    while True:
        try:
            # Test TCP connection to RDP port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((vm_details['public_ip'], 3389))
            sock.close()

            if result == 0:
                print("RDP port is now accessible")
                return True

        except Exception as e:
            pass

        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout_seconds:
            print("Timeout waiting for RDP port")
            return False

        await asyncio.sleep(15)

# Usage
vm_details = await vm_manager.provision_vm(worker)
rdp_ready = await wait_for_rdp_ready(vm_details)

if rdp_ready:
    print(f"Connect via: rdp://{vm_details['admin_username']}@{vm_details['public_ip']}:3389")
else:
    print("RDP connection not available, check NSG and VM status")
```

### Issue: Quota Exceeded

**Symptom**: VM provisioning fails with "quota exceeded" error.

**Causes**:
1. Subscription vCPU quota reached
2. Regional capacity limit
3. Too many public IPs allocated

**Solution**:

```bash
# Check current quota usage
az vm list-usage --location eastus --query "[?name.value=='cores'].{Name:name.localizedValue, Current:currentValue, Limit:limit}" -o table

# Output:
# Name                     Current  Limit
# -----------------------  -------  -----
# Total Regional vCPUs     48       50
# Standard BS Family vCPUs 10       20

# Request quota increase
az support tickets create \
  --ticket-name "increase-vcpu-quota" \
  --title "Increase vCPU quota for B-series VMs" \
  --description "Need additional 20 vCPUs for knowledge worker simulations" \
  --severity "minimal" \
  --problem-classification "/providers/Microsoft.Support/services/quota/problemClassifications/cores-or-vcpus"
```

**Temporary workaround**:
```python
# Use smaller VM size temporarily
vm_manager = WindowsVMManager(
    subscription_id=subscription_id,
    resource_group=resource_group,
    location=location,
    run_id=run_id,
    vm_size="Standard_B1s"  # 1 vCPU instead of 2
)
```

### Issue: Network Security Group Conflicts

**Symptom**: VM provisions successfully but RDP/WinRM ports not accessible.

**Causes**:
1. Existing NSG with conflicting rules
2. Subnet-level NSG blocking traffic
3. Azure Firewall or NVA blocking ports

**Solution**:

```python
# Verify NSG rules
from azure.mgmt.network import NetworkManagementClient
from azure.identity import DefaultAzureCredential

network_client = NetworkManagementClient(
    credential=DefaultAzureCredential(),
    subscription_id=subscription_id
)

# Get NSG for VM
nsg_name = f"{vm_name}-nsg"
nsg = network_client.network_security_groups.get(
    resource_group_name=resource_group,
    network_security_group_name=nsg_name
)

# Check security rules
print("Security Rules:")
for rule in nsg.security_rules:
    print(f"  {rule.name}: {rule.protocol} {rule.destination_port_range} -> {rule.access}")

# Output should include:
# AllowRDP: Tcp 3389 -> Allow
# AllowWinRMHTTP: Tcp 5985 -> Allow
# AllowWinRMHTTPS: Tcp 5986 -> Allow
```

### Issue: Password Not Working

**Symptom**: Generated password doesn't work for RDP login.

**Causes**:
1. Password copied incorrectly (special characters)
2. VM password policy rejection
3. Copy-paste encoding issues

**Solution**:

```python
# Reset VM password via Azure API
from azure.mgmt.compute import ComputeManagementClient

compute_client = ComputeManagementClient(
    credential=DefaultAzureCredential(),
    subscription_id=subscription_id
)

# Generate new password
import secrets
import string

def generate_secure_password(length: int = 20) -> str:
    """Generate secure password meeting Azure requirements."""

    # Ensure password has: uppercase, lowercase, digit, special char
    chars = string.ascii_letters + string.digits + "!@#$%^&*"

    while True:
        password = ''.join(secrets.choice(chars) for _ in range(length))

        # Validate requirements
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*" for c in password)

        if has_upper and has_lower and has_digit and has_special:
            return password

new_password = generate_secure_password()

# Reset password (requires VM running)
compute_client.virtual_machines.begin_run_command(
    resource_group_name=resource_group,
    vm_name=vm_name,
    parameters={
        "command_id": "RunPowerShellScript",
        "script": [
            f"net user azureuser {new_password}"
        ]
    }
).result()

print(f"New password: {new_password}")
```

---

## Cost Estimation

### VM Pricing

**Standard_D2s_v3 Pricing** (Pay-as-you-go rates):

| Component        | Specification      | Cost (USD/hour)* | Cost (USD/month)* |
| ---------------- | ------------------ | ---------------- | ----------------- |
| VM Compute       | 2 vCPU, 8GB RAM    | $0.096           | $70.08            |
| OS Disk          | 128GB Standard SSD | $0.0075          | $5.48             |
| Public IP        | Basic SKU          | $0.0036          | $2.63             |
| **Total**        | -                  | **$0.105**       | **$78.19**        |

*Approximate pricing for East US region. See [Azure pricing calculator](https://azure.microsoft.com/pricing/calculator/) for current rates.

### Cost Comparison

**Scenario**: 15 workers for 30 days continuous operation

| Strategy                   | Endpoint Mix        | Monthly Cost  | Notes                    |
| -------------------------- | ------------------- | ------------- | ------------------------ |
| All Cloud PCs              | 15 Cloud PCs        | $465          | Richest telemetry        |
| **Hybrid (VM fallback)**   | 12 Cloud PCs, 3 VMs | **$606**      | **Automatic resilience** |
| All Windows VMs            | 15 VMs              | $1,173        | No Cloud PC dependencies |
| Hybrid (container fallback)| 12 Cloud PCs, 3 containers | $471   | Lowest cost, reduced telemetry |

**Recommendation**: Accept the $141/month cost increase (30% higher than all Cloud PCs) for automatic fallback resilience. This prevents simulation failures when Cloud PC quota is exhausted.

### Cost Optimization Strategies

#### 1. Deallocate VMs During Idle Periods

```python
# Deallocate VM when worker is idle (stops compute charges, keeps disk)
async def deallocate_idle_vm(vm_name: str):
    """Deallocate VM to save costs during idle periods."""

    from azure.mgmt.compute import ComputeManagementClient
    from azure.identity import DefaultAzureCredential

    compute_client = ComputeManagementClient(
        credential=DefaultAzureCredential(),
        subscription_id=subscription_id
    )

    # Deallocate VM (async operation)
    compute_client.virtual_machines.begin_deallocate(
        resource_group_name=resource_group,
        vm_name=vm_name
    ).result()

    print(f"VM {vm_name} deallocated (saving ~$70/month)")

# Restart when needed
async def start_vm(vm_name: str):
    """Start previously deallocated VM."""

    compute_client.virtual_machines.begin_start(
        resource_group_name=resource_group,
        vm_name=vm_name
    ).result()

    print(f"VM {vm_name} started")
```

**Savings**: ~$70/month per deallocated VM (compute charges stopped)

#### 2. Use Spot VMs for Non-Critical Workers

```python
# Provision Spot VM (up to 90% discount, but can be evicted)
vm_manager = WindowsVMManager(
    subscription_id=subscription_id,
    resource_group=resource_group,
    location=location,
    run_id=run_id,
    use_spot_instances=True,  # Enable spot pricing
    spot_max_price=0.02       # Maximum hourly price (USD)
)

vm_details = await vm_manager.provision_vm(worker)
```

**Savings**: ~70-90% discount vs. pay-as-you-go pricing
**Risk**: VM can be evicted with 30-second notice if capacity needed

#### 3. Schedule VM Usage

```python
# Only run VMs during business hours (8 hours/day = 33% utilization)
import schedule
import asyncio

async def scheduled_vm_lifecycle():
    """Start VMs at 9 AM, stop at 5 PM daily."""

    # Morning: Start all VMs
    schedule.every().day.at("09:00").do(lambda: asyncio.create_task(start_all_vms()))

    # Evening: Deallocate all VMs
    schedule.every().day.at("17:00").do(lambda: asyncio.create_task(stop_all_vms()))

    while True:
        schedule.run_pending()
        await asyncio.sleep(60)

async def start_all_vms():
    vms = await vm_manager.list_vms_for_run()
    for vm in vms:
        await start_vm(vm['vm_name'])

async def stop_all_vms():
    vms = await vm_manager.list_vms_for_run()
    for vm in vms:
        await deallocate_idle_vm(vm['vm_name'])
```

**Savings**: ~$47/month per VM (67% reduction for 8-hour daily usage)

---

## Security Best Practices

### 1. Restrict Remote Access by Source IP

**Problem**: Default NSG allows RDP/WinRM from any IP (0.0.0.0/0).

**Solution**: Restrict to known IP ranges.

```python
vm_manager = WindowsVMManager(
    subscription_id=subscription_id,
    resource_group=resource_group,
    location=location,
    run_id=run_id,
    allowed_source_ips=[
        "203.0.113.0/24",    # Corporate network
        "198.51.100.50/32"   # VPN gateway
    ]
)
```

### 2. Store Credentials in Azure Key Vault

**Problem**: VM passwords logged or stored in plaintext.

**Solution**: Store in Key Vault, retrieve as needed.

```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

async def store_vm_credentials(vm_details: dict):
    """Store VM credentials securely in Key Vault."""

    kv_client = SecretClient(
        vault_url="https://haymaker-kv.vault.azure.net/",
        credential=DefaultAzureCredential()
    )

    # Store password
    secret_name = f"vm-{vm_details['vm_name']}-password"
    kv_client.set_secret(secret_name, vm_details['admin_password'])

    print(f"Password stored in Key Vault: {secret_name}")

    # Don't log password
    vm_details_safe = vm_details.copy()
    vm_details_safe['admin_password'] = "***REDACTED***"

    return vm_details_safe

# Usage
vm_details = await vm_manager.provision_vm(worker)
vm_details_safe = await store_vm_credentials(vm_details)

# Only log safe details
logger.info(f"VM provisioned: {vm_details_safe}")
```

### 3. Enable Azure Disk Encryption

```python
# Enable disk encryption for VM OS disk
from azure.mgmt.compute.models import DiskEncryptionSettings

vm_manager = WindowsVMManager(
    subscription_id=subscription_id,
    resource_group=resource_group,
    location=location,
    run_id=run_id,
    enable_disk_encryption=True,
    disk_encryption_key_vault="https://haymaker-kv.vault.azure.net/"
)
```

### 4. Enable Just-In-Time (JIT) VM Access

```python
# Enable JIT access (requires Azure Security Center Standard tier)
from azure.mgmt.security import SecurityCenter

security_client = SecurityCenter(
    credential=DefaultAzureCredential(),
    subscription_id=subscription_id,
    asc_location="eastus"
)

# Configure JIT policy
jit_policy = {
    "virtualMachines": [{
        "id": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines/{vm_name}",
        "ports": [
            {
                "number": 3389,
                "protocol": "Tcp",
                "allowedSourceAddressPrefix": "*",
                "maxRequestAccessDuration": "PT3H"  # 3 hours max
            }
        ]
    }]
}

security_client.jit_network_access_policies.create_or_update(
    resource_group_name=resource_group,
    jit_network_access_policy_name="haymaker-jit-policy",
    body=jit_policy
)
```

### 5. Rotate Credentials Regularly

```python
async def rotate_vm_password(vm_name: str) -> str:
    """Rotate VM administrator password."""

    from azure.mgmt.compute import ComputeManagementClient

    compute_client = ComputeManagementClient(
        credential=DefaultAzureCredential(),
        subscription_id=subscription_id
    )

    # Generate new password
    new_password = generate_secure_password()

    # Update VM password
    compute_client.virtual_machines.begin_run_command(
        resource_group_name=resource_group,
        vm_name=vm_name,
        parameters={
            "command_id": "RunPowerShellScript",
            "script": [
                f"net user azureuser {new_password}"
            ]
        }
    ).result()

    # Store in Key Vault
    kv_client = SecretClient(
        vault_url="https://haymaker-kv.vault.azure.net/",
        credential=DefaultAzureCredential()
    )

    secret_name = f"vm-{vm_name}-password"
    kv_client.set_secret(secret_name, new_password)

    # Add version tag
    kv_client.update_secret_properties(
        secret_name,
        tags={
            "rotated_at": datetime.utcnow().isoformat(),
            "rotation_reason": "scheduled_rotation"
        }
    )

    logger.info(f"Password rotated for VM: {vm_name}")

    return new_password

# Schedule rotation every 90 days
schedule.every(90).days.do(lambda: asyncio.create_task(rotate_vm_password(vm_name)))
```

---

## Examples

### Example 1: Complete Worker Provisioning with Fallback

```python
from azure_haymaker.knowledge_worker import KnowledgeWorkerOrchestrator
from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity, WorkerPersona, EndpointType

async def provision_worker_with_fallback():
    """Provision a worker with automatic Cloud PC → VM → Container fallback."""

    # Initialize orchestrator
    orchestrator = KnowledgeWorkerOrchestrator(
        subscription_id="12345678-1234-1234-1234-123456789abc",
        resource_group="haymaker-rg",
        location="eastus",
        run_id="abc12345-def6-7890-ghij-klmnopqrstuv"
    )

    # Define worker
    worker = WorkerIdentity(
        worker_id="kw-exec-001",
        display_name="Alex Executive",
        user_principal_name="alex.executive@contoso.onmicrosoft.com",
        department="executive",
        persona=WorkerPersona.EXECUTIVE,
        endpoint_type=EndpointType.CLOUD_PC,  # Preferred
        endpoint_id=""
    )

    # Provision with automatic fallback
    print(f"Provisioning worker: {worker.display_name}")
    provisioned_worker = await orchestrator.provision_worker(worker)

    print(f"\nProvisioning Result:")
    print(f"  Worker ID: {provisioned_worker.worker_id}")
    print(f"  Endpoint Type: {provisioned_worker.endpoint_type}")
    print(f"  Endpoint ID: {provisioned_worker.endpoint_id}")

    # Check if fallback occurred
    if provisioned_worker.endpoint_type == EndpointType.WINDOWS_VM:
        print(f"\n⚠️  Fallback applied: Cloud PC → Windows VM")
        print(f"  Reason: {provisioned_worker.endpoint_metadata.get('fallback_reason')}")

        # Get VM connection details
        vm_details = provisioned_worker.endpoint_metadata
        print(f"\n🔌 Connection Details:")
        print(f"  RDP: {vm_details['admin_username']}@{vm_details['public_ip']}:3389")
        print(f"  Password: {vm_details['admin_password']}")
        print(f"  WinRM: http://{vm_details['public_ip']}:5985")

    elif provisioned_worker.endpoint_type == EndpointType.CLI_CONTAINER:
        print(f"\n⚠️  Double fallback applied: Cloud PC → Windows VM → Container")
        print(f"  Reason: {provisioned_worker.endpoint_metadata.get('fallback_reason')}")

    else:
        print(f"\n✅ Cloud PC provisioned successfully (no fallback)")

    return provisioned_worker

# Run provisioning
worker = await provision_worker_with_fallback()
```

**Example Output (VM Fallback)**:
```
Provisioning worker: Alex Executive

INFO [kw-exec-001] Attempting Cloud PC provisioning
WARN [kw-exec-001] Cloud PC provisioning failed: License quota exceeded (15/15 used)
INFO [kw-exec-001] Falling back to Windows VM provisioning
INFO [kw-exec-001] Windows VM provisioned successfully: kw-abc12345-exec-001-vm

Provisioning Result:
  Worker ID: kw-exec-001
  Endpoint Type: EndpointType.WINDOWS_VM
  Endpoint ID: kw-abc12345-exec-001-vm

⚠️  Fallback applied: Cloud PC → Windows VM
  Reason: cloud_pc_quota_exceeded

🔌 Connection Details:
  RDP: azureuser@20.12.34.56:3389
  Password: K9mP$x2Qr7!vN8zL4wT
  WinRM: http://20.12.34.56:5985
```

### Example 2: Batch Provisioning with Fallback Statistics

```python
async def batch_provision_with_statistics():
    """Provision multiple workers and report fallback statistics."""

    from azure_haymaker.knowledge_worker import EndpointManager
    from azure_haymaker.knowledge_worker.telemetry import FallbackMetrics

    # Initialize endpoint manager
    endpoint_mgr = EndpointManager(
        subscription_id=subscription_id,
        resource_group=resource_group,
        location=location,
        run_id=run_id
    )

    # Define 20 workers
    workers = []
    for i in range(1, 21):
        persona = WorkerPersona.EXECUTIVE if i <= 5 else WorkerPersona.EMPLOYEE
        worker = WorkerIdentity(
            worker_id=f"kw-worker-{i:03d}",
            display_name=f"Worker {i}",
            user_principal_name=f"worker{i}@contoso.onmicrosoft.com",
            persona=persona,
            endpoint_type=EndpointType.CLOUD_PC,
            endpoint_id=""
        )
        workers.append(worker)

    # Provision all workers in parallel
    print(f"Provisioning {len(workers)} workers with automatic fallback...")

    provision_tasks = [
        endpoint_mgr.provision_endpoint(w, EndpointType.CLOUD_PC)
        for w in workers
    ]

    provisioned_workers = await asyncio.gather(*provision_tasks)

    # Collect statistics
    metrics = FallbackMetrics(run_id=run_id)
    stats = metrics.calculate_statistics(provisioned_workers)

    # Report results
    print(f"\n📊 Provisioning Statistics:")
    print(f"  Total workers: {stats['total_workers']}")
    print(f"  Cloud PC success: {stats['cloud_pc_success']} ({stats['cloud_pc_success_rate']:.1%})")
    print(f"  VM fallback: {stats['vm_fallback']} ({stats['vm_fallback_rate']:.1%})")
    print(f"  Container fallback: {stats['container_fallback']} ({stats['container_fallback_rate']:.1%})")

    print(f"\n📈 Fallback Reasons:")
    for reason, count in stats['fallback_reasons'].items():
        print(f"  {reason}: {count}")

    # Cost estimation
    cloud_pc_cost = stats['cloud_pc_success'] * 31  # $31/month
    vm_cost = stats['vm_fallback'] * 78.19  # $78.19/month
    container_cost = stats['container_fallback'] * 2  # $2/month
    total_cost = cloud_pc_cost + vm_cost + container_cost

    print(f"\n💰 Estimated Monthly Cost:")
    print(f"  Cloud PCs: ${cloud_pc_cost:.2f}")
    print(f"  Windows VMs: ${vm_cost:.2f}")
    print(f"  Containers: ${container_cost:.2f}")
    print(f"  Total: ${total_cost:.2f}")

    return provisioned_workers

# Run batch provisioning
workers = await batch_provision_with_statistics()
```

**Example Output**:
```
Provisioning 20 workers with automatic fallback...

INFO [batch] Starting parallel provisioning of 20 workers
INFO [batch] Batch 1/2: 10 workers
INFO [batch] Batch 2/2: 10 workers
WARN [kw-worker-016] Cloud PC provisioning failed: License quota exceeded
INFO [kw-worker-016] Falling back to Windows VM provisioning
WARN [kw-worker-017] Cloud PC provisioning failed: License quota exceeded
INFO [kw-worker-017] Falling back to Windows VM provisioning
WARN [kw-worker-018] Cloud PC provisioning failed: License quota exceeded
INFO [kw-worker-018] Falling back to Windows VM provisioning
INFO [batch] Provisioning complete: 17 Cloud PCs, 3 Windows VMs, 0 Containers

📊 Provisioning Statistics:
  Total workers: 20
  Cloud PC success: 17 (85.0%)
  VM fallback: 3 (15.0%)
  Container fallback: 0 (0.0%)

📈 Fallback Reasons:
  cloud_pc_quota_exceeded: 3

💰 Estimated Monthly Cost:
  Cloud PCs: $527.00
  Windows VMs: $234.57
  Containers: $0.00
  Total: $761.57
```

### Example 3: Cleanup All Endpoints

```python
async def cleanup_all_endpoints():
    """Clean up all endpoints (Cloud PCs, VMs, containers) for a run."""

    from azure_haymaker.knowledge_worker import EndpointManager

    endpoint_mgr = EndpointManager(
        subscription_id=subscription_id,
        resource_group=resource_group,
        location=location,
        run_id=run_id
    )

    print(f"Cleaning up all endpoints for run: {run_id}")

    # Cleanup returns statistics
    cleanup_stats = await endpoint_mgr.cleanup_all_endpoints()

    print(f"\n🧹 Cleanup Results:")
    print(f"  Cloud PCs deleted: {cleanup_stats['cloud_pcs_deleted']}")
    print(f"  Windows VMs deleted: {cleanup_stats['vms_deleted']}")
    print(f"  Containers deleted: {cleanup_stats['containers_deleted']}")
    print(f"  Failed deletions: {cleanup_stats['failed_deletions']}")

    if cleanup_stats['failed_deletions'] > 0:
        print(f"\n⚠️  Some resources failed to delete. Check logs for details.")
        print(f"  Failed resources: {cleanup_stats['failed_resources']}")

# Run cleanup
await cleanup_all_endpoints()
```

### Example 4: Computer Use Agent with Windows VM

```python
async def provision_computer_use_agent():
    """Provision Windows VM for Computer Use Agent with browser automation."""

    from azure_haymaker.knowledge_worker.endpoints.windows_vm import WindowsVMManager

    # Initialize VM manager
    vm_manager = WindowsVMManager(
        subscription_id=subscription_id,
        resource_group=resource_group,
        location="eastus",
        run_id=run_id
    )

    # Define worker for Computer Use Agent
    worker = WorkerIdentity(
        worker_id="kw-browser-agent-001",
        display_name="Browser Automation Agent",
        persona=WorkerPersona.EMPLOYEE,
        endpoint_type=EndpointType.WINDOWS_VM,
        endpoint_id=""
    )

    print("Provisioning Windows VM for Computer Use Agent...")
    vm_details = await vm_manager.provision_vm(worker)

    print(f"\n✅ VM Provisioned:")
    print(f"  Name: {vm_details['vm_name']}")
    print(f"  Public IP: {vm_details['public_ip']}")

    # Verify Computer Use Agent readiness
    print("\nVerifying Computer Use Agent readiness...")
    readiness = await vm_manager.verify_computer_use_ready(vm_details)

    if all(readiness.values()):
        print("✅ VM ready for Computer Use Agent")

        # Connect Computer Use Agent via RDP
        agent_config = {
            "endpoint_type": "rdp",
            "host": vm_details['public_ip'],
            "port": 3389,
            "username": vm_details['admin_username'],
            "password": vm_details['admin_password'],
            "browsers": ["chrome", "edge"],
            "desktop_mode": True
        }

        print(f"\n🤖 Computer Use Agent Configuration:")
        print(f"  RDP Endpoint: {agent_config['host']}:{agent_config['port']}")
        print(f"  Username: {agent_config['username']}")
        print(f"  Available Browsers: {', '.join(agent_config['browsers'])}")
        print(f"  Desktop Mode: {agent_config['desktop_mode']}")

        return agent_config
    else:
        print("⚠️  VM not ready for Computer Use Agent")
        for check, status in readiness.items():
            if not status:
                print(f"  Failed: {check}")

        return None

# Run provisioning
agent_config = await provision_computer_use_agent()

if agent_config:
    print("\n✅ Ready for Computer Use Agent testing")
    print("   - Browser automation (Chrome, Edge)")
    print("   - Desktop application interaction")
    print("   - GUI-based workflows")
```

**Example Output**:
```
Provisioning Windows VM for Computer Use Agent...

✅ VM Provisioned:
  Name: kw-abc12345-browser-agent-001-vm
  Public IP: 20.12.34.56

Verifying Computer Use Agent readiness...
✅ VM ready for Computer Use Agent

🤖 Computer Use Agent Configuration:
  RDP Endpoint: 20.12.34.56:3389
  Username: azureuser
  Available Browsers: chrome, edge
  Desktop Mode: True

✅ Ready for Computer Use Agent testing
   - Browser automation (Chrome, Edge)
   - Desktop application interaction
   - GUI-based workflows
```

---

## Related Documentation

- [Windows 365 Cloud PC Provisioning](./WINDOWS365_CLOUD_PC.md) - Primary endpoint provisioning
- [Knowledge Worker Framework Architecture](./ARCHITECTURE.md) - Overall framework design
- [Endpoint Strategy](./ARCHITECTURE.md#6-endpoint-strategy) - Endpoint comparison and selection
- [Azure Resource Cleanup](./ARCHITECTURE.md#8-resource-tracking-and-cleanup) - Cleanup guarantees

---

## Appendix: WindowsVMManager Implementation Details

### Resource Naming Convention

```python
# VM naming pattern
vm_name = f"{worker.worker_id}-vm"
# Example: kw-abc12345-exec-001-vm

# Associated resource names
nic_name = f"{vm_name}-nic"
public_ip_name = f"{vm_name}-pip"
nsg_name = f"{vm_name}-nsg"
os_disk_name = f"{vm_name}-osdisk"
```

### Azure SDK Dependencies

```python
# Required Azure SDK packages
azure-mgmt-compute>=30.0.0
azure-mgmt-network>=25.0.0
azure-identity>=1.15.0
```

### VM Provisioning Sequence

1. **Create Network Security Group**
   - Add RDP rule (3389)
   - Add WinRM HTTP rule (5985)
   - Add WinRM HTTPS rule (5986)

2. **Allocate Public IP Address**
   - Basic SKU
   - Static allocation
   - Tag with run_id

3. **Create Network Interface**
   - Attach to virtual network subnet
   - Associate with NSG
   - Associate with public IP

4. **Generate Admin Password**
   - 20 characters
   - Uppercase, lowercase, digit, special char
   - Store in endpoint_metadata

5. **Create Virtual Machine**
   - Windows Server 2022 Datacenter
   - Standard_D2s_v3 size (2 vCPU, 8GB RAM)
   - 128GB Standard SSD OS disk
   - Auto-shutdown disabled
   - Boot diagnostics enabled

6. **Wait for VM Ready**
   - Poll provisioning status
   - Timeout: 30 minutes
   - Return VM details on success

### VM Deletion Sequence

1. **Delete Virtual Machine**
   - Async operation (5-10 minutes)

2. **Delete OS Disk**
   - Wait for VM deletion first

3. **Delete Network Interface**
   - Wait for VM deletion first

4. **Delete Public IP Address**
   - Can run in parallel with NIC deletion

5. **Delete Network Security Group**
   - Wait for NIC deletion first

All deletions are idempotent and tagged for orphan cleanup.
