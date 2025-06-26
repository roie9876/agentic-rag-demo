#!/usr/bin/env python3
"""
Quick M365 Package Creator
==========================
Creates an M365 agent package for testing PowerShell deployment.
"""

import os
import json
import uuid
import zipfile
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_test_package():
    """Create a test M365 agent package"""
    
    # Package configuration
    plugin_id = "com.contoso.funcproxy"
    app_name = "Test Func Proxy"
    app_desc = "Test Azure Function proxy for M365 Copilot"
    package_ver = "1.0.0"
    
    # Get Azure Function URL from environment or use a test URL
    azure_func_url = os.getenv('AZURE_FUNCTION_URL', 'https://your-function-app.azurewebsites.net')
    func_key = os.getenv('AZURE_FUNCTION_KEY', 'your-function-key')
    
    print("🔧 Creating M365 Agent Package...")
    print(f"📦 App Name: {app_name}")
    print(f"🔗 Function URL: {azure_func_url}")
    
    # Create manifest
    manifest = {
        "$schema": "https://developer.microsoft.com/en-us/json-schemas/teams/v1.17/MicrosoftTeams.schema.json",
        "manifestVersion": "1.17",
        "version": package_ver,
        "id": plugin_id,
        "packageName": plugin_id,
        "developer": {
            "name": "Contoso",
            "websiteUrl": "https://www.contoso.com",
            "privacyUrl": "https://www.contoso.com/privacy",
            "termsOfUseUrl": "https://www.contoso.com/terms"
        },
        "icons": {
            "color": "color.png",
            "outline": "outline.png"
        },
        "name": {
            "short": app_name,
            "full": app_name
        },
        "description": {
            "short": app_desc,
            "full": app_desc
        },
        "accentColor": "#FFFFFF",
        "composeExtensions": [
            {
                "botId": plugin_id,
                "commands": [
                    {
                        "id": "searchQuery",
                        "context": ["compose", "commandBox"],
                        "description": "Search and retrieve information",
                        "title": "Search",
                        "type": "query",
                        "parameters": [
                            {
                                "name": "query",
                                "title": "Search Query",
                                "description": "Enter your search query",
                                "inputType": "text"
                            }
                        ]
                    }
                ]
            }
        ],
        "copilotExtensions": {
            "plugins": [
                {
                    "id": plugin_id,
                    "file": "ai-plugin.json"
                }
            ]
        },
        "permissions": [
            "identity",
            "messageTeamMembers"
        ],
        "validDomains": [
            "*.azurewebsites.net"
        ]
    }
    
    # Create AI plugin
    ai_plugin = {
        "schema_version": "v1",
        "name_for_human": app_name,
        "name_for_model": "func_proxy",
        "description_for_human": app_desc,
        "description_for_model": "A simple proxy to an Azure Function that can search and retrieve information.",
        "auth": {
            "type": "service_http",
            "authorization_type": "bearer",
            "verification_tokens": {
                "openai": func_key
            }
        },
        "api": {
            "type": "openapi",
            "url": f"{azure_func_url}/api/openapi.json",
            "is_user_authenticated": False
        },
        "logo_url": f"{azure_func_url}/logo.png",
        "contact_email": "support@contoso.com",
        "legal_info_url": "https://www.contoso.com/legal"
    }
    
    # Create simple placeholder icons (1x1 pixel PNGs)
    color_icon = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x12IDATx\x9cc```bPPP\x00\x02\xd2\'\x05\xfe\xbf\x00\x00\x0e\xa6\x00-\xcf7\xd4\x00\x00\x00\x00IEND\xaeB`\x82'
    outline_icon = color_icon  # Same for simplicity
    
    # Create package
    package_path = "appPackage.zip"
    
    with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add manifest
        zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))
        
        # Add AI plugin
        zip_file.writestr("ai-plugin.json", json.dumps(ai_plugin, indent=2))
        
        # Add icons
        zip_file.writestr("color.png", color_icon)
        zip_file.writestr("outline.png", outline_icon)
    
    print(f"✅ Package created: {package_path}")
    print(f"📊 Package size: {os.path.getsize(package_path)} bytes")
    
    # Verify package contents
    print("\n📋 Package contents:")
    with zipfile.ZipFile(package_path, 'r') as zip_file:
        for filename in zip_file.namelist():
            info = zip_file.getinfo(filename)
            print(f"  - {filename} ({info.file_size} bytes)")
    
    return package_path

def main():
    print("🚀 M365 Package Creator")
    print("=" * 40)
    
    try:
        package_path = create_test_package()
        
        print("\n" + "=" * 40)
        print("✅ Package ready for deployment!")
        print("=" * 40)
        print(f"📦 Package: {package_path}")
        print("\n🔧 Next steps:")
        print("1. Test PowerShell deployment:")
        print("   ./deploy_m365_powershell.ps1")
        print("\n2. Or upload manually:")
        print("   Teams Admin Center → Manage apps → Upload")
        print(f"   Upload file: {package_path}")
        
    except Exception as e:
        print(f"❌ Error creating package: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
