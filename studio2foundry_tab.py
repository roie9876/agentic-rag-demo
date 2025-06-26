import streamlit as st
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Tuple

# Import the existing Azure Function helper functions
from azure_function_helper import get_azure_subscription, list_function_apps


def zip_studio2foundry_folder(studio2foundry_dir: Path, zip_path: Path) -> None:
    """Zip the studio2foundry folder for deployment."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for item in studio2foundry_dir.rglob('*'):
            if item.is_file():
                # Skip certain files that shouldn't be deployed
                if item.name in ['.DS_Store', '.gitignore'] or item.suffix in ['.pyc']:
                    continue
                if '.git' in item.parts or '__pycache__' in item.parts:
                    continue
                # Add file to zip with relative path
                zf.write(item, item.relative_to(studio2foundry_dir))


def deploy_studio2foundry_code(
    resource_group: str,
    function_name: str,
    subscription_id: str
) -> Tuple[bool, str]:
    """
    Deploy local ./studio2foundry code to the Function App.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    if not all((subscription_id, resource_group, function_name)):
        return False, "Missing required parameters"
        
    studio2foundry_dir = Path.cwd() / "studio2foundry"
    if not studio2foundry_dir.exists():
        return False, f"Local 'studio2foundry' folder not found: {studio2foundry_dir}"
        
    try:
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / "studio2foundry.zip"
            zip_studio2foundry_folder(studio2foundry_dir, zip_path)
            
            cmd = [
                "az", "functionapp", "deployment", "source", "config-zip",
                "-g", resource_group,
                "-n", function_name,
                "--src", str(zip_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
            return True, f"✅ Studio2Foundry deployment completed successfully!\n\nOutput:\n{result.stdout.strip()}"
            
    except subprocess.TimeoutExpired:
        return False, "❌ Deployment timed out after 5 minutes"
    except subprocess.CalledProcessError as cerr:
        return False, f"❌ Azure CLI deployment failed:\n{cerr.stderr}"
    except Exception as ex:
        return False, f"❌ Failed to deploy: {ex}"


def create_custom_roles(subscription_id: str) -> Tuple[bool, str]:
    """
    Create the two required custom roles for Azure AI Services agents.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        import json
        import tempfile
        
        # Define the custom roles
        agentic_role = {
            "Name": "agentic",
            "Description": "Custom role for reading Azure AI Services agents",
            "Actions": [],
            "NotActions": [],
            "DataActions": [
                "Microsoft.CognitiveServices/accounts/AIServices/agents/read"
            ],
            "NotDataActions": [],
            "AssignableScopes": [f"/subscriptions/{subscription_id}"]
        }
        
        agentic_write_role = {
            "Name": "agentic-write", 
            "Description": "Custom role for writing Azure AI Services agents",
            "Actions": [],
            "NotActions": [],
            "DataActions": [
                "Microsoft.CognitiveServices/accounts/AIServices/agents/write"
            ],
            "NotDataActions": [],
            "AssignableScopes": [f"/subscriptions/{subscription_id}"]
        }
        
        results = []
        
        # Create both roles
        for role_name, role_def in [("agentic", agentic_role), ("agentic-write", agentic_write_role)]:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(role_def, f, indent=2)
                role_file = f.name
            
            try:
                # Create the role
                cmd = [
                    "az", "role", "definition", "create",
                    "--role-definition", role_file,
                    "--subscription", subscription_id
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
                results.append(f"✅ Created role: {role_name}")
                
            except subprocess.CalledProcessError as e:
                if "already exists" in e.stderr.lower():
                    results.append(f"ℹ️ Role already exists: {role_name}")
                else:
                    results.append(f"❌ Failed to create {role_name}: {e.stderr}")
            finally:
                # Clean up temp file
                try:
                    os.unlink(role_file)
                except:
                    pass
        
        return True, "\n".join(results)
        
    except Exception as e:
        return False, f"❌ Error creating custom roles: {e}"


def assign_roles_to_function_app(
    subscription_id: str,
    resource_group: str, 
    function_app_name: str
) -> Tuple[bool, str]:
    """
    Assign the custom roles to the Function App's managed identity.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        results = []
        
        # Get the Function App's managed identity principal ID
        get_identity_cmd = [
            "az", "functionapp", "identity", "show",
            "--name", function_app_name,
            "--resource-group", resource_group,
            "--query", "principalId",
            "--output", "tsv"
        ]
        
        identity_result = subprocess.run(get_identity_cmd, capture_output=True, text=True, check=True, timeout=30)
        principal_id = identity_result.stdout.strip()
        
        if not principal_id or principal_id == "None":
            return False, "❌ Function App does not have System-assigned Managed Identity enabled"
        
        # Assign both custom roles to the resource group
        roles = ["agentic", "agentic-write"]
        scope = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        
        for role_name in roles:
            cmd = [
                "az", "role", "assignment", "create",
                "--assignee", principal_id,
                "--role", role_name,
                "--scope", scope
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
                results.append(f"✅ Assigned role: {role_name}")
            except subprocess.CalledProcessError as e:
                if "already exists" in e.stderr.lower():
                    results.append(f"ℹ️ Role already assigned: {role_name}")
                else:
                    results.append(f"❌ Failed to assign {role_name}: {e.stderr}")
        
        return True, "\n".join(results)
        
    except subprocess.CalledProcessError as e:
        return False, f"❌ Error getting Function App identity: {e.stderr}"
    except Exception as e:
        return False, f"❌ Error assigning roles: {e}"


def set_function_app_setting_safely(
    app_name: str,
    resource_group: str,
    setting_name: str,
    setting_value: str
) -> Tuple[bool, str, int]:
    """
    Safely set a Function App setting while preserving all existing settings.
    
    Returns:
        Tuple of (success: bool, message: str, existing_settings_count: int)
    """
    try:
        import json
        
        # First, get existing app settings
        get_cmd = [
            "az", "functionapp", "config", "appsettings", "list",
            "--name", app_name,
            "--resource-group", resource_group,
            "--output", "json"
        ]
        
        get_result = subprocess.run(get_cmd, capture_output=True, text=True, check=True, timeout=60)
        existing_settings = json.loads(get_result.stdout)
        
        # Build settings list preserving existing values and adding/updating the target setting
        settings_list = []
        setting_found = False
        
        for setting in existing_settings:
            if setting["name"] == setting_name:
                settings_list.append(f"{setting_name}={setting_value}")
                setting_found = True
            else:
                # Escape special characters in setting values
                escaped_value = setting['value'].replace('"', '\\"')
                settings_list.append(f"{setting['name']}={escaped_value}")
        
        # Add the setting if it wasn't in existing settings
        if not setting_found:
            settings_list.append(f"{setting_name}={setting_value}")
        
        # Set all settings (existing + new/updated setting)
        set_cmd = [
            "az", "functionapp", "config", "appsettings", "set",
            "--name", app_name,
            "--resource-group", resource_group,
            "--settings"
        ] + settings_list
        
        result = subprocess.run(set_cmd, capture_output=True, text=True, check=True, timeout=60)
        
        action = "updated" if setting_found else "added"
        return True, f"✅ {setting_name} {action} successfully! All {len(existing_settings)} existing settings preserved.", len(existing_settings)
        
    except subprocess.CalledProcessError as e:
        return False, f"❌ Failed to set {setting_name}: {e.stderr}", 0
    except Exception as e:
        return False, f"❌ Error setting {setting_name}: {e}", 0


def render_studio2foundry_tab():
    """Render the Studio2Foundry tab UI - simplified version like Function Config"""
    st.header("🏭 Studio2Foundry Function Deployment")
    st.markdown("Deploy your local Studio2Foundry code to Azure Function Apps")
    
    # Important notice about Managed Identity
    st.error("""
    🚨 **CRITICAL REQUIREMENT**: Your Azure Function **MUST** have System-assigned Managed Identity enabled to work!
    
    Without Managed Identity, you'll get authentication errors like "DefaultAzureCredential failed to retrieve a token"
    """)
    
    # Check if studio2foundry folder exists
    studio2foundry_dir = Path.cwd() / "studio2foundry"
    if not studio2foundry_dir.exists():
        st.error("❌ Studio2Foundry folder not found")
        st.markdown("""
        **Setup Required:**
        Make sure you have a \`studio2foundry\` folder in your project root containing your Azure Function code.
        """)
        return
    
    # Show folder status
    st.success(f"✅ Studio2Foundry folder found: \`{studio2foundry_dir}\`")
    
    # Show files in the folder
    with st.expander("📁 Files in Studio2Foundry folder", expanded=False):
        try:
            files = list(studio2foundry_dir.rglob("*"))
            files = [f for f in files if f.is_file() and not f.name.startswith('.')]
            for file in sorted(files)[:20]:  # Show first 20 files
                st.write(f"📄 \`{file.relative_to(studio2foundry_dir)}\`")
            if len(files) > 20:
                st.write(f"... and {len(files) - 20} more files")
        except Exception as e:
            st.error(f"Error reading folder: {e}")
    
    st.divider()
    
    # Azure Function App Selection (same as Function Config tab)
    st.subheader("🎯 Select Target Function App")
    
    # Get Azure subscription
    cli_sub = get_azure_subscription()
    sub_id = st.text_input("Subscription ID", cli_sub, help="Azure subscription ID for your Function Apps")
    
    if not sub_id:
        st.warning("⚠️ Please enter your Azure subscription ID to continue")
        return
    
    # List Function Apps in this subscription
    with st.spinner("🔍 Loading Function Apps..."):
        func_choices, func_map = list_function_apps(sub_id)
    
    if not func_choices:
        st.warning("⚠️ No Function Apps found in this subscription")
        st.markdown("""
        **Options:**
        1. Create a Function App in Azure Portal
        2. Check your subscription ID
        3. Verify you have access to Function Apps in this subscription
        """)
        return
    
    # Function App selection dropdown
    func_sel_lbl = st.selectbox(
        "Choose Function App",
        ["-- Select Function App --"] + func_choices,
        index=0,
        help="Select the Azure Function App where you want to deploy the Studio2Foundry code"
    )
    
    if func_sel_lbl == "-- Select Function App --":
        st.info("👆 Please select a Function App to continue")
        return
    
    # Get selected Function App details
    app_name, resource_group = func_map[func_sel_lbl]
    
    st.success(f"✅ Selected: **{app_name}** in resource group **{resource_group}**")
    
    st.divider()
    
    # Deployment section
    st.subheader("🚀 Deploy Studio2Foundry Code")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Ready to deploy?**")
        st.info(f"This will deploy all files from \`studio2foundry/\` to Function App \`{app_name}\`")
        st.warning("⚠️ This will overwrite any existing code in the Function App")
    
    with col2:
        if st.button("🚀 Deploy Studio2Foundry Code", type="primary", help="Deploy the studio2foundry folder to Azure"):
            with st.spinner("Deploying Studio2Foundry code to Azure..."):
                success, message = deploy_studio2foundry_code(
                    resource_group=resource_group,
                    function_name=app_name,
                    subscription_id=sub_id
                )
                
                if success:
                    st.success(message)
                    st.balloons()
                else:
                    st.error(message)
    
    st.divider()
    
    # Authentication Setup Information
    with st.expander("🔐 Fix Azure Authentication Errors", expanded=True):
        st.markdown("""
        **Common Error:** `DefaultAzureCredential failed to retrieve a token`
        
        **✅ Solution: Setup Managed Identity + Custom Roles**
        
        **⚠️ CRITICAL: Your Azure Function will NOT work without Managed Identity enabled!**
        
        Your Azure Function needs specific permissions to access Azure AI Services agents.
        """)
        
        if func_sel_lbl != "-- Select Function App --":
            app_name, resource_group = func_map[func_sel_lbl]
            
            st.markdown("### 🔴 Step 1: Enable Managed Identity (REQUIRED)")
            st.error("**This step is MANDATORY - your function will fail without it!**")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.warning(f"**Must enable System-assigned Managed Identity for {app_name}**")
                st.markdown("""
                **Why this is required:**
                - Your function uses `DefaultAzureCredential()` for authentication
                - Without Managed Identity, Azure can't authenticate your function
                - This causes the "failed to retrieve a token" error
                
                **Manual steps (REQUIRED):**
                1. Go to Azure Portal → Your Function App
                2. Navigate to **Settings** → **Identity**
                3. Turn **ON** the System-assigned identity
                4. Click **Save** and wait for it to enable
                """)
            
            with col2:
                st.markdown("**🚨 Enable Now:**")
                if st.button("🔗 Open Identity Settings", type="primary", help="Open Function App Identity settings in Azure Portal"):
                    portal_url = f"https://portal.azure.com/#@/resource/subscriptions/{sub_id}/resourceGroups/{resource_group}/providers/Microsoft.Web/sites/{app_name}/identity"
                    st.markdown(f"[🔗 Open Function App Identity Settings]({portal_url})")
                    st.info("👆 Click the link above to open Azure Portal")
            
            st.markdown("### Step 2: Create Custom Roles")
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.info("Create required custom roles for Azure AI Services agents")
                st.markdown("""
                **Required roles:**
                - `agentic` - Read access to AI Services agents
                - `agentic-write` - Write access to AI Services agents
                """)
            
            with col2:
                if st.button("🚀 Create Custom Roles", type="primary", help="Create the required custom roles in your subscription"):
                    with st.spinner("Creating custom roles..."):
                        success, message = create_custom_roles(sub_id)
                        if success:
                            st.success("✅ Custom roles setup completed!")
                            st.text(message)
                        else:
                            st.error(message)
            
            st.markdown("### Step 3: Assign Roles to Function App")
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.info(f"Assign custom roles to **{app_name}** on resource group **{resource_group}**")
                st.warning("⚠️ Make sure Managed Identity is enabled first!")
            
            with col2:
                if st.button("🔧 Assign Roles", type="primary", help="Assign custom roles to Function App's managed identity"):
                    with st.spinner("Assigning roles to Function App..."):
                        success, message = assign_roles_to_function_app(sub_id, resource_group, app_name)
                        if success:
                            st.success("✅ Roles assigned successfully!")
                            st.text(message)
                            st.balloons()
                        else:
                            st.error(message)
        else:
            st.info("👆 Select a Function App above to setup authentication")
        
        st.markdown("""
        ### ⚡ Quick Setup Summary
        **For your function to work, you MUST:**
        1. **Enable Managed Identity** (click the button above)
        2. **Create Custom Roles** (click the button above)  
        3. **Assign Roles** (click the button above)
        4. **Set PROJECT_ENDPOINT** (in the section below)
        
        **Without Managed Identity, you'll get:**
        ```
        DefaultAzureCredential failed to retrieve a token from the included credentials.
        EnvironmentCredential: EnvironmentCredential authentication unavailable.
        ManagedIdentityCredential: No managed identity endpoint found.
        ```
        
        ### Alternative: Manual Role Assignment
        If the automatic setup doesn't work:
        
        1. **Create custom roles manually:**
        ```bash
        # Create agentic role
        az role definition create --role-definition '{
            "Name": "agentic",
            "Description": "Read access to AI Services agents", 
            "Actions": [],
            "DataActions": ["Microsoft.CognitiveServices/accounts/AIServices/agents/read"],
            "AssignableScopes": ["/subscriptions/YOUR_SUBSCRIPTION_ID"]
        }'
        
        # Create agentic-write role  
        az role definition create --role-definition '{
            "Name": "agentic-write",
            "Description": "Write access to AI Services agents",
            "Actions": [],
            "DataActions": ["Microsoft.CognitiveServices/accounts/AIServices/agents/write"], 
            "AssignableScopes": ["/subscriptions/YOUR_SUBSCRIPTION_ID"]
        }'
        ```
        
        2. **Assign roles to Function App:**
        ```bash
        az role assignment create --assignee <FUNCTION_APP_PRINCIPAL_ID> --role "agentic" --scope "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP"
        az role assignment create --assignee <FUNCTION_APP_PRINCIPAL_ID> --role "agentic-write" --scope "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP"
        ```
        """)
    
    st.divider()
    
    # Environment Variables Configuration
    st.subheader("🌍 Function App Environment Variables")
    
    st.markdown("""
    **🎯 Primary requirement:** Your function needs `PROJECT_ENDPOINT` to work (like your working example).
    
    **🔐 Authentication:** Uses Managed Identity (MUST be enabled first!)
    """)
    
    st.warning("⚠️ **Before setting environment variables**: Make sure Managed Identity is enabled in the authentication section above!")
    
    # Check local .env for PROJECT_ENDPOINT (most important)
    project_endpoint = os.getenv("PROJECT_ENDPOINT", "")
    
    # Optional: Check for Service Principal credentials
    optional_vars = {
        "AZURE_CLIENT_ID": os.getenv("AZURE_CLIENT_ID", ""),
        "AZURE_CLIENT_SECRET": os.getenv("AZURE_CLIENT_SECRET", ""),
        "AZURE_TENANT_ID": os.getenv("AZURE_TENANT_ID", "")
    }
    has_sp_credentials = all(optional_vars.values())
    
    # Show status
    if project_endpoint:
        st.success(f"✅ PROJECT_ENDPOINT found: `{project_endpoint}`")
    else:
        st.error("❌ PROJECT_ENDPOINT not found in local .env file")
    
    if has_sp_credentials:
        st.info("ℹ️ Service Principal credentials found (will be set for explicit auth)")
    else:
        st.info("ℹ️ No Service Principal credentials (will use Managed Identity - recommended)")

    with st.expander("⚙️ Configure Environment Variables", expanded=True):
        st.markdown("""
        **Configure your Function App environment variables:**
        
        **Required:**
        - `PROJECT_ENDPOINT` - Your Azure AI Project endpoint
        
        **Optional (for Service Principal auth):**
        - `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`
        
        **💡 Tip:** Use Managed Identity instead of Service Principal for better security!
        """)
        
        if func_sel_lbl != "-- Select Function App --":
            app_name, resource_group = func_map[func_sel_lbl]
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.info(f"Will configure environment variables in Function App: **{app_name}**")
                
                if project_endpoint:
                    st.write("**Will set:**")
                    st.write(f"- PROJECT_ENDPOINT: `{project_endpoint[:50]}...`")
                    
                    if has_sp_credentials:
                        st.write("- AZURE_CLIENT_ID: `[from local .env]`")
                        st.write("- AZURE_CLIENT_SECRET: `[from local .env]`")
                        st.write("- AZURE_TENANT_ID: `[from local .env]`")
                        st.info("🔐 Service Principal credentials will be set")
                    else:
                        st.info("🔐 Only PROJECT_ENDPOINT will be set (use Managed Identity for auth)")
                
                # Show existing settings info
                if st.button("🔍 View Current Settings", help="Show current environment variables in the Function App"):
                    with st.spinner("Loading current settings..."):
                        try:
                            import json
                            get_cmd = [
                                "az", "functionapp", "config", "appsettings", "list",
                                "--name", app_name,
                                "--resource-group", resource_group,
                                "--output", "json"
                            ]
                            
                            get_result = subprocess.run(get_cmd, capture_output=True, text=True, check=True, timeout=30)
                            existing_settings = json.loads(get_result.stdout)
                            
                            st.write(f"**Current settings ({len(existing_settings)} total):**")
                            
                            # Check PROJECT_ENDPOINT specifically
                            pe_exists = any(setting["name"] == "PROJECT_ENDPOINT" for setting in existing_settings)
                            if pe_exists:
                                current_pe = next(setting["value"] for setting in existing_settings if setting["name"] == "PROJECT_ENDPOINT")
                                if current_pe == project_endpoint:
                                    st.success("✅ PROJECT_ENDPOINT already set correctly")
                                else:
                                    st.warning("⚠️ PROJECT_ENDPOINT exists but differs from local value")
                            else:
                                st.error("❌ PROJECT_ENDPOINT not set")
                            
                            # Check auth credentials
                            auth_vars = ["AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID"]
                            auth_count = sum(1 for var in auth_vars if any(setting["name"] == var for setting in existing_settings))
                            
                            if auth_count > 0:
                                st.info(f"ℹ️ {auth_count}/3 Service Principal credentials set")
                            else:
                                st.success("✅ No explicit credentials (good for Managed Identity)")
                            
                            # Show all settings
                            with st.expander("All current settings", expanded=False):
                                for setting in sorted(existing_settings, key=lambda x: x["name"]):
                                    name = setting["name"]
                                    value = setting["value"]
                                    # Hide sensitive data
                                    if any(secret in name.upper() for secret in ['SECRET', 'KEY', 'PASSWORD', 'TOKEN']):
                                        display_value = "***[HIDDEN]***"
                                    else:
                                        display_value = value if len(value) <= 50 else f"{value[:50]}..."
                                    st.write(f"**{name}**: `{display_value}`")
                                    
                        except Exception as e:
                            st.error(f"❌ Error loading settings: {e}")
            
            with col2:
                if project_endpoint:
                    button_text = "🚀 Set PROJECT_ENDPOINT Only" if not has_sp_credentials else "🚀 Set All Variables"
                    button_help = "Set PROJECT_ENDPOINT (use with Managed Identity)" if not has_sp_credentials else "Set PROJECT_ENDPOINT + Service Principal credentials"
                    
                    if st.button(button_text, type="primary", help=button_help):
                        with st.spinner("Setting environment variables..."):
                            success_count = 0
                            error_messages = []
                            
                            # Always set PROJECT_ENDPOINT
                            success, message, _ = set_function_app_setting_safely(
                                app_name=app_name,
                                resource_group=resource_group,
                                setting_name="PROJECT_ENDPOINT",
                                setting_value=project_endpoint
                            )
                            
                            if success:
                                success_count += 1
                            else:
                                error_messages.append(f"PROJECT_ENDPOINT: {message}")
                            
                            # Optionally set Service Principal credentials
                            if has_sp_credentials:
                                for var_name, var_value in optional_vars.items():
                                    success, message, _ = set_function_app_setting_safely(
                                        app_name=app_name,
                                        resource_group=resource_group,
                                        setting_name=var_name,
                                        setting_value=var_value
                                    )
                                    
                                    if success:
                                        success_count += 1
                                    else:
                                        error_messages.append(f"{var_name}: {message}")
                            
                            # Show results
                            if success_count > 0:
                                st.success(f"✅ Successfully configured {success_count} environment variables!")
                                st.success("🔄 Your Function App will restart automatically.")
                                if not has_sp_credentials:
                                    st.info("💡 Remember to enable Managed Identity in Azure Portal!")
                                st.balloons()
                            
                            if error_messages:
                                st.error("❌ Some variables failed to set:")
                                for error in error_messages:
                                    st.error(error)
                else:
                    st.button("🚀 Set Variables", disabled=True, help="PROJECT_ENDPOINT not found in local .env")
        else:
            st.info("👆 Select a Function App above to configure environment variables")
            
        if not project_endpoint:
            st.markdown("""
            **Setup Required:**
            Add `PROJECT_ENDPOINT` to your `.env` file:
            ```
            PROJECT_ENDPOINT=https://your-ai-project-endpoint.com/api/projects/your-project
            ```
            
            **Optional (for Service Principal auth):**
            ```
            AZURE_CLIENT_ID=your-client-id
            AZURE_CLIENT_SECRET=your-client-secret
            AZURE_TENANT_ID=your-tenant-id
            ```
            """)
        
        st.markdown("""
        **Alternative: Set via Azure Portal**
        1. Go to [Azure Portal](https://portal.azure.com)
        2. Navigate to your Function App → **Settings** → **Environment variables**
        3. Add: `PROJECT_ENDPOINT` = `your-endpoint-value`
        """)
    
    st.divider()
    
    # Function Testing Section
    st.subheader("🧪 Test Your Function")
    
    if func_sel_lbl != "-- Select Function App --":
        app_name, resource_group = func_map[func_sel_lbl]
        
        # Generate test URL
        base_url = f"https://{app_name}.azurewebsites.net/api/agent_httptrigger"
        
        st.markdown("### ✅ Test Your Deployed Function")
        st.success("Your function is working! Use this URL format for testing:")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            test_message = st.text_input("Test Message", value="מי הם חברי ועדת התמיכות", help="Enter your question in any language")
            test_agent_id = st.text_input("Agent ID", value="asst_3NKExbfOlMe1tYTdvxi2Woxw", help="Your Azure AI Agent ID")
        
        with col2:
            st.markdown("**Quick Test URLs:**")
            
            # Generate English test
            import urllib.parse
            english_msg = urllib.parse.quote("Hello, how can you help me?")
            english_url = f"{base_url}?message={english_msg}&agentid={test_agent_id}"
            
            if st.button("🔗 Test English"):
                st.code(english_url, language="text")
                st.markdown(f"[🌐 Open in Browser]({english_url})")
            
            # Generate Hebrew test
            hebrew_msg = urllib.parse.quote(test_message)
            hebrew_url = f"{base_url}?message={hebrew_msg}&agentid={test_agent_id}"
            
            if st.button("🔗 Test Hebrew"):
                st.code(hebrew_url, language="text") 
                st.markdown(f"[🌐 Open in Browser]({hebrew_url})")
        
        st.markdown("### 🔧 Manual URL Generation")
        if st.button("🔗 Generate Custom Test URL", type="primary"):
            encoded_message = urllib.parse.quote(test_message)
            encoded_agent_id = urllib.parse.quote(test_agent_id)
            
            test_url = f"{base_url}?message={encoded_message}&agentid={encoded_agent_id}"
            
            st.markdown("**Your custom test URL:**")
            st.code(test_url, language="text")
            st.markdown(f"[🌐 Open in Browser]({test_url})")
            st.success("📋 Copy this URL and paste it in your browser to test!")
        
        st.markdown("### � URL Format Documentation")
        with st.expander("How to use your function", expanded=False):
            st.markdown(f"""
            **Base URL:** `{base_url}`
            
            **Required Parameters:**
            - `message` - Your question/prompt (URL-encoded for non-ASCII characters)
            - `agentid` - Your Azure AI Agent ID
            
            **Optional Parameters:**
            - `threadid` - Existing conversation thread ID (for multi-turn conversations)
            
            **Examples:**
            ```
            # Simple English question
            {base_url}?message=Hello&agentid=asst_3NKExbfOlMe1tYTdvxi2Woxw
            
            # Hebrew question (URL-encoded)
            {base_url}?message=%D7%9E%D7%99%20%D7%94%D7%9D%20%D7%97%D7%91%D7%A8%D7%99%20%D7%95%D7%A2%D7%93%D7%AA%20%D7%94%D7%AA%D7%9E%D7%99%D7%9B%D7%95%D7%AA&agentid=asst_3NKExbfOlMe1tYTdvxi2Woxw
            
            # With conversation thread
            {base_url}?message=Follow%20up%20question&agentid=asst_3NKExbfOlMe1tYTdvxi2Woxw&threadid=thread_abc123
            ```
            
            **Response:** Plain text response from your AI agent
            
            **Status Codes:**
            - 200: Success
            - 400: Missing required parameters
            - 404: Agent or thread not found  
            - 500: Internal server error
            """)
    else:
        st.info("👆 Select a Function App above to generate test URLs")
    
    st.divider()
    
    # Additional info
    with st.expander("ℹ️ About Studio2Foundry Deployment", expanded=False):
        st.markdown("""
        **What this does:**
        - Packages all files from your local \`studio2foundry/\` folder into a ZIP file
        - Deploys the ZIP file to the selected Azure Function App using Azure CLI
        - Overwrites the existing code in the Function App
        
        **Prerequisites:**
        - Azure CLI installed and authenticated (\`az login\`)
        - Access to the target Azure Function App
        - Studio2Foundry folder with valid Azure Function code
        
        **Files included:**
        - All Python files (\`.py\`)
        - Configuration files (\`host.json\`, \`requirements.txt\`, etc.)
        - Function bindings (\`function.json\` files)
        - Other relevant files (excludes \`.git\`, \`__pycache__\`, etc.)
        
        **After deployment:**
        - Your Function App will restart automatically
        - Functions will be available at their HTTP endpoints
        - You can monitor deployment status in Azure Portal
        """)
