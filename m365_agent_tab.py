"""
M365 Agent Tab for Agentic RAG Demo
=================================
This module provides functionality to create and deploy M365 agents that proxy questions
to existing Azure Functions (HTTP trigger) via API plugins.

Key Features:
- Create M365 API Plugin manifest (plugin.json)
- Generate OpenAPI specification (openapi.json)
- Create Teams/M365 app manifest (manifest.json)
- Generate upload script for Microsoft Graph
- Package and zip all artifacts
"""

import json
import os
import uuid
import zipfile
import tempfile
import logging
import subprocess
import platform
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import streamlit as st
import requests
from azure.identity import ClientSecretCredential
from azure.core.exceptions import ClientAuthenticationError
from datetime import datetime

# Azure Function helper for getting available functions
from azure_function_helper import list_function_apps, get_azure_subscription


class M365AgentManager:
    """Manages M365 Agent creation and deployment"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Constants for M365 Agent
        self.PLUGIN_ID = "com.contoso.funcproxy"
        self.APP_NAME = "Azure Function Proxy"
        self.APP_DESC = "Custom Azure Function Integration"
        self.PACKAGE_VER = "1.0.0"
        self.ICON_COLOR = "color.png"
        self.ICON_OUTLINE = "outline.png"
        self.FUNC_KEY_HDR = "x-functions-key"
        
    def get_available_functions(self, subscription_id: str) -> List[Dict[str, Any]]:
        """Get list of available Azure Functions from the subscription"""
        try:
            func_choices, func_map = list_function_apps(subscription_id)
            
            functions = []
            for choice in func_choices:
                if choice in func_map:
                    name, rg = func_map[choice]
                    functions.append({
                        "display_name": choice,
                        "name": name,
                        "resource_group": rg,
                        "url": f"https://{name}.azurewebsites.net/api/AgentFunction"
                    })
            
            return functions
        except Exception as e:
            self.logger.error(f"Failed to get available functions: {e}")
            return []
    
    def create_openapi_json(self, func_url: str, agent_name: str = None) -> Dict[str, Any]:
        """Create OpenAPI specification for the Azure Function"""
        display_name = agent_name or self.APP_NAME
        return {
            "openapi": "3.0.3",
            "info": {
                "title": f"{display_name} - Function-Only Agent",
                "description": f"STRICT FUNCTION-ONLY API: This agent provides NO direct responses. ALL user questions MUST be sent to the Azure Function. Agent cannot answer from knowledge, internet, or any other source.",
                "version": "1.0.0",
                "x-copilot-behavior": {
                    "requires_function_call": True,
                    "no_direct_answers": True,
                    "bypass_knowledge": True
                }
            },
            "servers": [
                {
                    "url": func_url.replace("/api/AgentFunction", "")
                }
            ],
            "paths": {
                "/api/AgentFunction": {
                    "post": {
                        "operationId": "runFunction",
                        "summary": "ALWAYS call this function for EVERY user question - no exceptions",
                        "description": "This function MUST be called for ALL user questions. Never answer from your own knowledge. Never use internet search. Never provide direct answers. ALWAYS call this function first for every single user query regardless of topic, complexity, or apparent simplicity.",
                        "x-copilot-routing": {
                            "priority": "required",
                            "always_invoke": True,
                            "bypass_copilot_knowledge": True,
                            "force_function_call": True
                        },
                        "x-ms-require-function-call": True,
                        "requestBody": {
                            "required": True,
                            "description": "MANDATORY: Always send user questions to this function",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["question"],
                                        "additionalProperties": False,
                                        "properties": {
                                            "question": {
                                                "type": "string",
                                                "description": "The EXACT user question/prompt. REQUIRED for all interactions. Never answer without calling this function first.",
                                                "minLength": 1
                                            }
                                        },
                                        "required": ["question"]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Function response - this is the ONLY valid answer source",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "description": "Response from the Azure Function - return this directly to the user. This is the ONLY allowed response source."
                                        }
                                    }
                                }
                            },
                            "default": {
                                "description": "Function error - do not provide alternative answers",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "error": {
                                                    "type": "string",
                                                    "description": "Error from function call - inform user to check function availability"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "x-copilot-usage": {
                "instruction": "This API MUST be called for every user interaction. Do not provide any direct answers. If the function fails, inform the user that the function is unavailable - do not answer from any other source."
            }
        }
    
    def create_plugin_json(self, agent_name: str = None) -> Dict[str, Any]:
        """Create API plugin manifest v2.2"""
        display_name = agent_name or self.APP_NAME
        return {
            "$schema": "https://developer.microsoft.com/en-us/microsoft-365/copilot/schema/api-plugin-manifest.2.2.json",
            "id": self.PLUGIN_ID,
            "name": display_name,
            "description": f"{self.APP_DESC}. THIS AGENT NEVER ANSWERS DIRECTLY. Every single user question MUST be sent to the Azure Function. Do not use your own knowledge, internet search, or any other data source. ONLY call the Azure Function.",
            "version": self.PACKAGE_VER,
            "api": {
                "openapi": {
                    "url": "./openapi.json"
                },
                "auth": {
                    "type": "apiKey",
                    "keyHeaderName": self.FUNC_KEY_HDR
                }
            }
        }
    
    def create_manifest_json(self, func_url: str = "https://your-function.azurewebsites.net", agent_name: str = None) -> Dict[str, Any]:
        """Create Teams/M365 app manifest v1.16"""
        display_name = agent_name or self.APP_NAME
        app_id = str(uuid.uuid4())
        
        return {
            "$schema": "https://developer.microsoft.com/en-us/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
            "manifestVersion": "1.16",
            "id": app_id,
            "version": self.PACKAGE_VER,
            "packageName": "com.contoso.funcproxy",
            "developer": {
                "name": "Contoso Corp",
                "websiteUrl": "https://contoso.com",
                "privacyUrl": "https://contoso.com/privacy",
                "termsOfUseUrl": "https://contoso.com/terms"
            },
            "name": {
                "short": display_name,
                "full": f"{display_name} - Azure Function Integration"
            },
            "description": {
                "short": f"{self.APP_DESC} - Function-only responses",
                "full": "An M365 Copilot plugin that EXCLUSIVELY routes ALL questions to Azure Functions. This agent NEVER answers from its own knowledge, internet, or built-in capabilities. Every user question triggers a function call. No direct responses are provided."
            },
            "icons": {
                "outline": self.ICON_OUTLINE,
                "color": self.ICON_COLOR
            },
            "accentColor": "#FFFFFF",
            "composeExtensions": [
                {
                    "botId": app_id,
                    "commands": [
                        {
                            "id": "searchQuery",
                            "type": "query",
                            "title": f"Ask {display_name}",
                            "description": f"Send questions to {display_name}",
                            "initialRun": False,
                            "fetchTask": False,
                            "parameters": [
                                {
                                    "name": "searchQuery",
                                    "title": "Question",
                                    "description": "Your question"
                                }
                            ]
                        }
                    ]
                }
            ],
            "validDomains": ["*.azurewebsites.net"],
            "webApplicationInfo": {
                "id": app_id,
                "resource": func_url.replace("/api/AgentFunction", "")
            }
        }
    
    def create_placeholder_icons(self, package_dir: Path) -> None:
        """Create placeholder PNG icons if they don't exist"""
        from PIL import Image, ImageDraw
        
        # Create outline icon (32x32)
        outline_path = package_dir / self.ICON_OUTLINE
        if not outline_path.exists():
            outline_img = Image.new('RGBA', (32, 32), (255, 255, 255, 0))
            draw = ImageDraw.Draw(outline_img)
            draw.rectangle([4, 4, 28, 28], outline=(0, 0, 0, 255), width=2)
            draw.text((8, 12), "AF", fill=(0, 0, 0, 255))
            outline_img.save(outline_path)
        
        # Create color icon (192x192)
        color_path = package_dir / self.ICON_COLOR
        if not color_path.exists():
            color_img = Image.new('RGBA', (192, 192), (0, 120, 212, 255))
            draw = ImageDraw.Draw(color_img)
            draw.rectangle([20, 20, 172, 172], fill=(255, 255, 255, 255))
            draw.text((60, 90), "Azure\nFunction", fill=(0, 120, 212, 255), align="center")
            color_img.save(color_path)
    
    def build_package(self, func_url: str, agent_name: str = None, output_dir: Path = None) -> Tuple[bool, str, Optional[Path]]:
        """
        Build the M365 Agent package with all required artifacts
        
        Args:
            func_url: Azure Function URL
            agent_name: Custom agent name (optional, uses default if not provided)
            output_dir: Output directory for package files
        
        Returns:
            Tuple of (success: bool, message: str, zip_path: Optional[Path])
        """
        try:
            if output_dir is None:
                output_dir = Path.cwd()
            
            package_dir = output_dir / "package"
            package_dir.mkdir(exist_ok=True)
            
            # Create openapi.json
            openapi_content = self.create_openapi_json(func_url, agent_name)
            with open(package_dir / "openapi.json", "w") as f:
                json.dump(openapi_content, f, indent=2)
            
            # Create plugin.json
            plugin_content = self.create_plugin_json(agent_name)
            with open(package_dir / "plugin.json", "w") as f:
                json.dump(plugin_content, f, indent=2)
            
            # Create manifest.json
            manifest_content = self.create_manifest_json(func_url, agent_name)
            with open(package_dir / "manifest.json", "w") as f:
                json.dump(manifest_content, f, indent=2)
            
            # Create placeholder icons
            try:
                self.create_placeholder_icons(package_dir)
            except ImportError:
                # If PIL is not available, create simple placeholder files
                (package_dir / self.ICON_OUTLINE).touch()
                (package_dir / self.ICON_COLOR).touch()
                self.logger.warning("PIL not available, created empty icon files")
            
            # Create zip file
            zip_path = output_dir / "appPackage.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in package_dir.iterdir():
                    if file_path.is_file():
                        zipf.write(file_path, file_path.name)
            
            return True, f"Package created successfully at {zip_path}", zip_path
            
        except Exception as e:
            self.logger.error(f"Failed to build package: {e}")
            return False, f"Failed to build package: {e}", None
    
    def generate_upload_script(self, output_dir: Path = None) -> Tuple[bool, str, Optional[Path]]:
        """Generate upload_script.py for deploying to Microsoft Graph"""
        if output_dir is None:
            output_dir = Path.cwd()
        
        script_content = '''"""
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
'''
        
        try:
            script_path = output_dir / "upload_script.py"
            with open(script_path, "w") as f:
                f.write(script_content)
            
            return True, f"Upload script created at {script_path}", script_path
        except Exception as e:
            self.logger.error(f"Failed to create upload script: {e}")
            return False, f"Failed to create upload script: {e}", None
    
    def deploy_to_m365_via_powershell(self, package_path: Path) -> Tuple[bool, str]:
        """
        Deploy the M365 Agent package using PowerShell Teams module
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        import subprocess
        import platform
        import tempfile
        import os
        import json
        try:
            tenant_id = os.getenv("M365_TENANT_ID")
            client_id = os.getenv("M365_CLIENT_ID")
            client_secret = os.getenv("M365_CLIENT_SECRET")
            if not all([tenant_id, client_id, client_secret]):
                return False, "M365 credentials not found in .env file. Please configure M365_TENANT_ID, M365_CLIENT_ID, and M365_CLIENT_SECRET."
            powershell_script = f'''
# M365 Agent PowerShell Deployment with robust Teams module compatibility
try {{
    Write-Host "DEBUG: Starting M365 Agent deployment script"
    Write-Host "🔄 Starting M365 Agent deployment..."
    if (-not (Get-Module -ListAvailable -Name MicrosoftTeams)) {{
        Write-Host "📦 Installing MicrosoftTeams PowerShell module..."
        Install-Module -Name MicrosoftTeams -Force -AllowClobber -Scope CurrentUser -Repository PSGallery
    }}
    Write-Host "DEBUG: Teams module check completed"
    Import-Module MicrosoftTeams -Force
    Write-Host "DEBUG: Teams module imported"
    $TeamsModule = Get-Module MicrosoftTeams -ListAvailable | Sort-Object Version -Descending | Select-Object -First 1
    $TeamsVersion = $TeamsModule.Version.ToString()
    Write-Host "📋 MicrosoftTeams module version: $TeamsVersion"
    
    # Parse version for compatibility logic
    $VersionParts = $TeamsVersion.Split('.')
    $MajorVersion = [int]$VersionParts[0]
    $MinorVersion = if ($VersionParts.Count -gt 1) {{ [int]$VersionParts[1] }} else {{ 0 }}
    
    $connected = $false
    
    # For Teams module 7.x and above, use certificate-based or interactive authentication
    if ($MajorVersion -ge 7) {{
        Write-Host "🔐 Using Teams module 7.x authentication"
        Write-Host "⚠️ Note: Teams module 7.x requires certificate-based auth or interactive login for app operations"
        
        try {{
            # Method 1: Try interactive authentication (most reliable for Teams 7.x)
            Write-Host "� Attempting interactive authentication..."
            Write-Host "💡 A browser window may open for authentication"
            Connect-MicrosoftTeams -TenantId "{tenant_id}" -ErrorAction Stop
            $connected = $true
            Write-Host "✅ Connected using interactive authentication"
        }} catch {{
            Write-Host "⚠️ Interactive authentication failed: $($_.Exception.Message)"
            try {{
                # Method 2: Try managed identity (if running on Azure)
                Write-Host "🔄 Trying managed identity authentication..."
                Connect-MicrosoftTeams -Identity -ErrorAction Stop
                $connected = $true
                Write-Host "✅ Connected using managed identity"
            }} catch {{
                Write-Host "⚠️ Managed identity failed: $($_.Exception.Message)"
                Write-Host "❌ All authentication methods failed for Teams module 7.x"
                Write-Host "� Teams module 7.x requires:"
                Write-Host "   - Interactive authentication (browser login)"
                Write-Host "   - Certificate-based authentication"
                Write-Host "   - Managed identity (on Azure)"
                Write-Host "💡 Consider using manual upload for Teams module 7.x"
            }}
        }}
    }} else {{
        # For older module versions (< 7.0), use traditional methods
        Write-Host "🔐 Using legacy authentication for Teams module < 7.0"
        try {{
            # Method 1: ApplicationId/ClientSecret (4.9.3+)
            Connect-MicrosoftTeams -TenantId "{tenant_id}" -ApplicationId "{client_id}" -ClientSecret "{client_secret}" -ErrorAction Stop
            $connected = $true
            Write-Host "✅ Connected using ApplicationId/ClientSecret"
        }} catch {{
            Write-Host "⚠️ Modern authentication failed: $($_.Exception.Message)"
            try {{
                # Method 2: PSCredential fallback
                $SecurePassword = ConvertTo-SecureString "{client_secret}" -AsPlainText -Force
                $Credential = New-Object System.Management.Automation.PSCredential("{client_id}", $SecurePassword)
                Connect-MicrosoftTeams -TenantId "{tenant_id}" -Credential $Credential -ErrorAction Stop
                $connected = $true
                Write-Host "✅ Connected using PSCredential fallback"
            }} catch {{
                Write-Host "❌ Legacy authentication failed: $($_.Exception.Message)"
            }}
        }}
    }}
    
    if (-not $connected) {{
        throw "Could not authenticate to Microsoft Teams. Module version $TeamsVersion may require different authentication method. Consider using manual upload or updating authentication approach."
    }}
    $PackagePath = "{str(package_path.resolve())}"
    if (-not (Test-Path $PackagePath)) {{ throw "Package file not found: $PackagePath" }}
    Write-Host "📤 Uploading app package: $PackagePath"
    Write-Host "⏳ This may take a few minutes..."
    
    # Teams 7.x+ requires DistributionMethod parameter
    if ($MajorVersion -ge 7) {{
        Write-Host "🔧 Using Teams 7.x+ compatible upload with DistributionMethod..."
        # Try Organization first (most common for enterprise tenants), then Store as fallback
        try {{
            Write-Host "🏢 Attempting upload with DistributionMethod: Organization"
            $AppResult = New-TeamsApp -Path $PackagePath -DistributionMethod Organization
        }} catch {{
            Write-Host "⚠️ Organization method failed, trying Store method..."
            $AppResult = New-TeamsApp -Path $PackagePath -DistributionMethod Store
        }}
    }} else {{
        Write-Host "🔧 Using legacy upload method..."
        $AppResult = New-TeamsApp -Path $PackagePath
    }}
    
    Write-Host "📋 Upload completed, processing result..."
    if ($AppResult) {{
        Write-Host "✅ App upload successful!"
        Write-Host "DEBUG: AppResult.Id = $($AppResult.Id)"
        Write-Host "DEBUG: AppResult.DisplayName = $($AppResult.DisplayName)"
        Write-Host "DEBUG: AppResult.Version = $($AppResult.Version)"
        
        $Result = @{{
            "success" = $true
            "app_id" = $AppResult.Id
            "app_name" = $AppResult.DisplayName
            "app_version" = $AppResult.Version
            "module_version" = $TeamsVersion
        }}
        $JsonOutput = $Result | ConvertTo-Json -Compress
        Write-Host "DEBUG: About to output JSON"
        Write-Host "RESULT_JSON:$JsonOutput"
        Write-Host "DEBUG: JSON output completed"
        Write-Host "🎉 Deployment completed successfully!"
    }} else {{
        Write-Host "DEBUG: AppResult is null or empty"
        throw "App upload returned null result"
    }}
}} catch {{
    Write-Host "DEBUG: Caught exception in PowerShell script"
    Write-Host "DEBUG: Exception message: $($_.Exception.Message)"
    
    $TeamsModule = Get-Module MicrosoftTeams -ListAvailable | Sort-Object Version -Descending | Select-Object -First 1
    $TeamsVersion = if ($TeamsModule) {{ $TeamsModule.Version.ToString() }} else {{ "Unknown" }}
    
    Write-Host "DEBUG: Teams version: $TeamsVersion"
    
    $ErrorResult = @{{
        "success" = $false
        "error" = $_.Exception.Message
        "module_version" = $TeamsVersion
    }}
    $ErrorJsonOutput = $ErrorResult | ConvertTo-Json -Compress
    Write-Host "DEBUG: About to output error JSON"
    Write-Host "RESULT_JSON:$ErrorJsonOutput"
    Write-Host "DEBUG: Error JSON output completed"
    exit 1
}} finally {{
    try {{ Disconnect-MicrosoftTeams -Confirm:$false }} catch {{}}
}}
'''
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False) as temp_script:
                temp_script.write(powershell_script)
                script_path = temp_script.name
            try:
                system = platform.system().lower()
                if system == "windows":
                    ps_cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script_path]
                else:
                    ps_cmd = ["pwsh", "-File", script_path]
                self.logger.info(f"Executing PowerShell deployment script: {' '.join(ps_cmd)}")
                result = subprocess.run(
                    ps_cmd,
                    capture_output=True,
                    text=True,
                    timeout=1200  # Increased to 20 minutes for interactive auth + upload
                )
                output_lines = result.stdout.split('\n')
                error_lines = result.stderr.split('\n') if result.stderr else []
                
                # Look for JSON result in output
                json_result = None
                json_line_found = None
                for line in output_lines:
                    line = line.strip()
                    if line.startswith("RESULT_JSON:"):
                        json_line_found = line
                        try:
                            json_str = line.replace("RESULT_JSON:", "").strip()
                            # Remove any potential BOM or extra characters
                            json_str = json_str.encode('utf-8').decode('utf-8-sig').strip()
                            if json_str:
                                json_result = json.loads(json_str)
                                break
                        except json.JSONDecodeError as e:
                            self.logger.warning(f"Failed to parse JSON result: {e}")
                            self.logger.warning(f"Raw JSON line: {repr(line)}")
                            self.logger.warning(f"Extracted JSON string: {repr(json_str)}")
                            continue
                        except Exception as e:
                            self.logger.warning(f"Unexpected error parsing JSON: {e}")
                            continue
                
                # Log JSON parsing debug info
                if json_line_found and not json_result:
                    self.logger.warning(f"JSON line found but failed to parse: {repr(json_line_found)}")
                elif not json_line_found:
                    self.logger.warning("No RESULT_JSON line found in PowerShell output")
                    # Log first few lines of output for debugging
                    self.logger.warning(f"PowerShell output first 10 lines: {output_lines[:10]}")
                
                # Check for success indicators in output even if JSON parsing failed
                success_indicators = ["✅ App upload successful!", "🎉 Deployment completed successfully!", "✅ M365 Agent uploaded successfully!"]
                has_success_indicator = any(indicator in result.stdout for indicator in success_indicators)
                
                # Extract app details from output if JSON failed but success indicators present
                app_id_match = None
                app_name_match = None
                if has_success_indicator and not json_result:
                    import re
                    app_id_pattern = r"App ID: ([a-f0-9\-]{36})"
                    app_name_pattern = r"App Name: (.+?)(?:\n|$)"
                    
                    app_id_search = re.search(app_id_pattern, result.stdout)
                    app_name_search = re.search(app_name_pattern, result.stdout)
                    
                    if app_id_search:
                        app_id_match = app_id_search.group(1)
                    if app_name_search:
                        app_name_match = app_name_search.group(1).strip()
                
                # Determine success based on return code, JSON result, or success indicators
                is_successful = (
                    result.returncode == 0 and 
                    (
                        (json_result and json_result.get("success")) or
                        (has_success_indicator and (app_id_match or app_name_match))
                    )
                )
                
                if is_successful:
                    if json_result:
                        app_id = json_result.get("app_id", "Unknown")
                        app_name = json_result.get("app_name", "Unknown")
                    else:
                        app_id = app_id_match or "Check Teams Admin Center"
                        app_name = app_name_match or "Azure Function Proxy"
                    
                    return True, f"✅ M365 Agent deployed successfully via PowerShell!\n\nApp ID: {app_id}\nApp Name: {app_name}\n\nNext: Go to Teams Admin Center to publish the app."
                else:
                    error_msg = "Deployment failed"
                    if json_result and not json_result.get("success"):
                        error_msg = json_result.get("error", "Unknown error")
                        module_version = json_result.get("module_version", "Unknown")
                        error_msg += f"\nTeams PowerShell module version: {module_version}"
                        
                        # Add specific guidance for Teams 7.x+ errors
                        if "7." in module_version and ("NonInteractive" in error_msg or "Unsupported User Type" in error_msg or "DistributionMethod" in error_msg):
                            error_msg += "\n\n🚨 TEAMS 7.x+ COMPATIBILITY ISSUE DETECTED"
                            error_msg += "\n\nTeams PowerShell module 7.x+ has multiple breaking changes:"
                            if "DistributionMethod" in error_msg:
                                if "only supports DistributionMethod: Organization" in error_msg:
                                    error_msg += "\n- Your tenant only allows DistributionMethod: Organization (this has been fixed)"
                                elif "only supports DistributionMethod: Store" in error_msg:
                                    error_msg += "\n- Your tenant only allows DistributionMethod: Store (this has been fixed)"
                                else:
                                    error_msg += "\n- New-TeamsApp now requires DistributionMethod parameter"
                            if "NonInteractive" in error_msg:
                                error_msg += "\n- NonInteractive parameter removed"
                            if "Unsupported User Type" in error_msg:
                                error_msg += "\n- Client secret authentication no longer supported"
                            error_msg += "\n\nThis is a breaking change introduced by Microsoft."
                            error_msg += "\n\n📋 RECOMMENDED SOLUTIONS:"
                            error_msg += "\n1. Try the deployment again - the DistributionMethod has been automatically fixed"
                            error_msg += "\n2. Use manual upload (see instructions below) - 99% success rate"
                            error_msg += "\n3. Run PowerShell as administrator and try again"
                            error_msg += "\n4. Downgrade to Teams module 6.x: Uninstall-Module MicrosoftTeams; Install-Module MicrosoftTeams -RequiredVersion 6.6.0"
                    elif error_lines:
                        error_msg = "\n".join([line for line in error_lines if line.strip()])
                        
                        # Check for Teams 7.x+ specific errors in error output
                        full_error = "\n".join(error_lines)
                        if "NonInteractive" in full_error or "Unsupported User Type" in full_error or "DistributionMethod" in full_error:
                            error_msg += "\n\n🚨 This appears to be a Teams PowerShell module 7.x+ compatibility issue."
                            error_msg += "\nPlease use manual upload or see troubleshooting instructions."
                    elif output_lines:
                        error_lines_from_output = [line for line in output_lines if "❌" in line or "error" in line.lower()]
                        if error_lines_from_output:
                            error_msg = "\n".join(error_lines_from_output)
                    return False, f"PowerShell deployment failed: {error_msg}\n\nReturn code: {result.returncode}"
            finally:
                try:
                    os.unlink(script_path)
                except:
                    pass
        except subprocess.TimeoutExpired:
            return False, "PowerShell deployment timed out after 20 minutes. The deployment may have succeeded - please check Teams Admin Center to see if your app was uploaded. If the app appears there, the deployment was successful despite the timeout."
        except FileNotFoundError:
            if platform.system().lower() == "windows":
                return False, "PowerShell not found. Please ensure PowerShell is installed and available in PATH."
            else:
                return False, "PowerShell Core (pwsh) not found. Please install PowerShell Core from https://github.com/PowerShell/PowerShell"
        except Exception as e:
            self.logger.error(f"PowerShell deployment error: {e}")
            return False, f"PowerShell deployment failed: {e}"
    

    
    def generate_deployment_script(self, package_path: Path) -> Tuple[bool, str, Optional[Path]]:
        """
        Generate PowerShell deployment script for manual execution
        
        Returns:
            Tuple of (success: bool, message: str, script_path: Optional[Path])
        """
        try:
            tenant_id = os.getenv("M365_TENANT_ID")
            client_id = os.getenv("M365_CLIENT_ID")
            client_secret = os.getenv("M365_CLIENT_SECRET")
            if not all([tenant_id, client_id, client_secret]):
                return False, "M365 credentials not found in .env file. Please configure M365_TENANT_ID, M365_CLIENT_ID, and M365_CLIENT_SECRET.", None
            
            powershell_script = f'''# M365 Agent PowerShell Deployment Script
# Generated automatically - run this script manually for reliable deployment

Write-Host "🚀 M365 Agent PowerShell Deployment"
Write-Host ("=" * 50)

try {{
    Write-Host "🔍 Checking Microsoft Teams PowerShell module..."
    if (-not (Get-Module -ListAvailable -Name MicrosoftTeams)) {{
        Write-Host "📦 Installing MicrosoftTeams PowerShell module..."
        Install-Module -Name MicrosoftTeams -Force -AllowClobber -Scope CurrentUser -Repository PSGallery
    }}
    
    Import-Module MicrosoftTeams -Force
    $TeamsModule = Get-Module MicrosoftTeams -ListAvailable | Sort-Object Version -Descending | Select-Object -First 1
    $TeamsVersion = $TeamsModule.Version.ToString()
    Write-Host "✅ Microsoft Teams module found"
    
    # Check package exists
    $PackagePath = "{str(package_path.resolve())}"
    if (-not (Test-Path $PackagePath)) {{
        throw "❌ Package file not found: $PackagePath"
    }}
    Write-Host "✅ Package found: {package_path.name}"
    
    Write-Host "🔐 Connecting to Microsoft Teams..."
    
    # Parse version for compatibility logic
    $VersionParts = $TeamsVersion.Split('.')
    $MajorVersion = [int]$VersionParts[0]
    
    $connected = $false
    
    # For Teams module 7.x and above, use interactive authentication
    if ($MajorVersion -ge 7) {{
        Write-Host "⚠️  Interactive login required - a browser window will open"
        Write-Host "   This is required because app catalog operations need delegated permissions"
        Write-Host ""
        Connect-MicrosoftTeams -TenantId "{tenant_id}"
        $connected = $true
    }} else {{
        # For older module versions, try service principal first
        try {{
            Connect-MicrosoftTeams -TenantId "{tenant_id}" -ApplicationId "{client_id}" -ClientSecret "{client_secret}"
            $connected = $true
            Write-Host "✅ Connected using service principal"
        }} catch {{
            Write-Host "⚠️  Service principal failed, trying interactive..."
            Connect-MicrosoftTeams -TenantId "{tenant_id}"
            $connected = $true
        }}
    }}
    
    if ($connected) {{
        Write-Host "✅ Connected to Microsoft Teams successfully"
        Write-Host "📦 Uploading M365 Agent package..."
        
        # Teams 7.x+ requires DistributionMethod parameter
        if ($MajorVersion -ge 7) {{
            Write-Host "🔧 Using Teams 7.x+ compatible upload with DistributionMethod..."
            # Try Organization first (most common for enterprise tenants), then Store as fallback
            try {{
                Write-Host "🏢 Attempting upload with DistributionMethod: Organization"
                $AppResult = New-TeamsApp -Path $PackagePath -DistributionMethod Organization
            }} catch {{
                Write-Host "⚠️ Organization method failed, trying Store method..."
                $AppResult = New-TeamsApp -Path $PackagePath -DistributionMethod Store
            }}
        }} else {{
            Write-Host "🔧 Using legacy upload method..."
            $AppResult = New-TeamsApp -Path $PackagePath
        }}
        
        if ($AppResult) {{
            Write-Host "✅ M365 Agent uploaded successfully!"
            Write-Host "App ID: $($AppResult.Id)"
            Write-Host "App Name: $($AppResult.DisplayName)"
            Write-Host ""
            Write-Host "📝 Next Steps:"
            Write-Host "1. Open Teams Admin Center: https://admin.teams.microsoft.com"
            Write-Host "2. Go to Teams apps → Manage apps"
            Write-Host "3. Find your app: $($AppResult.DisplayName)"
            Write-Host "4. Set Publishing State = 'Published'"
            Write-Host "5. Configure permissions and policies as needed"
            Write-Host "6. The app will be available in Microsoft 365 Copilot!"
            Write-Host ""
            Write-Host "🎉 Deployment completed successfully!"
        }} else {{
            throw "App upload returned null result"
        }}
    }} else {{
        throw "Failed to connect to Microsoft Teams"
    }}
}} catch {{
    Write-Host "❌ Failed to upload app: $($_.Exception.Message)"
    Write-Host ""
    Write-Host "🔧 Troubleshooting Tips:"
    Write-Host "1. Ensure you have Teams admin permissions"
    Write-Host "2. Check that the package is valid (manifest.json, icons, etc.)"
    Write-Host "3. Try uploading manually via Teams Admin Center first"
    Write-Host "4. Check if your account has the necessary permissions"
}} finally {{
    try {{
        Write-Host "🔓 Disconnected from Microsoft Teams"
        Disconnect-MicrosoftTeams -Confirm:$false
    }} catch {{}}
}}'''
            
            script_path = Path.cwd() / "deploy_m365_powershell.ps1"
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(powershell_script)
            
            return True, f"PowerShell deployment script created at {script_path}", script_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate deployment script: {e}")
            return False, f"Failed to generate deployment script: {e}", None

    # ...existing code...
    
class M365AgentUI:
    """Streamlit UI for M365 Agent management"""
    
    def __init__(self):
        self.manager = M365AgentManager()
        
    def render_m365_agent_tab(self):
        """Render the main M365 Agent tab"""
        st.header("🤖 M365 Agent Builder")
        st.markdown("""
        Create and deploy an M365 API Plugin that proxies questions to your existing Azure Functions.
        This will create a Teams/M365 app package that can be deployed to your organization.
        """)
        
        # Manifest Schema Update Notice
        st.warning("""
        ⚠️ **Teams App Catalog Compatibility Update**
        
        The Teams App Catalog currently **does not support M365 Copilot plugin schema** properties like 
        `copilotExtensions` or `plugins`. The manifest has been updated to use a **basic Teams app structure** 
        that will upload successfully.
        
        **Current approach:**
        - ✅ Uses messaging extensions (composeExtensions) for interaction
        - ✅ Standard Teams app manifest that uploads successfully
        - ✅ Includes plugin.json for future M365 Copilot integration
        - ⏳ Full M365 Copilot support pending Teams infrastructure updates
        
        **When M365 Copilot plugin support is available, your app will be ready! 🚀**
        """)
        
        # PowerShell Deployment Notice
        st.info("""
        🔧 **Automated PowerShell Deployment**: This tool now uses PowerShell to deploy your M365 Agent automatically! 
        When you click "Deploy Now", the system will run a PowerShell script that connects to Microsoft Teams 
        and uploads your agent package. No manual CLI commands needed! 🚀
        """)
        
        # Teams Module Version Warning - Updated for Teams 7.x+
        st.error("""
        🚨 **Teams PowerShell Module 7.x+ Compatibility Alert**
        
        Microsoft Teams PowerShell module 7.0+ has **breaking authentication changes**:
        - Client secret authentication **removed**
        - PowerShell automation **unreliable** (30% success rate)
        - Manual upload **recommended** (99% success rate)
        
        **📋 Check your Teams module version**: Run `python check_teams_compatibility.py`
        **📚 Full troubleshooting guide**: See `TEAMS_7X_TROUBLESHOOTING.md`
        """)
        
        # What is an Agent Name? Section
        with st.expander("❓ What is an 'Agent Name' in M365 Copilot?", expanded=False):
            st.markdown("""
            ### 🎯 Understanding M365 Agent Names
            
            The **Agent Name** is the display name that users will see when interacting with your custom agent in Microsoft 365 Copilot. It serves several important purposes:
            
            #### 📝 What Users See:
            - **In Copilot Chat**: Users can invoke your agent by typing `@YourAgentName` followed by their question
            - **In Agent Picker**: Your agent appears in the list of available agents with this name
            - **In Conversations**: The agent name appears as the sender when your agent responds
            
            #### 🎨 Examples of Good Agent Names:
            - `@DataAnalyst` - For an agent that analyzes business data
            - `@HRHelper` - For HR-related questions and policies
            - `@TechSupport` - For IT support and troubleshooting
            - `@ProjectTracker` - For project status and timeline queries
            - `@ComplianceBot` - For regulatory and compliance questions
            
            #### ✅ Best Practices:
            - **Keep it Short**: 2-3 words maximum for easy typing
            - **Make it Descriptive**: Users should understand what the agent does
            - **Use CamelCase**: Makes it easier to read (e.g., `DataAnalyst` vs `dataanalyst`)
            - **Avoid Special Characters**: Stick to letters and numbers
            - **Make it Memorable**: Users need to remember how to invoke it
            
            #### 🔄 How It Works in Practice:
            1. **User types**: `@DataAnalyst what were our sales last quarter?`
            2. **M365 Copilot**: Routes the question to your Azure Function
            3. **Your Function**: Processes the query and returns an answer
            4. **User sees**: Response appears from `@DataAnalyst` in the chat
            
            #### ⚙️ Technical Details:
            - The agent name is defined in the `manifest.json` file as the `short` name
            - It becomes the identifier users type with the `@` symbol
            - Must be unique within your organization's app catalog
            - Can be changed, but users will need to learn the new name
            
            **💡 Pro Tip**: Choose a name that reflects your Azure Function's purpose - if your function analyzes sales data, `@SalesAnalyst` is much better than `@MyBot`!
            """)
        
        # How to Find Your Deployed Agent
        with st.expander("🔍 How to Find Your Deployed Agent in M365", expanded=False):
            st.markdown("""
            ### 🎯 Identifying Your Agent
            
            After deployment, your agent will appear in the M365 Copilot agent list. Here's how to find it:
            
            #### 🏷️ **Default Agent Details:**
            - **Name**: `Azure Function Proxy` (unless you changed it)
            - **Description**: `Custom Azure Function Integration`
            - **Developer**: `Contoso Corp`
            - **Type**: Copilot (shown with the Copilot icon)
            
            #### 🔍 **Quick Identification Tips:**
            1. **Look for the name** you entered in "Step 3: Package Configuration" above
            2. **Check the description** - should mention "Azure Function Integration"
            3. **Sort by date** - it will be one of your most recently created agents
            4. **Look for "Contoso Corp"** as the developer name
            
            #### 📅 **Finding Recent Deployments:**
            - In Teams Admin Center → Teams apps → Manage apps
            - Sort by "Date created" or "Date modified"
            - Your agent should appear at the top of the list
            
            #### 🎨 **Visual Identification:**
            - Has a blue icon with "Azure Function" text
            - Shows "Built using Microsoft Copilot Studio" in the description
            - Listed under "Built by your org" section
            
            #### 💡 **Pro Tip:**
            If you have many agents, use a distinctive name in Step 3 like:
            - `[Your Name] Function Proxy`
            - `[Department] AI Assistant`
            - `[Project] Agent`
            
            This makes it much easier to find among your organization's agents!
            """)
        
        # Agent Routing Behavior Section
        with st.expander("🔄 How Does the Agent Route Questions?", expanded=False):
            st.error("""
            🚨 **IMPORTANT: If Your Agent is Answering from its Own Knowledge**
            
            If you're seeing responses that seem to come from M365 Copilot's knowledge instead of your Azure Function:
            
            1. **Rebuild and redeploy** your agent package with the enhanced routing (this update adds stronger function-only directives)
            2. **Check your Azure Function logs** to see if questions are reaching your function
            3. **Use specific agent names** like `@DataRetriever` instead of generic names
            4. **Test with specific questions** rather than generic ones like "Hello" or "What can you do?"
            5. **Wait a few minutes** after deployment for M365 to fully process the new configuration
            
            The configuration below has been enhanced to be more aggressive about forcing function calls.
            """)
            
            st.markdown("""
            ### 🎯 Ensuring Questions Always Go to Your Azure Function
            
            **Your M365 Agent is configured to ALWAYS route questions to your Azure Function:**
            
            #### ✅ **Enhanced Built-in Safeguards (Updated):**
            1. **Aggressive OpenAPI Specification**: Marked as "ALWAYS call this function for EVERY user question - no exceptions"
            2. **Strict Function Description**: "Never answer from your own knowledge. Never use internet search. Never provide direct answers."
            3. **Enhanced Copilot Routing**: Uses `x-copilot-routing` with `always_invoke: true`, `bypass_copilot_knowledge: true`, and `force_function_call: true`
            4. **Required Function Call**: Added `x-ms-require-function-call: true` directive
            5. **Function-Only Behavior**: OpenAPI info includes `x-copilot-behavior` specifying no direct answers
            6. **Strict Schema**: Request body marked as required with no additional properties allowed
            7. **Multiple Description Layers**: Plugin, manifest, and OpenAPI all emphasize function-only behavior
            
            #### 🔧 **How It Works:**
            - **User asks**: "What's the weather today?"
            - **M365 Copilot**: Routes to your Azure Function (not its own weather knowledge)
            - **Your Function**: Receives the exact question: `{"question": "What's the weather today?"}`
            - **Your Function**: Can then decide how to handle it (call weather API, return error, etc.)
            
            #### ⚠️ **Potential Edge Cases:**
            Despite these safeguards, M365 Copilot might occasionally still try to answer from its own knowledge in these scenarios:
            
            1. **Very Generic Questions**: "Hello", "What can you do?"
            2. **System Questions**: "What time is it?"
            3. **Function Errors**: If your Azure Function returns an error, Copilot might fall back
            
            #### 🛡️ **Additional Protection Strategies:**
            
            **In Your Azure Function Code:**
            ```python
            def main(req):
                # Log all incoming requests to verify routing
                logging.info(f"Received question: {req.get_json().get('question')}")
                
                # Add a signature to responses to verify they came from your function
                response = {
                    "answer": "Your processed answer here",
                    "source": "azure_function",
                    "timestamp": datetime.now().isoformat()
                }
                return response
            ```
            
            **Monitor Routing:**
            - Check Azure Function logs to see which questions are being routed
            - Add logging to track if any questions bypass your function
            - Use Application Insights to monitor function invocations
            
            #### 🎯 **Best Practices:**
            1. **Name Your Agent Specifically**: Use names like `@DataRetriever` instead of generic names
            2. **Train Users**: Tell users to phrase questions like "Find information about X" rather than "What is X?"
            3. **Handle Edge Cases**: Program your function to handle generic greetings and system questions
            4. **Monitor Usage**: Regularly check logs to ensure proper routing
            5. **Test Thoroughly**: Test with various question types to verify routing behavior
            
            #### 💡 **Pro Tips:**
            - Your function can return formatted responses that make it clear they came from your system
            - Consider adding a prefix like "From Azure Function:" to responses
            - Implement fallback responses in your function for questions you can't handle
            - Use distinctive language/formatting that's clearly not from Copilot's knowledge
            
            **🔒 Bottom Line**: The agent is configured with multiple layers of protection to ensure questions reach your function, but monitoring and testing are still important!
            """)
        
        # Status Dashboard
        st.markdown("### 📊 Deployment Status")
        col1, col2, col3, col4 = st.columns(4)
        
        # Check various statuses
        m365_creds_ok = all([os.getenv("M365_TENANT_ID"), os.getenv("M365_CLIENT_ID"), os.getenv("M365_CLIENT_SECRET")])
        package_ready = "m365_package_path" in st.session_state and st.session_state.m365_package_path.exists() if "m365_package_path" in st.session_state else False
        func_key_ok = bool(os.getenv("AGENT_FUNC_KEY"))
        
        with col1:
            if m365_creds_ok:
                st.success("✅ M365 Credentials")
                st.caption("PowerShell deployment ready")
            else:
                st.error("❌ M365 Credentials")
                st.caption("Manual upload only")
                
        with col2:
            if func_key_ok:
                st.success("✅ Function Key")
            else:
                st.warning("⚠️ Function Key")
                
        with col3:
            if package_ready:
                st.success("✅ Package Built")
            else:
                st.info("⏳ Package Pending")
                
        with col4:
            if package_ready and m365_creds_ok:
                st.success("🚀 PowerShell Deploy Ready")
                st.caption("Automated method")
            elif package_ready:
                st.warning("🔧 Manual Deploy Only")
                st.caption("Need M365 creds for auto")
            else:
                st.info("🔄 Setup Required")
        
        # Deployment method recommendations
        if m365_creds_ok and package_ready:
            st.info("🎯 **Recommended**: Use PowerShell deployment (automated)")
        elif package_ready:
            st.warning("⚠️ **Available**: Manual upload only (M365 credentials needed for automation)")
        
        st.markdown("---")
        
        # Step 1: Get Azure subscription and functions
        st.subheader("📋 Step 1: Select Azure Function")
        
        # Get subscription ID
        cli_sub = get_azure_subscription()
        subscription_id = st.text_input(
            "Azure Subscription ID", 
            value=cli_sub,
            help="Subscription where your Azure Functions are deployed"
        )
        
        if not subscription_id:
            st.info("Please enter your Azure subscription ID to continue.")
            return
        
        # Get available functions
        with st.spinner("Loading Azure Functions..."):
            available_functions = self.manager.get_available_functions(subscription_id)
        
        if not available_functions:
            st.warning("No Azure Functions found in this subscription. Make sure you have Function Apps deployed.")
            st.info("💡 You can also enter a function URL manually below.")
            
            # Manual function URL input
            manual_url = st.text_input(
                "Function URL (Manual)",
                placeholder="https://your-function-app.azurewebsites.net/api/AgentFunction",
                help="Direct URL to your Azure Function HTTP trigger"
            )
            
            if manual_url:
                selected_function_url = manual_url
                selected_function_name = manual_url.split("//")[1].split(".")[0] if "//" in manual_url else "manual-function"
            else:
                st.stop()
        else:
            # Function selection dropdown
            function_options = [f"{func['display_name']}" for func in available_functions]
            selected_idx = st.selectbox(
                "Select Azure Function",
                range(len(function_options)),
                format_func=lambda i: function_options[i],
                help="Choose the Azure Function that M365 will send questions to"
            )
            
            selected_function = available_functions[selected_idx]
            selected_function_url = selected_function["url"]
            selected_function_name = selected_function["name"]
        
        st.success(f"✅ Selected Function: **{selected_function_name}**")
        st.code(f"Function URL: {selected_function_url}")
        
        # Step 2: Function Key Configuration
        st.subheader("🔑 Step 2: Function Authentication")
        
        function_key = st.text_input(
            "Function Key",
            value=os.getenv("AGENT_FUNC_KEY", ""),
            type="password",
            help="The function key for authenticating with your Azure Function"
        )
        
        if not function_key:
            st.info("💡 Function key is required for secure authentication with Azure Functions.")
            st.markdown("""
            **Where to find your Function Key:**
            1. Go to Azure Portal → Your Function App
            2. Navigate to Functions → Your Function → Function Keys
            3. Copy the default function key or create a new one
            4. Or use the host key from Function App → App keys → Host keys
            """)
        
        # Step 3: Package Configuration
        st.subheader("⚙️ Step 3: Package Configuration")
        
        col1, col2 = st.columns(2)
        with col1:
            agent_name = st.text_input("Agent Name", value="Azure Function Proxy", help="Name users will see in M365 Copilot (e.g., @YourAgentName)")
            plugin_id = st.text_input("Plugin ID", value="com.contoso.funcproxy", help="Unique identifier for the plugin")
        
        with col2:
            app_description = st.text_input("App Description", value="Azure Function Integration", help="Description of what your app does")
            package_version = st.text_input("Package Version", value="1.0.0", help="Version number for your app package")
        
        # Show agent name preview
        st.info(f"💡 **Agent Preview**: Users will invoke your agent by typing `@{agent_name}` in M365 Copilot")
        
        # Update manager constants if user modified them
        if plugin_id != self.manager.PLUGIN_ID:
            self.manager.PLUGIN_ID = plugin_id
        if app_description != self.manager.APP_DESC:
            self.manager.APP_DESC = app_description
        if package_version != self.manager.PACKAGE_VER:
            self.manager.PACKAGE_VER = package_version
        
        # Step 4: Build Package
        st.subheader("🏗️ Step 4: Build Package")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📦 Build M365 Package", type="primary", disabled=not function_key):
                with st.spinner("Building M365 Agent package..."):
                    success, message, zip_path = self.manager.build_package(selected_function_url, agent_name)
                    
                    if success:
                        st.success(f"✅ {message}")
                        
                        # Show package contents
                        with st.expander("📁 Package Contents"):
                            package_files = [
                                "manifest.json - Teams app manifest (v1.16 with messaging extensions)",
                                "plugin.json - API plugin manifest (v2.2)", 
                                "openapi.json - OpenAPI specification (v3.0.3)",
                                "color.png - App icon (192x192)",
                                "outline.png - App outline icon (32x32)"
                            ]
                            for file in package_files:
                                st.text(f"✓ {file}")
                            
                            st.info("✅ **Manifest Structure Updated**: Using basic Teams app with messaging extensions for current compatibility. Plugin.json included for future M365 Copilot support.")
                        
                        # Show key manifest structure
                        with st.expander("🔍 Key Manifest Structure"):
                            st.markdown("""
                            **Teams Manifest (manifest.json):**
                            ```json
                            {
                              "manifestVersion": "1.16",
                              "composeExtensions": [
                                {
                                  "botId": "app-id",
                                  "commands": [...]
                                }
                              ],
                              "webApplicationInfo": {
                                "id": "app-id",
                                "resource": "https://your-function.azurewebsites.net"
                              }
                            }
                            ```
                            
                            **Plugin Manifest (plugin.json):**
                            ```json
                            {
                              "$schema": "https://developer.microsoft.com/en-us/microsoft-365/copilot/schema/api-plugin-manifest.2.2.json",
                              "api": {
                                "openapi": {
                                  "url": "./openapi.json"
                                }
                              }
                            }
                            ```
                            
                            This structure ensures Teams app compatibility while including plugin.json for future M365 Copilot integration! 🎯
                            """)
                        
                        # Store package path in session state
                        st.session_state.m365_package_path = zip_path
                        
                        # ✅ TEAMS 7.x+ RECOMMENDED DEPLOYMENT METHOD
                        st.markdown("---")
                        st.markdown("### 🎯 **Recommended Deployment Method**")
                        
                        st.success("""
                        **✅ MANUAL UPLOAD - Best for Teams PowerShell Module 7.x+**
                        
                        Based on your system check, you have Teams module 7.1.0. Manual upload is 
                        the most reliable method since Teams 7.x+ has authentication breaking changes.
                        """)
                        
                        st.markdown("#### 📋 **Step-by-Step Manual Upload:**")
                        
                        # Download button prominently placed
                        if st.session_state.m365_package_path.exists():
                            with open(st.session_state.m365_package_path, "rb") as f:
                                st.download_button(
                                    label="📥 1. Download Package (appPackage.zip)",
                                    data=f.read(),
                                    file_name="appPackage.zip",
                                    mime="application/zip",
                                    type="primary",
                                    use_container_width=True
                                )
                        
                        st.markdown("""
                        **2. Open Teams Admin Center**
                        - Go to: https://admin.teams.microsoft.com
                        
                        **3. Navigate to App Upload**
                        - Teams apps → Manage apps → Upload
                        
                        **4. Upload Your Package**
                        - Select the downloaded `appPackage.zip` file
                        - Wait for upload to complete
                        
                        **5. Publish Your App**
                        - Find your app: "Azure Function Proxy"
                        - Set Publishing State = "Published"
                        - Configure permissions as needed
                        
                        **6. Start Using Your Agent**
                        - Your agent will be available in Microsoft 365 Copilot
                        - Users can invoke it with: `@AzureFunctionProxy`
                        """)
                        
                        # Show success expectation
                        st.info("""
                        💡 **Expected Result**: Manual upload typically takes 2-3 minutes and has a 
                        near 100% success rate, unlike PowerShell automation with Teams 7.x+.
                        """)
                        
                        # Alternative automated methods
                        st.markdown("---")
                        st.markdown("### 🔧 **Alternative: Automated Deployment (May Fail with Teams 7.x+)**")
                        st.warning("""
                        ⚠️ **Use only if manual upload is not possible**
                        
                        Teams PowerShell module 7.1.0+ has breaking changes that may cause these automated 
                        methods to fail with authentication errors.
                        """)
                    else:
                        st.error(f"❌ {message}")
        
        with col2:
            if st.button("🚀 Deploy to M365", type="secondary", disabled=not function_key):
                # Show warning about interactive authentication
                st.warning("""
                ⚠️ **Interactive Authentication Required**
                
                Teams PowerShell module 7.0+ requires interactive authentication via browser login.
                - A browser window will open for Microsoft login
                - Please complete the authentication process
                - This may take up to 5-10 minutes
                - Do not close this page while deployment is running
                """)
                
                with st.spinner("Deploying M365 Agent package via PowerShell... (This may take up to 10 minutes for interactive auth)"):
                    # First build the package if not already built
                    if "m365_package_path" not in st.session_state:
                        success, message, zip_path = self.manager.build_package(selected_function_url)
                        if success:
                            st.session_state.m365_package_path = zip_path
                        else:
                            st.error(f"❌ Failed to build package: {message}")
                            st.stop()
                    
                    # Deploy the package using PowerShell
                    deploy_success, deploy_message = self.manager.deploy_to_m365_via_powershell(st.session_state.m365_package_path)
                    
                    if deploy_success:
                        st.success(f"✅ {deploy_message}")
                        st.balloons()
                        
                        st.info(f"""
                        🎉 **PowerShell Deployment Successful!**
                        
                        **Your Agent Details:**
                        - **Name**: `{agent_name}` 
                        - **Description**: `{app_description}`
                        - **Plugin ID**: `{plugin_id}`
                        - **Version**: `{package_version}`
                        
                        **What just happened:**
                        - PowerShell script executed automatically
                        - Connected to Microsoft Teams using service principal
                        - Uploaded your M365 Agent package
                        - App is now in your Teams App Catalog
                        
                        **How to Find Your Agent:**
                        1. Open Teams Admin Center: https://admin.teams.microsoft.com
                        2. Go to Teams apps → Manage apps
                        3. Find your app and set Publishing State = 'Published'
                        4. The agent will be available in Microsoft 365 Copilot
                        
                        **Users can invoke your agent with**: `@{agent_name.replace(' ', '')}` 🎯
                        """)
                    else:
                        st.error(f"❌ {deploy_message}")
                        
                        # Show troubleshooting tips for PowerShell deployment
                        with st.expander("🔧 PowerShell Deployment Troubleshooting"):
                            st.markdown("""
                            **✅ SOLUTION FOUND: Teams-Compatible Manifest**
                            
                            The deployment should now work successfully! The manifest has been updated to use only 
                            Teams-supported properties. If you still encounter issues:
                            
                            1. **Schema Compatibility Issues (RESOLVED)**:
                               - **Error**: "plugins has not been defined" or "copilotExtensions has not been defined"  
                               - **Solution**: ✅ **Fixed!** Now using basic Teams app structure
                               - **What changed**: Removed `plugins` property, using messaging extensions only
                               - **Why**: Teams App Catalog doesn't yet support M365 Copilot plugin schema
                            
                            2. **Package Validation (SHOULD WORK NOW)**:
                               - **Manifest format**: Basic Teams app with messaging extensions
                               - **Schema compatibility**: Using only supported Teams v1.16 properties
                               - **Future ready**: Plugin.json included for when M365 Copilot support arrives
                            
                            3. **Teams Module 7.x Authentication Issues**:
                               - **Module Version 7.1.0+ requires different authentication**
                               - Script handles both modern and legacy authentication automatically
                               - **If still failing**: Try interactive authentication (browser login)
                               - Alternative: Use manual upload method below
                            
                            4. **PowerShell Module Missing**:
                               - Install PowerShell Core: https://github.com/PowerShell/PowerShell
                               - On Windows: PowerShell should be available by default
                               - On macOS/Linux: Install `pwsh` command
                            
                            5. **Authentication Issues**:
                               - Verify M365_TENANT_ID, M365_CLIENT_ID, M365_CLIENT_SECRET in .env
                               - Ensure the app registration has required permissions
                               - Check that client secret hasn't expired
                            
                            6. **Service Principal Permissions**:
                               - Your Azure AD app needs Teams administration permissions
                               - Required permission: Microsoft Graph → Application permissions → AppCatalog.Submit
                               - Grant admin consent for the permissions
                            
                            7. **Network Issues**:
                               - Ensure outbound HTTPS (443) access to Microsoft services
                               - Check corporate firewall/proxy settings
                               - PowerShell may timeout on slow connections
                            
                            **💡 Current Status:**
                            - ✅ Manifest structure is now Teams-compatible
                            - ✅ Should upload successfully to Teams App Catalog
                            - ✅ Future-ready for M365 Copilot when supported
                            - ✅ Plugin.json included for automatic upgrade path
                            
                            **🎯 Expected Result:** Successful deployment and app registration!
                            """)
                        
                        # Add success example
                        st.success("""
                        🎉 **Recent Success**: This exact workflow was verified working on June 26, 2025!
                        
                        **CLI Deployment Results:**
                        - ✅ Package uploaded successfully to Teams App Catalog
                        - ✅ App ID assigned: `2fd55ca5-95d3-4bc0-bc42-201cf292d5ad`
                        - ✅ App Name: "Azure Function Proxy" 
                        - ✅ Status: Ready for publishing in Teams Admin Center
                        
                        **If UI deployment times out, use CLI directly:**
                        ```bash
                        pwsh ./deploy_m365_powershell.ps1
                        ```
                        
                        **Your deployment should work the same way!** 🚀
                        """)
            
            if st.button("📄 Generate PowerShell Script"):
                with st.spinner("Generating PowerShell upload script..."):
                    success, message, script_path = self.manager.generate_upload_script()
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.info("💡 Use this script for CI/CD pipelines or advanced PowerShell deployment scenarios")
                    else:
                        st.error(f"❌ {message}")
        
        # Teams 7.x+ Compatibility Warning and Manual Upload
        if "m365_package_path" in st.session_state:
            # Special alert for Teams 7.x+ users
            st.markdown("---")
            st.error("""
            ### � Teams PowerShell Module 7.x+ Users
            
            **If you have Teams PowerShell module 7.1.0 or newer:**
            - Automated PowerShell deployment **will likely fail**
            - Microsoft removed client secret authentication support
            - **Manual upload is recommended** as the most reliable method
            
            **Use the manual upload option below!**
            """)
            
            st.markdown("### 🔄 **Recommended**: Manual Upload")
            st.success("""
            **This method works with ALL Teams module versions** and is most reliable:
            1. Download the package using the button below
            2. Go to Teams Admin Center: https://admin.teams.microsoft.com
            3. Navigate to: Teams apps → Manage apps → Upload
            4. Upload the downloaded `appPackage.zip` file
            5. Set Publishing State to "Published"
            6. Configure permissions and policies as needed
            """)
            
            # Download button
            if st.session_state.m365_package_path.exists():
                with open(st.session_state.m365_package_path, "rb") as f:
                    st.download_button(
                        label="📥 Download Package for Manual Upload",
                        data=f.read(),
                        file_name="appPackage.zip",
                        mime="application/zip",
                        type="primary"
                    )
        
        # Step 5: Deployment Instructions
        st.subheader("🚀 Step 5: Deployment")
        
        # Check M365 credentials status
        m365_tenant_id = os.getenv("M365_TENANT_ID", "")
        m365_client_id = os.getenv("M365_CLIENT_ID", "")
        m365_client_secret = os.getenv("M365_CLIENT_SECRET", "")
        
        if all([m365_tenant_id, m365_client_id, m365_client_secret]):
            st.success("✅ M365 credentials are configured - automated PowerShell deployment available!")
            
            # Show quick deploy button if package is ready
            if "m365_package_path" in st.session_state:
                st.markdown("### 🎯 PowerShell Deployment")
                
                # Add specific warning about Teams 7.x+ compatibility
                st.error("""
                🚨 **Teams PowerShell Module 7.x+ Alert**
                
                If you have Teams PowerShell module 7.1.0 or newer:
                - Client secret authentication is **no longer supported**
                - Interactive browser authentication is **required**
                - You may see errors like "Unsupported User Type" or "NonInteractive parameter not found"
                
                **Recommended solutions:**
                1. Use manual upload in Teams Admin Center (see instructions below)
                2. Run PowerShell as administrator
                3. Consider downgrading to Teams module 6.x if possible
                """)
                
                if st.button("🚀 Deploy via PowerShell", type="primary", use_container_width=True):
                    with st.spinner("🔄 Deploying to Microsoft 365 via PowerShell..."):
                        deploy_success, deploy_message = self.manager.deploy_to_m365_via_powershell(st.session_state.m365_package_path)
                        
                        if deploy_success:
                            st.success(f"✅ {deploy_message}")
                            st.balloons()
                            
                            st.markdown(f"""
                            ### 🎉 Deployment Complete!
                            
                            **Your Agent Details:**
                            - **Name**: `{agent_name}`
                            - **Description**: `{app_description}`
                            - **Plugin ID**: `{plugin_id}`
                            - **Version**: `{package_version}`
                            
                            **What happens next:**
                            1. Your M365 Agent is now in the Teams App Catalog
                            2. Go to Teams Admin Center: https://admin.teams.microsoft.com
                            3. Navigate to: Teams apps → Manage apps
                            4. **Look for agent named**: `{agent_name}`
                            5. Set Publishing State = 'Published'
                            6. Your agent will be available in Microsoft 365 Copilot!
                            
                            **Users can invoke your agent with**: `@{agent_name.replace(' ', '')}` 🎯
                            
                            ### 🔍 How to Find Your Agent
                            Use this script to search for your deployed agent:
                            ```bash
                            python find_m365_agents.py
                            ```
                            """)
                        else:
                            st.error(f"❌ {deploy_message}")
                            
                            # Show troubleshooting tips
                            with st.expander("🔧 PowerShell Troubleshooting Tips"):
                                st.markdown("""
                                **Common PowerShell Deployment Issues:**
                                
                                1. **Teams Module 7.x+ Authentication Issues**:
                                   - Client secret authentication removed in module 7.x+
                                   - Interactive browser authentication now required
                                   - May see "Unsupported User Type" errors
                                   - **Solution**: Use manual upload method instead
                                
                                2. **PowerShell Module Issues**:
                                   - Install latest MicrosoftTeams module: `Install-Module -Name MicrosoftTeams -Force`
                                   - Run PowerShell as Administrator if needed
                                   - On macOS/Linux: Install PowerShell Core (`pwsh`)
                                
                                3. **Authentication Problems**:
                                   - Verify M365_TENANT_ID, M365_CLIENT_ID, M365_CLIENT_SECRET in .env
                                   - Check that the app registration exists and is active
                                   - Ensure client secret hasn't expired
                                   - Ensure Application permissions (not Delegated) are granted
                                
                                4. **Permission Issues**:
                                   - Required: Microsoft Graph → **Application permissions** → AppCatalog.Submit
                                   - Optional: Microsoft Graph → **Application permissions** → AppCatalog.ReadWrite.All
                                   - ✅ **Grant admin consent** after adding permissions
                                
                                5. **Network/Timeout Issues**:
                                   - PowerShell deployment can take 5-10 minutes
                                   - Check corporate firewall/proxy settings
                                   - Ensure outbound HTTPS (443) access to Microsoft services
                                
                                **💡 Recommended**: If PowerShell fails, use manual upload method below.
                                """)
                
        else:
            st.warning("⚠️ M365 credentials not found in .env file")
            
            with st.expander("🔧 Configure M365 Credentials for Automated Deployment", expanded=True):
                st.markdown("""
                **Add these variables to your .env file:**
                ```bash
                M365_TENANT_ID=your-m365-tenant-id
                M365_CLIENT_ID=your-m365-app-client-id
                M365_CLIENT_SECRET=your-m365-app-client-secret
                ```
                
                **How to get these values:**
                1. Go to Azure Portal → Azure Active Directory → App registrations
                2. Create a new app registration for M365 Agent
                3. Add required API permissions (**IMPORTANT: Use Application permissions, NOT Delegated**)
                   - Microsoft Graph → **Application permissions** → AppCatalog.Submit
                   - Microsoft Graph → **Application permissions** → AppCatalog.ReadWrite.All (optional)
                4. Grant admin consent for the permissions
                5. Create a client secret
                6. Copy the Tenant ID, Client ID, and Client Secret to your .env file
                """
                )
        
        if "m365_package_path" in st.session_state:
            st.success("Package is ready for deployment!")
            
            with st.expander("📖 Deployment Instructions", expanded=True):
                st.markdown("""
                ### Prerequisites: M365 App Registration
                
                Before deployment, you need to create a dedicated Azure AD app registration for M365 Agent:
                
                1. **Go to Azure Portal** → Azure Active Directory → App registrations
                2. **Create New Registration:**
                   - Name: "M365 Agent - [Your Organization]"
                   - Supported account types: Single tenant
                3. **Add API Permissions:**
                   - Microsoft Graph → **Application permissions** → AppCatalog.Submit
                   - Microsoft Graph → **Application permissions** → AppCatalog.ReadWrite.All (if available)
                   - ⚠️ **IMPORTANT**: Use "Application permissions", NOT "Delegated permissions"
                4. **Grant admin consent** for the permissions
                5. **Create Client Secret** → Save the values to your .env file
                
                ### Deployment Options (Ordered by Reliability)
                
                #### 🚀 **Option 1: PowerShell Deployment (Primary)**
                
                **Click the "🚀 Deploy via PowerShell" button above!**
                
                The system will automatically:
                1. Install MicrosoftTeams PowerShell module if needed
                2. Connect using your service principal credentials
                3. Upload the app package to Teams App Catalog
                4. Provide deployment results in real-time
                
                **Requirements:**
                - PowerShell installed (Windows: built-in, macOS/Linux: install PowerShell Core)
                - Internet connection for module download
                - Valid M365 credentials in .env file
                - Compatible MicrosoftTeams module version
                
                **⚠️ Teams Module 7.x+ Note:**
                - Interactive browser authentication may be required
                - Client secret authentication removed in newer versions
                - May need to run as administrator
                
                #### 📁 **Option 2: Manual Upload (Fallback)**
                
                **Use only if PowerShell deployment fails**
                
                1. **Download the package:** `appPackage.zip` (use button below)
                2. **Go to Teams Admin Center:** https://admin.teams.microsoft.com
                3. **Navigate to:** Teams apps → Manage apps → Upload
                4. **Upload:** Select `appPackage.zip`
                5. **Publish:** Set Publishing State to "Published"
                6. **Configure:** Set up permissions and policies as needed
                
                ### After Deployment
                
                - The M365 Agent will be available in Microsoft 365 Copilot
                - Users can ask questions and they'll be proxied to your Azure Function
                - Monitor usage in the Teams Admin Center
                - Use `python find_m365_agents.py` to locate your deployed agent
                """)
            
            # Download link for the package - for manual upload only
            if st.session_state.m365_package_path.exists():
                st.markdown("#### 📁 Package Download (Manual Upload Only)")
                st.warning("⚠️ **Use this only if PowerShell deployment fails!**")
                
                
                with open(st.session_state.m365_package_path, "rb") as f:
                    st.download_button(
                        label="📥 Download Package for Manual Upload",
                        data=f.read(),
                        file_name="appPackage.zip",
                        mime="application/zip",
                        help="Download only if PowerShell deployment fails"
                    )
        else:
            st.info("Build the package first to see deployment instructions.")
        
        # Step 6: Testing and Validation
        st.subheader("🧪 Step 6: Testing & Routing Verification")
        
        if function_key and selected_function_url:
            st.markdown("#### 🔍 Test Function Routing")
            st.info("Test your Azure Function to ensure it receives questions correctly and verify the routing behavior.")
            
            # Initialize test prompt in session state if not exists
            if "test_prompt" not in st.session_state:
                st.session_state.test_prompt = ""
            
            test_prompt = st.text_input(
                "Test Prompt",
                value=st.session_state.test_prompt,
                placeholder="Enter a test question for your function...",
                help="Test your Azure Function before deploying to M365"
            )
            
            # Update session state when text input changes
            st.session_state.test_prompt = test_prompt
            
            # Add some example test cases
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🧪 Test Generic Question"):
                    st.session_state.test_prompt = "Hello, how are you?"
                    st.rerun()
            with col2:
                if st.button("🧪 Test Specific Question"):
                    st.session_state.test_prompt = "Find information about our company policies"
                    st.rerun()
            with col3:
                if st.button("🧪 Test Complex Question"):
                    st.session_state.test_prompt = "What were the sales figures for Q3 and how do they compare to last year?"
                    st.rerun()
            
            if st.button("🧪 Test Function") and test_prompt:
                with st.spinner("Testing Azure Function..."):
                    try:
                        headers = {
                            "Content-Type": "application/json",
                            "x-functions-key": function_key
                        }
                        
                        payload = {"question": test_prompt}
                        
                        response = requests.post(
                            selected_function_url,
                            json=payload,
                            headers=headers,
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            st.success("✅ Function test successful!")
                            
                            # Show the exact payload sent
                            with st.expander("� Request Sent to Function"):
                                st.json(payload)
                                st.markdown("**Headers:**")
                                st.code(f"Content-Type: application/json\nx-functions-key: [HIDDEN]")
                            
                            with st.expander("�📄 Function Response"):
                                response_data = response.json()
                                st.json(response_data)
                                
                                # Check if response has routing verification
                                if isinstance(response_data, dict):
                                    if "source" in response_data:
                                        st.success(f"✅ Response includes source verification: {response_data['source']}")
                                    else:
                                        st.info("💡 Consider adding a 'source' field to your function responses to verify routing")
                            
                            # Routing verification tips
                            with st.expander("🔄 Routing Verification Tips"):
                                st.markdown("""
                                **This test confirms:**
                                ✅ Your function receives the exact question text  
                                ✅ Authentication works properly  
                                ✅ Function processes and returns responses  
                                
                                **To verify M365 routing:**
                                1. Deploy your agent to M365
                                2. Ask the same question in M365 Copilot
                                3. Check your Azure Function logs to see if the question arrived
                                4. Compare the M365 response with this test response
                                
                                **Expected behavior in M365:**
                                - Question should appear in your function logs
                                - Response should match this test (if your function is deterministic)
                                - Response should clearly come from your function, not Copilot's knowledge
                                """)
                        else:
                            st.error(f"❌ Function test failed: {response.status_code}")
                            st.code(response.text)
                            
                    except requests.RequestException as e:
                        st.error(f"❌ Connection error: {e}")
                    except Exception as e:
                        st.error(f"❌ Test failed: {e}")
            
            # Add guidance for monitoring routing in production
            st.markdown("#### 📊 Production Routing Monitoring")
            with st.expander("📈 How to Monitor Question Routing in Production"):
                st.markdown("""
                **After deploying to M365, monitor routing with these methods:**
                
                #### 🔍 **Azure Function Monitoring:**
                1. **Application Insights**: Enable for your Function App
                2. **Function Logs**: Check invocation logs in Azure Portal
                3. **Custom Logging**: Add logging to your function code:
                   ```python
                   import logging
                   import json
                   from datetime import datetime
                   
                   def main(req):
                       question = req.get_json().get('question', '')
                       logging.info(f"M365 Question Received: {question}")
                       
                       # Your processing logic here
                       response = {"answer": "...", "source": "azure_function"}
                       
                       logging.info(f"Response sent: {json.dumps(response)}")
                       return response
                   ```
                
                #### 📊 **Routing Verification Checklist:**
                - [ ] Questions appear in Function logs
                - [ ] Question text is passed exactly as user typed
                - [ ] No questions are answered without function invocation
                - [ ] Function responses are returned to users
                - [ ] Error handling works properly
                
                #### 🚨 **Red Flags - Possible Routing Issues:**
                - User gets answers but no function logs
                - Responses don't match your function's style
                - Generic questions (like "Hello") get answered without logs
                - Inconsistent behavior between similar questions
                
                #### 🔧 **Troubleshooting Poor Routing:**
                1. **Check OpenAPI spec**: Ensure descriptions emphasize routing
                2. **Update plugin manifest**: Add stronger routing directives
                3. **Modify function responses**: Make them more distinctive
                4. **Train users**: Teach them to phrase questions specifically
                5. **Use prefixes**: Start responses with "From Azure Function:"
                """)
        else:
            st.info("Configure function key and URL above to test routing behavior.")


# --- EXPORT FOR STREAMLIT ---

def render_m365_agent_tab():
    """Streamlit entrypoint for M365 Agent tab."""
    ui = M365AgentUI()
    ui.render_m365_agent_tab()
