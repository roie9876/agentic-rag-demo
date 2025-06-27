import streamlit as st
import os
import subprocess
import tempfile
import zipfile
import urllib.parse
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
        
        results = []
        
        # First, check if roles already exist and delete them if they have GUID names
        try:
            list_cmd = [
                "az", "role", "definition", "list",
                "--subscription", subscription_id,
                "--custom-role-only", "true",
                "--query", "[?contains(description, 'agentic') || contains(description, 'AI Services agents')].{name:roleName, displayName:displayName}",
                "--output", "json"
            ]
            list_result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=30)
            if list_result.returncode == 0:
                existing_roles = json.loads(list_result.stdout)
                for role in existing_roles:
                    # Delete roles with GUID names or old names
                    role_name = role.get('name', '')
                    if (len(role_name) == 36 and '-' in role_name) or role_name in ['agentic', 'agentic-write']:
                        delete_cmd = [
                            "az", "role", "definition", "delete",
                            "--name", role_name,
                            "--subscription", subscription_id
                        ]
                        subprocess.run(delete_cmd, capture_output=True, text=True, timeout=30)
                        results.append(f"🗑️ Deleted old role: {role_name}")
        except:
            pass  # Continue if listing fails
        
        # Define the custom roles with explicit readable names
        role_definitions = [
            {
                "name": "azure-index-agentic-read",
                "definition": {
                    "Name": "azure-index-agentic-read",
                    "Description": "Custom role for reading Azure AI Services agents and search index",
                    "Actions": [],
                    "NotActions": [],
                    "DataActions": [
                        "Microsoft.CognitiveServices/accounts/AIServices/agents/read",
                        "Microsoft.Search/searchServices/indexes/documents/read"
                    ],
                    "NotDataActions": [],
                    "AssignableScopes": [f"/subscriptions/{subscription_id}"]
                }
            },
            {
                "name": "azure-index-agentic-readwrite",
                "definition": {
                    "Name": "azure-index-agentic-readwrite", 
                    "Description": "Custom role for full access to Azure AI Services agents and search index",
                    "Actions": [],
                    "NotActions": [],
                    "DataActions": [
                        "Microsoft.CognitiveServices/accounts/AIServices/agents/read",
                        "Microsoft.CognitiveServices/accounts/AIServices/agents/write",
                        "Microsoft.Search/searchServices/indexes/documents/read",
                        "Microsoft.Search/searchServices/indexes/documents/write"
                    ],
                    "NotDataActions": [],
                    "AssignableScopes": [f"/subscriptions/{subscription_id}"]
                }
            }
        ]
        
        # Create both roles with explicit naming
        for role_info in role_definitions:
            role_name = role_info["name"]
            role_def = role_info["definition"]
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(role_def, f, indent=2)
                role_file = f.name
            
            try:
                # First try to create the role
                cmd = [
                    "az", "role", "definition", "create",
                    "--role-definition", role_file,
                    "--subscription", subscription_id
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
                
                # Verify the role was created with the correct name
                verify_cmd = [
                    "az", "role", "definition", "show",
                    "--name", role_name,
                    "--subscription", subscription_id,
                    "--query", "roleName",
                    "--output", "tsv"
                ]
                verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=30)
                
                if verify_result.returncode == 0:
                    actual_name = verify_result.stdout.strip()
                    if actual_name == role_name:
                        results.append(f"✅ Created role: {role_name}")
                    else:
                        results.append(f"⚠️ Role created but with name: {actual_name} (expected: {role_name})")
                else:
                    results.append(f"✅ Created role: {role_name} (verification failed)")
                
            except subprocess.CalledProcessError as e:
                if "already exists" in e.stderr.lower() or "conflictingrole" in e.stderr.lower():
                    # Try to update the existing role
                    try:
                        update_cmd = [
                            "az", "role", "definition", "update",
                            "--role-definition", role_file,
                            "--subscription", subscription_id
                        ]
                        update_result = subprocess.run(update_cmd, capture_output=True, text=True, timeout=60)
                        if update_result.returncode == 0:
                            results.append(f"✅ Updated existing role: {role_name}")
                        else:
                            results.append(f"ℹ️ Role already exists: {role_name}")
                    except:
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
        roles = ["azure-index-agentic-read", "azure-index-agentic-readwrite"]
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


def enable_managed_identity(
    subscription_id: str,
    resource_group: str,
    function_app_name: str
) -> Tuple[bool, str]:
    """
    Enable System-assigned Managed Identity for the Function App.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        cmd = [
            "az", "functionapp", "identity", "assign",
            "--name", function_app_name,
            "--resource-group", resource_group,
            "--subscription", subscription_id
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
        return True, "✅ System-assigned Managed Identity enabled successfully!"
        
    except subprocess.CalledProcessError as e:
        if "already exists" in e.stderr.lower() or "already assigned" in e.stderr.lower():
            return True, "ℹ️ System-assigned Managed Identity is already enabled"
        else:
            return False, f"❌ Failed to enable Managed Identity: {e.stderr}"
    except Exception as e:
        return False, f"❌ Error enabling Managed Identity: {e}"


def get_resource_groups(subscription_id: str) -> Tuple[list, dict]:
    """
    Get list of resource groups in the subscription.
    
    Returns:
        Tuple of (choices_list, name_to_info_map)
    """
    try:
        import json
        
        cmd = [
            "az", "group", "list",
            "--subscription", subscription_id,
            "--query", "[].{name:name, location:location}",
            "--output", "json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        groups = json.loads(result.stdout)
        
        choices = []
        group_map = {}
        
        for group in groups:
            name = group["name"]
            location = group["location"]
            display_name = f"{name} ({location})"
            choices.append(display_name)
            group_map[display_name] = name
        
        return choices, group_map
        
    except Exception as e:
        return [], {}


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


def cleanup_old_custom_roles(subscription_id: str) -> Tuple[bool, str]:
    """
    Clean up old custom roles that have GUID names or old naming.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        import json
        
        # List all custom roles in the subscription
        list_cmd = [
            "az", "role", "definition", "list",
            "--subscription", subscription_id,
            "--custom-role-only", "true",
            "--query", "[].{name:roleName, displayName:displayName, description:description}",
            "--output", "json"
        ]
        
        result = subprocess.run(list_cmd, capture_output=True, text=True, check=True, timeout=30)
        roles = json.loads(result.stdout)
        
        deleted_roles = []
        
        for role in roles:
            role_name = role.get('name', '')
            description = role.get('description', '').lower()
            
            # Delete if:
            # 1. Role name is a GUID (36 chars with dashes)
            # 2. Role name is old naming (agentic, agentic-write)
            # 3. Description contains "agentic" or "AI Services agents"
            should_delete = False
            
            if len(role_name) == 36 and role_name.count('-') == 4:
                should_delete = True  # GUID format
            elif role_name in ['agentic', 'agentic-write']:
                should_delete = True  # Old names
            elif 'agentic' in description or 'ai services agents' in description:
                # Only delete if it's not already the correct name
                if role_name not in ['azure-index-agentic-read', 'azure-index-agentic-readwrite']:
                    should_delete = True
            
            if should_delete:
                try:
                    delete_cmd = [
                        "az", "role", "definition", "delete",
                        "--name", role_name,
                        "--subscription", subscription_id
                    ]
                    
                    delete_result = subprocess.run(delete_cmd, capture_output=True, text=True, check=True, timeout=30)
                    deleted_roles.append(f"🗑️ Deleted: {role_name}")
                    
                except subprocess.CalledProcessError as e:
                    deleted_roles.append(f"⚠️ Failed to delete {role_name}: {e.stderr}")
        
        if deleted_roles:
            return True, "\n".join(deleted_roles)
        else:
            return True, "ℹ️ No old roles found to cleanup"
        
    except Exception as e:
        return False, f"❌ Error cleaning up roles: {e}"


def render_studio2foundry_tab():
    """Render the Studio2Foundry tab UI - simplified version like Function Config"""
    st.header("🏭 Studio2Foundry Function Deployment")
    st.markdown("Deploy your local Studio2Foundry code to Azure Function Apps")
    
    # Debug section (can be removed in production)
    with st.expander("🔧 Debug & Reset", expanded=False):
        st.write("**Current Session State:**")
        studio_keys = [k for k in st.session_state.keys() if k.startswith('studio2foundry_')]
        for key in studio_keys:
            st.write(f"- `{key}`: {st.session_state[key]}")
        
        if st.button("🔄 Reset All Selections", help="Clear all Studio2Foundry dropdown selections"):
            for key in studio_keys:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    # Initialize session state for persistent selections with unique keys
    if 'studio2foundry_selected_function_app' not in st.session_state:
        st.session_state.studio2foundry_selected_function_app = "-- Select Function App --"
    if 'studio2foundry_selected_resource_group' not in st.session_state:
        st.session_state.studio2foundry_selected_resource_group = "-- Select Resource Group --"
    if 'studio2foundry_subscription_id' not in st.session_state:
        st.session_state.studio2foundry_subscription_id = get_azure_subscription()
    
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
    
    # Get Azure subscription with session state
    sub_id = st.text_input(
        "Subscription ID", 
        value=st.session_state.studio2foundry_subscription_id, 
        help="Azure subscription ID for your Function Apps",
        key="studio2foundry_sub_id_input"
    )
    
    # Update session state when subscription changes
    if sub_id != st.session_state.studio2foundry_subscription_id:
        st.session_state.studio2foundry_subscription_id = sub_id
        # Reset selections when subscription changes
        st.session_state.studio2foundry_selected_function_app = "-- Select Function App --"
        st.session_state.studio2foundry_selected_resource_group = "-- Select Resource Group --"
    
    if not sub_id:
        st.warning("⚠️ Please enter your Azure subscription ID to continue")
        return
    
    # List Function Apps in this subscription (cache in session state)
    func_choices_key = f"studio2foundry_func_choices_{sub_id}"
    func_map_key = f"studio2foundry_func_map_{sub_id}"
    
    if func_choices_key not in st.session_state or func_map_key not in st.session_state:
        with st.spinner("🔍 Loading Function Apps..."):
            func_choices, func_map = list_function_apps(sub_id)
            st.session_state[func_choices_key] = func_choices
            st.session_state[func_map_key] = func_map
    else:
        func_choices = st.session_state[func_choices_key]
        func_map = st.session_state[func_map_key]
    
    if not func_choices:
        st.warning("⚠️ No Function Apps found in this subscription")
        st.markdown("""
        **Options:**
        1. Create a Function App in Azure Portal
        2. Check your subscription ID
        3. Verify you have access to Function Apps in this subscription
        """)
        return
    
    # Function App selection dropdown with session state
    available_choices = ["-- Select Function App --"] + func_choices
    
    # Find current index for session state value
    try:
        current_index = available_choices.index(st.session_state.studio2foundry_selected_function_app)
    except ValueError:
        current_index = 0
        st.session_state.studio2foundry_selected_function_app = "-- Select Function App --"
    
    func_sel_lbl = st.selectbox(
        "Choose Function App",
        available_choices,
        index=current_index,
        help="Select the Azure Function App where you want to deploy the Studio2Foundry code",
        key="studio2foundry_function_app_selector"
    )
    
    # Update session state when selection changes
    if func_sel_lbl != st.session_state.studio2foundry_selected_function_app:
        st.session_state.studio2foundry_selected_function_app = func_sel_lbl
        # Reset resource group selection when function app changes
        st.session_state.studio2foundry_selected_resource_group = "-- Select Resource Group --"
    
    if func_sel_lbl == "-- Select Function App --":
        st.info("👆 Please select a Function App to continue")
        return
    
    # Get selected Function App details
    app_name, resource_group = func_map[func_sel_lbl]
    
    st.success(f"✅ Selected: **{app_name}** in resource group **{resource_group}** (Selection persisted)")
    
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
    
    # One-Click Authentication Setup
    st.subheader("🔐 One-Click Authentication Setup")
    st.markdown("**Automated setup for your Function App to access Azure AI Services**")
    
    if func_sel_lbl != "-- Select Function App --":
        app_name, resource_group = func_map[func_sel_lbl]
        
        # Resource Group Selection for Role Assignment
        st.markdown("### 🎯 Select Resource Group for Role Assignment")
        with st.spinner("🔍 Loading resource groups..."):
            rg_choices, rg_map = get_resource_groups(sub_id)
        
        if rg_choices:
            # Resource group dropdown with session state
            rg_available_choices = ["-- Select Resource Group --"] + rg_choices
            
            # Find current index for session state value
            try:
                rg_current_index = rg_available_choices.index(st.session_state.studio2foundry_selected_resource_group)
            except ValueError:
                rg_current_index = 0
                st.session_state.studio2foundry_selected_resource_group = "-- Select Resource Group --"
            
            rg_sel_lbl = st.selectbox(
                "Resource Group for Role Assignment",
                rg_available_choices,
                index=rg_current_index,
                help="Select the resource group where you want to assign the custom roles",
                key="studio2foundry_resource_group_selector"
            )
            
            # Update session state when selection changes
            if rg_sel_lbl != st.session_state.studio2foundry_selected_resource_group:
                st.session_state.studio2foundry_selected_resource_group = rg_sel_lbl
            
            if rg_sel_lbl != "-- Select Resource Group --":
                selected_rg = rg_map[rg_sel_lbl]
                st.success(f"✅ Selected resource group: **{selected_rg}** (Selection persisted)")
                
                # One-Click Setup Buttons
                st.markdown("### 🚀 Automated Setup Buttons")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("🔧 Enable Managed Identity", type="primary", help="Enable System-assigned Managed Identity"):
                        with st.spinner("Enabling Managed Identity..."):
                            success, message = enable_managed_identity(sub_id, resource_group, app_name)
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                
                with col2:
                    if st.button("🗑️ Cleanup Old Roles", help="Remove roles with GUID names and old naming"):
                        with st.spinner("Cleaning up old roles..."):
                            success, message = cleanup_old_custom_roles(sub_id)
                            if success:
                                st.success("✅ Cleanup completed!")
                                st.text(message)
                            else:
                                st.error(message)
                
                with col3:
                    if st.button("📋 Create Custom Roles", type="primary", help="Create azure-index-agentic-read and azure-index-agentic-readwrite roles"):
                        with st.spinner("Creating custom roles..."):
                            success, message = create_custom_roles(sub_id)
                            if success:
                                st.success("✅ Custom roles created!")
                                st.text(message)
                            else:
                                st.error(message)
                
                with col4:
                    if st.button("🎯 Assign Roles", type="primary", help="Assign custom roles to Function App"):
                        with st.spinner("Assigning roles..."):
                            success, message = assign_roles_to_function_app(sub_id, selected_rg, app_name)
                            if success:
                                st.success("✅ Roles assigned successfully!")
                                st.text(message)
                                st.balloons()
                            else:
                                st.error(message)
                
                # Quick Setup All-in-One
                st.markdown("### ⚡ Complete Setup (All-in-One)")
                if st.button("🚀 Complete Authentication Setup", type="primary", help="Run all authentication steps automatically"):
                    with st.spinner("Running complete authentication setup..."):
                        results = []
                        all_success = True
                        
                        # Step 1: Enable Managed Identity
                        success, message = enable_managed_identity(sub_id, resource_group, app_name)
                        results.append(f"**Step 1 - Managed Identity:** {message}")
                        if not success:
                            all_success = False
                        
                        # Step 2: Cleanup Old Roles
                        success, message = cleanup_old_custom_roles(sub_id)
                        results.append(f"**Step 2 - Cleanup:** {message}")
                        # Don't fail on cleanup errors
                        
                        # Step 3: Create Custom Roles
                        success, message = create_custom_roles(sub_id)
                        results.append(f"**Step 3 - Custom Roles:** {message}")
                        if not success:
                            all_success = False
                        
                        # Step 4: Assign Roles
                        success, message = assign_roles_to_function_app(sub_id, selected_rg, app_name)
                        results.append(f"**Step 4 - Role Assignment:** {message}")
                        if not success:
                            all_success = False
                        
                        # Show results
                        if all_success:
                            st.success("🎉 Complete authentication setup completed successfully!")
                            st.balloons()
                        else:
                            st.warning("⚠️ Some steps completed with warnings")
                        
                        for result in results:
                            st.text(result)
            else:
                st.info("👆 Please select a resource group for role assignment")
        else:
            st.error("❌ Failed to load resource groups")
    else:
        st.info("👆 Select a Function App above to setup authentication")
    st.divider()
    
    # Environment Variables Configuration
    st.subheader("🌍 Function App Environment Variables")
    
    st.markdown("""
    **🎯 Required:** Your function needs `PROJECT_ENDPOINT` to work.
    
    **🔐 Authentication:** Uses Managed Identity (setup above!)
    """)
    
    # Check local .env for PROJECT_ENDPOINT
    project_endpoint = os.getenv("PROJECT_ENDPOINT", "")
    
    # Show status
    if project_endpoint:
        st.success(f"✅ PROJECT_ENDPOINT found: `{project_endpoint}`")
    else:
        st.error("❌ PROJECT_ENDPOINT not found in local .env file")

    with st.expander("⚙️ Configure PROJECT_ENDPOINT", expanded=True):
        st.markdown("""
        **Configure your Function App PROJECT_ENDPOINT:**
        
        **Required:**
        - `PROJECT_ENDPOINT` - Your Azure AI Project endpoint
        """)
        
        if func_sel_lbl != "-- Select Function App --":
            app_name, resource_group = func_map[func_sel_lbl]
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.info(f"Will configure PROJECT_ENDPOINT in Function App: **{app_name}**")
                
                if project_endpoint:
                    st.write("**Will set:**")
                    st.write(f"- PROJECT_ENDPOINT: `{project_endpoint[:50]}...`")
                else:
                    st.warning("⚠️ PROJECT_ENDPOINT not found in local .env file")
                
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
                    if st.button("🚀 Set PROJECT_ENDPOINT", type="primary", help="Set PROJECT_ENDPOINT in the Function App"):
                        with st.spinner("Setting PROJECT_ENDPOINT..."):
                            success, message, _ = set_function_app_setting_safely(
                                app_name=app_name,
                                resource_group=resource_group,
                                setting_name="PROJECT_ENDPOINT",
                                setting_value=project_endpoint
                            )
                            
                            if success:
                                st.success("✅ PROJECT_ENDPOINT configured successfully!")
                                st.success("🔄 Your Function App will restart automatically.")
                                st.balloons()
                            else:
                                st.error(f"❌ Failed to set PROJECT_ENDPOINT: {message}")
                else:
                    st.button("🚀 Set PROJECT_ENDPOINT", disabled=True, help="PROJECT_ENDPOINT not found in local .env")
        else:
            st.info("👆 Select a Function App above to configure PROJECT_ENDPOINT")
            
        if not project_endpoint:
            st.markdown("""
            **Setup Required:**
            Add `PROJECT_ENDPOINT` to your `.env` file:
            ```
            PROJECT_ENDPOINT=https://your-ai-project-endpoint.com/api/projects/your-project
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
            {base_url}?message=%D7%9E%D7%99%20%D7%94%D7%9D%20%D7%חבר%D7%99%20%D7%95%D7%A2%D7%93%D7%AA%20%D7%94%D7%AA%D7%9E%D7%99%D7%9B%D7%95%D7%AA&agentid=asst_3NKExbfOlMe1tYTdvxi2Woxw
            
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
