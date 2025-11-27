# Manual Testing Required for Windows VM Fallback (Issue #120)

## Unit Test Coverage: ✅ COMPLETE

- **Windows VM Tests**: 26/26 passing (95% coverage)
- **Worker Model Tests**: 21/21 passing (98% coverage)
- **Total**: 47 tests passing

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

## Security Testing: ⚠️ CRITICAL ISSUES IDENTIFIED

**Known Security Issues** (from security review - Score: 72/100):

### CRITICAL (Must Fix Before Production):
1. **Credentials Exposed in Return Values**
   - Admin password returned in plaintext
   - Should store in Azure Key Vault instead

2. **Unrestricted NSG Rules**
   - Current: RDP from ANY IP address (`source_address_prefix: "*"`)
   - Required: Restrict to specific IP ranges or use Azure Bastion

### HIGH PRIORITY:
3. **Public IP Exposure**
   - Every VM gets public IP by default
   - Consider private IPs + Azure Bastion for production

4. **Insufficient Input Validation**
   - Worker ID validation is basic
   - Should add comprehensive input sanitization

**See**: Security review report in PR comments for full details

## Test Results Summary

| Test Category | Status | Coverage |
|--------------|--------|----------|
| Unit Tests | ✅ PASS (47/47) | 95% |
| Integration Tests | ⚠️ MANUAL | Requires Azure credentials |
| Security Review | ⚠️ ISSUES | Score: 72/100 (C grade) |
| Code Review | ⚠️ ISSUES | Score: 72/100 |
| Philosophy Compliance | ✅ PASS | 98/100 |

## Recommendation

**For Testing/Development**: ✅ READY
- Unit tests comprehensive (47 tests, 95% coverage)
- All tests passing
- Linting clean
- Code quality good

**For Production Deployment**: ❌ NOT READY
- Security issues must be addressed
- Manual integration testing required
- Azure Bastion implementation recommended
- Credentials should be stored in Key Vault

## Manual Test Checklist

Before marking PR as production-ready:

- [ ] Test 1: Single VM provisioning verified
- [ ] Test 2: Cascade fallback verified
- [ ] Test 3: VM cleanup verified
- [ ] Test 4: Parallel provisioning tested (5 VMs)
- [ ] Test 5: Computer Use Agent connectivity verified
- [ ] Security Issue 1: Credentials moved to Key Vault
- [ ] Security Issue 2: NSG restricted to specific IPs
- [ ] Security Issue 3: Azure Bastion implemented (or public IPs justified)
- [ ] Security Issue 4: Input validation enhanced
