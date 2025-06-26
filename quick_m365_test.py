#!/usr/bin/env python3
"""
Quick M365 Agent Test
====================
A simple test script to quickly verify your M365 setup.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def quick_test():
    print("🚀 Quick M365 Agent Test")
    print("=" * 40)
    
    # Check environment variables
    tenant_id = os.getenv('M365_TENANT_ID')
    client_id = os.getenv('M365_CLIENT_ID')
    client_secret = os.getenv('M365_CLIENT_SECRET')
    
    print(f"✓ Tenant ID: {tenant_id[:8] + '...' if tenant_id else 'MISSING'}")
    print(f"✓ Client ID: {client_id[:8] + '...' if client_id else 'MISSING'}")
    print(f"✓ Client Secret: {'SET' if client_secret else 'MISSING'}")
    
    if not all([tenant_id, client_id, client_secret]):
        print("❌ Missing credentials in .env file")
        return False
    
    # Test authentication
    print("\n🔐 Testing authentication...")
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default'
    }
    
    try:
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            print("✅ Authentication successful!")
            
            # Test app catalog access
            print("\n📱 Testing app catalog access...")
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            headers = {'Authorization': f'Bearer {access_token}'}
            catalog_url = "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps"
            
            catalog_response = requests.get(catalog_url, headers=headers)
            
            if catalog_response.status_code == 200:
                print("✅ App catalog access successful!")
                print("🎉 Your M365 Agent deployment should work!")
                return True
            elif catalog_response.status_code == 403:
                print("❌ App catalog access denied")
                print("💡 You need Application permissions (not Delegated)")
                print("💡 Required: Microsoft Graph → Application permissions → AppCatalog.Submit")
                return False
            else:
                print(f"❌ App catalog test failed: {catalog_response.status_code}")
                return False
        else:
            error_data = response.json() if response.content else {}
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"Error: {error_data.get('error_description', 'Unknown')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = quick_test()
    
    if not success:
        print("\n🔧 Quick fixes:")
        print("1. Check your .env file has M365_TENANT_ID, M365_CLIENT_ID, M365_CLIENT_SECRET")
        print("2. Ensure your app has Application permissions (not Delegated)")
        print("3. Grant admin consent for permissions")
        
    exit(0 if success else 1)
