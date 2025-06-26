"""
M365 Agent Upload Script
=======================
Upload the M365 Agent package to Microsoft Graph App Catalog
"""

import os
import requests
import json
from pathlib import Path
from typing import Optional, Dict, Any


def get_access_token(tenant_id: str, client_id: str, client_secret: str) -> Optional[str]:
    """Get access token using client credentials flow"""
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
    
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json().get("access_token")
    except requests.RequestException as e:
        print(f"Failed to get access token: {e}")
        return None


def upload_to_app_catalog(access_token: str, zip_path: Path) -> Dict[str, Any]:
    """Upload the app package to Microsoft Graph App Catalog"""
    url = "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/zip"
    }
    
    try:
        with open(zip_path, "rb") as f:
            response = requests.post(url, headers=headers, data=f)
        
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Failed to upload app: {e}")
        return {"error": str(e)}


def main():
    """Main upload function"""
    # Read credentials from environment - using dedicated M365 variables
    tenant_id = os.getenv("M365_TENANT_ID")
    client_id = os.getenv("M365_CLIENT_ID")
    client_secret = os.getenv("M365_CLIENT_SECRET")
    
    if not all([tenant_id, client_id, client_secret]):
        print("Error: Missing required environment variables:")
        print("- M365_TENANT_ID")
        print("- M365_CLIENT_ID")
        print("- M365_CLIENT_SECRET")
        return
    
    # Check if app package exists
    zip_path = Path("appPackage.zip")
    if not zip_path.exists():
        print(f"Error: {zip_path} not found. Run the M365 Agent tab to create the package first.")
        return
    
    print("Getting access token...")
    access_token = get_access_token(tenant_id, client_id, client_secret)
    if not access_token:
        print("Failed to get access token")
        return
    
    print(f"Uploading {zip_path} to Microsoft Graph App Catalog...")
    result = upload_to_app_catalog(access_token, zip_path)
    
    if "error" in result:
        print(f"Upload failed: {result['error']}")
    else:
        print("✅ Upload successful!")
        print(f"App ID: {result.get('id', 'Not provided')}")
        print(f"Display Name: {result.get('displayName', 'Not provided')}")
        print()
        print("📝 Next Steps:")
        print("1. Open Teams Admin Center (https://admin.teams.microsoft.com)")
        print("2. Go to Teams apps → Manage apps")
        print("3. Find your app and set Publishing State = 'Published'")
        print("4. Configure permissions and policies as needed")
        print("5. The app will be available in Microsoft 365 Copilot")


if __name__ == "__main__":
    main()
