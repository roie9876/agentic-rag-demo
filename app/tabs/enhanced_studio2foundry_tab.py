"""
Enhanced Studio2Foundry Tab Module
Combines AI Foundry discovery with Function App environment variable management.
"""
import streamlit as st
import os
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from azure_function_helper import (
    get_azure_subscription, 
    get_available_subscriptions,
    list_function_apps, 
    load_function_settings,
    push_function_settings
)
from services.ai_foundry_discovery import ai_foundry_discovery


def render_enhanced_studio2foundry_tab(
    session_state: Dict[str, Any],
    **kwargs
) -> None:
    """Render the Enhanced Studio2Foundry tab with AI Foundry integration."""
    st.header("🏭 Enhanced Studio2Foundry: AI Foundry to Azure Functions")
    
    st.markdown("""
    **🎯 Purpose**: Scan for AI Foundry accounts, generate PROJECT_ENDPOINT, and push it to Azure Functions 
    while preserving existing environment variables.
    """)
    
    # Initialize AI Foundry Discovery Service
    if 'ai_foundry_discovery_service' not in st.session_state:
        try:
            st.session_state.ai_foundry_discovery_service = ai_foundry_discovery
        except Exception as e:
            st.error(f"❌ Failed to initialize discovery service: {e}")
            st.session_state.ai_foundry_discovery_service = None
    
    discovery_service = st.session_state.ai_foundry_discovery_service
    
    if not discovery_service:
        st.error("❌ Discovery service not available. Cannot proceed.")
        return
    
    # =================== AZURE FUNCTION SELECTION ===================
    st.subheader("⚙️ Step 1: Select Azure Function App")
    
    subscription_id, resource_group, function_app = render_function_selection_section()
    
    # =================== AI FOUNDRY ACCOUNT DISCOVERY ===================
    st.subheader("🔍 Step 2: Discover AI Foundry Accounts")
    
    render_ai_foundry_discovery_section(discovery_service)
    
    # =================== LOAD EXISTING ENVIRONMENT VARIABLES ===================
    st.subheader("📥 Step 3: Load Existing Environment Variables")
    
    existing_env_vars = render_load_existing_env_vars_section(
        subscription_id, resource_group, function_app
    )
    
    # =================== PROJECT ENDPOINT GENERATION ===================
    st.subheader("🎯 Step 4: Generate PROJECT_ENDPOINT")
    
    project_endpoint = render_project_endpoint_generation_section()
    
    # =================== MERGE AND PUSH PROJECT_ENDPOINT ===================
    st.subheader("🚀 Step 5: Add PROJECT_ENDPOINT and Push to Azure")
    
    render_push_project_endpoint_section(
        project_endpoint, existing_env_vars, subscription_id, resource_group, function_app
    )


def render_ai_foundry_discovery_section(discovery_service) -> None:
    """Render the AI Foundry account discovery section."""
    st.info("🔎 **Account Discovery**: This will scan for AI Foundry Accounts. The subscription can be different from your Function App subscription.")
    
    # Add option to use different subscription for AI Foundry discovery
    col1, col2 = st.columns([3, 1])
    
    with col1:
        use_different_subscription = st.checkbox(
            "🔄 Use different subscription for AI Foundry discovery",
            help="Check this if your AI Foundry accounts are in a different subscription than your Function Apps",
            key="studio2foundry_different_subscription"
        )
    
    with col2:
        if st.button("🔄 Scan for AI Foundry Accounts", type="primary", key="studio2foundry_scan_accounts"):
            with st.spinner("Scanning subscriptions for AI Foundry Accounts..."):
                try:
                    if use_different_subscription:
                        # Let user choose subscription for AI Foundry discovery
                        st.info("💡 **Multi-subscription mode**: Will auto-discover or use AZURE_SUBSCRIPTION_ID for AI Foundry scanning")
                    
                    # Check if subscription ID is available from environment
                    subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
                    
                    if subscription_id and not use_different_subscription:
                        discovery_service.set_subscription(subscription_id)
                        st.info(f"💡 **Using environment subscription**: {subscription_id[:8]}... for AI Foundry discovery")
                    else:
                        # Auto-discover subscriptions
                        discovery_service._ensure_credential_initialized()
                        
                        try:
                            subscriptions = discovery_service.list_subscriptions()
                            
                            if subscriptions:
                                if use_different_subscription and len(subscriptions) > 1:
                                    # Show subscription selection
                                    subscription_options = [f"{sub['name']} ({sub['id'][:8]}...)" for sub in subscriptions]
                                    selected_idx = st.selectbox(
                                        "Select subscription for AI Foundry discovery:",
                                        range(len(subscription_options)),
                                        format_func=lambda x: subscription_options[x],
                                        key="studio2foundry_ai_subscription_selector"
                                    )
                                    selected_subscription = subscriptions[selected_idx]
                                    discovery_service.set_subscription(selected_subscription['id'])
                                    st.info(f"💡 **Selected**: {selected_subscription['name']} for AI Foundry discovery")
                                else:
                                    # Use first available subscription
                                    auto_subscription_id = subscriptions[0]['id']
                                    discovery_service.set_subscription(auto_subscription_id)
                                    st.info(f"💡 **Auto-discovery**: Using subscription '{subscriptions[0]['name'][:50]}...' ({auto_subscription_id[:8]}...)")
                            else:
                                st.error("❌ No accessible subscriptions found")
                                st.markdown("💡 **Tip**: Make sure you're logged in with `az login` and have access to at least one subscription")
                                st.stop()
                                
                        except Exception as sub_error:
                            st.error(f"❌ Failed to auto-discover subscriptions: {sub_error}")
                            st.markdown("💡 **Alternative**: Set `AZURE_SUBSCRIPTION_ID` in your `.env` file")
                            st.stop()
                    
                    # Discover AI Foundry Accounts
                    accounts = discovery_service.discover_ai_foundry_accounts()
                    if accounts:
                        st.success(f"✅ Discovery completed! Found {len(accounts)} AI Foundry Account(s).")
                    else:
                        st.warning("⚠️ No AI Foundry Accounts found. Check your subscription or permissions.")
                    
                    # Store in session state
                    st.session_state.discovered_accounts = accounts
                    st.session_state.discovered_hubs = []
                    st.session_state.discovery_errors = []
                    
                except Exception as e:
                    st.error(f"❌ Discovery failed: {e}")
                    st.session_state.discovered_accounts = []
    
    # Display discovered accounts
    if st.session_state.get('discovered_accounts'):
        accounts = st.session_state.discovered_accounts
        st.success(f"📋 **Found {len(accounts)} AI Foundry Account(s)**")
        
        for i, account in enumerate(accounts):
            with st.expander(f"🏭 **{account['name']}** ({account['location']})", expanded=(i == 0)):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Resource Group**: {account['resource_group']}")
                    st.write(f"**Location**: {account['location']}")
                    st.write(f"**SKU**: {account['sku']}")
                
                with col2:
                    st.write(f"**Kind**: {account['kind']}")
                    st.write(f"**Status**: {account['status']}")
                    st.write(f"**Type**: {account['type']}")
                
                st.markdown(f"**🔗 Account Endpoint**: `{account['endpoint']}`")
                
                # Store selected account info in session state for project endpoint generation
                st.session_state[f'account_endpoint_{i}'] = account['endpoint']
                st.session_state[f'account_name_{i}'] = account['name']
    else:
        st.info("🔍 Click 'Scan for AI Foundry Accounts' above to discover resources.")


def render_project_endpoint_generation_section() -> Optional[str]:
    """Render the project endpoint generation section."""
    if not st.session_state.get('discovered_accounts'):
        st.info("👆 Complete Step 2 to discover AI Foundry accounts first.")
        return None
    
    accounts = st.session_state.discovered_accounts
    project_endpoint = None
    
    for i, account in enumerate(accounts):
        with st.expander(f"🎯 Generate Project Endpoint for: **{account['name']}**", expanded=(i == 0)):
            st.markdown(f"**Account Endpoint**: `{account['endpoint']}`")
            
            # Project name input
            project_name = st.text_input(
                "Project Name",
                key=f"studio2foundry_project_name_{i}",
                placeholder="Enter your AI Foundry project name (e.g., agentic-rag)",
                help="This will be used to construct the PROJECT_ENDPOINT URL"
            )
            
            if project_name:
                # Generate the PROJECT_ENDPOINT
                account_hostname = account['endpoint'].replace('https://', '').replace('http://', '')
                generated_endpoint = f"https://{account_hostname}/api/projects/{project_name}"
                
                st.markdown("**Generated PROJECT_ENDPOINT:**")
                st.code(generated_endpoint)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"📋 Copy Endpoint", key=f"studio2foundry_copy_{i}"):
                        st.success("📋 Endpoint copied to clipboard!")
                
                with col2:
                    if st.button(f"✅ Use This Endpoint", key=f"studio2foundry_use_{i}"):
                        st.session_state.selected_project_endpoint = generated_endpoint
                        project_endpoint = generated_endpoint
                        st.success(f"✅ Selected PROJECT_ENDPOINT: {generated_endpoint}")
    
    # Show selected endpoint if any
    if st.session_state.get('selected_project_endpoint'):
        st.success(f"🎯 **Selected PROJECT_ENDPOINT**: `{st.session_state.selected_project_endpoint}`")
        return st.session_state.selected_project_endpoint
    
    return project_endpoint


def render_function_selection_section() -> Tuple[str, str, str]:
    """Render the Azure Function App selection section."""
    # Initialize session state for subscription selection
    if "selected_subscription" not in st.session_state:
        st.session_state.selected_subscription = ""
    if "selected_function_app" not in st.session_state:
        st.session_state.selected_function_app = "-- manual input --"

    # Get available subscriptions
    with st.spinner("🔍 Loading subscriptions..."):
        subscription_choices, subscription_map = get_available_subscriptions()
    
    subscription_id = ""
    resource_group = ""
    function_app = ""
    
    if subscription_choices:
        # Add current/default subscription to the top if available
        default_sub = get_azure_subscription()
        if default_sub:
            # Find the default subscription in the list
            default_choice = None
            for choice in subscription_choices:
                if default_sub in choice:
                    default_choice = choice
                    break
            
            if default_choice:
                # Move default to front of list
                subscription_choices.remove(default_choice)
                subscription_choices.insert(0, default_choice)
        
        # Add placeholder option
        subscription_options = ["-- Select Subscription --"] + subscription_choices
        
        # Find current selection index
        current_sub_index = 0
        if st.session_state.selected_subscription:
            try:
                current_sub_index = subscription_options.index(st.session_state.selected_subscription)
            except ValueError:
                current_sub_index = 0
        
        selected_subscription_label = st.selectbox(
            "🔹 Azure Subscription",
            subscription_options,
            index=current_sub_index,
            help="Select the Azure subscription containing your Function Apps",
            key="studio2foundry_subscription_selector"
        )
        
        # Update session state and get subscription ID
        if selected_subscription_label != "-- Select Subscription --":
            st.session_state.selected_subscription = selected_subscription_label
            subscription_id = subscription_map[selected_subscription_label]
            st.success(f"✅ Selected subscription: {selected_subscription_label}")
        else:
            st.info("👆 Please select a subscription to see Function Apps")
    else:
        st.warning("⚠️ Could not load subscriptions automatically. Using Azure CLI default or manual input.")
        # Fallback to manual input or CLI default
        cli_sub = get_azure_subscription()
        subscription_id = st.text_input("Subscription ID", cli_sub, key="studio2foundry_manual_subscription_input")

    # Function App Selection (only if subscription is selected)
    if subscription_id:
        # Cache function apps for the selected subscription
        func_cache_key = f"func_apps_{subscription_id}"
        
        if func_cache_key not in st.session_state:
            with st.spinner("🔍 Loading Function Apps..."):
                func_choices, func_map = list_function_apps(subscription_id)
                st.session_state[func_cache_key] = (func_choices, func_map)
        else:
            func_choices, func_map = st.session_state[func_cache_key]
        
        if func_choices:
            # Function App selection dropdown
            available_choices = ["-- manual input --"] + func_choices
            
            # Find current index for session state value
            current_index = 0
            if st.session_state.selected_function_app in available_choices:
                current_index = available_choices.index(st.session_state.selected_function_app)
            
            func_sel_lbl = st.selectbox(
                "🔹 Choose Function App",
                available_choices,
                index=current_index,
                help="Select the Function App to configure",
                key="studio2foundry_function_app_selector"
            )
            
            # Update session state when selection changes
            st.session_state.selected_function_app = func_sel_lbl
            
            if func_sel_lbl != "-- manual input --":
                function_app, resource_group, hostname = func_map[func_sel_lbl]
                # Store in session state
                st.session_state["current_rg"] = resource_group
                st.session_state["current_app"] = function_app
                st.session_state["current_hostname"] = hostname
                st.success(f"✅ Selected: **{function_app}** in resource group **{resource_group}**")
            else:
                resource_group = st.text_input("Resource Group", 
                                             value=st.session_state.get("current_rg", os.getenv("AZURE_RG", "")),
                                             key="studio2foundry_manual_rg_input")
                function_app = st.text_input("Function App name", 
                                          value=st.session_state.get("current_app", os.getenv("AZURE_FUNCTION_APP", "")),
                                          key="studio2foundry_manual_app_input")
                # Update session state
                st.session_state["current_rg"] = resource_group
                st.session_state["current_app"] = function_app
        else:
            st.warning("⚠️ No Function Apps found in selected subscription")
            # Manual input fallback
            resource_group = st.text_input("Resource Group", 
                                         value=st.session_state.get("current_rg", os.getenv("AZURE_RG", "")),
                                         key="studio2foundry_manual_rg_fallback")
            function_app = st.text_input("Function App name", 
                                      value=st.session_state.get("current_app", os.getenv("AZURE_FUNCTION_APP", "")),
                                      key="studio2foundry_manual_app_fallback")
            st.session_state["current_rg"] = resource_group
            st.session_state["current_app"] = function_app
    else:
        # No subscription selected, show info message
        st.info("👆 Select a subscription above to see Function Apps")

    return subscription_id, resource_group, function_app


def render_load_existing_env_vars_section(
    subscription_id: str, 
    resource_group: str, 
    function_app: str
) -> Dict[str, str]:
    """Render the load existing environment variables section."""
    existing_env_vars = {}
    
    if not all((subscription_id, resource_group, function_app)):
        st.info("👆 Complete Step 1 to select a Function App first.")
        return existing_env_vars
    
    st.info(f"📥 **Function App**: {function_app} in resource group {resource_group}")
    
    # Initialize session state for existing environment variables
    if "existing_func_raw" not in st.session_state:
        st.session_state.existing_func_raw = {}
    
    if st.button("🔄 Load Existing Environment Variables", type="secondary", key="studio2foundry_load_env_vars"):
        with st.spinner("Loading existing environment variables from Azure Function..."):
            try:
                # Load existing settings from Azure Function (without any local .env merging)
                # We'll use an empty env_vars dict to get only the Function App settings
                empty_env_vars = {}
                success, df, raw, error_msg = load_function_settings(
                    resource_group, function_app, subscription_id, empty_env_vars
                )
                
                if success:
                    st.session_state.existing_func_raw = raw
                    existing_env_vars = raw
                    st.success(f"✅ Loaded {len(raw)} existing environment variables from Function App")
                    
                    # Show loaded variables in an expander
                    with st.expander(f"📋 Existing Environment Variables ({len(raw)} items)", expanded=False):
                        if raw:
                            for key, value in raw.items():
                                # Mask sensitive values for display
                                if any(sensitive in key.lower() for sensitive in ['key', 'secret', 'password', 'token']):
                                    display_value = "••••••••"
                                else:
                                    display_value = value[:50] + "..." if len(value) > 50 else value
                                st.write(f"- `{key}`: {display_value}")
                        else:
                            st.write("No environment variables found.")
                else:
                    st.error(f"❌ Failed to load existing environment variables: {error_msg}")
                    
            except Exception as e:
                st.error(f"❌ Error loading environment variables: {e}")
    
    # Show currently loaded variables if any
    if st.session_state.get("existing_func_raw"):
        existing_env_vars = st.session_state.existing_func_raw
        st.info(f"📊 **Currently loaded**: {len(existing_env_vars)} environment variables")
        
        # Check if PROJECT_ENDPOINT already exists
        if "PROJECT_ENDPOINT" in existing_env_vars:
            current_value = existing_env_vars["PROJECT_ENDPOINT"]
            st.warning(f"⚠️ **PROJECT_ENDPOINT already exists**: `{current_value}`")
            st.markdown("💡 The new PROJECT_ENDPOINT will **replace** the existing value.")
    
    return existing_env_vars


def render_push_project_endpoint_section(
    project_endpoint: Optional[str],
    existing_env_vars: Dict[str, str],
    subscription_id: str,
    resource_group: str,
    function_app: str
) -> None:
    """Render the push PROJECT_ENDPOINT section."""
    if not project_endpoint:
        st.info("👆 Complete Step 4 to generate a PROJECT_ENDPOINT first.")
        return
    
    if not all((subscription_id, resource_group, function_app)):
        st.info("👆 Complete Step 1 to select a Function App first.")
        return
    
    if not existing_env_vars:
        st.info("👆 Complete Step 3 to load existing environment variables first.")
        return
    
    st.success(f"🎯 **Ready to push PROJECT_ENDPOINT**: `{project_endpoint}`")
    
    # Check if PROJECT_ENDPOINT already exists and handle confirmation
    is_replacement = "PROJECT_ENDPOINT" in existing_env_vars
    existing_value = existing_env_vars.get("PROJECT_ENDPOINT", "")
    
    # Prepare the updated environment variables
    updated_env_vars = existing_env_vars.copy()
    updated_env_vars["PROJECT_ENDPOINT"] = project_endpoint
    
    # Show what will be updated
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 Summary**")
        st.write(f"- **Existing variables**: {len(existing_env_vars)}")
        st.write(f"- **Total after update**: {len(updated_env_vars)}")
        if is_replacement:
            st.write("- **Action**: ⚠️ Replace existing PROJECT_ENDPOINT")
        else:
            st.write("- **Action**: ✅ Add new PROJECT_ENDPOINT")
    
    with col2:
        st.markdown("**🎯 Target Function App**")
        st.write(f"- **Name**: {function_app}")
        st.write(f"- **Resource Group**: {resource_group}")
        st.write(f"- **Subscription**: {subscription_id[:8]}...")
    
    # Show the difference
    with st.expander("🔍 Show Changes", expanded=is_replacement):
        if is_replacement:
            st.warning("**⚠️ PROJECT_ENDPOINT will be REPLACED:**")
            st.markdown("**Current Value:**")
            st.code(existing_value, language=None)
            st.markdown("**New Value:**")
            st.code(project_endpoint, language=None)
            
            # Show differences if values are different
            if existing_value != project_endpoint:
                st.error("**🚨 Values are DIFFERENT - This will overwrite the existing PROJECT_ENDPOINT!**")
            else:
                st.info("**✅ Values are identical - No actual change needed**")
        else:
            st.success("**✅ New Variable (No conflicts):**")
            st.write(f"**PROJECT_ENDPOINT**: `{project_endpoint}`")
        
        st.markdown("**All Other Variables**: Preserved unchanged")
    
    # Confirmation logic for replacement
    if is_replacement:
        st.warning("**⚠️ Confirmation Required for Replacement**")
        
        # Initialize confirmation state
        if "project_endpoint_replacement_confirmed" not in st.session_state:
            st.session_state.project_endpoint_replacement_confirmed = False
        
        # Reset confirmation if the values changed
        if st.session_state.get("last_project_endpoint") != project_endpoint:
            st.session_state.project_endpoint_replacement_confirmed = False
            st.session_state.last_project_endpoint = project_endpoint
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ I Confirm - Replace PROJECT_ENDPOINT", type="secondary", key="studio2foundry_confirm_replace"):
                st.session_state.project_endpoint_replacement_confirmed = True
                st.success("✅ Replacement confirmed! You can now push the changes.")
        
        with col2:
            if st.button("❌ Cancel - Keep Existing Value", key="studio2foundry_cancel_replace"):
                st.session_state.project_endpoint_replacement_confirmed = False
                st.info("❌ Replacement cancelled. Existing PROJECT_ENDPOINT will be preserved.")
                return
        
        # Show confirmation status
        if st.session_state.project_endpoint_replacement_confirmed:
            st.success("✅ **Replacement Confirmed** - Ready to proceed")
            can_push = True
        else:
            st.info("⏳ **Waiting for confirmation** - Click 'I Confirm' above to proceed with replacement")
            can_push = False
    else:
        # No existing PROJECT_ENDPOINT, can push directly
        can_push = True
    
    # Push button (only enabled if confirmed or no replacement needed)
    if can_push:
        if st.button("🚀 Push PROJECT_ENDPOINT to Azure Function", type="primary", key="studio2foundry_push_endpoint"):
            with st.spinner("Pushing PROJECT_ENDPOINT to Azure Function App..."):
                try:
                    # Convert to DataFrame format expected by push_function_settings
                    # Create a DataFrame with key-value pairs
                    df_data = [{"key": key, "value": value} for key, value in updated_env_vars.items()]
                    df = pd.DataFrame(df_data)
                    
                    # Use the push_function_settings function
                    success, message = push_function_settings(
                        resource_group, function_app, subscription_id, df
                    )
                    
                    if success:
                        st.success("✅ PROJECT_ENDPOINT successfully pushed to Azure Function App!")
                        st.balloons()
                        
                        # Update session state
                        st.session_state.existing_func_raw = updated_env_vars
                        
                        # Reset confirmation state
                        st.session_state.project_endpoint_replacement_confirmed = False
                        
                        # Show success details
                        with st.expander("✅ Success Details", expanded=True):
                            st.write(f"**✅ Updated Function App**: {function_app}")
                            st.write(f"**✅ Total Environment Variables**: {len(updated_env_vars)}")
                            st.write(f"**✅ PROJECT_ENDPOINT**: `{project_endpoint}`")
                            if is_replacement:
                                st.write(f"**✅ Action**: Replaced existing PROJECT_ENDPOINT")
                            else:
                                st.write(f"**✅ Action**: Added new PROJECT_ENDPOINT")
                            st.markdown("**✅ Status**: All existing environment variables preserved")
                    else:
                        st.error(f"❌ Failed to push PROJECT_ENDPOINT: {message}")
                        
                except Exception as e:
                    st.error(f"❌ Error pushing PROJECT_ENDPOINT: {e}")
                    st.write("**Debug Information:**")
                    st.write(f"- Function App: {function_app}")
                    st.write(f"- Resource Group: {resource_group}")
                    st.write(f"- Subscription: {subscription_id}")
                    st.write(f"- PROJECT_ENDPOINT: {project_endpoint}")
                    st.write(f"- Total variables to push: {len(updated_env_vars)}")
    else:
        st.button("🚀 Push PROJECT_ENDPOINT to Azure Function", disabled=True, help="Confirm replacement above first", key="studio2foundry_push_endpoint_disabled")


# Helper function to render the tab (for main app integration)
def render_studio2foundry_tab() -> None:
    """Main entry point for the enhanced studio2foundry tab."""
    render_enhanced_studio2foundry_tab(
        session_state=st.session_state
    )
