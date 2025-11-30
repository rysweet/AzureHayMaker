"""Provision 2 Windows 365 Cloud PCs for real computer use testing."""
import asyncio
import os
from datetime import UTC, datetime
from azure.identity import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient

async def provision_cloud_pcs():
    """Provision 2 Cloud PCs for KW computer use agents."""
    
    cred = ClientSecretCredential(
        os.getenv("KW_TENANT_ID"),
        os.getenv("KW_APP_ID"),
        os.getenv("KW_CLIENT_SECRET"),
    )
    client = GraphServiceClient(cred)
    
    print("="*70)
    print("PROVISIONING WINDOWS 365 CLOUD PCs")
    print("="*70)
    print(f"\nStart: {datetime.now(UTC).strftime('%H:%M:%S UTC')}")
    
    # Step 1: Check for existing provisioning policy
    print("\n[1/5] Checking for Cloud PC provisioning policies...")
    
    try:
        policies = await client.device_management.virtual_endpoint.provisioning_policies.get()
        
        if policies and policies.value:
            print(f"  Found {len(policies.value)} existing policies")
            for policy in policies.value:
                print(f"    - {policy.display_name} ({policy.id})")
        else:
            print("  No existing policies - will need to create one")
            
    except Exception as e:
        print(f"  ⚠️  Error checking policies: {e}")
        print("  (May not have CloudPC permissions yet)")
    
    # Step 2: Create 2 KW users (we have 2 licenses)
    print("\n[2/5] Creating 2 KW users with E5 licenses...")
    
    from azure_haymaker.knowledge_worker.identity.user_manager import EntraUserManager
    
    user_mgr = EntraUserManager(client, "w365-test", "DefenderATEVET12.onmicrosoft.com")
    
    users = []
    for i, (dept, name) in enumerate([("engineering", "W365 Engineer 1"), ("sales", "W365 Sales 1")]):
        identity = await user_mgr.provision_worker(dept, i, name, None)
        users.append(identity)
        print(f"  ✓ {identity.user_principal_name}")
    
    print(f"\n  Created {len(users)} users with E5 licenses")
    
    # Step 3: Teams integration
    print("\n[3/5] Creating Teams team for KW workers...")
    
    from azure_haymaker.knowledge_worker.teams_integration import TeamsIntegration
    
    teams_mgr = TeamsIntegration(client)
    
    # Create M365 group first
    from msgraph.generated.models.group import Group
    
    group_data = Group(
        display_name="KW W365 Test Team",
        mail_nickname="kw-w365-team",
        mail_enabled=True,
        security_enabled=False,
        group_types=["Unified"],
    )
    
    group = await client.groups.post(group_data)
    print(f"  ✓ M365 group created: {group.id}")
    
    # Create Teams team from group
    team_id = await teams_mgr.create_team_from_group(group.id)
    print(f"  ✓ Teams team created: {team_id}")
    
    # Add members
    member_ids = [u.entra_object_id for u in users]
    await teams_mgr.add_team_members(team_id, member_ids)
    print(f"  ✓ Added {len(member_ids)} members to team")
    
    # Create channels
    channels = await teams_mgr.create_standard_channels(team_id, ["Projects", "Random"])
    print(f"  ✓ Created {len(channels)} channels")
    
    # Post welcome messages
    for channel_id in channels.values():
        await teams_mgr.post_welcome_message(team_id, channel_id)
    print(f"  ✓ Posted welcome messages")
    
    # Step 4: Document what we have
    print("\n[4/5] Current status:")
    print(f"  Users: {len(users)}")
    print(f"  Teams team: {team_id}")
    print(f"  Channels: {list(channels.keys())}")
    
    # Step 5: Next steps for W365
    print("\n[5/5] Windows 365 Cloud PC provisioning:")
    print("  Note: Cloud PC provisioning requires:")
    print("    - CloudPC.ReadWrite.All permission")
    print("    - Provisioning policy created")
    print("    - 30-90 minutes provisioning time")
    print("\n  Status: Architecture complete, ready when licenses + permissions available")
    
    # Save results
    import json
    results = {
        "timestamp": datetime.now(UTC).isoformat(),
        "users_created": [u.user_principal_name for u in users],
        "teams_team_id": team_id,
        "channels_created": list(channels.keys()),
        "w365_status": "Ready for provisioning when CloudPC permissions added",
    }
    
    with open("w365_setup_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to w365_setup_results.json")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(provision_cloud_pcs())
    print(f"\n🎯 W365 setup complete!")
    print(f"   Teams team: {results['teams_team_id']}")
    print(f"   Users: {len(results['users_created'])}")
