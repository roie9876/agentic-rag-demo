#!/usr/bin/env python3
"""
Force Delete Stuck Resource Group Script

This script handles the specific case where Azure Container Apps service association links
block resource group deletion indefinitely. It uses advanced techniques to break the deadlock.
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


def find_container_app_environments():
    """Find all Container App Environments that might be linked to the stuck subnet."""
    print("=" * 80)
    print("🔍 SEARCHING FOR CONTAINER APP ENVIRONMENTS")
    print("=" * 80)
    
    # Search in all resource groups
    success, stdout, stderr = run_az_command(
        ["az", "resource", "list", 
         "--resource-type", "Microsoft.App/managedEnvironments",
         "--output", "json"],
        "Searching for Container App Environments across all resource groups"
    )
    
    environments = []
    if success:
        try:
            envs = json.loads(stdout)
            print(f"📊 Found {len(envs)} Container App Environment(s)")
            
            for env in envs:
                env_name = env.get('name', 'Unknown')
                env_rg = env.get('resourceGroup', 'Unknown')
                env_location = env.get('location', 'Unknown')
                
                print(f"  🏗️ Environment: {env_name}")
                print(f"    📁 Resource Group: {env_rg}")
                print(f"    📍 Location: {env_location}")
                
                # Get detailed info about this environment
                success, stdout, stderr = run_az_command(
                    ["az", "containerapp", "env", "show",
                     "--name", env_name,
                     "--resource-group", env_rg,
                     "--output", "json"],
                    f"Getting details for Container App Environment '{env_name}'"
                )
                
                if success:
                    try:
                        env_details = json.loads(stdout)
                        vnet_config = env_details.get('properties', {}).get('vnetConfiguration', {})
                        if vnet_config:
                            subnet_id = vnet_config.get('infrastructureSubnetId', '')
                            print(f"    🌐 Linked Subnet: {subnet_id}")
                            
                            # Check if this is linked to our problematic subnet
                            if 'bciep-test-8' in subnet_id and 'agent-subnet' in subnet_id:
                                print(f"    ⚠️ THIS ENVIRONMENT IS LINKED TO OUR PROBLEMATIC SUBNET!")
                                environments.append({
                                    'name': env_name,
                                    'resourceGroup': env_rg,
                                    'location': env_location,
                                    'subnetId': subnet_id,
                                    'isProblematic': True
                                })
                            else:
                                environments.append({
                                    'name': env_name,
                                    'resourceGroup': env_rg,
                                    'location': env_location,
                                    'subnetId': subnet_id,
                                    'isProblematic': False
                                })
                        else:
                            print(f"    ✅ No VNet configuration (not linked to any subnet)")
                            environments.append({
                                'name': env_name,
                                'resourceGroup': env_rg,
                                'location': env_location,
                                'subnetId': '',
                                'isProblematic': False
                            })
                    except json.JSONDecodeError:
                        print(f"    ❌ Failed to parse environment details")
                
        except json.JSONDecodeError:
            print("❌ Failed to parse Container App Environments list")
    
    return environments


def delete_problematic_container_apps(environments: List[Dict]):
    """Delete Container App Environments that are blocking our subnet."""
    print("=" * 80)
    print("🗑️ DELETING PROBLEMATIC CONTAINER APP ENVIRONMENTS")
    print("=" * 80)
    
    problematic_envs = [env for env in environments if env.get('isProblematic', False)]
    
    if not problematic_envs:
        print("✅ No problematic Container App Environments found")
        return True
    
    print(f"⚠️ Found {len(problematic_envs)} problematic environment(s) to delete:")
    
    all_success = True
    for env in problematic_envs:
        env_name = env['name']
        env_rg = env['resourceGroup']
        
        print(f"\n🗑️ Deleting Container App Environment: {env_name}")
        print(f"   📁 Resource Group: {env_rg}")
        print(f"   🌐 Linked Subnet: {env['subnetId']}")
        
        # First, try to delete any container apps in this environment
        success, stdout, stderr = run_az_command(
            ["az", "containerapp", "list",
             "--environment-name", env_name,
             "--resource-group", env_rg,
             "--output", "json"],
            f"Getting container apps in environment '{env_name}'"
        )
        
        if success:
            try:
                apps = json.loads(stdout)
                print(f"   📊 Found {len(apps)} container app(s) in environment")
                
                for app in apps:
                    app_name = app.get('name', 'Unknown')
                    print(f"   🗑️ Deleting container app: {app_name}")
                    
                    success, stdout, stderr = run_az_command(
                        ["az", "containerapp", "delete",
                         "--name", app_name,
                         "--resource-group", env_rg,
                         "--yes"],
                        f"Deleting container app '{app_name}'",
                        timeout=300
                    )
                    
                    if not success:
                        print(f"   ⚠️ Failed to delete container app '{app_name}': {stderr}")
                        all_success = False
                
            except json.JSONDecodeError:
                print(f"   ❌ Failed to parse container apps list")
        
        # Now delete the environment itself
        print(f"\n🗑️ Deleting Container App Environment: {env_name}")
        success, stdout, stderr = run_az_command(
            ["az", "containerapp", "env", "delete",
             "--name", env_name,
             "--resource-group", env_rg,
             "--yes"],
            f"Deleting Container App Environment '{env_name}'",
            timeout=600  # 10 minutes
        )
        
        if success:
            print(f"✅ Successfully deleted Container App Environment '{env_name}'")
        else:
            print(f"❌ Failed to delete Container App Environment '{env_name}': {stderr}")
            all_success = False
    
    return all_success


def force_clear_subnet_associations(rg_name: str):
    """Use advanced techniques to clear subnet associations."""
    print("=" * 80)
    print("🔧 FORCE CLEARING SUBNET ASSOCIATIONS")
    print("=" * 80)
    
    # Method 1: Try to update the subnet to remove service association links
    print("\n🔧 Method 1: Direct subnet update...")
    
    success, stdout, stderr = run_az_command(
        ["az", "network", "vnet", "subnet", "update",
         "--resource-group", rg_name,
         "--vnet-name", "agent-vnet-test",
         "--name", "agent-subnet",
         "--set", "serviceAssociationLinks=[]",
         "--set", "delegations=[]"],
        "Attempting to clear service association links and delegations"
    )
    
    if success:
        print("✅ Successfully cleared subnet associations")
        return True
    
    # Method 2: Try to recreate the subnet
    print("\n🔧 Method 2: Recreating subnet...")
    
    # First, delete the subnet
    success, stdout, stderr = run_az_command(
        ["az", "network", "vnet", "subnet", "delete",
         "--resource-group", rg_name,
         "--vnet-name", "agent-vnet-test",
         "--name", "agent-subnet"],
        "Deleting problematic subnet"
    )
    
    if success:
        print("✅ Successfully deleted problematic subnet")
        # Note: We don't recreate it since we're deleting the whole RG anyway
        return True
    
    print("⚠️ All subnet clearing methods failed")
    return False


def attempt_azure_rest_api_deletion(rg_name: str):
    """Use Azure REST API for more aggressive deletion."""
    print("=" * 80)
    print("🌐 ATTEMPTING AZURE REST API DELETION")
    print("=" * 80)
    
    print("📝 Getting access token...")
    success, stdout, stderr = run_az_command(
        ["az", "account", "get-access-token", "--output", "json"],
        "Getting Azure access token"
    )
    
    if not success:
        print("❌ Failed to get access token")
        return False
    
    try:
        token_info = json.loads(stdout)
        access_token = token_info.get('accessToken', '')
        subscription_id = None
        
        # Get subscription ID
        success, stdout, stderr = run_az_command(
            ["az", "account", "show", "--output", "json"],
            "Getting subscription information"
        )
        
        if success:
            account_info = json.loads(stdout)
            subscription_id = account_info.get('id', '')
        
        if not subscription_id:
            print("❌ Failed to get subscription ID")
            return False
        
        # Use curl to call Azure REST API for force deletion
        print(f"🌐 Calling Azure REST API to force delete resource group...")
        
        # Azure REST API endpoint for force deletion
        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourcegroups/{rg_name}"
        
        success, stdout, stderr = run_az_command(
            ["curl", "-X", "DELETE",
             "-H", f"Authorization: Bearer {access_token}",
             "-H", "Content-Type: application/json",
             f"{url}?forceDeletionTypes=Microsoft.App/managedEnvironments&api-version=2021-04-01"],
            "Force deleting resource group via REST API",
            timeout=300
        )
        
        if success:
            print("✅ REST API deletion request submitted")
            return True
        else:
            print(f"❌ REST API deletion failed: {stderr}")
            return False
            
    except json.JSONDecodeError:
        print("❌ Failed to parse token information")
        return False


def comprehensive_force_deletion(rg_name: str):
    """Comprehensive approach to force delete the stuck resource group."""
    print("=" * 80)
    print(f"💥 COMPREHENSIVE FORCE DELETION: {rg_name}")
    print("=" * 80)
    
    print("⚠️ This will use all available methods to force delete the resource group")
    print("⚠️ This may take up to 30 minutes")
    
    # Step 1: Find and delete problematic Container App Environments
    print("\n📋 Step 1: Finding and deleting Container App Environments...")
    environments = find_container_app_environments()
    
    if environments:
        delete_success = delete_problematic_container_apps(environments)
        if delete_success:
            print("✅ Container App Environments cleaned up")
            time.sleep(60)  # Wait for cleanup to propagate
        else:
            print("⚠️ Some Container App Environments could not be deleted")
    
    # Step 2: Force clear subnet associations
    print("\n📋 Step 2: Force clearing subnet associations...")
    subnet_success = force_clear_subnet_associations(rg_name)
    if subnet_success:
        print("✅ Subnet associations cleared")
        time.sleep(30)
    
    # Step 3: Try standard resource group deletion again
    print("\n📋 Step 3: Attempting standard resource group deletion...")
    success, stdout, stderr = run_az_command(
        ["az", "group", "delete",
         "--name", rg_name,
         "--yes", "--no-wait"],
        f"Standard deletion of resource group '{rg_name}'"
    )
    
    if success:
        print(f"✅ Standard deletion initiated for '{rg_name}'")
        
        # Check for completion
        for i in range(10):
            print(f"\n⏳ Checking deletion status (attempt {i+1}/10)...")
            time.sleep(30)
            
            success, stdout, stderr = run_az_command(
                ["az", "group", "show", "--name", rg_name],
                f"Checking if resource group '{rg_name}' still exists"
            )
            
            if not success:
                print(f"✅ Resource group '{rg_name}' successfully deleted!")
                return True
            else:
                print(f"⏳ Still exists, waiting...")
        
        print("⚠️ Standard deletion is taking too long, trying REST API...")
    
    # Step 4: Try Azure REST API deletion
    print("\n📋 Step 4: Attempting REST API force deletion...")
    api_success = attempt_azure_rest_api_deletion(rg_name)
    
    if api_success:
        # Check for completion after REST API call
        for i in range(10):
            print(f"\n⏳ Checking REST API deletion status (attempt {i+1}/10)...")
            time.sleep(30)
            
            success, stdout, stderr = run_az_command(
                ["az", "group", "show", "--name", rg_name],
                f"Checking if resource group '{rg_name}' still exists"
            )
            
            if not success:
                print(f"✅ Resource group '{rg_name}' successfully deleted via REST API!")
                return True
            else:
                print(f"⏳ Still exists after REST API call...")
    
    # Step 5: Final attempt with force deletion types
    print("\n📋 Step 5: Final attempt with force deletion types...")
    success, stdout, stderr = run_az_command(
        ["az", "group", "delete",
         "--name", rg_name,
         "--yes",
         "--force-deletion-types", 
         "Microsoft.App/managedEnvironments,Microsoft.Network/virtualNetworks,Microsoft.Network/networkSecurityGroups"],
        f"Force deletion with specific types for '{rg_name}'",
        timeout=1800  # 30 minutes
    )
    
    if success:
        print(f"✅ Force deletion completed for '{rg_name}'")
        return True
    else:
        print(f"❌ All deletion methods failed: {stderr}")
        
        # Provide manual instructions
        print("\n" + "=" * 80)
        print("📋 MANUAL RESOLUTION REQUIRED")
        print("=" * 80)
        print("All automated methods have failed. Here are manual steps to try:")
        print("\n1. Open Azure Portal")
        print("2. Navigate to Resource Groups > bciep-test-8")
        print("3. Try to delete individual resources first:")
        print("   - Delete any Container Apps")
        print("   - Delete Container App Environments")
        print("   - Delete Network Security Groups")
        print("   - Delete Virtual Network (this should work after Container Apps are gone)")
        print("4. If that fails, open a support ticket with Microsoft")
        print("5. Alternatively, wait 24-48 hours as sometimes the deletion completes eventually")
        
        return False


def main():
    """Main function for comprehensive force deletion."""
    print("💥 AZURE STUCK RESOURCE GROUP FORCE DELETE TOOL")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target Resource Group: bciep-test-8")
    print("=" * 80)
    
    rg_name = "bciep-test-8"
    
    print("⚠️ WARNING: This tool will use aggressive methods to delete the resource group")
    print("⚠️ This should only be used when standard deletion has been stuck for hours/days")
    print("⚠️ This process may take up to 30 minutes")
    
    try:
        confirm = input("\nType 'FORCE DELETE NOW' to proceed: ").strip()
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        return 1
    
    if confirm != "FORCE DELETE NOW":
        print("❌ Force deletion not confirmed")
        return 1
    
    # Check Azure login
    success, stdout, stderr = run_az_command(
        ["az", "account", "show"],
        "Checking Azure CLI login status"
    )
    
    if not success:
        print("❌ Not logged in to Azure CLI. Please run: az login")
        return 1
    
    # Proceed with comprehensive force deletion
    success = comprehensive_force_deletion(rg_name)
    
    if success:
        print("\n🎉 FORCE DELETION COMPLETED SUCCESSFULLY!")
        return 0
    else:
        print("\n💔 FORCE DELETION FAILED - MANUAL INTERVENTION REQUIRED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
