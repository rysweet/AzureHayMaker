#!/usr/bin/env python3
"""
Integration Test: Windows VM Provisioning

Tests WindowsVMManager with REAL Azure credentials.
WARNING: This provisions a REAL VM and incurs Azure costs (~$0.10-0.20 for the test).

Usage:
    python integration_test_vm_provisioning.py [--provision] [--cleanup-only]

    --provision: Actually provision a VM (default: dry-run validation only)
    --cleanup-only: Only cleanup existing test VMs

Requirements:
    - Azure CLI authenticated (`az login`)
    - Or Service Principal credentials in environment variables
"""

import asyncio
import sys
import time
from datetime import datetime

from azure.identity.aio import DefaultAzureCredential
from azure.mgmt.compute.aio import ComputeManagementClient
from azure.mgmt.network.aio import NetworkManagementClient

# Add project to path
sys.path.insert(0, '/home/azureuser/src/h2/worktrees/feat-issue-120-windows-vm-fallback')

from src.azure_haymaker.knowledge_worker.endpoints.windows_vm import WindowsVMManager
from src.azure_haymaker.knowledge_worker.models.worker import WorkerIdentity, WorkerPersona, EndpointType


async def validate_azure_connectivity():
    """Validate Azure credentials and connectivity."""
    print("=" * 80)
    print("STEP 1: Validating Azure Connectivity")
    print("=" * 80)

    try:
        credential = DefaultAzureCredential()

        # Get subscription ID from az cli
        import subprocess
        result = subprocess.run(['az', 'account', 'show', '--query', 'id', '-o', 'tsv'],
                               capture_output=True, text=True, check=True)
        subscription_id = result.stdout.strip()

        print(f"✅ Subscription ID: {subscription_id}")

        # Test compute client
        compute_client = ComputeManagementClient(credential, subscription_id)
        print("✅ Compute Management Client initialized")

        # Test network client
        network_client = NetworkManagementClient(credential, subscription_id)
        print("✅ Network Management Client initialized")

        # List resource groups (test API access)
        import subprocess
        result = subprocess.run(['az', 'group', 'list', '--query', '[].name', '-o', 'tsv'],
                               capture_output=True, text=True, check=True)
        rgs = result.stdout.strip().split('\n')
        print(f"✅ Found {len(rgs)} resource groups")
        print(f"   Available RGs: {', '.join(rgs[:5])}")

        return subscription_id, credential, compute_client, network_client, rgs

    except Exception as e:
        print(f"❌ Azure connectivity failed: {e}")
        return None


async def _ensure_vnet_exists(subscription_id, resource_group, location):
    """Ensure VNet exists for testing, create if needed."""
    import subprocess

    # Check if VNet exists
    result = subprocess.run(
        ['az', 'network', 'vnet', 'list', '--resource-group', resource_group, '--query', '[0].id', '-o', 'tsv'],
        capture_output=True, text=True
    )

    if result.returncode == 0 and result.stdout.strip():
        vnet_id = result.stdout.strip()
        print(f"Using existing VNet: {vnet_id}")
        # Get default subnet
        result = subprocess.run(
            ['az', 'network', 'vnet', 'subnet', 'list', '--resource-group', resource_group,
             '--vnet-name', vnet_id.split('/')[-1], '--query', '[0].id', '-o', 'tsv'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()

    # Create minimal VNet for testing
    print(f"Creating test VNet in {resource_group}...")
    vnet_name = f"vnet-test-{int(time.time())}"
    subprocess.run(
        ['az', 'network', 'vnet', 'create',
         '--resource-group', resource_group,
         '--name', vnet_name,
         '--address-prefix', '10.0.0.0/16',
         '--subnet-name', 'default',
         '--subnet-prefix', '10.0.0.0/24',
         '--location', location],
        check=True, capture_output=True
    )

    # Get subnet ID
    result = subprocess.run(
        ['az', 'network', 'vnet', 'subnet', 'show',
         '--resource-group', resource_group,
         '--vnet-name', vnet_name,
         '--name', 'default',
         '--query', 'id', '-o', 'tsv'],
        capture_output=True, text=True, check=True
    )

    return result.stdout.strip()


async def test_vm_manager_initialization(subscription_id, credential, compute_client, network_client):
    """Test WindowsVMManager initialization."""
    print("\n" + "=" * 80)
    print("STEP 2: Testing WindowsVMManager Initialization")
    print("=" * 80)

    try:
        # Pick a resource group (or create test RG)
        resource_group = "rg-haymaker-test"  # You may need to create this
        location = "eastus"  # Same as RG location
        run_id = f"integration-test-{int(time.time())}"

        # Create or get VNet for testing
        print(f"Checking for VNet in {resource_group}...")
        vnet_id = await _ensure_vnet_exists(subscription_id, resource_group, location)
        print(f"✅ VNet ID: {vnet_id}")

        # Get the public IP of the test machine for NSG whitelist
        import subprocess
        try:
            # Get public IP from ipify.org
            result = subprocess.run(['curl', '-s', 'https://api.ipify.org'],
                                   capture_output=True, text=True, timeout=5)
            public_ip = result.stdout.strip()
            # Add /32 for single IP CIDR notation
            allowed_ips = [f"{public_ip}/32"]
            print(f"✅ Detected public IP for NSG whitelist: {public_ip}")
        except Exception as e:
            print(f"⚠️  Could not detect public IP: {e}")
            print("   Using RFC 5737 test network range instead")
            # Fallback to test network (this will block actual RDP access)
            allowed_ips = ["203.0.113.0/24"]

        # Initialize manager
        manager = WindowsVMManager(
            compute_client=compute_client,
            network_client=network_client,
            subscription_id=subscription_id,
            resource_group_name=resource_group,
            location=location,
            run_id=run_id,
            vnet_id=vnet_id,  # Required parameter
            allowed_source_ips=allowed_ips,  # REQUIRED - explicit IPs only
            vm_size="Standard_B2s",  # Available in most regions
        )

        print(f"✅ WindowsVMManager initialized")
        print(f"   Resource Group: {resource_group}")
        print(f"   Location: {location}")
        print(f"   Run ID: {run_id}")
        print(f"   VM Size: Standard_B1s (testing)")

        return manager, resource_group, run_id

    except Exception as e:
        print(f"❌ Manager initialization failed: {e}")
        return None, None, None


async def test_vm_provisioning(manager, run_id):
    """Test actual VM provisioning (WARNING: COSTS MONEY)."""
    print("\n" + "=" * 80)
    print("STEP 3: Provisioning Test VM")
    print("=" * 80)
    print("⚠️  WARNING: This will provision a REAL Windows VM!")
    print("⚠️  Estimated cost: ~$0.10-0.20 for 10-15 minutes")
    print("⚠️  VM will be cleaned up after test")
    print()

    start_time = time.time()

    try:
        # Create test worker
        worker = WorkerIdentity(
            worker_id=f"integration-test-{int(time.time())}",
            display_name="Integration Test Worker",
            department="engineering",  # Required field
            persona=WorkerPersona.EXECUTIVE,
            endpoint_type=EndpointType.WINDOWS_VM,
            user_principal_name=f"test-{int(time.time())}@test.local",
        )

        print(f"Provisioning VM for worker: {worker.worker_id}")
        print("This will take 10-15 minutes...")
        print()

        # Provision VM
        result = await manager.provision_vm(worker)

        elapsed = time.time() - start_time

        print(f"\n✅ VM PROVISIONED SUCCESSFULLY!")
        print(f"   Elapsed time: {elapsed/60:.1f} minutes")
        print(f"   VM Name: {result['vm_name']}")
        print(f"   Public IP: {result['public_ip']}")
        print(f"   Admin User: {result['admin_username']}")
        print(f"   RDP Port: {result['rdp_port']}")
        print(f"   Password: {'*' * len(result['admin_password'])} (hidden)")

        # Test RDP connectivity
        print("\n" + "=" * 80)
        print("STEP 4: Testing RDP Connectivity")
        print("=" * 80)

        is_ready = await manager.verify_computer_use_ready(
            result['vm_name'],
            result['public_ip']
        )

        if is_ready:
            print("✅ RDP port 3389 is accessible")
        else:
            print("⚠️  RDP port not yet accessible (may need more time)")

        return result

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ VM provisioning failed after {elapsed/60:.1f} minutes")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_vm_cleanup(manager, vm_name):
    """Test VM cleanup."""
    print("\n" + "=" * 80)
    print("STEP 5: Cleaning Up Test VM")
    print("=" * 80)

    try:
        print(f"Deleting VM: {vm_name}")
        print("This may take 2-5 minutes...")

        success = await manager.delete_vm(vm_name)

        if success:
            print("✅ VM and resources deleted successfully")
        else:
            print("⚠️  VM deletion may have had issues (check Azure Portal)")

        return success

    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False


async def cleanup_test_vms():
    """Cleanup any existing test VMs."""
    print("=" * 80)
    print("Cleaning Up Existing Test VMs")
    print("=" * 80)

    import subprocess

    # List VMs with "integration-test" in name
    result = subprocess.run(
        ['az', 'vm', 'list', '--query', "[?contains(name, 'integration-test')].{name:name, rg:resourceGroup}", '-o', 'json'],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        import json
        vms = json.loads(result.stdout)

        if vms:
            print(f"Found {len(vms)} test VMs to clean up:")
            for vm in vms:
                print(f"  - {vm['name']} (in {vm['rg']})")
                # Delete VM and resources
                subprocess.run(['az', 'vm', 'delete', '--name', vm['name'], '--resource-group', vm['rg'], '--yes'])
                print(f"    ✅ Deleted")
        else:
            print("No test VMs found")
    else:
        print("Could not list VMs")


async def main():
    """Run integration tests."""
    args = sys.argv[1:]

    do_provision = '--provision' in args
    cleanup_only = '--cleanup-only' in args

    print("\n" + "=" * 80)
    print("Windows VM Provisioning - Integration Test")
    print("=" * 80)
    print(f"Mode: {'CLEANUP ONLY' if cleanup_only else 'PROVISION' if do_provision else 'VALIDATION ONLY (DRY RUN)'}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 80)

    if cleanup_only:
        await cleanup_test_vms()
        return

    # Step 1: Validate Azure connectivity
    result = await validate_azure_connectivity()
    if not result:
        print("\n❌ FAILED: Azure connectivity issues")
        return 1

    subscription_id, credential, compute_client, network_client, rgs = result

    # Step 2: Initialize manager
    manager, resource_group, run_id = await test_vm_manager_initialization(
        subscription_id, credential, compute_client, network_client
    )

    if not manager:
        print("\n❌ FAILED: Manager initialization issues")
        return 1

    if not do_provision:
        print("\n" + "=" * 80)
        print("✅ VALIDATION PASSED")
        print("=" * 80)
        print("Azure connectivity: ✅")
        print("Manager initialization: ✅")
        print()
        print("To provision a REAL VM, run:")
        print("  python integration_test_vm_provisioning.py --provision")
        print()
        print("WARNING: Provisioning incurs Azure costs (~$0.10-0.20 for test)")
        return 0

    # Step 3: Provision VM (if --provision flag)
    vm_result = await test_vm_provisioning(manager, run_id)

    if not vm_result:
        print("\n❌ FAILED: VM provisioning issues")
        return 1

    # Step 4: Cleanup
    cleanup_success = await test_vm_cleanup(manager, vm_result['vm_name'])

    print("\n" + "=" * 80)
    print("✅ INTEGRATION TEST COMPLETE")
    print("=" * 80)
    print("Azure connectivity: ✅")
    print("Manager initialization: ✅")
    print(f"VM provisioning: {'✅' if vm_result else '❌'}")
    print(f"VM cleanup: {'✅' if cleanup_success else '⚠️'}")

    return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
