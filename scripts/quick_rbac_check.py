#!/usr/bin/env python3
"""
Quick RBAC Check for AI Foundry
This script quickly checks what RBAC permissions are needed and provides specific commands.
"""

import os
import subprocess
import json
from typing import Dict, List, Optional
from dotenv import load_dotenv

def run_az_command(command: List[str]) -> Optional[str]:
    """Run an Azure CLI command and return the output."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(command)}")
        print(f"   Error: {e.stderr}")
        return None

def get_current_user() -> Optional[str]:
    """Get the current Azure CLI user."""
    output = run_az_command(['az', 'account', 'show', '--query', 'user.name', '-o', 'tsv'])
    return output

def get_subscription_info() -> Dict[str, str]:
    """Get current subscription information."""
    output = run_az_command(['az', 'account', 'show', '--query', '{id:id, name:name}', '-o', 'json'])
    if output:
        return json.loads(output)
    return {}

def parse_project_endpoint(endpoint: str) -> Dict[str, str]:
    """Parse the project endpoint to extract foundry information."""
    try:
        # https://aiagenticservicesfgtt.services.ai.azure.com/api/projects/agentic-rag
        parts = endpoint.split('/')
        foundry_hostname = parts[2]
        project_name = parts[-1]
        foundry_name = foundry_hostname.split('.')[0]
        
        return {
            'foundry_hostname': foundry_hostname,
            'foundry_name': foundry_name,
            'project_name': project_name
        }
    except Exception as e:
        print(f"❌ Error parsing endpoint: {e}")
        return {}

def find_foundry_hub(foundry_name: str) -> Optional[Dict[str, str]]:
    """Find the AI Foundry hub resource."""
    # List all ML workspaces
    output = run_az_command(['az', 'ml', 'workspace', 'list', '--query', 
                           f"[?contains(name, '{foundry_name}')]", '-o', 'json'])
    
    if output:
        workspaces = json.loads(output)
        if workspaces:
            return workspaces[0]
    
    # Try a broader search
    output = run_az_command(['az', 'ml', 'workspace', 'list', '-o', 'json'])
    if output:
        workspaces = json.loads(output)
        print(f"\n🔍 Available AI Foundry hubs:")
        for ws in workspaces:
            print(f"   📍 {ws['name']} (in {ws['resourceGroup']})")
        
        if workspaces:
            print(f"\n💡 Could not find exact match for '{foundry_name}'")
            print(f"   You might need to use one of the hubs listed above")
    
    return None

def check_user_permissions(user_email: str, hub_info: Dict[str, str]) -> List[str]:
    """Check what permissions the user currently has."""
    if not hub_info:
        return []
    
    subscription_id = get_subscription_info().get('id', '')
    resource_group = hub_info.get('resourceGroup', '')
    hub_name = hub_info.get('name', '')
    
    hub_resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{hub_name}"
    
    # Check hub-level permissions
    output = run_az_command([
        'az', 'role', 'assignment', 'list',
        '--assignee', user_email,
        '--scope', hub_resource_id,
        '--query', '[].roleDefinitionName',
        '-o', 'json'
    ])
    
    roles = []
    if output:
        try:
            roles.extend(json.loads(output))
        except:
            pass
    
    # Check resource group level
    rg_scope = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
    output = run_az_command([
        'az', 'role', 'assignment', 'list',
        '--assignee', user_email,
        '--scope', rg_scope,
        '--query', '[].roleDefinitionName',
        '-o', 'json'
    ])
    
    if output:
        try:
            roles.extend(json.loads(output))
        except:
            pass
    
    return list(set(roles))  # Remove duplicates

def generate_rbac_commands(user_email: str, hub_info: Dict[str, str]) -> List[str]:
    """Generate the Azure CLI commands needed to assign RBAC permissions."""
    if not hub_info:
        return []
    
    subscription_id = get_subscription_info().get('id', '')
    resource_group = hub_info.get('resourceGroup', '')
    hub_name = hub_info.get('name', '')
    
    hub_resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{hub_name}"
    
    commands = [
        f"# Assign Azure AI Developer role (recommended)",
        f"az role assignment create \\",
        f"  --assignee '{user_email}' \\",
        f"  --role 'Azure AI Developer' \\",
        f"  --scope '{hub_resource_id}'",
        f"",
        f"# Alternative: Minimum permissions (read-only)",
        f"az role assignment create \\",
        f"  --assignee '{user_email}' \\",
        f"  --role 'Cognitive Services User' \\",
        f"  --scope '{hub_resource_id}'",
    ]
    
    return commands

def main():
    """Main function."""
    print("🚀 AI Foundry RBAC Quick Check")
    print("=" * 50)
    
    # Load environment
    load_dotenv()
    project_endpoint = os.getenv('PROJECT_ENDPOINT')
    
    if not project_endpoint:
        print("❌ PROJECT_ENDPOINT not found in .env file")
        return
    
    print(f"📋 Project Endpoint: {project_endpoint}")
    
    # Parse endpoint
    parsed = parse_project_endpoint(project_endpoint)
    if not parsed:
        return
    
    foundry_name = parsed['foundry_name']
    print(f"🏢 Foundry Name: {foundry_name}")
    print(f"📋 Project Name: {parsed['project_name']}")
    
    # Get current user
    current_user = get_current_user()
    if not current_user:
        print("❌ Could not get current Azure CLI user")
        return
    
    print(f"👤 Current User: {current_user}")
    
    # Get subscription info
    sub_info = get_subscription_info()
    print(f"📊 Subscription: {sub_info.get('name', 'Unknown')} ({sub_info.get('id', 'Unknown')})")
    
    # Find the foundry hub
    print(f"\n🔍 Looking for AI Foundry hub...")
    hub_info = find_foundry_hub(foundry_name)
    
    if not hub_info:
        print(f"\n❌ Could not find AI Foundry hub matching '{foundry_name}'")
        print(f"\n💡 Try running this command to see all hubs:")
        print(f"   az ml workspace list")
        return
    
    print(f"✅ Found hub: {hub_info['name']} in {hub_info['resourceGroup']}")
    
    # Check current permissions
    print(f"\n🔐 Checking current permissions...")
    current_roles = check_user_permissions(current_user, hub_info)
    
    if current_roles:
        print(f"✅ Current roles:")
        for role in current_roles:
            print(f"   📋 {role}")
    else:
        print(f"❌ No relevant permissions found")
    
    # Check if user has sufficient permissions
    sufficient_roles = [
        'Azure AI Developer', 'Azure AI Administrator', 
        'Cognitive Services User', 'Owner', 'Contributor'
    ]
    
    has_sufficient = any(role in sufficient_roles for role in current_roles)
    
    if has_sufficient:
        print(f"\n✅ User has sufficient permissions for AI Foundry access")
        print(f"\n💡 If you're still having issues, try:")
        print(f"   1. Wait a few minutes for permissions to propagate")
        print(f"   2. Check if the project name in the URL is correct")
        print(f"   3. Verify the foundry is using the correct authentication method")
    else:
        print(f"\n⚠️  User needs additional permissions")
        print(f"\n🔧 Required RBAC commands:")
        print()
        
        commands = generate_rbac_commands(current_user, hub_info)
        for cmd in commands:
            print(cmd)
        
        print(f"\n📖 For more details, see: docs/AI_FOUNDRY_RBAC_REQUIREMENTS.md")
        
        # Option to run the setup script
        print(f"\n💡 You can also run the interactive setup script:")
        print(f"   ./scripts/setup_ai_foundry_rbac.sh")

if __name__ == "__main__":
    main()
