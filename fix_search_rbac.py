#!/usr/bin/env python3
"""
Fix Azure AI Search RBAC Permissions for Azure OpenAI
=====================================================
This script assigns the necessary RBAC roles to Azure AI Search service 
so it can browse and access Azure OpenAI models for vectorization.
"""

import subprocess
import json
import os
from dotenv import load_dotenv

load_dotenv()

def get_search_service_principal():
    """Get the managed identity principal ID for the Azure AI Search service"""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    if not search_endpoint:
        print("❌ AZURE_SEARCH_ENDPOINT not found in environment")
        return None
    
    # Extract service name from endpoint
    service_name = search_endpoint.split("//")[1].split(".")[0]
    
    print(f"🔍 Looking for Azure AI Search service: {service_name}")
    
    try:
        # Get the search service details including managed identity
        result = subprocess.run([
            "az", "search", "service", "show",
            "--name", service_name,
            "--resource-group", "ai-hub",  # Adjust if needed
            "--query", "identity.principalId",
            "--output", "tsv"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            principal_id = result.stdout.strip()
            if principal_id and principal_id != "None":
                print(f"✅ Found search service principal ID: {principal_id}")
                return principal_id
            else:
                print("⚠️  Search service doesn't have managed identity enabled")
                return None
        else:
            print(f"❌ Failed to get search service: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting search service: {e}")
        return None

def get_openai_resource_id():
    """Get the resource ID for the Azure OpenAI service"""
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    if not openai_endpoint:
        print("❌ AZURE_OPENAI_ENDPOINT not found in environment")
        return None
    
    # Extract service name from endpoint  
    service_name = openai_endpoint.split("//")[1].split(".")[0]
    
    print(f"🔍 Looking for Azure OpenAI service: {service_name}")
    
    try:
        # Find the OpenAI resource
        result = subprocess.run([
            "az", "cognitiveservices", "account", "show",
            "--name", service_name,
            "--resource-group", "aistudio",  # Correct resource group
            "--query", "id",
            "--output", "tsv"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            resource_id = result.stdout.strip()
            print(f"✅ Found OpenAI resource ID: {resource_id}")
            return resource_id
        else:
            print(f"❌ Failed to get OpenAI resource: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting OpenAI resource: {e}")
        return None

def assign_role(principal_id, resource_id, role_name, role_id):
    """Assign a role to the principal on the resource"""
    print(f"🔧 Assigning role '{role_name}' to search service...")
    
    try:
        result = subprocess.run([
            "az", "role", "assignment", "create",
            "--assignee", principal_id,
            "--role", role_id,
            "--scope", resource_id
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✅ Successfully assigned '{role_name}'")
            return True
        else:
            error_msg = result.stderr.strip()
            if "already exists" in error_msg.lower():
                print(f"✅ Role '{role_name}' already assigned")
                return True
            else:
                print(f"❌ Failed to assign '{role_name}': {error_msg}")
                return False
                
    except Exception as e:
        print(f"❌ Error assigning role '{role_name}': {e}")
        return False

def main():
    print("🔧 AZURE AI SEARCH RBAC PERMISSIONS FIXER")
    print("=" * 80)
    print("This script will assign OpenAI permissions to Azure AI Search service")
    print("so it can browse and access Azure OpenAI models for vectorization.")
    print("=" * 80)
    
    # Get search service principal ID
    search_principal = get_search_service_principal()
    if not search_principal:
        print("❌ Cannot proceed without search service principal ID")
        return
    
    # Get OpenAI resource ID  
    openai_resource = get_openai_resource_id()
    if not openai_resource:
        print("❌ Cannot proceed without OpenAI resource ID")
        return
    
    print(f"\n🎯 Assigning RBAC roles...")
    print(f"   Principal: {search_principal}")
    print(f"   Resource:  {openai_resource}")
    print("-" * 80)
    
    # Roles to assign
    roles = [
        ("Cognitive Services OpenAI User", "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"),
        ("Cognitive Services User", "a97b65f3-24c7-4388-baec-2e87135dc908")
    ]
    
    success_count = 0
    for role_name, role_id in roles:
        if assign_role(search_principal, openai_resource, role_name, role_id):
            success_count += 1
    
    print("\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)
    
    if success_count == len(roles):
        print("🎉 All roles assigned successfully!")
        print("✅ Azure AI Search can now browse Azure OpenAI models")
        print("\n💡 Next steps:")
        print("   1. Refresh the Azure Portal page")
        print("   2. Try selecting the Azure OpenAI service in the vectorizer dropdown")
        print("   3. You should now see 'text-embedding-3-large' as an option")
    else:
        print(f"⚠️  Assigned {success_count}/{len(roles)} roles successfully")
        print("   Some role assignments may have failed - check the output above")

if __name__ == "__main__":
    main()
