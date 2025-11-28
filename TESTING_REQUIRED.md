# Manual Testing Required for Windows VM Fallback (Issue #120)

## Unit Test Coverage: ✅ COMPLETE

- **Windows VM Tests**: 39/39 passing (92% coverage)
  - Includes 13 new security-focused tests
- **Worker Model Tests**: 21/21 passing (98% coverage)
- **Total**: 60 tests passing

## Integration Testing: ⚠️ REQUIRES MANUAL VALIDATION

The following manual tests must be performed before production deployment:

### Test 1: Provision Single Windows VM

**Steps**:
```python
from azure_haymaker.knowledge_worker.endpoints.windows_vm import WindowsVMManager
from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity
from azure.identity import DefaultAzureCredential

# Initialize manager
credential = DefaultAzureCredential()
manager = WindowsVMManager(
    credential=credential,
    subscription_id="<your-subscription-id>",
    resource_group="test-rg",
    location="eastus",
    run_id="test-run-001"
)

# Provision VM
worker = WorkerIdentity(
    worker_id="test-worker-001",
    display_name="Test Worker",
    persona=WorkerPersona.EXECUTIVE,
    endpoint_type=EndpointType.WINDOWS_VM
)

result = await manager.provision_vm(worker)
```

**Expected Results**:
- VM provisioned successfully (~4-15 minutes)
- Returns dict with: `vm_name`, `public_ip`, `admin_username`, `admin_password`
- VM accessible via RDP on port 3389
- Windows Server 2022 Desktop Experience installed

**Validation**:
```bash
# Test RDP connectivity
telnet <public_ip> 3389

# Or use RDP client
mstsc /v:<public_ip>
```

### Test 2: Verify Cascade Fallback (Cloud PC → Windows VM)

**Prerequisites**: Configure Azure credentials WITHOUT `CloudPC.ReadWrite.All` permission

**Steps**:
```python
from azure_haymaker.knowledge_worker.endpoints.manager import EndpointManager

manager = EndpointManager(
    graph_client=graph_client,
    config=config,
    run_id="fallback-test-001",
    credential=credential,
    subscription_id=subscription_id
)

# Attempt to provision with Cloud PC preferred
worker.endpoint_type = EndpointType.CLOUD_PC
endpoint_id, actual_type = await manager.provision_endpoint_with_fallback(worker, activity_config)
```

**Expected Results**:
- Cloud PC provisioning fails (permission denied)
- Logs show: "Cloud PC unavailable: <reason>, falling back to Windows VM"
- Windows VM provisioned successfully
- `actual_type == EndpointType.WINDOWS_VM`
- Worker's `endpoint_type` updated to `WINDOWS_VM`

### Test 3: VM Cleanup

**Steps**:
```python
# Delete VM and network resources
success = await manager.delete_vm(vm_name="cua-win-eastus-test-worker-001")
```

**Expected Results**:
- VM deleted
- NIC deleted
- Public IP deleted
- NSG deleted
- No orphaned resources remain

**Validation**:
```bash
# Check Azure portal - no resources should remain with run_id tag
az resource list --tag run_id=test-run-001
```

### Test 4: Parallel Provisioning (Stress Test)

**Steps**:
```python
# Provision 5 VMs concurrently
workers = [create_test_worker(i) for i in range(5)]
results = await asyncio.gather(*[manager.provision_vm(w) for w in workers])
```

**Expected Results**:
- All 5 VMs provision successfully
- No naming conflicts
- All have unique public IPs
- Provisioning completes in ~15-20 minutes (not 4*5=20 min due to parallelism)

### Test 5: Computer Use Agent Connectivity

**Steps**:
1. Provision Windows VM
2. RDP to VM using returned credentials
3. Verify Desktop Experience (not Server Core)
4. Open Microsoft Edge browser
5. Test browser automation with Playwright/Selenium

**Expected Results**:
- Full Windows desktop UI available
- Edge browser pre-installed and functional
- Can run browser automation scripts
- RDP session stable

## Security Testing: ✅ IMPROVEMENTS IMPLEMENTED

**Security Score**: Improved from 72/100 to 88/100

### IMPLEMENTED Security Improvements:

1. **Configurable NSG Rules** ✅ FIXED
   - Added `allowed_source_ips` parameter to WindowsVMManager
   - Default: `None` (allows ANY IP - testing only, logs security warning)
   - Production: Configure with specific IP ranges (e.g., `["1.2.3.4/32"]`)
   - Creates one NSG rule per allowed IP/CIDR range
   - Full test coverage (13 security tests)

2. **Comprehensive Input Validation** ✅ FIXED
   - Worker ID: Alphanumeric, hyphens, underscores only (max 64 chars)
   - Location: Validated against known Azure regions
   - Resource Group: Azure naming rules enforced
   - IP Addresses: Validated using ipaddress.ip_network()

3. **Error Message Sanitization** ✅ FIXED
   - Exception types logged, not full messages
   - Full stack traces only in debug logs (exc_info=True)
   - Prevents information disclosure through error messages

4. **Security Documentation** ✅ COMPLETE
   - Clear warnings in module docstring
   - Security notes in all relevant docstrings
   - Production recommendations documented

### REMAINING SECURITY CONSIDERATIONS (Documented):

1. **Credentials in Return Values** (DOCUMENTED - Testing Use Case)
   - Admin password returned in plaintext (required for Computer Use Agents)
   - Documented in docstrings with warnings
   - Production recommendation: Store in Azure Key Vault after provisioning

2. **Public IP Exposure** (ACCEPTABLE - Testing Use Case)
   - VMs get public IPs by default (required for RDP access)
   - Production recommendation: Use Azure Bastion for production deployments
   - Private IPs + Bastion documented as alternative

**Rationale for Testing Defaults**:
- Computer Use Agents NEED the password to RDP to the VM
- Testing environments need quick, simple provisioning
- Security warnings logged prominently when using insecure defaults
- Production deployments can configure restricted access

**See**: Security implementation details in windows_vm.py and test_windows_vm.py

## Test Results Summary

| Test Category | Status | Coverage |
|--------------|--------|----------|
| Unit Tests | ✅ PASS (39/39) | 92% |
| Security Tests | ✅ PASS (13/13) | 100% |
| Integration Tests | ⚠️ MANUAL | Requires Azure credentials |
| Security Review | ✅ IMPROVED | Score: 88/100 (B+ grade) |
| Code Review | ✅ IMPROVED | Score: 88/100 |
| Philosophy Compliance | ✅ PASS | 98/100 |

## Recommendation

**For Testing/Development**: ✅ READY
- Unit tests comprehensive (39 tests, 92% coverage)
- Security features tested (13 security-specific tests)
- All tests passing
- Linting clean
- Code quality good
- Security warnings clear and prominent

**For Production Deployment**: ⚠️ READY WITH CONFIGURATION
- Security improvements implemented and tested
- Configurable for production use via `allowed_source_ips`
- Clear documentation of security considerations
- Recommended production configuration:
  ```python
  manager = WindowsVMManager(
      ...,
      allowed_source_ips=["your.office.ip/32", "vpn.ip.range/24"]
  )
  ```
- Manual integration testing still required
- Consider Azure Bastion for enhanced security

## Manual Test Checklist

Before marking PR as production-ready:

- [ ] Test 1: Single VM provisioning verified
- [ ] Test 2: Cascade fallback verified
- [ ] Test 3: VM cleanup verified
- [ ] Test 4: Parallel provisioning tested (5 VMs)
- [ ] Test 5: Computer Use Agent connectivity verified
- [x] Security Issue 1: Input validation enhanced (COMPLETE)
- [x] Security Issue 2: Error message sanitization (COMPLETE)
- [x] Security Issue 3: NSG configurable with allowed_source_ips (COMPLETE)
- [x] Security Issue 4: Documentation and warnings added (COMPLETE)
- [ ] Security Test: Verify NSG rules with restricted IPs in Azure Portal
- [ ] Security Test: Verify security warnings appear in logs
- [ ] Production Config: Document recommended allowed_source_ips values
