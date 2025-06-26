#!/usr/bin/env python3
"""
M365 App Catalog Permissions Research
====================================
This script will help identify what permissions are actually available for AppCatalog operations.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def research_app_catalog_permissions():
    """Research what AppCatalog permissions are available"""
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
        
        print("🔍 Researching Available AppCatalog Permissions")
        print("=" * 60)
        
        # Get Microsoft Graph service principal to see all available permissions
        graph_sp_url = "https://graph.microsoft.com/v1.0/servicePrincipals?$filter=displayName eq 'Microsoft Graph'"
        graph_response = requests.get(graph_sp_url, headers=headers)
        
        if graph_response.status_code == 200:
            graph_data = graph_response.json()
            if graph_data.get('value'):
                graph_sp = graph_data['value'][0]
                
                print("📋 Available Application Permissions (App Roles):")
                print("-" * 50)
                
                app_roles = graph_sp.get('appRoles', [])
                app_catalog_app_roles = []
                
                for role in app_roles:
                    if 'AppCatalog' in role.get('value', ''):
                        app_catalog_app_roles.append(role)
                        print(f"✅ {role.get('value')}")
                        print(f"   Display: {role.get('displayName')}")
                        print(f"   Description: {role.get('description', '')[:100]}...")
                        print()
                
                if not app_catalog_app_roles:
                    print("❌ No AppCatalog Application permissions found!")
                
                print("\n📋 Available Delegated Permissions (OAuth2 Permissions):")
                print("-" * 50)
                
                oauth2_permissions = graph_sp.get('oauth2PermissionScopes', [])
                app_catalog_delegated = []
                
                for perm in oauth2_permissions:
                    if 'AppCatalog' in perm.get('value', ''):
                        app_catalog_delegated.append(perm)
                        print(f"✅ {perm.get('value')}")
                        print(f"   Display: {perm.get('displayName')}")
                        print(f"   Description: {perm.get('description', '')[:100]}...")
                        print(f"   Admin Consent Required: {perm.get('isEnabled')}")
                        print()
                
                if not app_catalog_delegated:
                    print("❌ No AppCatalog Delegated permissions found!")
                
                # Analysis
                print("\n" + "=" * 60)
                print("🎯 ANALYSIS:")
                print("=" * 60)
                
                if app_catalog_app_roles:
                    print("✅ AppCatalog Application permissions are available")
                    print("   → You can use client credentials flow")
                elif app_catalog_delegated:
                    print("⚠️ Only AppCatalog Delegated permissions are available")
                    print("   → You need to use a different authentication flow")
                    print("   → Options:")
                    print("     1. Use authorization code flow with user consent")
                    print("     2. Use device code flow")
                    print("     3. Check if there are alternative permissions")
                else:
                    print("❌ No AppCatalog permissions found at all!")
                    print("   → This tenant may not support app catalog operations")
                    print("   → Or the permissions have different names")
                
                # Alternative approaches
                print("\n💡 ALTERNATIVE APPROACHES:")
                print("-" * 40)
                print("1. **Teams Admin Center**: Manual upload via web interface")
                print("2. **Teams PowerShell**: Use Teams PowerShell module")
                print("3. **Different API**: Check if there are other APIs available")
                print("4. **Service Account**: Use a service account with delegated permissions")
                
            else:
                print("❌ Microsoft Graph service principal not found")
        else:
            print(f"❌ Could not get Microsoft Graph service principal: {graph_response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def suggest_solutions():
    """Suggest alternative solutions"""
    print("\n" + "=" * 60)
    print("🔧 SOLUTION OPTIONS:")
    print("=" * 60)
    
    print("\n**Option 1: Use Delegated Permissions with Service Account**")
    print("1. Create a dedicated service account user")
    print("2. Grant that user Teams admin permissions")
    print("3. Use authorization code flow or device code flow")
    print("4. Store refresh token for automated operations")
    
    print("\n**Option 2: Use Teams PowerShell Module**")
    print("1. Install Microsoft Teams PowerShell module")
    print("2. Use Connect-MicrosoftTeams with service account")
    print("3. Use New-TeamsApp cmdlet to upload apps")
    
    print("\n**Option 3: Manual Upload with Automation**")
    print("1. Use Selenium or similar to automate web browser")
    print("2. Navigate to Teams Admin Center")
    print("3. Automate the upload process via UI")
    
    print("\n**Option 4: Check for Alternative Permissions**")
    print("1. Look for TeamsApp.* permissions")
    print("2. Check Directory.* permissions")
    print("3. Look for Application.* permissions")

def main():
    print("🔍 M365 App Catalog Permissions Research")
    print("=" * 60)
    print("Investigating what permissions are actually available...")
    print()
    
    research_app_catalog_permissions()
    suggest_solutions()
    
    print("\n" + "=" * 60)
    print("📝 NEXT STEPS:")
    print("=" * 60)
    print("1. Review the available permissions above")
    print("2. Choose the most suitable approach for your use case")
    print("3. Implement the chosen solution")
    print("4. Test the deployment")

if __name__ == "__main__":
    main()
