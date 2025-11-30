# Windows VM Security Hardening Specification

**Status:** Critical | **Priority:** P0
**Security Score:** 72/100 (Current) → Target: 95+/100

---

## 1. Security Assessment

### Critical Vulnerabilities (Score Impact: -20 pts)

| Vulnerability | CVSS | Impact | Status |
|---|---|---|---|
| Credentials logged in plaintext | HIGH | Credential exposure in logs | CRITICAL |
| NSG allows RDP from ANY IP (*) | HIGH | Brute force, unauthorized access | CRITICAL |
| Public IPs on all VMs | MEDIUM | Network exposure surface | HIGH |
| No disk encryption | MEDIUM | Data at rest unprotected | HIGH |
| No JIT VM access | MEDIUM | Always-on attack surface | MEDIUM |
| Basic input validation | LOW | Injection vectors possible | MEDIUM |

### Current Threat Vectors

```
Attacker     RDP (ANY IP)     Public IP
   ↓             ↓                ↓
   └──────────────────────────────┘
                  ↓
            Admin password
              (plaintext in logs)
                  ↓
            VM compromised
                  ↓
        Data in plaintext OSes
```

---

## 2. Threat Model

### Attack Scenarios

**Scenario A: Log-Based Credential Theft**
- Admin password logged during provisioning
- Logs accessible via Azure Monitor, application logs, or file system
- Attacker gains permanent access to VM

**Scenario B: RDP Brute Force**
- NSG rule: `source_address_prefix: "*"` allows ANY IP
- Attacker performs dictionary attack on admin account
- No rate limiting, no JIT access delay

**Scenario C: Network Reconnaissance**
- Public IP directly accessible
- Attacker maps services on port 3389 (RDP)
- Escalates to internal network if compromised

---

## 3. Implementation Plan

### Phase 1: Credential Protection (Days 1-2) ⭐ START HERE

**Goal:** Remove passwords from plaintext logs, use Key Vault

**Key Changes:**

1. **Remove password from return value:**
   ```python
   # BEFORE: Returns plaintext password (INSECURE)
   result = {
       "admin_password": admin_password,  # Exposed!
       "vm_name": vm_name,
       ...
   }

   # AFTER: Store in Key Vault, return secret reference
   from azure.keyvault.secrets.aio import SecretClient

   async def _store_credential_in_keyvault(
       self,
       keyvault_url: str,
       vm_name: str,
       admin_password: str,
       credential: Any
   ) -> str:
       """Store password in Key Vault, return secret URL."""
       client = SecretClient(vault_url=keyvault_url, credential=credential)

       secret_name = f"{vm_name}-admin-password"
       secret_properties = await client.set_secret(
           name=secret_name,
           value=admin_password,
           expires_on=datetime.utcnow() + timedelta(days=90)  # Rotate after 90 days
       )

       logger.info(f"Credential stored in Key Vault: {secret_name} (no value logged)")

       return secret_properties.id  # Return only the URL, not the password
   ```

2. **Update provision_vm return type:**
   ```python
   # AFTER Phase 1
   result = {
       "vm_name": vm_name,
       "public_ip": public_ip,
       "rdp_port": rdp_port,
       "admin_username": admin_username,
       "credential_keyvault_url": secret_url,  # Not the password!
       "credential_expires_at": expiry_date,
   }
   ```

3. **Stop logging credentials:**
   ```python
   # REMOVE THIS:
   logger.info(f"Admin password: {admin_password}")  # NEVER!

   # ADD THIS:
   logger.info(f"VM provisioned. Credential stored in Key Vault (not logged)")
   ```

4. **Add requirements:**
   ```bash
   azure-keyvault-secrets>=4.4.0
   azure-identity>=1.14.0
   ```

---

### Phase 2: Network Isolation + Azure Bastion (Days 2-4)

**Goal:** Eliminate public RDP, restrict access via Bastion

**Key Changes:**

1. **Restrict NSG to Bastion only:**
   ```python
   # BEFORE: Allows RDP from ANY IP
   "sourceAddressPrefix": "*",
   "destinationPortRange": "3389",

   # AFTER: Allow only from Azure Bastion service tag
   async def _create_nsg_rule(self) -> str:
       """Create NSG allowing RDP only from Azure Bastion."""
       nsg_rules = [
           {
               "name": "AllowBastionRDP",
               "properties": {
                   "protocol": "*",
                   "sourcePortRange": "*",
                   "destinationPortRange": "3389",
                   "sourceAddressPrefix": "BastionSubnet",  # Or specific Bastion subnet IP
                   "destinationAddressPrefix": "*",
                   "access": "Allow",
                   "priority": 100,
                   "direction": "Inbound"
               }
           },
           {
               "name": "DenyRDPFromInternet",
               "properties": {
                   "protocol": "*",
                   "sourcePortRange": "*",
                   "destinationPortRange": "3389",
                   "sourceAddressPrefix": "Internet",
                   "destinationAddressPrefix": "*",
                   "access": "Deny",
                   "priority": 50,  # Higher priority = evaluated first
                   "direction": "Inbound"
               }
           }
       ]
       return nsg_rules
   ```

2. **Deploy VMs without public IPs:**
   ```python
   # BEFORE: Every VM gets public IP
   public_ip_config = {
       "name": "myPublicIP",
       "properties": {
           "publicIPAllocationMethod": "Static"
       }
   }

   # AFTER: Optional public IP, Bastion by default
   def __init__(
       self,
       ...,
       use_bastion: bool = True,  # Enable by default
       expose_public_ip: bool = False,  # Disable by default
   ):
       self.use_bastion = use_bastion
       self.expose_public_ip = expose_public_ip

   async def _create_public_ip(self, vm_name: str) -> str | None:
       """Create public IP only if explicitly enabled."""
       if not self.expose_public_ip:
           logger.info("Skipping public IP (using Bastion for access)")
           return None

       # Only create if needed for specific scenarios
       ...
   ```

3. **Add Bastion prerequisites validation:**
   ```python
   async def validate_bastion_prerequisites(self) -> None:
       """Validate Bastion subnet and resources exist."""
       # Check for AzureBastionSubnet
       # Check for Bastion resource
       # Log warnings if missing
   ```

---

### Phase 3: Encryption + JIT Access (Days 3-5)

**Goal:** Enable disk encryption and JIT VM access

**Key Changes:**

1. **Enable Azure Disk Encryption:**
   ```python
   async def _enable_disk_encryption(self, vm_name: str) -> None:
       """Enable Azure Disk Encryption (ADE) on OS and data disks."""
       from azure.mgmt.compute import models

       encryption_settings = models.DiskEncryptionSettings(
           enabled=True,
           key_vault_secret_url=keyvault_secret_url,
           key_vault_key_url=keyvault_key_url,
           source_vault=models.SourceVault(id=keyvault_id)
       )

       logger.info(f"Enabling Azure Disk Encryption for {vm_name}")

       # Note: ADE has prerequisites; use managed disk encryption as simpler alternative

   # SIMPLER: Enable managed disk encryption (no Key Vault needed)
   async def _enable_managed_disk_encryption(self, disk_id: str) -> None:
       """Enable encryption at rest for managed disks (Default)."""
       # Azure Managed Disks are encrypted by default with platform-managed keys
       # For customer-managed keys, use Key Vault integration
       logger.info(f"Disk encrypted with platform-managed keys: {disk_id}")
   ```

2. **Implement JIT VM Access:**
   ```python
   async def _enable_jit_vm_access(
       self,
       vm_name: str,
       max_access_hours: int = 4
   ) -> None:
       """Enable Just-In-Time VM access via Azure Security Center."""
       from azure.mgmt.security import SecurityCenter

       jit_policy = {
           "virtualMachines": [
               {
                   "id": vm_resource_id,
                   "ports": [
                       {
                           "number": 3389,  # RDP
                           "protocol": "TCP",
                           "allowedSourceAddresses": ["*"],
                           "maxRequestAccessDuration": f"PT{max_access_hours}H"
                       }
                   ]
               }
           ]
       }

       logger.info(f"JIT access enabled for {vm_name} ({max_access_hours}h max)")
   ```

3. **Add configuration:**
   ```python
   # New params
   SECURITY_CONFIG = {
       "enable_disk_encryption": True,  # Default: ON
       "enable_jit_access": True,       # Default: ON
       "jit_max_hours": 4,              # Time-limited access
       "require_bastion": True,         # Default: Bastion required
       "allow_public_ip": False,        # Default: No public IP
   }
   ```

---

### Phase 4: Testing & Monitoring (Days 4-6)

**Goal:** Validate security hardening, add telemetry

**Test Cases:**

```python
class TestWindowsVMSecurityHardening:
    """Security hardening validation tests."""

    async def test_no_credentials_in_logs(self):
        """Verify passwords never logged."""
        # Provision VM
        # Check logs for password strings
        # Assert password NOT found
        pass

    async def test_nsg_allows_only_bastion(self):
        """Verify NSG restricts RDP to Bastion only."""
        # Get NSG rules
        # Assert "Internet" source DENIED for port 3389
        # Assert "BastionSubnet" source ALLOWED for port 3389
        pass

    async def test_vm_has_no_public_ip_by_default(self):
        """Verify VMs created without public IPs."""
        # Provision with defaults
        # Assert public_ip is None
        pass

    async def test_disk_encryption_enabled(self):
        """Verify managed disk encryption active."""
        # Get VM disk properties
        # Assert encryption_enabled=True
        pass

    async def test_jit_access_policy_active(self):
        """Verify JIT access policy configured."""
        # Get JIT policy
        # Assert max request duration set
        pass

    async def test_credentials_in_keyvault(self):
        """Verify credentials stored in Key Vault."""
        # Provision VM
        # Verify credential_keyvault_url returned
        # Verify secret exists in Key Vault
        # Verify password NOT returned in response
        pass

    async def test_rdp_denied_from_internet(self):
        """Verify RDP blocked from public internet."""
        # Try RDP from random IP
        # Assert connection refused
        pass
```

**Monitoring & Alerts:**

```python
# Add Application Insights telemetry
import logging.handlers
from opencensus.ext.azure.log_exporter import AzureEventHandler

def setup_security_monitoring():
    """Configure security event monitoring."""

    security_logger = logging.getLogger("security")
    security_logger.setLevel(logging.INFO)

    # Send security events to Application Insights
    handler = AzureEventHandler(
        connection_string=os.environ.get("APPINSIGHTS_CONNECTION_STRING")
    )

    security_logger.addHandler(handler)

    return security_logger

# Track security-relevant events
security_logger = setup_security_monitoring()

# Events to track:
# - VM provisioned with Bastion access
# - Credentials stored in Key Vault (with expiry)
# - JIT access request approved/denied
# - NSG rule modified
# - Disk encryption status
```

---

## 4. Code Examples: Before/After Comparison

### Example 1: Credential Handling

**BEFORE (Insecure):**
```python
async def provision_vm(self, worker: WorkerIdentity) -> dict:
    admin_password = self._generate_secure_password()

    # SECURITY ISSUE: Password logged here
    logger.info(f"Generated admin password: {admin_password}")  # EXPOSED!

    # SECURITY ISSUE: Password returned in plaintext
    return {
        "vm_name": vm_name,
        "admin_password": admin_password,  # Anyone with access to response sees password
        "public_ip": public_ip,
    }
```

**AFTER (Secure):**
```python
async def provision_vm(self, worker: WorkerIdentity) -> dict:
    admin_password = self._generate_secure_password()

    # SECURE: Password stored in Key Vault, never logged
    secret_url = await self._store_credential_in_keyvault(
        keyvault_url=self.keyvault_url,
        vm_name=vm_name,
        admin_password=admin_password,
        credential=self.credential
    )

    logger.info(f"VM {vm_name} provisioned. Credentials stored in Key Vault.")

    # SECURE: Only Key Vault URL returned, not password
    return {
        "vm_name": vm_name,
        "credential_keyvault_url": secret_url,  # Reference, not value
        "credential_expires_at": expiry_date,
    }
```

### Example 2: Network Security Group

**BEFORE (Insecure):**
```python
nsg_rules = {
    "name": "AllowRDP",
    "properties": {
        "protocol": "TCP",
        "sourcePortRange": "*",
        "destinationPortRange": "3389",
        "sourceAddressPrefix": "*",  # ALLOWS ANY IP - CRITICAL ISSUE
        "destinationAddressPrefix": "*",
        "access": "Allow",
        "priority": 100,
    }
}
```

**AFTER (Secure):**
```python
nsg_rules = [
    {
        "name": "DenyRDPFromInternet",  # Deny first (priority 50)
        "properties": {
            "protocol": "*",
            "sourcePortRange": "*",
            "destinationPortRange": "3389",
            "sourceAddressPrefix": "Internet",  # Deny from internet
            "destinationAddressPrefix": "*",
            "access": "Deny",
            "priority": 50,
            "direction": "Inbound"
        }
    },
    {
        "name": "AllowBastionRDP",  # Allow only from Bastion (priority 100)
        "properties": {
            "protocol": "*",
            "sourcePortRange": "*",
            "destinationPortRange": "3389",
            "sourceAddressPrefix": "BastionSubnet",  # Only from Bastion
            "destinationAddressPrefix": "*",
            "access": "Allow",
            "priority": 100,
            "direction": "Inbound"
        }
    }
]
```

### Example 3: VM Configuration

**BEFORE (Insecure):**
```python
vm_config = {
    "location": location,
    "properties": {
        "hardwareProfile": {"vmSize": vm_size},
        "networkProfile": {
            "networkInterfaces": [
                {"id": nic_id, "properties": {"primary": True}}
            ]
        },
        # ISSUE: Public IP always created
        "publicIpAddress": {
            "name": "myPublicIP",
            "properties": {"publicIPAllocationMethod": "Static"}
        }
    }
}
```

**AFTER (Secure):**
```python
vm_config = {
    "location": location,
    "properties": {
        "hardwareProfile": {"vmSize": vm_size},
        "storageProfile": {
            "osDisk": {
                "caching": "ReadWrite",
                "createOption": "FromImage",
                "managedDisk": {
                    "storageAccountType": "Premium_LRS"  # Encrypted by default
                }
            },
            "imageReference": {
                "publisher": "MicrosoftWindowsServer",
                "offer": "WindowsServer",
                "sku": "2022-datacenter-azure-edition",
                "version": "latest"
            }
        },
        "networkProfile": {
            "networkInterfaces": [
                {"id": nic_id, "properties": {"primary": True}}
            ]
        },
        # SECURE: No public IP (use Bastion instead)
        "publicIpAddress": None
    },
    "tags": {
        "security-profile": "bastion-isolated",
        "encryption": "managed-disk",
        "jit-enabled": "true"
    }
}
```

---

## 5. Testing Requirements

### Security Test Suite

```bash
# Run all security tests
pytest tests/security/test_windows_vm_security.py -v

# Test credential protection
pytest tests/security/test_windows_vm_security.py::test_no_credentials_in_logs -v

# Test NSG configuration
pytest tests/security/test_windows_vm_security.py::test_nsg_restricts_rdp -v

# Test encryption
pytest tests/security/test_windows_vm_security.py::test_disk_encryption_enabled -v

# Test JIT access
pytest tests/security/test_windows_vm_security.py::test_jit_access_policy -v
```

### Manual Security Validation

```bash
# 1. Verify credentials stored in Key Vault
az keyvault secret list --vault-name <vault-name>

# 2. Check NSG rules
az network nsg rule list --resource-group <rg> --nsg-name <nsg-name> \
  --query "[?name=='AllowRDP'].{source:properties.sourceAddressPrefix}"

# 3. Verify no public IP
az vm nic list --resource-group <rg> --vm-name <vm-name> \
  --query "[].publicIpAddresses"

# 4. Confirm disk encryption
az vm encryption show --resource-group <rg> --name <vm-name>

# 5. Check JIT policy
az security jit-network-access-policy list --resource-group <rg>
```

---

## 6. Rollout Plan

### Phase Timeline

| Phase | Duration | Deliverable | Status |
|---|---|---|---|
| Phase 1 | Days 1-2 | Key Vault integration | TODO |
| Phase 2 | Days 2-4 | Bastion + NSG hardening | TODO |
| Phase 3 | Days 3-5 | Disk encryption + JIT | TODO |
| Phase 4 | Days 4-6 | Testing + monitoring | TODO |

### Deployment Order

1. ✅ Phase 1: Credential protection (no API changes)
2. ✅ Phase 2: Network isolation (backward compatible)
3. ✅ Phase 3: Encryption + JIT (non-breaking)
4. ✅ Phase 4: Testing (validation suite)

---

## 7. Security Checklist

- [ ] No credentials logged in any form
- [ ] NSG denies RDP from Internet (priority 50)
- [ ] NSG allows RDP from Bastion only (priority 100)
- [ ] VMs deployed without public IPs by default
- [ ] Managed disk encryption enabled on all OS/data disks
- [ ] JIT VM access policy configured (4-hour max)
- [ ] Credentials stored in Key Vault with rotation policy
- [ ] All security changes documented in logs (no sensitive data)
- [ ] Security tests pass (100% coverage)
- [ ] Monitoring alerts configured for security events

---

## 8. Success Metrics

| Metric | Target | Current |
|---|---|---|
| Security Score | 95+/100 | 72/100 |
| Credentials exposed in logs | 0 | TBD |
| NSG rule violations | 0 | 1 (allows *) |
| VMs with public RDP | 0% | 100% |
| Disk encryption coverage | 100% | 0% |
| JIT access enabled | 100% | 0% |

---

## References

- [Azure Key Vault Integration](https://learn.microsoft.com/en-us/azure/key-vault/general/overview)
- [Azure Bastion Documentation](https://learn.microsoft.com/en-us/azure/bastion/bastion-overview)
- [Network Security Groups Best Practices](https://learn.microsoft.com/en-us/azure/virtual-network/network-security-groups-overview)
- [Just-In-Time VM Access](https://learn.microsoft.com/en-us/azure/security-center/security-center-just-in-time)
- [Azure Disk Encryption](https://learn.microsoft.com/en-us/azure/virtual-machines/windows/disk-encryption)
