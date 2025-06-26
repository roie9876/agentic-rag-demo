#!/usr/bin/env python3
"""
Test HTTP-based M365 deployment method
"""

import os
import sys
from pathlib import Path
import json

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from m365_agent_tab import M365AgentManager
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Check if we have the required credentials
    tenant_id = os.getenv("M365_TENANT_ID")
    client_id = os.getenv("M365_CLIENT_ID") 
    client_secret = os.getenv("M365_CLIENT_SECRET")
    
    print("🔍 Testing HTTP Deployment Method")
    print("=" * 50)
    
    if not all([tenant_id, client_id, client_secret]):
        print("❌ Missing M365 credentials in .env file")
        print("Required: M365_TENANT_ID, M365_CLIENT_ID, M365_CLIENT_SECRET")
        sys.exit(1)
    
    print("✅ M365 credentials found")
    print(f"   Tenant ID: {tenant_id[:8]}...")
    print(f"   Client ID: {client_id[:8]}...")
    print(f"   Secret: {'*' * len(client_secret)}")
    
    # Create manager instance
    manager = M365AgentManager()
    
    # Test the HTTP deployment method (without actually deploying)
    print("\n🧪 Testing HTTP deployment connectivity...")
    
    # We'll test just the token acquisition part
    import requests
    
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default"
    }
    
    print(f"🔐 Testing token acquisition from: {token_url}")
    
    try:
        token_response = requests.post(token_url, data=token_data, timeout=30)
        
        if token_response.status_code == 200:
            token_data = token_response.json()
            if "access_token" in token_data:
                print("✅ Successfully obtained access token")
                print(f"   Token type: {token_data.get('token_type', 'Unknown')}")
                print(f"   Expires in: {token_data.get('expires_in', 'Unknown')} seconds")
                
                # Test permissions by attempting to read the app catalog
                print("\n🔍 Testing permissions (reading app catalog)...")
                headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                catalog_url = "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps"
                
                catalog_response = requests.get(catalog_url, headers=headers, timeout=30)
                
                if catalog_response.status_code == 200:
                    print("✅ Successfully accessed Teams App Catalog")
                    catalog_data = catalog_response.json()
                    app_count = len(catalog_data.get("value", []))
                    print(f"   Found {app_count} apps in catalog")
                    print("✅ HTTP deployment method should work!")
                    
                elif catalog_response.status_code == 403:
                    print("❌ Access denied to Teams App Catalog")
                    print("   Issue: Missing or incorrect permissions")
                    print("   Solution: Add 'AppCatalog.Submit' Application permission")
                    print("   Note: Must be Application permission, not Delegated")
                    
                else:
                    print(f"⚠️ Unexpected response: {catalog_response.status_code}")
                    print(f"   Response: {catalog_response.text[:200]}")
                    
            else:
                print("❌ No access token in response")
                print(f"   Response: {token_response.text}")
        
        else:
            print(f"❌ Failed to get token: {token_response.status_code}")
            print(f"   Response: {token_response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print("\n📋 Summary:")
    print("- HTTP deployment method is available")
    print("- Should be faster and more reliable than PowerShell")
    print("- Requires correct Application permissions in Azure AD")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the correct directory")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
