# Getting Started: Windows VM Security Hardening (Issue #125)

**Your complete guide to implementing Issue #125**

**Priority**: P0-Critical | **Effort**: 1-2 weeks | **ROI**: 1,165%

---

## What You're Fixing

Critical security vulnerabilities in Windows VM provisioning (from PR #121):

1. 🔴 **Credentials exposed** in plaintext (logs)
2. 🔴 **Unrestricted NSG** rules (RDP from ANY IP)
3. 🟠 **Public IPs** on all VMs
4. 🟠 **No disk encryption**
5. 🟠 **No JIT access**

**Current Score**: 72/100 (C grade)
**Target Score**: 95+/100 (A grade)

---

## Before You Start (10 minutes)

### 1. Read the Spec
📄 **Full Specification**: [`specs/WINDOWS_VM_SECURITY_HARDENING.md`](../specs/WINDOWS_VM_SECURITY_HARDENING.md) (19KB)

**Key sections**:
- Security Assessment (vulnerabilities with CVSS scores)
- Threat Model (attack vectors)
- Implementation Plan (4 phases with code examples)

### 2. Review Current Code
```bash
# Read the INSECURE implementation
cat src/azure_haymaker/knowledge_worker/endpoints/windows_vm.py

# Review the security issues
# - Line ~200: Password returned in plaintext
# - Line ~150: NSG rule with source_address_prefix="*"
# - Line ~100: Public IP creation
# - Missing: Disk encryption configuration
# - Missing: JIT access policy
```

### 3. Review Starter Code
```bash
# See BEFORE and AFTER comparisons
cat examples/windows_vm_security_starter.py

# Note the SECURE implementation approach
```

---

## Phase 1: Key Vault Integration (Days 1-2, ~12 hours)

**Goal**: Store VM passwords in Azure Key Vault, not plaintext

### 1.1: Add Key Vault Client

**File**: `src/azure_haymaker/knowledge_worker/endpoints/windows_vm.py`

```python
from azure.keyvault.secrets import SecretClient

class WindowsVMManager:
    def __init__(self, ..., keyvault_name: str):
        # Add Key Vault client
        vault_url = f"https://{keyvault_name}.vault.azure.net"
        self.keyvault_client = SecretClient(vault_url, credential)
```

### 1.2: Modify provision_vm() Method

**BEFORE** (INSECURE):
```python
password = secrets.token_urlsafe(24)
return vm_id, {
    "admin_password": password  # ⚠️ PLAINTEXT
}
```

**AFTER** (SECURE):
```python
password = secrets.token_urlsafe(32)  # Longer password
secret_name = f"vm-{worker_id}-admin-password"

# Store in Key Vault IMMEDIATELY
self.keyvault_client.set_secret(secret_name, password)

return vm_id, {
    "password_secret_uri": f"https://{self.keyvault_name}.vault.azure.net/secrets/{secret_name}"
    # ✅ URI only, NOT plaintext
}
```

### 1.3: Write Security Tests

**File**: `tests/security/test_windows_vm_security.py`

```python
import pytest
import logging
from io import StringIO

def test_password_not_in_return_value():
    """Verify password not returned in plaintext."""
    manager = WindowsVMManager(...)
    vm_id, vm_info = manager.provision_vm("worker-001")

    # Password should NOT be in vm_info
    assert "admin_password" not in vm_info
    assert "password" not in str(vm_info).lower()

    # Key Vault URI should be present
    assert "password_secret_uri" in vm_info
    assert "vault.azure.net" in vm_info["password_secret_uri"]

def test_password_not_in_logs(caplog):
    """Verify password never appears in logs."""
    with caplog.at_level(logging.INFO):
        manager = WindowsVMManager(...)
        vm_id, vm_info = manager.provision_vm("worker-001")

    # Check all log messages
    all_logs = " ".join(record.message for record in caplog.records)

    # Password should NOT appear anywhere
    # (This test will help catch accidental logging)
    assert len(all_logs) > 0  # Ensure logs were captured
    # Note: Hard to test without knowing the actual password
    # Use mock and verify the mock password doesn't appear
```

### Run Tests (Should FAIL initially)
```bash
pytest tests/security/test_windows_vm_security.py -v
```

---

## Phase 2: Network Security (Days 3-5, ~18 hours)

**Goal**: Restrict NSG rules, use Azure Bastion instead of public IPs

### 2.1: Update NSG Rules

**BEFORE** (INSECURE):
```python
security_rules = [{
    "source_address_prefix": "*",  # ⚠️ ANY IP
}]
```

**AFTER** (SECURE):
```python
security_rules = [
    {
        "name": "Allow-RDP-From-Bastion-Only",
        "source_address_prefix": "10.0.1.0/24",  # ✅ Bastion subnet
        "destination_port_range": "3389",
        "access": "Allow",
        "priority": 100,
    },
    {
        "name": "Deny-RDP-From-Internet",
        "source_address_prefix": "Internet",
        "access": "Deny",  # ✅ Explicit deny
        "priority": 200,
    }
]
```

### 2.2: Remove Public IP Assignment

**Change**: Make public IP optional (default: disabled)

```python
def _create_network_interface(
    self,
    worker_id: str,
    location: str,
    assign_public_ip: bool = False  # ✅ Default: NO public IP
):
    ip_config = {
        "name": "ipconfig1",
        "subnet": {"id": subnet_id},
    }

    if assign_public_ip:
        # Only create public IP if explicitly requested
        ip_config["public_ip_address"] = {"id": public_ip_id}

    # ✅ By default, no public IP (access via Bastion)
```

### 2.3: Write NSG Tests

```python
def test_nsg_blocks_internet_rdp():
    """Verify NSG rules block internet RDP."""
    manager = WindowsVMManager(...)
    nsg_rules = manager._get_nsg_rules()

    # Should NOT allow from "*" or "Internet" for port 3389
    rdp_allow_rules = [r for r in nsg_rules
                       if r["destination_port_range"] == "3389"
                       and r["access"] == "Allow"]

    for rule in rdp_allow_rules:
        assert rule["source_address_prefix"] != "*"
        assert rule["source_address_prefix"] != "Internet"

    # Should have explicit deny from Internet
    deny_rules = [r for r in nsg_rules if r["access"] == "Deny"]
    assert len(deny_rules) > 0

def test_no_public_ip_by_default():
    """Verify VMs don't get public IPs by default."""
    manager = WindowsVMManager(...)
    vm_id, vm_info = manager.provision_vm("worker-001")

    # Public IP should not be assigned
    assert "public_ip" not in vm_info or vm_info["public_ip"] is None
```

---

## Phase 3: Encryption & JIT Access (Days 6-8, ~18 hours)

### 3.1: Enable Disk Encryption

**Add to VM configuration**:
```python
vm_config = {
    "storage_profile": {
        "os_disk": {
            "managed_disk": {
                "security_profile": {
                    "security_encryption_type": "DiskWithVMGuestState"
                    # ✅ Encryption enabled
                }
            }
        }
    }
}
```

### 3.2: Configure JIT VM Access

**Create JIT policy** (separate API call after VM creation):
```python
from azure.mgmt.security import SecurityCenter

def _configure_jit_access(self, vm_id: str):
    """Configure Just-In-Time VM access."""
    jit_policy = {
        "kind": "Basic",
        "properties": {
            "virtual_machines": [{
                "id": vm_id,
                "ports": [{
                    "number": 3389,
                    "protocol": "TCP",
                    "max_request_access_duration": "PT4H"  # 4 hours
                }]
            }]
        }
    }
    # Create JIT policy via Security Center API
```

### 3.3: Write Encryption/JIT Tests

```python
def test_disk_encryption_enabled():
    """Verify VM disks are encrypted."""
    manager = WindowsVMManager(...)
    vm_id, vm_info = manager.provision_vm("worker-001")

    # Query VM configuration
    vm = manager.compute_client.virtual_machines.get(
        resource_group, vm_name
    )

    # Verify encryption enabled
    assert vm.storage_profile.os_disk.managed_disk.security_profile is not None
    assert "encryption" in vm.storage_profile.os_disk.managed_disk.security_profile.security_encryption_type.lower()

def test_jit_access_configured():
    """Verify JIT VM access is configured."""
    # Query Security Center for JIT policies
    # Verify policy exists for this VM
    # Verify 4-hour max duration
```

---

## Phase 4: Final Testing & Documentation (Days 9-10, ~12 hours)

### Run Full Test Suite
```bash
# All unit tests
pytest tests/unit/test_windows_vm.py -v

# All security tests
pytest tests/security/test_windows_vm_security.py -v

# All integration tests (requires Azure)
pytest tests/integration/test_windows_vm_integration.py -v
```

### Run Security Scan
```bash
# Detect hardcoded secrets
pre-commit run detect-secrets --all-files

# Security linting
bandit -r src/azure_haymaker/knowledge_worker/endpoints/windows_vm.py

# Should find 0 issues
```

### E2E Testing (MANDATORY)
```bash
# Provision actual VM with security fixes
python -c "from azure_haymaker.knowledge_worker.endpoints import WindowsVMManager; ..."

# Verify:
# - Password in Key Vault (check Azure Portal)
# - No public IP on VM (check VM config)
# - NSG blocks internet (try RDP from home - should fail)
# - NSG allows Bastion (RDP via Bastion - should work)
# - Disk encrypted (check disk properties)
# - JIT policy exists (check Security Center)
```

### Calculate Security Score
Use spec's scoring rubric:
- Key Vault: +10 points
- NSG restrictions: +8 points
- Disk encryption: +5 points
- Should reach 95+/100

---

## Create PR & Merge

### PR Description Template
```markdown
## Summary
Fixes critical security vulnerabilities in Windows VM provisioning.

## Security Improvements
- ✅ Credentials stored in Key Vault only (Issue 1 fixed)
- ✅ NSG restricts RDP to Bastion subnet (Issue 2 fixed)
- ✅ Public IPs optional, default disabled (Issue 3 fixed)
- ✅ Disk encryption enabled (Issue 4 fixed)
- ✅ JIT VM access configured (Issue 5 fixed)

## Security Score
- Before: 72/100 (C grade)
- After: 97/100 (A grade)
- Improvement: +25 points

## Testing
[Paste E2E test results]

Closes #125
```

---

## Success Criteria

**Must achieve before marking complete**:
- [ ] Security score >90/100
- [ ] External security audit passed
- [ ] All 5 vulnerabilities fixed and verified
- [ ] No credentials in logs (tested)
- [ ] NSG blocks internet RDP (tested)
- [ ] Disk encryption working (tested)
- [ ] Can merge PR #121 safely

---

## Timeline

| Phase | Days | Cumulative |
|-------|------|------------|
| 1: Key Vault | 2 | Day 2 |
| 2: Network Security | 3 | Day 5 |
| 3: Encryption & JIT | 3 | Day 8 |
| 4: Testing & Docs | 2 | Day 10 |

**Total**: 10 days (2 weeks)

---

**Full Spec**: [`specs/WINDOWS_VM_SECURITY_HARDENING.md`](../specs/WINDOWS_VM_SECURITY_HARDENING.md)
**Issue**: [#125](https://github.com/rysweet/AzureHayMaker/issues/125)
**Milestone**: [Q1 2026](https://github.com/rysweet/AzureHayMaker/milestone/1)

🔒 **Ready to secure those VMs? Follow Phase 1 above!**
