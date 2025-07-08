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
    deploy_function_code
)
from utils.file_utils import _st_data_editor


def render_function_config_tab(
    session_state: Dict[str, Any],
    **kwargs
) -> None:
    """Render the Function Config tab."""
    st.header("⚙️ Azure Function Configuration")
    
    # Load environment variables (updated for managed identity)
    # Map local .env variables to Function App settings
    local_to_function_mapping = {
        # INDEX_NAME will be set from UI selection below - not from .env
        "AGENT_NAME": "AGENT_NAME", 
        "AZURE_SEARCH_ENDPOINT": "SERVICE_NAME",  # Extract service name from endpoint
        "AZURE_OPENAI_ENDPOINT": "OPENAI_ENDPOINT",
        "AZURE_OPENAI_ENDPOINT_41": "OPENAI_ENDPOINT",  # Support _41 suffix (preferred)
        "AZURE_OPENAI_DEPLOYMENT": "OPENAI_DEPLOYMENT", 
        "AZURE_OPENAI_DEPLOYMENT_41": "OPENAI_DEPLOYMENT",  # Support _41 suffix (preferred)
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "OPENAI_DEPLOYMENT",  # Alternative deployment name
        # API_VERSION removed - should be empty when loading settings
        "MAX_OUTPUT_SIZE": "MAX_OUTPUT_SIZE",
        "RERANKER_THRESHOLD": "RERANKER_THRESHOLD", 
        "TOP_K": "TOP_K",
        "debug": "debug",
        "includesrc": "includesrc",
        # Legacy keys (optional for development/fallback compatibility)
        "AZURE_OPENAI_KEY": "OPENAI_KEY",
        "AZURE_OPENAI_KEY_41": "OPENAI_KEY",  # Support _41 suffix
        "AZURE_SEARCH_KEY": "SEARCH_API_KEY"
    }
    
    env_vars = {}
    for local_key, function_key in local_to_function_mapping.items():
        local_value = os.getenv(local_key, "")
        
        # Special handling for SERVICE_NAME - extract from AZURE_SEARCH_ENDPOINT
        if function_key == "SERVICE_NAME" and local_value:
            # Extract service name from https://service-name.search.windows.net
            import re
            match = re.search(r'https://([^.]+)\.search\.windows\.net', local_value)
            if match:
                env_vars[function_key] = match.group(1)
            else:
                env_vars[function_key] = ""
        else:
            # Only update if we don't have this function_key already, or if this is a _41 variant (preferred)
            if function_key not in env_vars or local_key.endswith('_41'):
                if local_value:  # Only set if there's a value
                    env_vars[function_key] = local_value

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
                success, df, raw, error_msg = load_function_settings(rg, app, sub_id, env_vars)
                if success:
                    st.session_state.func_raw = raw
                    st.session_state.func_df = df
                    st.success(f"Loaded & merged {len(df)} setting(s).")
                    
                    # Debug information
                    with st.expander("🔍 Debug: Loaded Settings", expanded=False):
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

        # Test URL Generation Section
        st.divider()
        st.subheader("🧪 Test Function URL Generator")
        st.markdown("Generate a test URL to verify your Azure Function is working correctly.")
        
        if not all((sub_id, rg, app)):
            st.info("ℹ️ Configure Function App details above to generate test URLs")
        else:
            # Get function key from settings if available
            func_key = ""
            if "func_raw" in st.session_state and st.session_state.func_raw:
                func_key = st.session_state.func_raw.get("AGENT_FUNC_KEY", "")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Test message input
                test_message = st.text_area(
                    "Test Message",
                    value="Hello, can you help me find information about Azure services?",
                    height=100,
                    help="Enter a message to test your function with"
                )
                
                # Function endpoint name
                endpoint_name = st.text_input(
                    "Function Endpoint",
                    value="agent_chat",
                    help="The name of your function endpoint (usually 'agent_chat' or 'api')"
                )
            
            with col2:
                # Function key input
                test_func_key = st.text_input(
                    "Function Key (Optional)",
                    value=func_key,
                    type="password",
                    help="Function key for authentication (if required)"
                )
                
                # URL format selection
                url_format = st.selectbox(
                    "URL Format",
                    ["Query Parameter", "JSON Body"],
                    help="How to send the message to the function"
                )
            
            if st.button("🔗 Generate Test URL"):
                if test_message.strip():
                    # Generate the test URL
                    base_url = f"https://{app}.azurewebsites.net/api/{endpoint_name}"
                    
                    if url_format == "Query Parameter":
                        # Encode the message as a query parameter
                        encoded_message = urllib.parse.quote(test_message)
                        
                        if test_func_key:
                            test_url = f"{base_url}?message={encoded_message}&code={test_func_key}"
                        else:
                            test_url = f"{base_url}?message={encoded_message}"
                        
                        st.success("✅ Test URL Generated!")
                        st.markdown("**Copy this URL to test your function:**")
                        st.code(test_url, language="text")
                        
                        # Also show curl command
                        st.markdown("**Or use this curl command:**")
                        curl_cmd = f'curl "{test_url}"'
                        st.code(curl_cmd, language="bash")
                        
                    else:  # JSON Body format
                        # For JSON body, show curl command with POST
                        if test_func_key:
                            json_url = f"{base_url}?code={test_func_key}"
                        else:
                            json_url = base_url
                        
                        st.success("✅ Test URL Generated!")
                        st.markdown("**Use this curl command to test with JSON body:**")
                        
                        json_payload = {
                            "message": test_message
                        }
                        
                        curl_cmd = f'''curl -X POST "{json_url}" \\
  -H "Content-Type: application/json" \\
  -d '{{"message": "{test_message.replace('"', '\\"')}"}}' '''
                        
                        st.code(curl_cmd, language="bash")
                        
                        st.markdown("**Or simple GET URL:**")
                        st.code(json_url, language="text")
                    
                    # Additional testing information
                    st.info("""
                    **💡 Testing Tips:**
                    - Copy the URL/command and run it in a browser or terminal
                    - Check that your function returns a proper response
                    - Monitor Azure Function logs for any errors
                    - Verify that managed identity and search index are configured correctly
                    """)
                    
                else:
                    st.warning("⚠️ Please enter a test message first")
