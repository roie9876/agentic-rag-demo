"""
M365 Agent Tab for Agentic RAG Demo - Simplified Version
========================================================
Focus on package creation since automated upload requires delegated permissions.
"""

import json
import os
import uuid
import zipfile
import tempfile
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import streamlit as st
import requests
from datetime import datetime

# Azure Function helper for getting available functions
from azure_function_helper import list_function_apps, get_azure_subscription


class M365AgentManager:
    """Manages M365 Agent creation and deployment"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Constants for M365 Agent
        self.PLUGIN_ID = "com.contoso.funcproxy"
        self.APP_NAME = "Func Proxy"
        self.APP_DESC = "Simple pipe to an Azure Function"
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
    
    def create_openapi_json(self, func_url: str) -> Dict[str, Any]:
        """Create OpenAPI specification for the Azure Function"""
        return {
            "openapi": "3.0.3",
            "info": {
                "title": "Azure Function Proxy",
                "description": "Proxy API for Azure Function",
                "version": "1.0.0"
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
                        "summary": "Execute Azure Function",
                        "description": "Send a question to the Azure Function",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "question": {
                                                "type": "string",
                                                "description": "The question or prompt to send to the function"
                                            }
                                        },
                                        "required": ["question"]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Successful response",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "description": "Response from the Azure Function"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    
    def create_plugin_json(self) -> Dict[str, Any]:
        """Create API plugin manifest v2.2"""
        return {
            "$schema": "https://developer.microsoft.com/en-us/microsoft-365/copilot/schema/api-plugin-manifest.2.2.json",
            "id": self.PLUGIN_ID,
            "name": self.APP_NAME,
            "description": self.APP_DESC,
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
    
    def create_manifest_json(self) -> Dict[str, Any]:
        """Create Teams/M365 app manifest v1.16"""
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
                "short": self.APP_NAME,
                "full": f"{self.APP_NAME} - Azure Function Integration"
            },
            "description": {
                "short": self.APP_DESC,
                "full": "An M365 Copilot plugin that proxies questions to Azure Functions for intelligent responses"
            },
            "icons": {
                "outline": self.ICON_OUTLINE,
                "color": self.ICON_COLOR
            },
            "accentColor": "#FFFFFF",
            "copilotAgents": {
                "declarativeAgents": [
                    {
                        "id": self.PLUGIN_ID,
                        "file": "plugin.json"
                    }
                ]
            }
        }
    
    def create_placeholder_icons(self, package_dir: Path) -> None:
        """Create placeholder PNG icons if they don't exist"""
        try:
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
        except ImportError:
            # If PIL is not available, create simple placeholder files
            (package_dir / self.ICON_OUTLINE).touch()
            (package_dir / self.ICON_COLOR).touch()
            self.logger.warning("PIL not available, created empty icon files")
    
    def build_package(self, func_url: str, output_dir: Path = None) -> Tuple[bool, str, Optional[Path]]:
        """
        Build the M365 Agent package with all required artifacts
        
        Returns:
            Tuple of (success: bool, message: str, zip_path: Optional[Path])
        """
        try:
            if output_dir is None:
                output_dir = Path.cwd()
            
            package_dir = output_dir / "package"
            package_dir.mkdir(exist_ok=True)
            
            # Create openapi.json
            openapi_content = self.create_openapi_json(func_url)
            with open(package_dir / "openapi.json", "w") as f:
                json.dump(openapi_content, f, indent=2)
            
            # Create plugin.json
            plugin_content = self.create_plugin_json()
            with open(package_dir / "plugin.json", "w") as f:
                json.dump(plugin_content, f, indent=2)
            
            # Create manifest.json
            manifest_content = self.create_manifest_json()
            with open(package_dir / "manifest.json", "w") as f:
                json.dump(manifest_content, f, indent=2)
            
            # Create placeholder icons
            self.create_placeholder_icons(package_dir)
            
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


def render_m365_agent_tab():
    """Render the M365 Agent tab with focus on package creation"""
    st.header("🤖 M365 Agent Builder")
    st.markdown("""
    Create an M365 API Plugin that proxies questions to your existing Azure Functions.
    This will create a Teams/M365 app package ready for deployment.
    """)
    
    # Important notice about deployment limitations
    st.warning("""
    🚨 **Important Notice**: Automated upload via Microsoft Graph API is not available because 
    `AppCatalog.Submit` permission is only available as a Delegated permission (requires user interaction).
    
    ✅ **Solutions**: Use PowerShell script, manual upload, or Teams Developer Portal for deployment.
    """)
    
    manager = M365AgentManager()
    
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
        available_functions = manager.get_available_functions(subscription_id)
    
    if not available_functions:
        st.warning("No Azure Functions found in this subscription.")
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
            format_func=lambda i: function_options[i]
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
        st.info("💡 Function key is required for secure authentication.")
    
    # Step 3: Package Configuration
    st.subheader("⚙️ Step 3: Package Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        app_name = st.text_input("App Name", value="M365 Agent")
        plugin_id = st.text_input("Plugin ID", value="com.contoso.funcproxy")
    
    with col2:
        app_description = st.text_input("App Description", value="Azure Function Integration")
        package_version = st.text_input("Package Version", value="1.0.0")
    
    # Update manager constants
    manager.APP_NAME = app_name
    manager.PLUGIN_ID = plugin_id
    manager.APP_DESC = app_description
    manager.PACKAGE_VER = package_version
    
    # Step 4: Build Package
    st.subheader("🏗️ Step 4: Build Package")
    
    if st.button("📦 Build M365 Package", type="primary", disabled=not function_key):
        with st.spinner("Building M365 Agent package..."):
            success, message, zip_path = manager.build_package(selected_function_url)
            
            if success:
                st.success(f"✅ {message}")
                
                # Show package contents
                with st.expander("📁 Package Contents"):
                    package_files = [
                        "manifest.json - Teams/M365 app manifest",
                        "plugin.json - API plugin manifest", 
                        "openapi.json - OpenAPI specification",
                        "color.png - App icon (192x192)",
                        "outline.png - App outline icon (32x32)"
                    ]
                    for file in package_files:
                        st.text(f"✓ {file}")
                
                # Download button
                with open(zip_path, "rb") as f:
                    st.download_button(
                        label="📥 Download M365 Package",
                        data=f.read(),
                        file_name="appPackage.zip",
                        mime="application/zip"
                    )
                
                # Store package path in session state
                st.session_state.m365_package_path = zip_path
            else:
                st.error(f"❌ {message}")
    
    # Step 5: Deployment Instructions
    st.subheader("🚀 Step 5: Deployment Options")
    
    if "m365_package_path" in st.session_state:
        st.success("✅ Package is ready for deployment!")
        
        # Deployment options
        tab1, tab2, tab3 = st.tabs(["🥇 PowerShell", "🥈 Manual Upload", "🥉 Developer Portal"])
        
        with tab1:
            st.markdown("""
            ### PowerShell Deployment (Recommended)
            
            1. **Install Teams PowerShell module** (if not already installed):
            ```powershell
            Install-Module -Name MicrosoftTeams -Force -AllowClobber
            ```
            
            2. **Run deployment script**:
            ```powershell
            # Import module
            Import-Module MicrosoftTeams
            
            # Connect (will open browser for login)
            Connect-MicrosoftTeams
            
            # Upload app
            $Result = New-TeamsApp -Path "appPackage.zip"
            
            # Show result
            Write-Host "App ID: $($Result.Id)"
            Write-Host "App Name: $($Result.DisplayName)"
            
            # Disconnect
            Disconnect-MicrosoftTeams
            ```
            
            3. **Go to Teams Admin Center** to publish the app
            """)
        
        with tab2:
            st.markdown("""
            ### Manual Upload via Teams Admin Center
            
            1. **Download** the `appPackage.zip` file (use download button above)
            2. **Go to**: [Teams Admin Center](https://admin.teams.microsoft.com)
            3. **Navigate to**: Teams apps → Manage apps
            4. **Click**: Upload new app → Upload
            5. **Select**: The `appPackage.zip` file
            6. **Set Publishing State** to 'Published'
            """)
        
        with tab3:
            st.markdown("""
            ### Teams Developer Portal
            
            1. **Go to**: [Teams Developer Portal](https://dev.teams.microsoft.com)
            2. **Sign in** with your M365 account
            3. **Click**: Apps → Import app
            4. **Upload**: The `appPackage.zip` file
            5. **Publish** to your organization
            """)
        
        st.info("""
        💡 **After deployment**: The M365 Agent will be available in Microsoft 365 Copilot.
        Users can ask questions and they'll be proxied to your Azure Function!
        """)
    
    # Step 6: Testing
    st.subheader("🧪 Step 6: Test Your Function")
    
    if function_key and selected_function_url:
        test_prompt = st.text_input(
            "Test Prompt",
            placeholder="Enter a test question for your function..."
        )
        
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
                        with st.expander("📄 Response"):
                            st.json(response.json())
                    else:
                        st.error(f"❌ Function test failed: {response.status_code}")
                        st.code(response.text)
                        
                except requests.RequestException as e:
                    st.error(f"❌ Connection error: {e}")
                except Exception as e:
                    st.error(f"❌ Test failed: {e}")


if __name__ == "__main__":
    # For testing the module standalone
    render_m365_agent_tab()
