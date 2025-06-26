#!/usr/bin/env python3
"""
M365 Authentication Verification Script
This script will help verify your M365 app registration settings and permissions.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_token():
    """Get an access token using client credentials flow"""
    tenant_id = os.getenv('M365_TENANT_ID')
    client_id = os.getenv('M365_CLIENT_ID')
    client_secret = os.getenv('M365_CLIENT_SECRET')
    
    print("🔍 Checking M365 credentials...")
    print(f"Tenant ID: {tenant_id}")
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {'*' * len(client_secret) if client_secret else 'NOT SET'}")
    
    if not all([tenant_id, client_id, client_secret]):
        print("❌ Missing M365 credentials in .env file")
        return None
    
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default'
    }
    
    print("\n🔐 Testing authentication...")
    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get('access_token')
        
        if access_token:
            print("✅ Authentication successful!")
            return access_token
        else:
            print("❌ No access token received")
            return None
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ Authentication failed: {e}")
        if response.status_code == 400:
            error_data = response.json()
            error_desc = error_data.get('error_description', 'Unknown error')
            print(f"Error details: {error_desc}")
            
            if 'invalid_client' in error_desc:
                print("\n🔧 Troubleshooting: Invalid Client Error")
                print("- Check that M365_CLIENT_ID is correct")
                print("- Check that M365_CLIENT_SECRET is correct and not expired")
                print("- Verify the app registration exists in the correct tenant")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def check_permissions(access_token):
    """Check what permissions the token has"""
    print("\n🔍 Checking token permissions...")
    
    # Try to access the app catalog endpoint to see if we have permissions
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # First try to get apps from the catalog (read permission check)
    try:
        catalog_url = "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps"
        response = requests.get(catalog_url, headers=headers)
        
        if response.status_code == 200:
            print("✅ Can read from app catalog (good sign)")
        elif response.status_code == 403:
            print("⚠️ Cannot read from app catalog (this might be okay)")
            error_data = response.json()
            print(f"Error: {error_data.get('error', {}).get('message', 'Unknown error')}")
        else:
            print(f"❓ Unexpected response from app catalog: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking app catalog: {e}")

def main():
    print("=" * 60)
    print("🔧 M365 Authentication Verification Tool")
    print("=" * 60)
    
    # Step 1: Get access token
    access_token = get_token()
    
    if not access_token:
        print("\n❌ Cannot proceed without valid access token")
        print("\n🔧 Next Steps:")
        print("1. Verify your M365 app registration exists in Azure Portal")
        print("2. Check that M365_TENANT_ID, M365_CLIENT_ID, M365_CLIENT_SECRET are correct in .env")
        print("3. Ensure the client secret hasn't expired")
        print("4. Make sure you're using the correct tenant ID")
        return
    
    # Step 2: Check permissions
    check_permissions(access_token)
    
    print("\n📋 Required Permissions Check:")
    print("Your app registration should have these permissions:")
    print("- Microsoft Graph → Application permissions → AppCatalog.Submit")
    print("- Microsoft Graph → Application permissions → AppCatalog.ReadWrite.All (optional)")
    print("\n⚠️ IMPORTANT: Admin consent must be granted for these permissions!")
    
    print("\n🔗 How to check/grant permissions:")
    print("1. Go to Azure Portal → Azure Active Directory → App registrations")
    print("2. Find your M365 app registration")
    print("3. Go to 'API permissions'")
    print("4. Check that AppCatalog.Submit is listed")
    print("5. Click 'Grant admin consent for [Your Organization]'")
    print("6. Ensure the status shows 'Granted for [Your Organization]'")

if __name__ == "__main__":
    main()
