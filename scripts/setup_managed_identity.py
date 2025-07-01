#!/usr/bin/env python3
"""
Setup Managed Identity for Private Endpoint Azure Resources

This script helps configure managed identity authentication for:
- Azure OpenAI (private-openai-agentic)
- Document Intelligence (private-doc-int) 
- AI Search (private-ai-search)

It will:
1. Get the current user/service principal info
2. Check managed identity status on resources
3. Provide commands to enable managed identity
4. Set up proper RBAC role assignments
"""

import os
import sys
import json
import subprocess
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class AzureResource:
    name: str
    resource_type: str
    endpoint: str
    required_roles: List[str]
    resource_group: Optional[str] = None

class ManagedIdentitySetup:
    def __init__(self):
        self.resources = [
            AzureResource(
                name="private-openai-agentic",
                resource_type="Microsoft.CognitiveServices/accounts",
                endpoint="https://private-openai-agentic.openai.azure.com/",
                required_roles=["Cognitive Services OpenAI User"]
            ),
            AzureResource(
                name="private-doc-int", 
                resource_type="Microsoft.CognitiveServices/accounts",
                endpoint="https://private-doc-int.cognitiveservices.azure.com/",
                required_roles=["Cognitive Services User"]
            ),
            AzureResource(
                name="private-ai-search",
                resource_type="Microsoft.Search/searchServices", 
                endpoint="https://private-ai-search.search.windows.net",
                required_roles=["Search Index Data Contributor", "Search Service Contributor"]
            )
        ]
        
    def run_azure_cli(self, command: str) -> tuple[bool, str]:
        """Run Azure CLI command and return success status and output."""
        try:
            result = subprocess.run(
                f"az {command}", 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def check_azure_cli(self) -> bool:
        """Check if Azure CLI is installed and user is logged in."""
        print("🔍 Checking Azure CLI setup...")
        
        # Check if az command exists
        success, output = self.run_azure_cli("--version")
        if not success:
            print("❌ Azure CLI is not installed")
            print("   Install it: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
            return False
        
        print("✅ Azure CLI is installed")
        
        # Check if logged in
        success, output = self.run_azure_cli("account show")
        if not success:
            print("❌ Not logged into Azure CLI")
            print("   Run: az login")
            return False
            
        print("✅ Logged into Azure CLI")
        try:
            account_info = json.loads(output)
            print(f"   Subscription: {account_info.get('name', 'Unknown')}")
            print(f"   User: {account_info.get('user', {}).get('name', 'Unknown')}")
        except:
            pass
            
        return True

    def get_current_user_info(self) -> Optional[Dict]:
        """Get current user/service principal information."""
        print("\n🔍 Getting current user information...")
        
        success, output = self.run_azure_cli("ad signed-in-user show")
        if success:
            try:
                user_info = json.loads(output)
                print(f"✅ Current user: {user_info.get('displayName', 'Unknown')}")
                print(f"   Object ID: {user_info.get('id', 'Unknown')}")
                return user_info
            except:
                pass
        
        # Try getting service principal info if user command failed
        success, output = self.run_azure_cli("account show")
        if success:
            try:
                account_info = json.loads(output)
                user_info = account_info.get('user', {})
                print(f"✅ Current principal: {user_info.get('name', 'Unknown')}")
                print(f"   Type: {user_info.get('type', 'Unknown')}")
                return user_info
            except:
                pass
                
        print("❌ Could not get user information")
        return None

    def discover_resources(self):
        """Discover resource groups for the Azure resources."""
        print("\n🔍 Discovering Azure resources...")
        
        for resource in self.resources:
            print(f"\n   Searching for {resource.name}...")
            
            # Search for the resource
            success, output = self.run_azure_cli(
                f"resource list --name {resource.name} --resource-type {resource.resource_type}"
            )
            
            if success:
                try:
                    resources_list = json.loads(output)
                    if resources_list:
                        resource_info = resources_list[0]
                        resource.resource_group = resource_info['resourceGroup']
                        print(f"   ✅ Found in resource group: {resource.resource_group}")
                        print(f"      Location: {resource_info.get('location', 'Unknown')}")
                    else:
                        print(f"   ❌ Resource {resource.name} not found")
                except:
                    print(f"   ❌ Error parsing resource information")
            else:
                print(f"   ❌ Error searching for resource: {output}")

    def check_managed_identity_status(self):
        """Check if managed identity is enabled on resources."""
        print("\n🔍 Checking managed identity status...")
        
        for resource in self.resources:
            if not resource.resource_group:
                print(f"   ⏭️  Skipping {resource.name} (not found)")
                continue
                
            print(f"\n   Checking {resource.name}...")
            
            if resource.resource_type == "Microsoft.Search/searchServices":
                # For Search Service, check identity
                success, output = self.run_azure_cli(
                    f"search service show --name {resource.name} --resource-group {resource.resource_group}"
                )
            else:
                # For Cognitive Services, check identity
                success, output = self.run_azure_cli(
                    f"cognitiveservices account show --name {resource.name} --resource-group {resource.resource_group}"
                )
            
            if success:
                try:
                    resource_info = json.loads(output)
                    identity = resource_info.get('identity', {})
                    
                    if identity and identity.get('type') == 'SystemAssigned':
                        principal_id = identity.get('principalId', 'Unknown')
                        print(f"   ✅ System-assigned managed identity enabled")
                        print(f"      Principal ID: {principal_id}")
                    else:
                        print(f"   ❌ Managed identity not enabled")
                        self.print_enable_identity_command(resource)
                        
                except Exception as e:
                    print(f"   ❌ Error parsing identity info: {e}")
            else:
                print(f"   ❌ Error checking resource: {output}")

    def print_enable_identity_command(self, resource: AzureResource):
        """Print command to enable managed identity."""
        print(f"      💡 To enable managed identity, run:")
        
        if resource.resource_type == "Microsoft.Search/searchServices":
            print(f"         az search service update --name {resource.name} --resource-group {resource.resource_group} --identity-type SystemAssigned")
        else:
            print(f"         az cognitiveservices account update --name {resource.name} --resource-group {resource.resource_group} --assign-identity")

    def check_rbac_assignments(self, user_info: Dict):
        """Check RBAC role assignments for current user."""
        print("\n🔍 Checking RBAC role assignments...")
        
        user_object_id = user_info.get('id') or user_info.get('objectId')
        if not user_object_id:
            print("   ❌ Cannot check RBAC - no user object ID")
            return
        
        print(f"   Checking roles for user: {user_object_id}")
        
        for resource in self.resources:
            if not resource.resource_group:
                continue
                
            print(f"\n   Checking {resource.name}...")
            
            # Get resource ID
            success, output = self.run_azure_cli(
                f"resource show --name {resource.name} --resource-group {resource.resource_group} --resource-type {resource.resource_type} --query id -o tsv"
            )
            
            if not success:
                print(f"   ❌ Could not get resource ID: {output}")
                continue
                
            resource_id = output.strip()
            
            # Check role assignments
            for role in resource.required_roles:
                success, output = self.run_azure_cli(
                    f"role assignment list --assignee {user_object_id} --scope {resource_id} --role \"{role}\" --query length(@) -o tsv"
                )
                
                if success and output.strip() != "0":
                    print(f"   ✅ Has role: {role}")
                else:
                    print(f"   ❌ Missing role: {role}")
                    print(f"      💡 To assign role, run:")
                    print(f"         az role assignment create --assignee {user_object_id} --role \"{role}\" --scope {resource_id}")

    def test_managed_identity_auth(self):
        """Test managed identity authentication."""
        print("\n🧪 Testing managed identity authentication...")
        
        # Test if we can get a token
        success, output = self.run_azure_cli("account get-access-token --resource https://cognitiveservices.azure.com/")
        
        if success:
            print("✅ Can get Cognitive Services token")
        else:
            print(f"❌ Cannot get Cognitive Services token: {output}")
        
        # Test Search token
        success, output = self.run_azure_cli("account get-access-token --resource https://search.azure.com/")
        
        if success:
            print("✅ Can get Search token")
        else:
            print(f"❌ Cannot get Search token: {output}")

    def print_summary_recommendations(self):
        """Print summary and recommendations."""
        print("\n" + "="*60)
        print("📋 MANAGED IDENTITY SETUP SUMMARY")
        print("="*60)
        
        print("\n🎯 Next Steps:")
        print("1. Enable managed identity on all resources (see commands above)")
        print("2. Assign required RBAC roles (see commands above)")
        print("3. Update your .env file to remove any API keys")
        print("4. Test connectivity with the health check system")
        
        print("\n🔧 Environment Configuration:")
        print("Your .env file should only have endpoints, no keys:")
        print("   AZURE_OPENAI_ENDPOINT=https://private-openai-agentic.openai.azure.com/")
        print("   DOCUMENT_INTEL_ENDPOINT=https://private-doc-int.cognitiveservices.azure.com/") 
        print("   AZURE_SEARCH_ENDPOINT=https://private-ai-search.search.windows.net")
        print("   # No API keys needed!")
        
        print("\n🏥 Health Check:")
        print("After setup, run the enhanced health check:")
        print("   python health_check/private_endpoint_health_checker.py")

def main():
    """Main function to run managed identity setup."""
    print("🚀 Azure Managed Identity Setup for Private Endpoints")
    print("="*60)
    
    setup = ManagedIdentitySetup()
    
    # Check prerequisites
    if not setup.check_azure_cli():
        return 1
    
    # Get user info
    user_info = setup.get_current_user_info()
    if not user_info:
        return 1
    
    # Discover resources
    setup.discover_resources()
    
    # Check managed identity status
    setup.check_managed_identity_status()
    
    # Check RBAC assignments
    setup.check_rbac_assignments(user_info)
    
    # Test authentication
    setup.test_managed_identity_auth()
    
    # Print summary
    setup.print_summary_recommendations()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
