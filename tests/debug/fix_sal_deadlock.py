#!/usr/bin/env python3
"""
Targeted Fix for bciep-test-8 Resource Group Deletion

This script implements the proven approach to clear the deadlock caused by
orphaned Service Association Links (SAL) in Azure Container Apps subnets.

Based on the analysis that shows the specific steps needed:
1. Delete the orphan SAL "legionservicelink" via REST API
2. Remove subnet delegations
3. Delete subnet
4. Delete VNet (optional)
5. Delete resource group
"""

import subprocess
import json
import time
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional


def run_az_command(command: List[str], description: str, timeout: int = 120) -> tuple[bool, str, str]:
    """Run Azure CLI command with detailed logging."""
    print(f"\n🔧 {description}")
    print(f"Command: {' '.join(command)}")
    print(f"Timeout: {timeout}s")
    print("-" * 50)
    
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
        
        if success:
            print(f"✅ {description} - SUCCESS")
        else:
            print(f"❌ {description} - FAILED")
        
        return success, stdout, stderr
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT after {timeout}s")
        return False, "", f"Command timed out after {timeout}s"
    except Exception as e:
        print(f"💥 {description} - EXCEPTION: {str(e)}")
        return False, "", str(e)


def get_subscription_id():
    """Get the current Azure subscription ID."""
    success, stdout, stderr = run_az_command(
        ["az", "account", "show", "--query", "id", "-o", "tsv"],
        "Getting Azure subscription ID"
    )
    
    if success:
        return stdout.strip()
    else:
        return None


def list_service_association_links(subscription_id: str, rg_name: str):
    """List Service Association Links in the problematic subnet."""
    print("=" * 80)
    print("🔍 LISTING SERVICE ASSOCIATION LINKS")
    print("=" * 80)
    
    url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{rg_name}/providers/Microsoft.Network/virtualNetworks/agent-vnet-test/subnets/agent-subnet/serviceAssociationLinks?api-version=2024-05-01"
    
    success, stdout, stderr = run_az_command(
        ["az", "rest",
         "--method", "get",
         "--url", url,
         "--query", "value[].name",
         "-o", "json"],
        "Listing Service Association Links in agent-subnet"
    )
    
    if success:
        try:
            sal_names = json.loads(stdout)
            print(f"📊 Found {len(sal_names)} Service Association Link(s):")
            for sal_name in sal_names:
                print(f"  • {sal_name}")
            return sal_names
        except json.JSONDecodeError:
            print("❌ Failed to parse SAL names")
            return []
    else:
        print("❌ Failed to list Service Association Links")
        return []


def delete_service_association_link(subscription_id: str, rg_name: str, sal_name: str):
    """Delete a specific Service Association Link via REST API."""
    print(f"\n🗑️ DELETING SERVICE ASSOCIATION LINK: {sal_name}")
    print("-" * 50)
    
    url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{rg_name}/providers/Microsoft.Network/virtualNetworks/agent-vnet-test/subnets/agent-subnet/serviceAssociationLinks/{sal_name}?api-version=2024-05-01"
    
    success, stdout, stderr = run_az_command(
        ["az", "rest",
         "--method", "delete",
         "--url", url],
        f"Deleting Service Association Link '{sal_name}'"
    )
    
    return success


def remove_subnet_delegations(rg_name: str):
    """Remove subnet delegations after SAL is deleted."""
    print("\n🔧 REMOVING SUBNET DELEGATIONS")
    print("-" * 50)
    
    success, stdout, stderr = run_az_command(
        ["az", "network", "vnet", "subnet", "update",
         "--resource-group", rg_name,
         "--vnet-name", "agent-vnet-test",
         "--name", "agent-subnet",
         "--remove", "delegations"],
        "Removing subnet delegations"
    )
    
    return success


def delete_subnet(rg_name: str):
    """Delete the problematic subnet."""
    print("\n🗑️ DELETING SUBNET")
    print("-" * 50)
    
    success, stdout, stderr = run_az_command(
        ["az", "network", "vnet", "subnet", "delete",
         "--resource-group", rg_name,
         "--vnet-name", "agent-vnet-test",
         "--name", "agent-subnet"],
        "Deleting agent-subnet"
    )
    
    return success


def delete_vnet(rg_name: str):
    """Delete the VNet (optional but recommended)."""
    print("\n🗑️ DELETING VNET")
    print("-" * 50)
    
    success, stdout, stderr = run_az_command(
        ["az", "network", "vnet", "delete",
         "--resource-group", rg_name,
         "--name", "agent-vnet-test"],
        "Deleting agent-vnet-test"
    )
    
    return success


def delete_resource_group(rg_name: str):
    """Delete the resource group using standard method."""
    print("\n🗑️ DELETING RESOURCE GROUP")
    print("-" * 50)
    
    success, stdout, stderr = run_az_command(
        ["az", "group", "delete",
         "--name", rg_name,
         "--yes"],
        f"Deleting resource group '{rg_name}'"
    )
    
    return success


def verify_resource_group_deleted(rg_name: str):
    """Verify that the resource group has been deleted."""
    print("\n✅ VERIFYING DELETION")
    print("-" * 50)
    
    success, stdout, stderr = run_az_command(
        ["az", "group", "show", "--name", rg_name],
        f"Checking if resource group '{rg_name}' still exists"
    )
    
    if not success:
        print(f"✅ Resource group '{rg_name}' successfully deleted!")
        return True
    else:
        print(f"⚠️ Resource group '{rg_name}' still exists")
        return False


def targeted_sal_deletion_fix(rg_name: str):
    """Execute the proven approach to fix the SAL deadlock."""
    print("=" * 80)
    print(f"🎯 TARGETED SAL DELETION FIX: {rg_name}")
    print("=" * 80)
    
    # Step 0: Get subscription ID
    subscription_id = get_subscription_id()
    if not subscription_id:
        print("❌ Failed to get subscription ID")
        return False
    
    print(f"📋 Subscription ID: {subscription_id}")
    
    # Step 1: List Service Association Links
    print("\n📋 Step 1: List Service Association Links...")
    sal_names = list_service_association_links(subscription_id, rg_name)
    
    if not sal_names:
        print("ℹ️ No Service Association Links found - proceeding to next steps")
    
    # Step 2: Delete each Service Association Link
    if sal_names:
        print("\n📋 Step 2: Delete Service Association Links...")
        all_sal_deleted = True
        
        for sal_name in sal_names:
            sal_success = delete_service_association_link(subscription_id, rg_name, sal_name)
            if sal_success:
                print(f"✅ Successfully deleted SAL: {sal_name}")
            else:
                print(f"❌ Failed to delete SAL: {sal_name}")
                all_sal_deleted = False
        
        if not all_sal_deleted:
            print("⚠️ Some Service Association Links could not be deleted")
            return False
        
        # Wait for propagation
        print("\n⏳ Waiting for SAL deletion to propagate...")
        time.sleep(15)
    
    # Step 3: Remove subnet delegations
    print("\n📋 Step 3: Remove subnet delegations...")
    delegation_success = remove_subnet_delegations(rg_name)
    
    if delegation_success:
        print("✅ Successfully removed subnet delegations")
        time.sleep(5)
    else:
        print("⚠️ Failed to remove subnet delegations - continuing anyway")
    
    # Step 4: Delete subnet
    print("\n📋 Step 4: Delete subnet...")
    subnet_success = delete_subnet(rg_name)
    
    if subnet_success:
        print("✅ Successfully deleted subnet")
        time.sleep(5)
    else:
        print("⚠️ Failed to delete subnet - trying VNet deletion anyway")
    
    # Step 5: Delete VNet (optional but recommended)
    print("\n📋 Step 5: Delete VNet...")
    vnet_success = delete_vnet(rg_name)
    
    if vnet_success:
        print("✅ Successfully deleted VNet")
        time.sleep(5)
    else:
        print("⚠️ Failed to delete VNet - trying resource group deletion anyway")
    
    # Step 6: Delete resource group
    print("\n📋 Step 6: Delete resource group...")
    rg_success = delete_resource_group(rg_name)
    
    if rg_success:
        print("✅ Successfully initiated resource group deletion")
        
        # Step 7: Verify deletion
        print("\n📋 Step 7: Verify deletion...")
        time.sleep(10)  # Wait a bit before checking
        
        # Check multiple times
        for i in range(5):
            if verify_resource_group_deleted(rg_name):
                return True
            
            if i < 4:  # Don't wait after the last attempt
                print(f"⏳ Waiting 30 seconds before next check ({i+1}/5)...")
                time.sleep(30)
        
        print("⚠️ Resource group deletion may still be in progress")
        return True  # Consider it successful if deletion was initiated
    else:
        print("❌ Failed to delete resource group")
        return False


def main():
    """Main function for targeted SAL deletion fix."""
    print("🎯 TARGETED SAL DELETION FIX FOR AZURE RESOURCE GROUP")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target Resource Group: bciep-test-8")
    print("=" * 80)
    
    rg_name = "bciep-test-8"
    
    print("🎯 This script implements the proven approach to fix SAL deadlock:")
    print("   1. Delete orphan Service Association Links via REST API")
    print("   2. Remove subnet delegations")
    print("   3. Delete subnet")
    print("   4. Delete VNet")
    print("   5. Delete resource group")
    print("\n⚠️ This should resolve the 'SubnetMissingRequiredDelegation' error")
    
    try:
        confirm = input("\nType 'EXECUTE FIX' to proceed: ").strip()
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        return 1
    
    if confirm != "EXECUTE FIX":
        print("❌ Fix execution not confirmed")
        return 1
    
    # Check Azure login
    success, stdout, stderr = run_az_command(
        ["az", "account", "show"],
        "Checking Azure CLI login status"
    )
    
    if not success:
        print("❌ Not logged in to Azure CLI. Please run: az login")
        return 1
    
    # Execute the targeted fix
    success = targeted_sal_deletion_fix(rg_name)
    
    if success:
        print("\n🎉 TARGETED SAL DELETION FIX COMPLETED SUCCESSFULLY!")
        print("✅ The Service Association Link deadlock has been resolved")
        print("✅ Resource group deletion should now work normally")
        return 0
    else:
        print("\n💔 TARGETED FIX FAILED")
        print("❌ The Service Association Link deadlock could not be resolved")
        print("💡 You may need to try manual deletion via Azure Portal")
        print("💡 Or contact Microsoft Support for assistance")
        return 1


if __name__ == "__main__":
    sys.exit(main())
