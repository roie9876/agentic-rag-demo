#!/usr/bin/env python3
"""
Check RBAC Permissions for AI Foundry Account
This script checks if the current user has the necessary permissions 
to access the AI Foundry account and projects.
"""

import os
import subprocess
import json
from typing import Dict, List, Optional
from azure.identity import DefaultAzureCredential
from azure.mgmt.authorization import AuthorizationManagementClient
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from dotenv import load_dotenv

def load_environment():
    """Load environment variables from .env file."""
    load_dotenv()
    return {
        'project_endpoint': os.getenv('PROJECT_ENDPOINT'),
        'subscription_id': None,  # Will be detected
        'resource_group': None,   # Will be detected
        'foundry_account': None   # Will be extracted from endpoint
    }

def parse_foundry_endpoint(endpoint: str) -> Dict[str, str]:
    """Parse AI Foundry endpoint to extract account name."""
    try:
        # https://aiagenticservicesfgtt.services.ai.azure.com/api/projects/agentic-rag
        parts = endpoint.split('/')
        hostname = parts[2]  # aiagenticservicesfgtt.services.ai.azure.com
        account_name = hostname.split('.')[0]  # aiagenticservicesfgtt
        project_name = parts[-1]  # agentic-rag
        
        return {
            'account_name': account_name,
            'project_name': project_name,
            'hostname': hostname
        }
    except Exception as e:
        print(f"❌ Error parsing endpoint: {e}")
        return {}

def get_current_user_info():
    """Get current user information using Azure CLI."""
    try:
        print("🔍 Getting current user information...")
        result = subprocess.run(
            ['az', 'ad', 'signed-in-user', 'show'],
            capture_output=True, text=True, check=True
        )
        user_info = json.loads(result.stdout)
        
        print(f"✅ Current user: {user_info.get('userPrincipalName', 'Unknown')}")
        print(f"   User ID: {user_info.get('id', 'Unknown')}")
        print(f"   Display Name: {user_info.get('displayName', 'Unknown')}")
        
        return user_info
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to get user info: {e}")
        print("💡 Make sure you're logged in: az login")
        return None
    except Exception as e:
        print(f"❌ Error getting user info: {e}")
        return None

def find_foundry_resource(account_name: str):
    """Find the AI Foundry account resource in Azure."""
    try:
        print(f"🔍 Searching for AI Foundry account: {account_name}")
        
        # First, get all subscriptions
        result = subprocess.run(
            ['az', 'account', 'list', '--query', '[].{id:id,name:name}'],
            capture_output=True, text=True, check=True
        )
        subscriptions = json.loads(result.stdout)
        
        for sub in subscriptions:
            sub_id = sub['id']
            sub_name = sub['name']
            print(f"🔸 Checking subscription: {sub_name} ({sub_id})")
            
            try:
                # Search for cognitive services accounts
                result = subprocess.run([
                    'az', 'cognitiveservices', 'account', 'list',
                    '--subscription', sub_id,
                    '--query', f"[?name=='{account_name}']"
                ], capture_output=True, text=True, check=True)
                
                accounts = json.loads(result.stdout)
                if accounts:
                    account = accounts[0]
                    print(f"✅ Found AI Foundry account!")
                    print(f"   Name: {account['name']}")
                    print(f"   Resource Group: {account['resourceGroup']}")
                    print(f"   Location: {account['location']}")
                    print(f"   Kind: {account['kind']}")
                    
                    return {
                        'subscription_id': sub_id,
                        'resource_group': account['resourceGroup'],
                        'account_name': account['name'],
                        'resource_id': account['id'],
                        'location': account['location'],
                        'kind': account['kind']
                    }
            except subprocess.CalledProcessError:
                continue  # Try next subscription
        
        print(f"❌ AI Foundry account '{account_name}' not found in any subscription")
        return None
        
    except Exception as e:
        print(f"❌ Error finding foundry resource: {e}")
        return None

def check_user_permissions(user_info: Dict, foundry_resource: Dict):
    """Check what permissions the user has on the AI Foundry account."""
    try:
        print("\n🔍 Checking RBAC permissions...")
        
        user_id = user_info['id']
        resource_id = foundry_resource['resource_id']
        
        # Get role assignments for the user on this resource
        result = subprocess.run([
            'az', 'role', 'assignment', 'list',
            '--assignee', user_id,
            '--scope', resource_id,
            '--include-inherited'
        ], capture_output=True, text=True, check=True)
        
        assignments = json.loads(result.stdout)
        
        if assignments:
            print(f"✅ Found {len(assignments)} role assignment(s):")
            for assignment in assignments:
                role_name = assignment.get('roleDefinitionName', 'Unknown')
                scope = assignment.get('scope', 'Unknown')
                print(f"   📋 Role: {role_name}")
                print(f"      Scope: {scope}")
                print()
        else:
            print("❌ No direct role assignments found")
            
        # Check for group memberships that might give access
        print("🔍 Checking group memberships...")
        result = subprocess.run([
            'az', 'ad', 'user', 'get-member-groups',
            '--id', user_id
        ], capture_output=True, text=True, check=True)
        
        groups = json.loads(result.stdout)
        if groups:
            print(f"✅ User is member of {len(groups)} group(s)")
            # Check if any groups have permissions
            for group_id in groups[:3]:  # Check first 3 groups
                try:
                    result = subprocess.run([
                        'az', 'role', 'assignment', 'list',
                        '--assignee', group_id,
                        '--scope', resource_id,
                        '--include-inherited'
                    ], capture_output=True, text=True, check=True)
                    
                    group_assignments = json.loads(result.stdout)
                    if group_assignments:
                        print(f"   🎯 Group {group_id} has permissions:")
                        for assignment in group_assignments:
                            role_name = assignment.get('roleDefinitionName', 'Unknown')
                            print(f"      📋 Role: {role_name}")
                except:
                    continue
        
        return assignments
        
    except Exception as e:
        print(f"❌ Error checking permissions: {e}")
        return []

def check_required_permissions(assignments: List[Dict]) -> bool:
    """Check if the user has the required permissions."""
    print("\n🎯 Analyzing permissions...")
    
    required_roles = [
        'Azure AI Developer',
        'Cognitive Services Contributor',
        'Contributor',
        'Owner'
    ]
    
    user_roles = [assignment.get('roleDefinitionName', '') for assignment in assignments]
    
    has_required = False
    for role in required_roles:
        if role in user_roles:
            print(f"✅ Found required role: {role}")
            has_required = True
            break
    
    if not has_required:
        print("❌ Missing required permissions!")
        print("\n💡 You need one of these roles:")
        for role in required_roles:
            print(f"   📋 {role}")
    
    return has_required

def suggest_permission_assignment(foundry_resource: Dict, user_info: Dict):
    """Suggest commands to assign the necessary permissions."""
    print("\n🔧 To fix permissions, run this command:")
    print("(Replace YOUR_ADMIN_USER with someone who has permission to assign roles)")
    print()
    
    resource_id = foundry_resource['resource_id']
    user_id = user_info['id']
    
    print("# Using Azure CLI:")
    print(f"az role assignment create \\")
    print(f"  --assignee {user_id} \\")
    print(f"  --role 'Azure AI Developer' \\")
    print(f"  --scope '{resource_id}'")
    print()
    
    print("# Or using PowerShell:")
    print(f"New-AzRoleAssignment `")
    print(f"  -ObjectId {user_id} `")
    print(f"  -RoleDefinitionName 'Azure AI Developer' `")
    print(f"  -Scope '{resource_id}'")

def test_token_access():
    """Test if we can get a token for AI services."""
    print("\n🔑 Testing token access...")
    
    try:
        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        print("✅ Successfully obtained token for Cognitive Services")
        return True
    except Exception as e:
        print(f"❌ Failed to get token: {e}")
        return False

def main():
    """Main function to check RBAC permissions."""
    print("🚀 AI Foundry Account RBAC Checker")
    print("=" * 50)
    
    # Load configuration
    config = load_environment()
    
    if not config['project_endpoint']:
        print("❌ PROJECT_ENDPOINT not found in .env file")
        return
    
    print(f"📋 Checking access to: {config['project_endpoint']}")
    print()
    
    # Parse the endpoint
    foundry_info = parse_foundry_endpoint(config['project_endpoint'])
    if not foundry_info:
        return
    
    account_name = foundry_info['account_name']
    print(f"🎯 Target AI Foundry Account: {account_name}")
    print()
    
    # Get current user info
    user_info = get_current_user_info()
    if not user_info:
        return
    
    # Find the foundry resource
    foundry_resource = find_foundry_resource(account_name)
    if not foundry_resource:
        return
    
    # Check permissions
    assignments = check_user_permissions(user_info, foundry_resource)
    
    # Analyze permissions
    has_access = check_required_permissions(assignments)
    
    # Test token access
    token_works = test_token_access()
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 SUMMARY")
    print("=" * 50)
    
    if has_access and token_works:
        print("✅ You have the necessary permissions!")
        print("✅ Token acquisition works!")
        print("🚀 You should be able to access the AI Foundry project")
    else:
        print("❌ Access issues detected:")
        if not has_access:
            print("   🔒 Missing required RBAC permissions")
        if not token_works:
            print("   🔑 Token acquisition failed")
        
        print()
        suggest_permission_assignment(foundry_resource, user_info)

if __name__ == "__main__":
    main()
