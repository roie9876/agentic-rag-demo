#!/usr/bin/env python3
"""
Check AI Search RBAC Permissions on AI Foundry Project
=====================================================
Script to check if Azure AI Search has the right permissions on the AI Foundry project
"""

import json
import subprocess
import sys

def check_project_permissions():
    """Check if AI Search has permissions on the AI Foundry project"""
    
    search_service_name = "ai-serach-demo-eastus"
    project_name = "admin-m845f4ec-eastus2-project"
    
    print(f"🔍 CHECKING AI FOUNDRY PROJECT PERMISSIONS")
    print(f"=" * 80)
    print(f"🔍 Search Service: {search_service_name}")
    print(f"📁 Project: {project_name}")
    print(f"=" * 80)
    
    # Step 1: Get the search service principal ID (we already know this)
    print(f"🔍 Getting search service principal ID...")
    try:
        result = subprocess.run([
            "az", "search", "service", "show",
            "--name", search_service_name,
            "--resource-group", "ai-hub",  # assuming it's in ai-hub
            "--query", "identity.principalId",
            "--output", "tsv"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            search_principal_id = result.stdout.strip()
            print(f"✅ Search service principal ID: {search_principal_id}")
        else:
            print(f"❌ Failed to get search service info: {result.stderr}")
            return
            
    except Exception as e:
        print(f"❌ Error getting search service info: {e}")
        return
    
    # Step 2: Find the AI Foundry project resource
    print(f"\n🔍 Looking for AI Foundry project resource...")
    try:
        # Search for AI Studio/Foundry projects
        result = subprocess.run([
            "az", "resource", "list",
            "--query", f"[?name=='{project_name}'].{{id:id,resourceGroup:resourceGroup,type:type}}",
            "--output", "json"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            resources = json.loads(result.stdout)
            if resources:
                project_resource = resources[0]
                project_id = project_resource['id']
                project_rg = project_resource['resourceGroup']
                project_type = project_resource['type']
                
                print(f"✅ Found project resource:")
                print(f"   ID: {project_id}")
                print(f"   Resource Group: {project_rg}")
                print(f"   Type: {project_type}")
            else:
                print(f"❌ Project '{project_name}' not found")
                return
        else:
            print(f"❌ Failed to search for project: {result.stderr}")
            return
            
    except Exception as e:
        print(f"❌ Error searching for project: {e}")
        return
    
    # Step 3: Check current role assignments on the project
    print(f"\n🔍 Checking current role assignments on project...")
    try:
        result = subprocess.run([
            "az", "role", "assignment", "list",
            "--scope", project_id,
            "--query", f"[?principalId=='{search_principal_id}'].{{principalId:principalId,roleDefinitionName:roleDefinitionName,scope:scope}}",
            "--output", "json"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            assignments = json.loads(result.stdout)
            
            print(f"📋 Current role assignments for search service on project:")
            if assignments:
                for assignment in assignments:
                    role_name = assignment.get('roleDefinitionName', 'Unknown')
                    print(f"   ✅ {role_name}")
            else:
                print(f"   ❌ No role assignments found")
                
                # Suggest roles to assign
                print(f"\n💡 SUGGESTED ACTIONS:")
                print(f"================================================================================")
                print(f"The Azure AI Search service needs permissions on the AI Foundry project.")
                print(f"Suggested roles to assign:")
                print(f"   • Azure AI Developer")
                print(f"   • Cognitive Services OpenAI User") 
                print(f"   • Azure Machine Learning Workspace Connection Secrets Reader")
                
                # Ask if user wants to assign roles
                assign_roles = input(f"\n❓ Would you like to assign these roles now? (y/n): ").strip().lower()
                
                if assign_roles == 'y':
                    assign_project_roles(search_principal_id, project_id)
                else:
                    print(f"📋 Manual assignment needed. Use these commands:")
                    print_manual_commands(search_principal_id, project_id)
        else:
            print(f"❌ Failed to check role assignments: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error checking role assignments: {e}")

def assign_project_roles(principal_id, project_id):
    """Assign necessary roles to the search service on the project"""
    
    roles_to_assign = [
        ("Azure AI Developer", "64702f94-c441-49e6-a78b-ef80e0188fee"),
        ("Cognitive Services OpenAI User", "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"),
    ]
    
    print(f"\n🔧 Assigning roles to search service on project...")
    
    for role_name, role_id in roles_to_assign:
        try:
            print(f"🔧 Assigning '{role_name}'...")
            
            result = subprocess.run([
                "az", "role", "assignment", "create",
                "--assignee", principal_id,
                "--role", role_id,
                "--scope", project_id
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"   ✅ Successfully assigned '{role_name}'")
            else:
                error_msg = result.stderr.strip()
                if "already exists" in error_msg.lower():
                    print(f"   ℹ️  '{role_name}' already assigned")
                else:
                    print(f"   ❌ Failed to assign '{role_name}': {error_msg}")
                    
        except Exception as e:
            print(f"   ❌ Error assigning '{role_name}': {e}")
    
    print(f"\n🎉 Role assignment completed!")

def print_manual_commands(principal_id, project_id):
    """Print manual commands for role assignment"""
    
    print(f"\n📋 MANUAL ROLE ASSIGNMENT COMMANDS:")
    print(f"================================================================================")
    print(f"# Assign Azure AI Developer role")
    print(f"az role assignment create \\")
    print(f"  --assignee {principal_id} \\")
    print(f"  --role '64702f94-c441-49e6-a78b-ef80e0188fee' \\")
    print(f"  --scope '{project_id}'")
    
    print(f"\n# Assign Cognitive Services OpenAI User role")
    print(f"az role assignment create \\")
    print(f"  --assignee {principal_id} \\")
    print(f"  --role '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' \\")
    print(f"  --scope '{project_id}'")

if __name__ == "__main__":
    check_project_permissions()
