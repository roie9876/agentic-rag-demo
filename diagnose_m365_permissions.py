#!/usr/bin/env python3
"""
M365 Permissions Diagnostic Tool
==============================
This script will show exactly what permissions you have and guide you to add the missing ones.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_detailed_permissions():
    """Get detailed information about current permissions"""
    tenant_id = os.getenv('M365_TENANT_ID')
    client_id = os.getenv('M365_CLIENT_ID')
    client_secret = os.getenv('M365_CLIENT_SECRET')
    
    # Get access token
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default'
    }
    
    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        access_token = response.json().get('access_token')
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        print("🔍 Detailed Permissions Analysis")
        print("=" * 50)
        
        # Get service principal
        sp_url = f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '{client_id}'"
        sp_response = requests.get(sp_url, headers=headers)
        
        if sp_response.status_code == 200:
            sp_data = sp_response.json()
            if sp_data.get('value'):
                sp = sp_data['value'][0]
                sp_id = sp.get('id')
                
                print(f"📱 App: {sp.get('displayName')}")
                print(f"🆔 Service Principal ID: {sp_id}")
                print()
                
                # Get all role assignments
                assignments_url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{sp_id}/appRoleAssignments"
                assignments_response = requests.get(assignments_url, headers=headers)
                
                if assignments_response.status_code == 200:
                    assignments = assignments_response.json().get('value', [])
                    
                    print("📋 Current Application Permissions:")
                    print("-" * 40)
                    
                    if not assignments:
                        print("❌ NO PERMISSIONS FOUND!")
                        print("This explains the 403 Forbidden error.")
                        return False
                    
                    found_app_catalog_permissions = []
                    
                    for assignment in assignments:
                        resource_name = assignment.get('resourceDisplayName', 'Unknown')
                        resource_id = assignment.get('resourceId')
                        
                        print(f"\n🔗 Resource: {resource_name}")
                        
                        if resource_id and resource_name == 'Microsoft Graph':
                            # Get the specific permission details
                            resource_url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{resource_id}"
                            resource_response = requests.get(resource_url, headers=headers)
                            
                            if resource_response.status_code == 200:
                                resource_data = resource_response.json()
                                app_roles = resource_data.get('appRoles', [])
                                role_id = assignment.get('appRoleId')
                                
                                for role in app_roles:
                                    if role.get('id') == role_id:
                                        permission_name = role.get('value')
                                        permission_display = role.get('displayName')
                                        permission_desc = role.get('description', '')
                                        
                                        print(f"  ✅ {permission_name}")
                                        print(f"     Display: {permission_display}")
                                        print(f"     Description: {permission_desc[:100]}...")
                                        
                                        # Check if this is an AppCatalog permission
                                        if permission_name and 'AppCatalog' in permission_name:
                                            found_app_catalog_permissions.append(permission_name)
                                        break
                    
                    print("\n" + "=" * 50)
                    print("🎯 App Catalog Permissions Analysis:")
                    print("=" * 50)
                    
                    required_permissions = {
                        'AppCatalog.Submit': 'Required - Allows submitting apps to catalog',
                        'AppCatalog.ReadWrite.All': 'Optional - Full read/write access to catalog',
                        'AppCatalog.Read.All': 'Read-only - Can read apps from catalog'
                    }
                    
                    for perm, desc in required_permissions.items():
                        if perm in found_app_catalog_permissions:
                            print(f"✅ {perm}: FOUND - {desc}")
                        else:
                            status = "REQUIRED" if perm == 'AppCatalog.Submit' else "OPTIONAL"
                            print(f"❌ {perm}: MISSING ({status}) - {desc}")
                    
                    # Determine what needs to be done
                    has_submit = 'AppCatalog.Submit' in found_app_catalog_permissions
                    has_readwrite = 'AppCatalog.ReadWrite.All' in found_app_catalog_permissions
                    has_read = 'AppCatalog.Read.All' in found_app_catalog_permissions
                    
                    print("\n" + "=" * 50)
                    print("🔧 DIAGNOSIS:")
                    print("=" * 50)
                    
                    if has_submit:
                        print("✅ You have AppCatalog.Submit - deployment should work!")
                        return True
                    elif has_readwrite:
                        print("✅ You have AppCatalog.ReadWrite.All - this includes submit rights!")
                        return True
                    elif has_read:
                        print("⚠️ You only have READ access to the app catalog.")
                        print("❌ You need AppCatalog.Submit permission to upload apps.")
                    else:
                        print("❌ You have NO AppCatalog permissions.")
                        print("❌ This explains why you can't upload apps.")
                    
                    print("\n🔗 Azure Portal Link to fix permissions:")
                    portal_url = f"https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/{client_id}"
                    print(portal_url)
                    
                    print("\n📝 Steps to fix:")
                    print("1. Click the Azure Portal link above")
                    print("2. Click 'Add a permission'")
                    print("3. Select 'Microsoft Graph'")
                    print("4. Select 'Application permissions'")
                    print("5. Search for and select 'AppCatalog.Submit'")
                    print("6. Click 'Add permissions'")
                    print("7. Click 'Grant admin consent for [Your Organization]'")
                    print("8. Ensure status shows 'Granted for [Your Organization]'")
                    
                    return False
                else:
                    print(f"❌ Could not get role assignments: {assignments_response.status_code}")
                    return False
            else:
                print("❌ Service principal not found")
                return False
        else:
            print(f"❌ Could not get service principal: {sp_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🔍 M365 Permissions Diagnostic Tool")
    print("=" * 50)
    print("Analyzing your current permissions and providing specific guidance...")
    print()
    
    success = get_detailed_permissions()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Your permissions look good for M365 deployment!")
    else:
        print("⚠️ Permission issues found. Follow the guidance above to fix them.")
    print("=" * 50)

if __name__ == "__main__":
    main()
