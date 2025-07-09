"""
Function Config Tab Module
"""
import streamlit as st
import pandas as pd
import os
import urllib.parse
from typing import Dict, Any, Tuple, Optional
from azure_function_helper import (
    get_azure_subscription, 
    get_available_subscriptions,
    list_function_apps, 
    load_function_settings,
    push_function_settings,
    deploy_function_code,
    assign_search_rbac_roles,
    assign_openai_rbac_roles,
    assign_all_rbac_roles,
    generate_test_function_url
)
from utils.file_utils import _st_data_editor


def render_function_config_tab(
    session_state: Dict[str, Any],
    **kwargs
) -> None:
    """Render the Function Config tab."""
    st.header("⚙️ Azure Function Configuration")
    
    # Load environment variables (raw values - let azure_function_helper.py handle the mapping)
    env_vars = {}
    
    # Get raw environment values and pass them directly to azure_function_helper.py
    raw_env_keys = [
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_OPENAI_ENDPOINT", 
        "AZURE_OPENAI_ENDPOINT_41",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_DEPLOYMENT_41", 
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT",
        "MAX_OUTPUT_SIZE",
        "RERANKER_THRESHOLD",
        "TOP_K", 
        "debug",
        "includesrc",
        # Legacy keys for fallback
        "AZURE_OPENAI_KEY",
        "AZURE_OPENAI_KEY_41",
        "AZURE_SEARCH_KEY"
    ]
    
    # Load raw environment variables
    for key in raw_env_keys:
        value = os.getenv(key, "")
        if value:  # Only include non-empty values
            env_vars[key] = value
    
    # Debug: Show what environment variables we loaded
    print(f"DEBUG Function Config Tab: Loaded {len(env_vars)} environment variables:")
    for key, value in env_vars.items():
        # Mask sensitive values for logging
        display_value = "••••••" if "key" in key.lower() else value[:30] + "..." if len(value) > 30 else value
        print(f"DEBUG Function Config Tab:   {key}: {display_value}")

    st.markdown("Configure environment variables for Azure Function deployment.")
    
    # Add information about managed identity
    st.info("💡 **Managed Identity Configuration**: This setup prioritizes managed identity authentication. "
            "API keys (AZURE_OPENAI_KEY, AZURE_SEARCH_KEY) are optional fallback credentials.")
    
    with st.expander("🔧 Managed Identity Setup Guide", expanded=False):
        st.markdown("""
        **Prerequisites for Managed Identity:**
        1. **Function App Identity**: Enable system-assigned managed identity on your Function App
        2. **RBAC Roles Required**:
           - **Azure AI Search**: `Search Index Data Contributor` + `Search Service Contributor` 
           - **Azure OpenAI**: `Cognitive Services OpenAI User`
        3. **Environment Variables**: Only endpoint URLs and deployment names are required
        
        **Benefits:**
        - ✅ No API keys to manage or rotate
        - ✅ Enhanced security with Azure RBAC
        - ✅ Automatic credential management
        - ✅ Fallback to API keys for development/testing
        """)

    # Index selection for function config
    index_options = st.session_state.get("available_indexes", [])
    if index_options:
        # Pre‑select value from .env if present
        try:
            preselect = index_options.index(env_vars.get("INDEX_NAME", index_options[0]))
        except ValueError:
            preselect = 0
        idx_selected = st.selectbox("INDEX_NAME", index_options, index=preselect)
    else:
        st.warning("No index list detected – enter manually.")
        idx_selected = st.text_input("INDEX_NAME", env_vars.get("INDEX_NAME", ""))

    # Update env_vars with the chosen/typed value
    env_vars["INDEX_NAME"] = idx_selected.strip()
    env_vars["AGENT_NAME"] = f"{idx_selected.strip()}-agent" if idx_selected else ""

    # Display the derived AGENT_NAME (read‑only)
    st.text_input("AGENT_NAME", env_vars["AGENT_NAME"], disabled=True)

    # Subscription Selection
    st.divider()
    st.subheader("🎯 Azure Subscription & Function App Selection")
    
    # Initialize session state for subscription selection
    if "selected_subscription" not in st.session_state:
        st.session_state.selected_subscription = ""
    if "selected_function_app" not in st.session_state:
        st.session_state.selected_function_app = "-- manual input --"

    # Get available subscriptions
    with st.spinner("🔍 Loading subscriptions..."):
        subscription_choices, subscription_map = get_available_subscriptions()
    
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
            key="subscription_selector"
        )
        
        # Update session state and get subscription ID
        if selected_subscription_label != "-- Select Subscription --":
            st.session_state.selected_subscription = selected_subscription_label
            sub_id = subscription_map[selected_subscription_label]
            st.success(f"✅ Selected subscription: {selected_subscription_label}")
        else:
            sub_id = ""
            st.info("👆 Please select a subscription to see Function Apps")
    else:
        st.warning("⚠️ Could not load subscriptions automatically. Using Azure CLI default or manual input.")
        # Fallback to manual input or CLI default
        cli_sub = get_azure_subscription()
        sub_id = st.text_input("Subscription ID", cli_sub)

    # Function App Selection (only if subscription is selected)
    if sub_id:
        # Cache function apps for the selected subscription
        func_cache_key = f"func_apps_{sub_id}"
        
        if func_cache_key not in st.session_state:
            with st.spinner("🔍 Loading Function Apps..."):
                func_choices, func_map = list_function_apps(sub_id)
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
                key="function_app_selector"
            )
            
            # Update session state when selection changes
            st.session_state.selected_function_app = func_sel_lbl
            
            if func_sel_lbl != "-- manual input --":
                app, rg, hostname = func_map[func_sel_lbl]
                # Store in session state to prevent resets
                st.session_state["current_rg"] = rg
                st.session_state["current_app"] = app
                st.session_state["current_hostname"] = hostname
                st.success(f"✅ Selected: **{app}** in resource group **{rg}**")
            else:
                rg = st.text_input("Resource Group", 
                                 value=st.session_state.get("current_rg", os.getenv("AZURE_RG", "")),
                                 key="manual_rg_input")
                app = st.text_input("Function App name", 
                                  value=st.session_state.get("current_app", os.getenv("AZURE_FUNCTION_APP", "")),
                                  key="manual_app_input")
                # Update session state
                st.session_state["current_rg"] = rg
                st.session_state["current_app"] = app
        else:
            st.warning("⚠️ No Function Apps found in selected subscription")
            # Manual input fallback
            rg = st.text_input("Resource Group", 
                             value=st.session_state.get("current_rg", os.getenv("AZURE_RG", "")))
            app = st.text_input("Function App name", 
                              value=st.session_state.get("current_app", os.getenv("AZURE_FUNCTION_APP", "")))
            st.session_state["current_rg"] = rg
            st.session_state["current_app"] = app
    else:
        # No subscription selected, show info message
        rg = ""
        app = ""
        st.info("👆 Select a subscription above to see Function Apps")

    # Normalize variable names (func_name / func_rg) and keep old aliases
    func_name = app
    func_rg = rg

    # Settings loading and editing section
    if not all((sub_id, rg, app)):
        st.info("Fill subscription / RG / Function-App and click 🔄 Load settings.")
    else:
        if "func_raw" not in st.session_state:
            st.session_state.func_raw = {}
        if "func_df" not in st.session_state:
            st.session_state.func_df = pd.DataFrame(columns=["key", "value"])

        if st.button("🔄 Load settings"):
            with st.spinner("Loading Function App settings..."):
                # Create UI overrides dict with user selections that should always take precedence
                ui_overrides = {
                    "INDEX_NAME": idx_selected.strip() if idx_selected else "",
                    "AGENT_NAME": f"{idx_selected.strip()}-agent" if idx_selected else ""
                }
                
                success, df, raw, error_msg = load_function_settings(rg, app, sub_id, env_vars, ui_overrides)
                if success:
                    st.session_state.func_raw = raw
                    st.session_state.func_df = df
                    st.success(f"Loaded & merged {len(df)} setting(s).")
                    
                    # Debug information
                    with st.expander("🔍 Debug: Loaded Settings", expanded=False):
                        st.write("**UI Overrides (always applied):**")
                        for key, value in ui_overrides.items():
                            if value:
                                st.write(f"- `{key}`: {value}")
                        
                        st.write("**Environment variables mapped:**")
                        for key, value in env_vars.items():
                            if value:
                                display_value = value[:50] + "..." if len(value) > 50 else value
                                # Mask sensitive values
                                if "key" in key.lower() or "secret" in key.lower():
                                    display_value = "••••••"
                                st.write(f"- `{key}`: {display_value}")
                        
                        st.write(f"**Function App settings loaded:** {len(raw)} items")
                        st.write(f"**Final merged settings:** {len(df)} items")
                else:
                    st.error(f"Failed to load: {error_msg}")
                    
                    # Show debug info on failure
                    st.write("**Debug Information:**")
                    st.write(f"- Resource Group: `{rg}`")
                    st.write(f"- Function App: `{app}`") 
                    st.write(f"- Subscription: `{sub_id}`")
                    st.write(f"- Environment variables provided: {len([k for k, v in env_vars.items() if v])}")
                    
                    # Show available env vars (masked)
                    with st.expander("Available Environment Variables", expanded=False):
                        for key, value in env_vars.items():
                            if value:
                                display_value = "••••••" if "key" in key.lower() else value[:30] + "..."
                                st.write(f"- `{key}`: {display_value}")

    # Show editable table on every render once loaded
    if st.session_state.get("func_df") is not None and not st.session_state.func_df.empty:
        st.markdown("#### Function App Settings")
        st.session_state.func_df = _st_data_editor(
            st.session_state.func_df,
            num_rows="dynamic",
            use_container_width=True,
            key="func_editor",
        )

        # Push edited settings back to the Function App
        st.divider()
        if st.button("💾 Push settings to Function"):
            success, message = push_function_settings(
                func_rg, 
                func_name, 
                sub_id, 
                st.session_state.func_df,
                st.session_state.func_raw
            )
            if success:
                st.success(f"✅ {message} on **{func_name}**")
                st.balloons()
            else:
                st.error(f"Failed to update Function settings:\n{message}")

        # Deploy local ./function code to this Function App
        st.divider()
        if st.button("🚀 Deploy local code to Function"):
            with st.spinner("⏳ Zipping and deploying, please wait…"):
                success, message, stdout = deploy_function_code(func_rg, func_name, sub_id)
                if success:
                    st.success(f"✅ {message}")
                    if stdout:
                        st.text(stdout)
                else:
                    st.error(message)
                    
                    # Check if it's an SSL certificate error and provide helpful instructions
                    if any(ssl_term in message.lower() for ssl_term in ['ssl', 'certificate', 'tls', 'hostname']):
                        st.warning("🔧 **SSL Certificate Issue Detected**")
                        st.markdown("""
                        This error commonly occurs in private network environments. Here are your options:
                        
                        **Option 1: Manual Deployment Script**
                        ```bash
                        cd /home/azureuser/agentic-rag-demo
                        python3 scripts/manual_function_deploy.py "{}" "{}"
                        ```
                        
                        **Option 2: Azure Portal Deployment**
                        1. Zip the `./function` folder manually
                        2. Go to Azure Portal → Function App → Deployment Center
                        3. Upload the zip file directly
                        
                        **Option 3: Network Configuration**
                        - Contact your network administrator about Azure certificate trust
                        - Configure proxy settings to trust Azure certificates
                        """.format(func_rg, func_name))
                        
                        # Provide a download link for the function code
                        st.info("💡 **Quick Solution**: Download the function code as a zip file and upload it manually via Azure Portal")

        # RBAC Configuration for Azure AI Search
        st.divider()
        st.subheader("🔐 Azure AI Search RBAC Configuration")
        st.markdown("Configure managed identity permissions for Azure AI Search access.")
        
        # Get Azure Search service name from environment variables
        search_service_name = env_vars.get("SERVICE_NAME", "")
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
        
        if search_service_name or search_endpoint:
            if not search_service_name and search_endpoint:
                # Extract service name from endpoint if not already extracted
                import re
                match = re.search(r'https://([^.]+)\.search\.windows\.net', search_endpoint)
                if match:
                    search_service_name = match.group(1)
            
            if search_service_name:
                st.info(f"🔍 **Target Azure AI Search Service**: `{search_service_name}`")
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown("""
                    **Required RBAC Roles:**
                    - 🔹 **Search Index Data Contributor** - Allows reading, writing, and deleting search index data
                    - 🔹 **Search Service Contributor** - Allows managing search services and indexes
                    
                    This will enable the Function App's managed identity to access Azure AI Search without API keys.
                    """)
                
                with col2:
                    if st.button("🔐 Assign RBAC Roles", help="Assign required roles to Function App managed identity"):
                        with st.spinner("🔄 Configuring RBAC roles for Azure AI Search..."):
                            success, message = assign_search_rbac_roles(
                                subscription_id=sub_id,
                                function_app_name=func_name,
                                resource_group=func_rg,
                                search_service_name=search_service_name
                            )
                            
                            if success:
                                st.success(f"✅ {message}")
                                st.balloons()
                                st.info("🔄 **Next Steps**: The Function App can now access Azure AI Search using managed identity!")
                            else:
                                st.error(f"❌ Failed to assign RBAC roles: {message}")
                                
                                # Provide manual instructions
                                st.warning("🔧 **Manual RBAC Assignment Required**")
                                st.markdown(f"""
                                **Manual Steps via Azure Portal:**
                                1. Go to [Azure Portal](https://portal.azure.com)
                                2. Navigate to Azure AI Search service: `{search_service_name}`
                                3. Go to **Access control (IAM)** → **Add role assignment**
                                4. Assign these roles to Function App `{func_name}`:
                                   - **Search Index Data Contributor**
                                   - **Search Service Contributor**
                                
                                **Or use Azure CLI:**
                                ```bash
                                # Get Function App principal ID
                                PRINCIPAL_ID=$(az functionapp identity show --name {func_name} --resource-group {func_rg} --query principalId -o tsv)
                                
                                # Get Search service resource ID
                                SEARCH_ID=$(az search service show --name {search_service_name} --resource-group {func_rg} --query id -o tsv)
                                
                                # Assign roles
                                az role assignment create --assignee $PRINCIPAL_ID --role "Search Index Data Contributor" --scope $SEARCH_ID
                                az role assignment create --assignee $PRINCIPAL_ID --role "Search Service Contributor" --scope $SEARCH_ID
                                ```
                                """)
            else:
                st.warning("⚠️ Could not determine Azure AI Search service name from configuration.")
        else:
            st.warning("⚠️ Azure AI Search endpoint not configured. Please set AZURE_SEARCH_ENDPOINT environment variable.")

        # RBAC Configuration for Azure OpenAI
        st.divider()
        st.subheader("🤖 Azure OpenAI RBAC Configuration")
        st.markdown("Configure managed identity permissions for Azure OpenAI access.")
        
        # Get Azure OpenAI service name from environment variables (use env_vars dict instead of os.getenv)
        openai_endpoint = (
            env_vars.get("AZURE_OPENAI_ENDPOINT_41", "") or 
            env_vars.get("AZURE_OPENAI_ENDPOINT", "") or
            os.getenv("AZURE_OPENAI_ENDPOINT_41", "") or 
            os.getenv("AZURE_OPENAI_ENDPOINT", "")
        )
        openai_service_name = ""
        
        if openai_endpoint:
            # Extract service name from endpoint
            import re
            match = re.search(r'https://([^.]+)\.openai\.azure\.com', openai_endpoint)
            if match:
                openai_service_name = match.group(1)
        
        if openai_service_name:
            st.info(f"🤖 **Target Azure OpenAI Service**: `{openai_service_name}`")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown("""
                **Required RBAC Role:**
                - 🔹 **Cognitive Services OpenAI User** - Allows reading and using Azure OpenAI models
                
                This will enable the Function App's managed identity to access Azure OpenAI without API keys.
                """)
            
            with col2:
                if st.button("🤖 Assign OpenAI RBAC", help="Assign required role to Function App managed identity", key="openai_rbac"):
                    with st.spinner("🔄 Configuring RBAC roles for Azure OpenAI..."):
                        success, message = assign_openai_rbac_roles(
                            subscription_id=sub_id,
                            function_app_name=func_name,
                            resource_group=func_rg,
                            openai_service_name=openai_service_name
                        )
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.balloons()
                            st.info("🔄 **Next Steps**: The Function App can now access Azure OpenAI using managed identity!")
                        else:
                            st.error(f"❌ Failed to assign Azure OpenAI RBAC role: {message}")
                            
                            # Provide manual instructions
                            st.warning("🔧 **Manual RBAC Assignment Required**")
                            st.markdown(f"""
                            **Manual Steps via Azure Portal:**
                            1. Go to [Azure Portal](https://portal.azure.com)
                            2. Navigate to Azure OpenAI service: `{openai_service_name}`
                            3. Go to **Access control (IAM)** → **Add role assignment**
                            4. Assign this role to Function App `{func_name}`:
                               - **Cognitive Services OpenAI User**
                            
                            **Or use Azure CLI:**
                            ```bash
                            # Get Function App principal ID
                            PRINCIPAL_ID=$(az functionapp identity show --name {func_name} --resource-group {func_rg} --query principalId -o tsv)
                            
                            # Get OpenAI service resource ID
                            OPENAI_ID=$(az cognitiveservices account show --name {openai_service_name} --resource-group {func_rg} --query id -o tsv)
                            
                            # Assign role
                            az role assignment create --assignee $PRINCIPAL_ID --role "Cognitive Services OpenAI User" --scope $OPENAI_ID
                            ```
                            """)
        else:
            # Show debug information to help understand why OpenAI section is not showing
            st.warning("⚠️ Azure OpenAI endpoint not configured or could not extract service name.")
            
            with st.expander("🔍 Debug: OpenAI Configuration", expanded=False):
                st.write("**Environment Variables Checked:**")
                st.write(f"- `AZURE_OPENAI_ENDPOINT`: `{env_vars.get('AZURE_OPENAI_ENDPOINT', 'Not found')}`")
                st.write(f"- `AZURE_OPENAI_ENDPOINT_41`: `{env_vars.get('AZURE_OPENAI_ENDPOINT_41', 'Not found')}`")
                st.write(f"- OS env `AZURE_OPENAI_ENDPOINT`: `{os.getenv('AZURE_OPENAI_ENDPOINT', 'Not found')}`")
                st.write(f"- OS env `AZURE_OPENAI_ENDPOINT_41`: `{os.getenv('AZURE_OPENAI_ENDPOINT_41', 'Not found')}`")
                st.write(f"**Detected endpoint**: `{openai_endpoint}`")
                st.write(f"**Extracted service name**: `{openai_service_name}`")
                
                st.markdown("""
                **To fix this:**
                1. Set `AZURE_OPENAI_ENDPOINT` or `AZURE_OPENAI_ENDPOINT_41` in your `.env` file
                2. Format should be: `https://your-service-name.openai.azure.com/`
                3. Reload the settings after updating the `.env` file
                """)
        
        # Combined RBAC Configuration
        if search_service_name and openai_service_name:
            st.divider()
            st.subheader("⚡ Quick Setup: Assign All RBAC Roles")
            st.markdown("Configure both Azure AI Search and Azure OpenAI permissions at once.")
            
            if st.button("🚀 Assign All RBAC Roles", help="Assign all required roles for both services", key="all_rbac"):
                with st.spinner("🔄 Configuring all RBAC roles..."):
                    success, message = assign_all_rbac_roles(
                        subscription_id=sub_id,
                        function_app_name=func_name,
                        resource_group=func_rg,
                        search_service_name=search_service_name,
                        openai_service_name=openai_service_name
                    )
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                        st.info("🎉 **All Done!** Your Function App is now configured for managed identity access to both services!")
                    else:
                        st.error(f"⚠️ {message}")

        # Test URL Generation Section
        st.divider()
        st.subheader("🧪 Test Function URL Generator")
        st.markdown("Generate a test URL to verify your Azure Function is working correctly.")
        
        if not all((sub_id, rg, app)):
            st.info("ℹ️ Configure Function App details above to generate test URLs")
        else:
            # Get function key from .env file as fallback
            env_func_key = os.getenv("AGENT_FUNC_KEY", "")
            
            # Get function key from loaded settings if available
            loaded_func_key = ""
            if "func_raw" in st.session_state and st.session_state.func_raw:
                loaded_func_key = st.session_state.func_raw.get("AGENT_FUNC_KEY", "")
            
            # Prefer loaded key over env key
            default_key = loaded_func_key if loaded_func_key else env_func_key
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Test message input (used as path param)
                test_message = st.text_area(
                    "Test Message (Path Parameter)",
                    value="מי הם חברי ועדת התמיכות",  # Hebrew test message like in your example
                    height=100,
                    help="Enter a message to test your function with (will be used as the path parameter)"
                )
                # Function name
                function_name = st.text_input(
                    "Function Name",
                    value="AgentFunction",
                    help="The name of your Azure Function"
                )
            
            with col2:
                # Function key input with better default
                test_func_key = st.text_input(
                    "Function Key",
                    value=default_key,
                    type="password",
                    help="Function key for authentication. Will attempt to retrieve from Azure if empty."
                )
                
                # Add option to retrieve key from Azure
                if st.button("🔑 Get Key from Azure", help="Retrieve function key from Azure", key="get_key"):
                    with st.spinner("🔄 Retrieving function key from Azure..."):
                        from azure_function_helper import get_function_url_and_key
                        success, _, azure_key, error_msg = get_function_url_and_key(
                            sub_id, rg, app, function_name
                        )
                        if success and azure_key:
                            st.session_state["retrieved_func_key"] = azure_key
                            st.success("✅ Function key retrieved from Azure!")
                            st.rerun()
                        else:
                            st.warning(f"⚠️ Could not retrieve function key: {error_msg}")
                
                # Use retrieved key if available
                if "retrieved_func_key" in st.session_state:
                    test_func_key = st.session_state["retrieved_func_key"]
            
            col1_gen, col2_gen = st.columns([1, 1])
            
            with col1_gen:
                if st.button("🔗 Generate Smart URL", help="Generate URL using actual Azure Function details"):
                    if test_message.strip():
                        with st.spinner("🔄 Getting actual Function URL from Azure..."):
                            success, test_url, error_msg = generate_test_function_url(
                                subscription_id=sub_id,
                                resource_group=rg,
                                function_app_name=app,
                                test_message=test_message,
                                function_name=function_name,
                                fallback_function_key=test_func_key
                            )
                            
                            if success:
                                st.success("✅ Smart Test URL Generated!")
                                st.markdown("**Copy this URL to test your function:**")
                                st.code(test_url, language="text")
                                st.markdown("**Or use this curl command:**")
                                st.code(f'curl "{test_url}"', language="bash")
                                
                                # Show URL breakdown
                                with st.expander("🔍 URL Breakdown", expanded=False):
                                    import urllib.parse
                                    parsed = urllib.parse.urlparse(test_url)
                                    st.write(f"**Host**: {parsed.netloc}")
                                    st.write(f"**Path**: {parsed.path}")
                                    if parsed.query:
                                        params = urllib.parse.parse_qs(parsed.query)
                                        st.write("**Query Parameters**:")
                                        for key, values in params.items():
                                            if key == "code":
                                                st.write(f"  - {key}: ••••••")
                                            else:
                                                st.write(f"  - {key}: {values[0]}")
                            else:
                                st.error(f"❌ Failed to generate URL: {error_msg}")
                    else:
                        st.warning("⚠️ Please enter a test message first")
            
            with col2_gen:
                if st.button("📋 Generate Simple URL", help="Generate URL using simple pattern (may not work)"):
                    if test_message.strip():
                        # Fallback to simple URL generation
                        encoded_message = urllib.parse.quote(test_message, safe="")
                        simple_url = f"https://{app}.azurewebsites.net/api/{function_name}/{encoded_message}"
                        
                        # Add query parameters
                        query_params = []
                        if test_func_key:
                            query_params.append(f"code={test_func_key}")
                        query_params.append("includesrc=true")
                        
                        if query_params:
                            simple_url += "?" + "&".join(query_params)
                        
                        st.warning("⚠️ Simple URL Generated (may not work with complex hostnames)")
                        st.markdown("**Simple URL:**")
                        st.code(simple_url, language="text")
                        st.info("💡 **Note**: This uses a simple hostname pattern. Use 'Generate Smart URL' for the actual Azure Function URL.")
                    else:
                        st.warning("⚠️ Please enter a test message first")
            
            # Additional testing information
            st.info("""
            **💡 Testing Tips:**
            - **Smart URL**: Retrieves the actual Function URL and key from Azure (recommended)
            - **Simple URL**: Uses basic pattern (may not work if your Function App has complex hostname)
            - Copy the URL/command and run it in a browser or terminal
            - Check that your function returns a proper response
            - Monitor Azure Function logs for any errors
            - Verify that managed identity and search index are configured correctly
            """)
