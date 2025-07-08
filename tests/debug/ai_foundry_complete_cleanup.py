#!/usr/bin/env python3
"""
Script: AI Foundry Complete Network-Secured Cleanup
Purpose: Follow official Microsoft documentation for proper AI Foundry resource cleanup
Reference: https://learn.microsoft.com/en-us/azure/ai-studio/how-to/network-isolation-managed-identity

This script implements the correct deletion order as documented by Microsoft:
1. Delete AI Foundry project resources first
2. Purge deleted Cognitive Services accounts via portal
3. Only then attempt to delete VNet/subnet resources

Created per new policy: all debug scripts go in tests/debug/
"""

import subprocess
import json
import time
import sys
from typing import Dict, List, Optional

class AIFoundryCleanup:
    def __init__(self, resource_group: str = "bciep-test-8"):
        self.resource_group = resource_group
        self.subscription_id = self._get_subscription_id()
        
    def _get_subscription_id(self) -> str:
        """Get current subscription ID."""
        try:
            result = subprocess.run(
                ["az", "account", "show", "--query", "id", "-o", "tsv"],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error getting subscription ID: {e}")
            sys.exit(1)
    
    def _run_command(self, command: List[str], ignore_errors: bool = False) -> Optional[str]:
        """Run Azure CLI command and return output."""
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if not ignore_errors:
                print(f"Command failed: {' '.join(command)}")
                print(f"Error: {e.stderr}")
            return None
    
    def check_ai_foundry_projects(self) -> List[Dict]:
        """Check for AI Foundry projects in the resource group."""
        print("🔍 Checking for AI Foundry projects...")
        
        # Check for AI hubs
        hubs_output = self._run_command([
            "az", "resource", "list",
            "--resource-group", self.resource_group,
            "--resource-type", "Microsoft.MachineLearningServices/workspaces",
            "--query", "[?properties.hubWorkspaceId != null]",
            "-o", "json"
        ], ignore_errors=True)
        
        foundry_resources = []
        
        if hubs_output:
            try:
                hubs = json.loads(hubs_output)
                foundry_resources.extend(hubs)
                print(f"Found {len(hubs)} AI Foundry hubs")
            except json.JSONDecodeError:
                pass
        
        # Check for AI projects  
        projects_output = self._run_command([
            "az", "resource", "list",
            "--resource-group", self.resource_group,
            "--resource-type", "Microsoft.MachineLearningServices/workspaces",
            "--query", "[?properties.hubWorkspaceId == null]",
            "-o", "json"
        ], ignore_errors=True)
        
        if projects_output:
            try:
                projects = json.loads(projects_output)
                foundry_resources.extend(projects)
                print(f"Found {len(projects)} AI Foundry projects")
            except json.JSONDecodeError:
                pass
        
        return foundry_resources
    
    def delete_ai_foundry_resources(self) -> bool:
        """Delete AI Foundry project resources following Microsoft documentation."""
        print("\n🗑️  STEP 1: Deleting AI Foundry resources...")
        
        foundry_resources = self.check_ai_foundry_projects()
        
        if not foundry_resources:
            print("✅ No AI Foundry resources found")
            return True
        
        success = True
        for resource in foundry_resources:
            resource_name = resource.get('name', 'unknown')
            resource_type = resource.get('type', 'unknown')
            
            print(f"Deleting {resource_type}: {resource_name}")
            
            delete_result = self._run_command([
                "az", "resource", "delete",
                "--ids", resource['id'],
                "--verbose"
            ], ignore_errors=True)
            
            if delete_result is None:
                print(f"❌ Failed to delete {resource_name}")
                success = False
            else:
                print(f"✅ Deleted {resource_name}")
        
        return success
    
    def check_cognitive_services(self) -> List[Dict]:
        """Check for Cognitive Services accounts in the resource group."""
        print("\n🧠 Checking for Cognitive Services accounts...")
        
        cs_output = self._run_command([
            "az", "cognitiveservices", "account", "list",
            "--resource-group", self.resource_group,
            "-o", "json"
        ], ignore_errors=True)
        
        if cs_output:
            try:
                accounts = json.loads(cs_output)
                print(f"Found {len(accounts)} Cognitive Services accounts")
                return accounts
            except json.JSONDecodeError:
                pass
        
        print("No Cognitive Services accounts found")
        return []
    
    def purge_cognitive_services(self) -> bool:
        """
        Instruct to purge Cognitive Services via portal.
        This is the critical step from Microsoft documentation.
        """
        print("\n🔥 STEP 2: Purging Cognitive Services accounts...")
        
        accounts = self.check_cognitive_services()
        
        if not accounts:
            # Check for deleted accounts that may need purging
            print("Checking for soft-deleted Cognitive Services accounts...")
            
            deleted_output = self._run_command([
                "az", "cognitiveservices", "account", "list-deleted",
                "-o", "json"
            ], ignore_errors=True)
            
            if deleted_output:
                try:
                    deleted_accounts = json.loads(deleted_output)
                    rg_deleted = [acc for acc in deleted_accounts 
                                if acc.get('properties', {}).get('resourceGroup') == self.resource_group]
                    
                    if rg_deleted:
                        print(f"\n⚠️  CRITICAL: Found {len(rg_deleted)} soft-deleted Cognitive Services accounts")
                        print("These MUST be purged before VNet deletion can succeed!")
                        print("\nTo purge these accounts:")
                        print("1. Go to Azure Portal -> Cognitive Services")
                        print("2. Click 'Manage deleted resources'")
                        print("3. Find and purge all accounts from this resource group")
                        print("4. Wait for purge to complete (can take several minutes)")
                        
                        for acc in rg_deleted:
                            name = acc.get('name', 'unknown')
                            location = acc.get('properties', {}).get('location', 'unknown')
                            print(f"   - {name} in {location}")
                        
                        return False
                    else:
                        print("✅ No soft-deleted accounts found for this resource group")
                        return True
                except json.JSONDecodeError:
                    pass
        else:
            # Delete active accounts first
            print("Deleting active Cognitive Services accounts...")
            for account in accounts:
                account_name = account['name']
                print(f"Deleting Cognitive Services account: {account_name}")
                
                delete_result = self._run_command([
                    "az", "cognitiveservices", "account", "delete",
                    "--name", account_name,
                    "--resource-group", self.resource_group,
                    "--yes"
                ], ignore_errors=True)
                
                if delete_result is None:
                    print(f"❌ Failed to delete {account_name}")
            
            print("\n⚠️  After deletion, you MUST purge these accounts via Azure Portal:")
            print("1. Go to Azure Portal -> Cognitive Services")
            print("2. Click 'Manage deleted resources'")
            print("3. Find and purge all accounts from this resource group")
            print("4. Wait for purge to complete")
            return False
        
        return True
    
    def check_service_association_links(self) -> List[Dict]:
        """Check for service association links in subnets."""
        print("\n🔗 Checking for Service Association Links...")
        
        # Get VNets in the resource group
        vnets_output = self._run_command([
            "az", "network", "vnet", "list",
            "--resource-group", self.resource_group,
            "-o", "json"
        ], ignore_errors=True)
        
        if not vnets_output:
            return []
        
        try:
            vnets = json.loads(vnets_output)
        except json.JSONDecodeError:
            return []
        
        sal_links = []
        
        for vnet in vnets:
            vnet_name = vnet['name']
            subnets = vnet.get('subnets', [])
            
            for subnet in subnets:
                subnet_name = subnet['name']
                service_association_links = subnet.get('serviceAssociationLinks', [])
                
                if service_association_links:
                    print(f"Found {len(service_association_links)} SAL(s) in {vnet_name}/{subnet_name}")
                    
                    for sal in service_association_links:
                        sal_info = {
                            'vnet_name': vnet_name,
                            'subnet_name': subnet_name,
                            'sal_name': sal.get('name', 'unknown'),
                            'sal_id': sal.get('id', ''),
                            'linked_resource_type': sal.get('linkedResourceType', 'unknown'),
                            'allow_delete': sal.get('allowDelete', False)
                        }
                        sal_links.append(sal_info)
                        
                        print(f"  SAL: {sal_info['sal_name']}")
                        print(f"  Type: {sal_info['linked_resource_type']}")
                        print(f"  Allow Delete: {sal_info['allow_delete']}")
        
        return sal_links
    
    def attempt_vnet_cleanup(self) -> bool:
        """
        STEP 3: Attempt VNet cleanup after AI Foundry resources are purged.
        This should only be done after Step 2 is complete.
        """
        print("\n🌐 STEP 3: Attempting VNet cleanup...")
        
        # Check for remaining SALs
        sal_links = self.check_service_association_links()
        
        if sal_links:
            print(f"\n❌ Found {len(sal_links)} orphaned Service Association Links:")
            for sal in sal_links:
                print(f"  - {sal['sal_name']} in {sal['vnet_name']}/{sal['subnet_name']}")
                print(f"    Type: {sal['linked_resource_type']}")
                print(f"    Allow Delete: {sal['allow_delete']}")
            
            print("\n⚠️  These orphaned SALs are blocking VNet deletion.")
            print("This requires Microsoft Support intervention.")
            return False
        
        # If no SALs, try to delete VNets
        vnets_output = self._run_command([
            "az", "network", "vnet", "list",
            "--resource-group", self.resource_group,
            "--query", "[].name",
            "-o", "tsv"
        ], ignore_errors=True)
        
        if vnets_output:
            vnet_names = vnets_output.strip().split('\n')
            
            for vnet_name in vnet_names:
                if vnet_name.strip():
                    print(f"Deleting VNet: {vnet_name}")
                    
                    delete_result = self._run_command([
                        "az", "network", "vnet", "delete",
                        "--name", vnet_name,
                        "--resource-group", self.resource_group,
                        "--yes"
                    ], ignore_errors=True)
                    
                    if delete_result is None:
                        print(f"❌ Failed to delete VNet {vnet_name}")
                        return False
                    else:
                        print(f"✅ Deleted VNet {vnet_name}")
        
        return True
    
    def attempt_resource_group_deletion(self) -> bool:
        """STEP 4: Final resource group deletion attempt."""
        print(f"\n🗑️  STEP 4: Attempting to delete resource group {self.resource_group}...")
        
        delete_result = self._run_command([
            "az", "group", "delete",
            "--name", self.resource_group,
            "--yes",
            "--no-wait"
        ], ignore_errors=True)
        
        if delete_result is None:
            print(f"❌ Resource group deletion failed")
            return False
        else:
            print(f"✅ Resource group deletion initiated (running in background)")
            return True
    
    def run_complete_cleanup(self):
        """Run the complete AI Foundry cleanup procedure."""
        print("🚀 Starting AI Foundry Complete Cleanup")
        print("Following Microsoft documentation for network-secured environments")
        print(f"Resource Group: {self.resource_group}")
        print("=" * 60)
        
        # Step 1: Delete AI Foundry resources
        foundry_success = self.delete_ai_foundry_resources()
        
        # Step 2: Check and instruct on Cognitive Services purging
        purge_ready = self.purge_cognitive_services()
        
        if not purge_ready:
            print("\n⚠️  PROCESS PAUSED")
            print("You must complete Cognitive Services purging in the Azure Portal")
            print("Run this script again after purging is complete")
            return False
        
        # Step 3: VNet cleanup
        vnet_success = self.attempt_vnet_cleanup()
        
        if not vnet_success:
            print("\n❌ VNet cleanup failed due to orphaned Service Association Links")
            print("Microsoft Support intervention required")
            return False
        
        # Step 4: Resource group deletion
        rg_success = self.attempt_resource_group_deletion()
        
        if rg_success:
            print("\n🎉 Complete cleanup procedure executed successfully!")
            print("Monitor resource group deletion with:")
            print(f"az group show --name {self.resource_group}")
        
        return rg_success

def main():
    cleanup = AIFoundryCleanup()
    success = cleanup.run_complete_cleanup()
    
    if not success:
        print("\n📋 Next Steps:")
        print("1. Complete any required manual steps (Cognitive Services purging)")
        print("2. If orphaned SALs remain, contact Microsoft Support")
        print("3. Reference: azure_support_ticket_template.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()
