#!/usr/bin/env python3
"""
Simple M365 Deployment Test
===========================
Test actual deployment to M365 with a minimal package.
"""

import os
import requests
import json
import tempfile
import zipfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def create_minimal_test_package():
    """Create a minimal test package for deployment"""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create minimal manifest
    manifest = {
        "$schema": "https://developer.microsoft.com/en-us/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
        "manifestVersion": "1.16",
        "id": f"test-m365-agent-{os.urandom(4).hex()}",
        "version": "1.0.0",
        "packageName": "com.test.m365agent",
        "developer": {
            "name": "Test Corp",
            "websiteUrl": "https://test.com",
            "privacyUrl": "https://test.com/privacy",
            "termsOfUseUrl": "https://test.com/terms"
        },
        "name": {
            "short": "Test M365 Agent",
            "full": "Test M365 Agent - Deployment Test"
        },
        "description": {
            "short": "Test agent",
            "full": "A test M365 Copilot plugin for testing deployment"
        },
        "icons": {
            "outline": "outline.png",
            "color": "color.png"
        },
        "accentColor": "#FFFFFF",
        "copilotAgents": {
            "declarativeAgents": [
                {
                    "id": "com.test.agent",
                    "file": "plugin.json"
                }
            ]
        }
    }
    
    # Create minimal plugin
    plugin = {
        "$schema": "https://developer.microsoft.com/en-us/microsoft-365/copilot/schema/api-plugin-manifest.2.2.json",
        "id": "com.test.agent",
        "name": "Test Agent",
        "description": "Test agent for deployment",
        "version": "1.0.0",
        "api": {
            "openapi": {
                "url": "./openapi.json"
            },
            "auth": {
                "type": "apiKey",
                "keyHeaderName": "x-functions-key"
            }
        }
    }
    
    # Create minimal OpenAPI
    openapi = {
        "openapi": "3.0.3",
        "info": {
            "title": "Test API",
            "description": "Test API",
            "version": "1.0.0"
        },
        "servers": [{"url": "https://test.azurewebsites.net"}],
        "paths": {
            "/api/test": {
                "post": {
                    "operationId": "test",
                    "summary": "Test",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"question": {"type": "string"}}
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Success"}}
                }
            }
        }
    }
    
    # Write files
    with open(temp_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    
    with open(temp_dir / "plugin.json", "w") as f:
        json.dump(plugin, f, indent=2)
    
    with open(temp_dir / "openapi.json", "w") as f:
        json.dump(openapi, f, indent=2)
    
    # Create minimal PNG placeholders (1x1 pixel)
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'
    
    (temp_dir / "color.png").write_bytes(png_data)
    (temp_dir / "outline.png").write_bytes(png_data)
    
    # Create zip
    zip_path = temp_dir / "test-package.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file_path in temp_dir.iterdir():
            if file_path.is_file() and file_path.name != "test-package.zip":
                zipf.write(file_path, file_path.name)
    
    return zip_path

def test_deployment():
    """Test actual deployment"""
    print("🚀 Testing M365 Agent Deployment")
    print("=" * 50)
    
    # Get credentials
    tenant_id = os.getenv('M365_TENANT_ID')
    client_id = os.getenv('M365_CLIENT_ID')
    client_secret = os.getenv('M365_CLIENT_SECRET')
    
    if not all([tenant_id, client_id, client_secret]):
        print("❌ Missing M365 credentials")
        return False
    
    # Get access token
    print("🔐 Getting access token...")
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default'
    }
    
    try:
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        access_token = token_response.json().get('access_token')
        
        if not access_token:
            print("❌ No access token received")
            return False
        
        print("✅ Access token obtained")
        
        # Create test package
        print("📦 Creating test package...")
        package_path = create_minimal_test_package()
        print(f"✅ Test package created: {package_path}")
        
        # Upload to M365
        print("🚀 Uploading to Microsoft Graph...")
        upload_url = "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/zip'
        }
        
        with open(package_path, "rb") as f:
            upload_response = requests.post(upload_url, headers=headers, data=f)
        
        print(f"📊 Upload response: HTTP {upload_response.status_code}")
        
        if upload_response.status_code in [200, 201]:
            result = upload_response.json()
            app_id = result.get('id', 'Unknown')
            app_name = result.get('displayName', 'Unknown')
            
            print("🎉 SUCCESS! M365 Agent deployed!")
            print(f"   App ID: {app_id}")
            print(f"   App Name: {app_name}")
            print()
            print("📝 Next Steps:")
            print("1. Go to Teams Admin Center: https://admin.teams.microsoft.com")
            print("2. Navigate to Teams apps → Manage apps")
            print("3. Find your test app and DELETE it (it's just a test)")
            print("4. Your real M365 Agent deployment should now work!")
            
            # Clean up
            package_path.unlink()
            try:
                package_path.parent.rmdir()
            except OSError:
                pass
            
            return True
        else:
            print(f"❌ Upload failed: HTTP {upload_response.status_code}")
            
            try:
                error_data = upload_response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {upload_response.text}")
            
            # Clean up
            package_path.unlink()
            try:
                package_path.parent.rmdir()
            except OSError:
                pass
            
            return False
            
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_deployment()
    
    if success:
        print("\n🎯 Your M365 Agent setup is working!")
        print("You can now deploy real M365 agents using the Streamlit app.")
    else:
        print("\n🔧 Deployment test failed. Check the errors above.")
    
    exit(0 if success else 1)
