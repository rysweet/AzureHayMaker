# Azure HayMaker Code Examples

This directory contains starter code templates and examples for Azure HayMaker development.

---

## Enhancement Starter Templates

Skeleton implementations to help contributors get started on roadmap enhancements.

### P0-Critical Enhancements

#### 1. SIEM Telemetry Export (Issue #124)

**File**: [`siem_export_starter.py`](siem_export_starter.py)

**What's Included**:
- `TelemetryEvent` dataclass - Standardized event model
- `SIEMConnector` abstract base class - Connector interface
- `SentinelConnector` skeleton - Azure Sentinel implementation (priority)
- `EventNormalizer` - CEF/JSON/Syslog format converters
- `TelemetryExporter` - Main orchestrator
- Example configuration and usage

**How to Use**:
```bash
# 1. Copy to production location
cp examples/siem_export_starter.py src/azure_haymaker/knowledge_worker/telemetry/exporter.py

# 2. Write tests first (TDD)
# Create: tests/unit/test_siem_export.py

# 3. Implement TODOs marked in code
# Focus on SentinelConnector first (priority)

# 4. Run tests
pytest tests/unit/test_siem_export.py -v
```

**Full Spec**: [`specs/SIEM_TELEMETRY_EXPORT.md`](../specs/SIEM_TELEMETRY_EXPORT.md)

---

#### 2. Windows VM Security Hardening (Issue #125)

**File**: [`windows_vm_security_starter.py`](windows_vm_security_starter.py)

**What's Included**:
- `WindowsVMManager_BEFORE` - Current INSECURE implementation (DO NOT USE)
- `WindowsVMManager_SECURE` - SECURE implementation with all fixes
- Before/After comparisons for all 5 security issues:
  1. Key Vault credential storage (not plaintext)
  2. Restricted NSG rules (Bastion subnet only)
  3. No public IPs (Azure Bastion access)
  4. Disk encryption enabled
  5. JIT VM access configured
- Security test examples
- Integration example

**How to Use**:
```bash
# 1. Review BEFORE code to understand security issues
# See: WindowsVMManager_BEFORE class

# 2. Implement AFTER code (security fixes)
# See: WindowsVMManager_SECURE class

# 3. Update existing file
# File: src/azure_haymaker/knowledge_worker/endpoints/windows_vm.py

# 4. Write security tests
# Create: tests/security/test_windows_vm_security.py

# 5. Run tests
pytest tests/security/test_windows_vm_security.py -v
```

**Full Spec**: [`specs/WINDOWS_VM_SECURITY_HARDENING.md`](../specs/WINDOWS_VM_SECURITY_HARDENING.md)

---

## Knowledge Worker Examples

Existing examples for Knowledge Worker framework.

### Teams Integration

**File**: [`examples/teams_orchestrator_integration.py`](teams_orchestrator_integration.py)

Demonstrates how to integrate Teams functionality with the orchestrator.

### Telemetry Reporting

**File**: [`examples/gorgeous_telemetry_report.py`](gorgeous_telemetry_report.py)

Shows how to generate telemetry reports (console and JSON formats).

---

## Cloud PC Provisioning Examples

### Windows 365 E2E Demo

**Files**:
- `provision_w365_e2e.py` - Complete E2E workflow with 6 phases
- `provision_w365_cloudpc.py` - Cloud PC provisioning only

**Usage**:
```bash
# Full E2E (users + Cloud PC + activities + telemetry)
python provision_w365_e2e.py --workers 2 --duration-minutes 30

# Cloud PC provisioning only
python provision_w365_cloudpc.py
```

**Documentation**: [`docs/knowledge-worker-framework/WINDOWS365_E2E_DEMO.md`](../docs/knowledge-worker-framework/WINDOWS365_E2E_DEMO.md)

---

## Integration Testing

### Windows VM Provisioning

**File**: `integration_test_vm_provisioning.py`

Tests Windows VM provisioning with real Azure credentials (requires manual execution).

---

## How to Use These Examples

### For Learning

1. **Read the examples** to understand implementation patterns
2. **Review the specs** (in `specs/` directory) for complete requirements
3. **Check existing code** in `src/azure_haymaker/` for similar patterns
4. **Run examples** locally to see how they work

### For Contributing

1. **Copy starter template** to production location
2. **Write tests first** (TDD approach - tests before implementation)
3. **Implement TODOs** marked in starter code
4. **Run tests continuously** as you develop
5. **Submit PR** when all tests pass and E2E testing complete

### Running Examples

```bash
# Most examples are standalone Python scripts
python examples/siem_export_starter.py

# Some require Azure credentials
export AZURE_SUBSCRIPTION_ID="..."
export AZURE_TENANT_ID="..."
python examples/provision_w365_e2e.py
```

---

## Testing Examples

All examples include inline testing suggestions. For comprehensive testing patterns, see:

- **Unit Testing**: `tests/unit/` - Mock Azure clients, fast feedback
- **Integration Testing**: `tests/integration/` - Real Azure resources, comprehensive
- **Security Testing**: `tests/security/` - Vulnerability scanning, injection tests
- **E2E Testing**: Manual user workflow validation (MANDATORY before PR)

---

## Contributing New Examples

To add a new example:

1. **Create the file** in this directory
2. **Add docstring** explaining purpose and usage
3. **Include inline comments** for learning
4. **Add to this README** under appropriate section
5. **Test the example** to ensure it works
6. **Link to related specs** and documentation

**Template**:
```python
"""Brief description of what this example demonstrates.

Related Enhancement: Issue #XXX
Full Spec: specs/ENHANCEMENT_SPEC.md

Usage:
    python examples/your_example.py
"""

# Your code here with helpful comments
```

---

## Related Documentation

- [Enhancement Roadmap](../docs/ENHANCEMENT_ROADMAP.md) - Strategic plan for platform evolution
- [Specifications Index](../specs/README.md) - All implementation specs
- [Contributing to Enhancements](../docs/CONTRIBUTING_ENHANCEMENTS.md) - Contributor workflow
- [Quick Start for Contributors](../docs/QUICK_START_CONTRIBUTORS.md) - 15-minute onboarding

---

**Questions?** Open a GitHub issue or discussion!
