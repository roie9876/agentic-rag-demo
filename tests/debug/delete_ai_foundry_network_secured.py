#!/usr/bin/env python3
"""
AI Foundry Network-Secured Resource Deletion Script

This script follows the official Microsoft documentation for deleting
AI Foundry resources with secured network setup:

https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/virtual-networks

Official procedure:
1. Delete AI Foundry resource 
2. PURGE the AI Foundry resource from "Manage deleted resources"
3. Delete virtual network last

Created: 2025-07-08
Location: tests/debug/ (following new organization policy)
"""

import subprocess
import json
import time
import sys
from datetime import datetime
from typing import Tuple, Optional, List

def run_az_command(cmd: List[str], desc: str, timeout: int = 120) -> Tuple[bool, str, str]:
    """Run Azure CLI command with detailed logging."""
    print(f"\n🔧 {desc}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        success = result.returncode == 0
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        print(f"Return Code: {result.returncode}")
        if stdout:
            print(f"STDOUT:\n{stdout}")
        if stderr:
            print(f"STDERR:\n{stderr}")
        
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {desc}")
        
        return success, stdout, stderr
        
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT after {timeout}s: {desc}")
        return False, "", f"Command timed out after {timeout}s"
    except Exception as e:
        print(f"💥 EXCEPTION: {desc} - {str(e)}")
        return False, "", str(e)


def find_ai_foundry_resources(rg_name: str) -> List[dict]:
    """Find AI Foundry resources in the resource group."""
    print("=" * 80)
    print("🔍 SEARCHING FOR AI FOUNDRY RESOURCES")
    print("=" * 80)
    
    # Look for Machine Learning workspaces (AI Foundry projects)
    success, stdout, stderr = run_az_command(
        ["az", "resource", "list",
         "--resource-group", rg_name,
         "--resource-type", "Microsoft.MachineLearningServices/workspaces",
         "--output", "json"],
        "Searching for AI Foundry projects (ML workspaces)"
    )
    
    foundry_resources = []
    if success and stdout:
        try:
            resources = json.loads(stdout)
            foundry_resources.extend(resources)
        except json.JSONDecodeError:
            print("❌ Failed to parse ML workspace list")
    
    # Look for Cognitive Services accounts (AI Services)
    success, stdout, stderr = run_az_command(
        ["az", "resource", "list",
         "--resource-group", rg_name,
         "--resource-type", "Microsoft.CognitiveServices/accounts",
         "--output", "json"],
        "Searching for AI Services accounts"
    )
    
    if success and stdout:
        try:
            resources = json.loads(stdout)
            foundry_resources.extend(resources)
        except json.JSONDecodeError:
            print("❌ Failed to parse Cognitive Services list")
    
    print(f"📊 Found {len(foundry_resources)} AI Foundry related resource(s)")
    for resource in foundry_resources:
        print(f"  • {resource.get('name', 'Unknown')} ({resource.get('type', 'Unknown')})")
    
    return foundry_resources


def delete_ai_foundry_resources(foundry_resources: List[dict]) -> bool:
    """Delete AI Foundry resources."""
    print("=" * 80)
    print("🗑️ DELETING AI FOUNDRY RESOURCES")
    print("=" * 80)
    
    if not foundry_resources:
        print("✅ No AI Foundry resources found to delete")
        return True
    
    all_success = True
    for resource in foundry_resources:
        resource_name = resource.get('name', 'Unknown')
        resource_type = resource.get('type', 'Unknown')
        resource_group = resource.get('resourceGroup', 'Unknown')
        
        print(f"\n🗑️ Deleting {resource_type}: {resource_name}")
        
        success, stdout, stderr = run_az_command(
            ["az", "resource", "delete",
             "--resource-group", resource_group,
             "--name", resource_name,
             "--resource-type", resource_type],
            f"Deleting {resource_name}",
            timeout=300  # 5 minutes
        )
        
        if success:
            print(f"✅ Successfully deleted {resource_name}")
        else:
            print(f"❌ Failed to delete {resource_name}: {stderr}")
            all_success = False
    
    return all_success


def check_deleted_resources() -> None:
    """Check for deleted AI Foundry resources that need purging."""
    print("=" * 80)
    print("🔍 CHECKING FOR DELETED AI FOUNDRY RESOURCES TO PURGE")
    print("=" * 80)
    
    print("📋 Checking for deleted Machine Learning workspaces...")
    success, stdout, stderr = run_az_command(
        ["az", "ml", "workspace", "list-deleted", "--output", "json"],
        "Listing deleted ML workspaces"
    )
    
    if success and stdout:
        try:
            deleted_workspaces = json.loads(stdout)
            if deleted_workspaces:
                print(f"⚠️ Found {len(deleted_workspaces)} deleted workspace(s) that need purging:")
                for ws in deleted_workspaces:
                    ws_name = ws.get('name', 'Unknown')
                    ws_location = ws.get('location', 'Unknown')
                    deletion_time = ws.get('deletionTime', 'Unknown')
                    print(f"  • {ws_name} (Location: {ws_location}, Deleted: {deletion_time})")
                
                print("\n📋 TO PURGE THESE RESOURCES:")
                print("1. Go to Azure Portal")
                print("2. Navigate to 'Manage deleted resources'")
                print("3. Select your subscription")
                print("4. Find and purge the AI Foundry resources listed above")
                print("5. Wait for purge to complete before proceeding with VNet deletion")
            else:
                print("✅ No deleted ML workspaces found")
        except json.JSONDecodeError:
            print("❌ Failed to parse deleted workspaces list")
    
    # Check for deleted Cognitive Services accounts
    print("\n📋 Checking for deleted Cognitive Services accounts...")
    success, stdout, stderr = run_az_command(
        ["az", "cognitiveservices", "account", "list-deleted", "--output", "json"],
        "Listing deleted Cognitive Services accounts"
    )
    
    if success and stdout:
        try:
            deleted_accounts = json.loads(stdout)
            if deleted_accounts:
                print(f"⚠️ Found {len(deleted_accounts)} deleted Cognitive Services account(s):")
                for acc in deleted_accounts:
                    acc_name = acc.get('name', 'Unknown')
                    acc_location = acc.get('location', 'Unknown')
                    print(f"  • {acc_name} (Location: {acc_location})")
                
                print("\n🗑️ Purging deleted Cognitive Services accounts...")
                for acc in deleted_accounts:
                    acc_name = acc.get('name', 'Unknown')
                    acc_location = acc.get('location', 'Unknown')
                    
                    success, stdout, stderr = run_az_command(
                        ["az", "cognitiveservices", "account", "purge",
                         "--name", acc_name,
                         "--location", acc_location,
                         "--resource-group", "dummy"],  # Required but ignored for purge
                        f"Purging Cognitive Services account {acc_name}"
                    )
                    
                    if success:
                        print(f"✅ Successfully purged {acc_name}")
                    else:
                        print(f"⚠️ Failed to purge {acc_name}: {stderr}")
            else:
                print("✅ No deleted Cognitive Services accounts found")
        except json.JSONDecodeError:
            print("❌ Failed to parse deleted accounts list")


def wait_for_purge_completion() -> None:
    """Wait for resource purge to complete."""
    print("=" * 80)
    print("⏳ WAITING FOR PURGE COMPLETION")
    print("=" * 80)
    
    print("⏳ Waiting 60 seconds for purge operations to complete...")
    print("📝 Note: If you manually purged resources in the portal, ensure they are fully purged before continuing")
    
    for i in range(12):  # 60 seconds total
        print(f"⏳ {60 - (i * 5)} seconds remaining...")
        time.sleep(5)
    
    print("✅ Wait period completed")


def delete_virtual_network(rg_name: str) -> bool:
    """Delete the virtual network and associated resources."""
    print("=" * 80)
    print("🗑️ DELETING VIRTUAL NETWORK AND ASSOCIATED RESOURCES")
    print("=" * 80)
    
    # Try to delete the problematic subnet first
    print("\n🗑️ Step 1: Attempting to delete agent-subnet...")
    success, stdout, stderr = run_az_command(
        ["az", "network", "vnet", "subnet", "delete",
         "--resource-group", rg_name,
         "--vnet-name", "agent-vnet-test",
         "--name", "agent-subnet"],
        "Deleting agent-subnet"
    )
    
    if success:
        print("✅ Successfully deleted agent-subnet")
    else:
        print(f"⚠️ Could not delete agent-subnet: {stderr}")
        print("📝 This is expected if Service Association Links still exist")
    
    # Try to delete the entire VNet
    print("\n🗑️ Step 2: Attempting to delete VNet...")
    success, stdout, stderr = run_az_command(
        ["az", "network", "vnet", "delete",
         "--resource-group", rg_name,
         "--name", "agent-vnet-test"],
        "Deleting agent-vnet-test"
    )
    
    if success:
        print("✅ Successfully deleted VNet")
        return True
    else:
        print(f"❌ Failed to delete VNet: {stderr}")
        return False


def delete_resource_group(rg_name: str) -> bool:
    """Delete the resource group."""
    print("=" * 80)
    print("🗑️ DELETING RESOURCE GROUP")
    print("=" * 80)
    
    success, stdout, stderr = run_az_command(
        ["az", "group", "delete",
         "--name", rg_name,
         "--yes"],
        f"Deleting resource group '{rg_name}'"
    )
    
    if success:
        print(f"✅ Successfully deleted resource group: {rg_name}")
        return True
    else:
        print(f"❌ Failed to delete resource group: {rg_name}")
        print(f"Error: {stderr}")
        return False


def main():
    """Main function implementing the official AI Foundry deletion procedure."""
    print("🎯 AI FOUNDRY NETWORK-SECURED RESOURCE DELETION")
    print("=" * 80)
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Target Resource Group: bciep-test-8")
    print(f"📍 Script Location: tests/debug/ (following new organization policy)")
    print("=" * 80)
    print("\n📋 Following official Microsoft documentation:")
    print("https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/virtual-networks")
    print("\n🔄 Official procedure:")
    print("1. Delete AI Foundry resource")
    print("2. PURGE the AI Foundry resource from 'Manage deleted resources'") 
    print("3. Delete virtual network last")
    print("=" * 80)
    
    rg_name = "bciep-test-8"
    
    # Get user confirmation
    try:
        confirm = input("\n⚠️ Type 'FOLLOW OFFICIAL PROCEDURE' to proceed: ").strip()
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        return 1
    
    if confirm != "FOLLOW OFFICIAL PROCEDURE":
        print("❌ Deletion not confirmed")
        return 1
    
    # Step 1: Find AI Foundry resources
    foundry_resources = find_ai_foundry_resources(rg_name)
    
    # Step 2: Delete AI Foundry resources
    if foundry_resources:
        print("\n📋 Step 1: Deleting AI Foundry resources...")
        delete_success = delete_ai_foundry_resources(foundry_resources)
        
        if delete_success:
            print("✅ AI Foundry resources deleted successfully")
        else:
            print("⚠️ Some AI Foundry resources could not be deleted")
        
        # Wait for deletion to propagate
        print("\n⏳ Waiting 30 seconds for deletion to propagate...")
        time.sleep(30)
    else:
        print("ℹ️ No AI Foundry resources found in this resource group")
    
    # Step 3: Check for deleted resources that need purging
    print("\n📋 Step 2: Checking for deleted resources to purge...")
    check_deleted_resources()
    
    # Step 4: Wait for manual purge or automatic completion
    print("\n📋 Step 3: Waiting for purge completion...")
    wait_for_purge_completion()
    
    # Step 5: Delete virtual network
    print("\n📋 Step 4: Deleting virtual network...")
    vnet_success = delete_virtual_network(rg_name)
    
    # Step 6: Delete resource group
    print("\n📋 Step 5: Deleting resource group...")
    rg_success = delete_resource_group(rg_name)
    
    # Summary
    if rg_success:
        print("\n🎉 SUCCESS! AI Foundry network-secured deletion completed!")
        print("✅ All resources have been properly deleted following official procedure")
        return 0
    elif vnet_success:
        print("\n⚠️ PARTIAL SUCCESS!")
        print("✅ Virtual network deleted successfully")
        print("❌ Resource group deletion failed - may need manual intervention")
        return 0
    else:
        print("\n💔 DELETION INCOMPLETE")
        print("❌ Could not complete the official deletion procedure")
        print("💡 Manual intervention may be required")
        print("💡 Consider opening a Microsoft Support ticket")
        return 1


if __name__ == "__main__":
    sys.exit(main())
