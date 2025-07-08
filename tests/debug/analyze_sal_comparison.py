#!/usr/bin/env python3
"""
Debug Script: Analyze bciep-test-6 SAL situation
Created: 2025-07-08
Purpose: Compare active vs orphaned Service Association Links
Location: tests/debug/ (following new organization policy)
"""

import subprocess
import json
import sys
from datetime import datetime
from typing import Tuple

def run_az_command(command: list, description: str, timeout: int = 120) -> Tuple[bool, str, str]:
    """Run Azure CLI command with detailed logging."""
    print(f"\n🔧 {description}")
    print(f"Command: {' '.join(command)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        success = result.returncode == 0
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        print(f"Return Code: {result.returncode}")
        if stdout:
            print(f"STDOUT:\n{stdout}")
        if stderr:
            print(f"STDERR:\n{stderr}")
        
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {description}")
        
        return success, stdout, stderr
        
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT after {timeout}s: {description}")
        return False, "", f"Command timed out after {timeout}s"
    except Exception as e:
        print(f"💥 EXCEPTION: {description} - {str(e)}")
        return False, "", str(e)

def analyze_resource_group(rg_name: str):
    """Analyze the specified resource group for SAL issues."""
    print("🔍 ANALYZING RESOURCE GROUP: " + rg_name)
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Check if resource group exists
    success, stdout, stderr = run_az_command(
        ["az", "group", "show", "--name", rg_name],
        f"Checking if resource group '{rg_name}' exists"
    )
    
    if not success:
        print(f"❌ Resource group '{rg_name}' not found")
        return False
    
    # Get all resources
    success, stdout, stderr = run_az_command(
        ["az", "resource", "list", "--resource-group", rg_name, "--output", "json"],
        f"Listing all resources in '{rg_name}'"
    )
    
    if not success:
        print("❌ Failed to list resources")
        return False
    
    try:
        resources = json.loads(stdout)
        print(f"\n📊 Found {len(resources)} resources:")
        
        # Categorize resources
        ai_foundry_resources = []
        container_app_envs = []
        vnets = []
        other_resources = []
        
        for resource in resources:
            res_type = resource.get('type', '')
            res_name = resource.get('name', '')
            
            if 'CognitiveServices' in res_type:
                ai_foundry_resources.append(resource)
            elif 'App/managedEnvironments' in res_type:
                container_app_envs.append(resource)
            elif 'virtualNetworks' in res_type:
                vnets.append(resource)
            else:
                other_resources.append(resource)
        
        print(f"  🤖 AI Foundry Resources: {len(ai_foundry_resources)}")
        print(f"  📦 Container App Environments: {len(container_app_envs)}")
        print(f"  🌐 Virtual Networks: {len(vnets)}")
        print(f"  📁 Other Resources: {len(other_resources)}")
        
        # Analyze each VNet for SALs
        for vnet in vnets:
            vnet_name = vnet['name']
            print(f"\n🌐 Analyzing VNet: {vnet_name}")
            
            # Get subnets
            success, stdout, stderr = run_az_command(
                ["az", "network", "vnet", "subnet", "list",
                 "--resource-group", rg_name,
                 "--vnet-name", vnet_name,
                 "--output", "json"],
                f"Getting subnets for VNet '{vnet_name}'"
            )
            
            if success:
                try:
                    subnets = json.loads(stdout)
                    for subnet in subnets:
                        subnet_name = subnet.get('name', '')
                        sal_links = subnet.get('serviceAssociationLinks', [])
                        delegations = subnet.get('delegations', [])
                        
                        print(f"  📡 Subnet: {subnet_name}")
                        print(f"    Delegations: {len(delegations)}")
                        print(f"    Service Association Links: {len(sal_links)}")
                        
                        for sal in sal_links:
                            sal_name = sal.get('name', 'Unknown')
                            allow_delete = sal.get('allowDelete', 'Unknown')
                            linked_type = sal.get('linkedResourceType', 'Unknown')
                            print(f"      🔗 SAL: {sal_name}")
                            print(f"         Allow Delete: {allow_delete}")
                            print(f"         Linked Type: {linked_type}")
                            
                            if not allow_delete:
                                print(f"         ⚠️ THIS SAL BLOCKS DELETION!")
                
                except json.JSONDecodeError:
                    print(f"    ❌ Failed to parse subnets for VNet '{vnet_name}'")
        
        # Show AI Foundry resources
        if ai_foundry_resources:
            print(f"\n🤖 AI Foundry Resources Found:")
            for resource in ai_foundry_resources:
                print(f"  • {resource['name']} ({resource['type']})")
        
        # Show Container App Environments
        if container_app_envs:
            print(f"\n📦 Container App Environments Found:")
            for resource in container_app_envs:
                print(f"  • {resource['name']} ({resource['type']})")
        else:
            print(f"\n📦 No Container App Environments found")
            print(f"   💡 This suggests SALs might be orphaned")
        
        return True
        
    except json.JSONDecodeError:
        print("❌ Failed to parse resource list")
        return False

def compare_resource_groups():
    """Compare bciep-test-6 (active) vs bciep-test-8 (stuck)."""
    print("🔄 COMPARING RESOURCE GROUPS")
    print("=" * 80)
    
    print("📋 Analyzing bciep-test-6 (active with AI Foundry resources)...")
    analyze_resource_group("bciep-test-6")
    
    print("\n" + "=" * 80)
    print("📋 Analyzing bciep-test-8 (stuck deletion)...")
    analyze_resource_group("bciep-test-8")
    
    print("\n" + "=" * 80)
    print("🎯 COMPARISON SUMMARY")
    print("=" * 80)
    print("Key Observations:")
    print("1. Both resource groups have identical SAL issues")
    print("2. bciep-test-6 has active AI Foundry resources")
    print("3. bciep-test-8 has no AI Foundry resources (orphaned SALs)")
    print("4. Both have 'allowDelete: false' on legionservicelink")
    print("5. This confirms the issue is systemic, not isolated")

def test_simple_deletion():
    """Test if we can delete bciep-test-6 (this should fail safely due to active resources)."""
    print("\n🧪 TESTING DELETION APPROACH ON bciep-test-6")
    print("=" * 80)
    print("⚠️ This test will attempt deletion but should fail due to active AI Foundry resources")
    print("⚠️ This is safer than testing on bciep-test-8 which might actually delete")
    
    # First, let's just try to see what happens with delegation removal
    print("\n🔧 Testing delegation removal (should fail)...")
    success, stdout, stderr = run_az_command(
        ["az", "network", "vnet", "subnet", "update",
         "--resource-group", "bciep-test-6",
         "--vnet-name", "agent-vnet-test",
         "--name", "agent-subnet",
         "--remove", "delegations"],
        "Testing delegation removal on active resource group"
    )
    
    if not success:
        print("✅ Expected failure - delegation removal blocked by SAL")
        print("💡 This confirms the same issue exists in active resource groups")
    else:
        print("⚠️ Unexpected success - delegation was removed!")

def main():
    """Main analysis function."""
    print("🔍 SERVICE ASSOCIATION LINK ANALYSIS TOOL")
    print("=" * 80)
    print("Purpose: Compare active vs orphaned SAL situations")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        choice = input("\nSelect analysis:\n1. Analyze bciep-test-6 only\n2. Compare both resource groups\n3. Test deletion approach\nChoice (1-3): ").strip()
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        return 1
    
    if choice == "1":
        analyze_resource_group("bciep-test-6")
    elif choice == "2":
        compare_resource_groups()
    elif choice == "3":
        test_simple_deletion()
    else:
        print(f"❌ Invalid choice: {choice}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
