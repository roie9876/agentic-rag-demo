"""
Enhanced AI Foundry Tab - Full Version with Delete Tab Fix

Comprehensive UI for managing AI Foundry Accounts and agent deployment.
This version includes all original functionality while ensuring the delete tab works properly.

Features:
- 🔍 Resource Discovery: Discover AI Foundry Accounts only
- 🤖 Agent Management: Deploy and manage agents
- 🚀 Account Deployment: Deploy new AI Foundry Accounts (manual process)
- 🗑️ Delete Deployment: Safe resource group deletion
"""

import streamlit as st
import os
import traceback
import time
import datetime
import subprocess
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

def render_enhanced_ai_foundry_tab(
    session_state: Dict[str, Any],
    **kwargs
) -> None:
    """Render the enhanced AI Foundry account management tab."""
    
    # Track timing for performance monitoring - initialize at function start
    tab_start_time = time.time()
    
    st.header("🏭 AI Foundry Account Management")

    # Add important notice about supported resources
    st.info("""
    **📋 Resource Support**: 
    
    **✅ AI Foundry Accounts**: Supported for project endpoint generation and agent deployment
    
    **ℹ️ AI Foundry Accounts**: Use the Deploy New Account tab for manual account creation guidance
    
    **💡 Focus**: This tab discovers and works with AI Foundry Accounts only - NO HUBS.
    """)
        
    # Add refresh button to clear cached services
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄", help="Refresh services"):
            # Clear cached services to force refresh
            keys_to_clear = [
                'ai_foundry_discovery_service',
                'ai_foundry_rbac_service', 
                'ai_foundry_service',
                'ai_foundry_deployment_service'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("✅ Services refreshed!")
            st.rerun()
    
    st.markdown("---")
    
    # Initialize services with lazy loading to prevent blocking
    
    # Primary discovery service - initialize immediately but lightweight
    if 'ai_foundry_discovery_service' not in st.session_state:
        try:
            from services.ai_foundry_discovery import ai_foundry_discovery
            st.session_state.ai_foundry_discovery_service = ai_foundry_discovery
        except Exception as e:
            st.error(f"❌ Failed to initialize discovery service: {e}")
            st.session_state.ai_foundry_discovery_service = None
    
    discovery_service = st.session_state.ai_foundry_discovery_service
    
    # Other services - initialize only when first accessed to improve tab loading speed
    def get_rbac_service():
        if 'ai_foundry_rbac_service' not in st.session_state:
            try:
                from services.azure_rbac_manager import AzureRBACManager
                st.session_state.ai_foundry_rbac_service = AzureRBACManager()
            except Exception as e:
                st.error(f"❌ Failed to initialize RBAC service: {e}")
                st.session_state.ai_foundry_rbac_service = None
        return st.session_state.ai_foundry_rbac_service
    
    def get_ai_foundry_service():
        if 'ai_foundry_service' not in st.session_state:
            try:
                from services.ai_foundry_service import AIFoundryService
                st.session_state.ai_foundry_service = AIFoundryService()
            except Exception as e:
                st.error(f"❌ Failed to initialize AI Foundry service: {e}")
                st.session_state.ai_foundry_service = None
        return st.session_state.ai_foundry_service
    
    def get_deployment_service():
        if 'ai_foundry_deployment_service' not in st.session_state:
            try:
                from services.ai_foundry_agent_deployment import get_ai_foundry_agent_deployment_service
                st.session_state.ai_foundry_deployment_service = get_ai_foundry_agent_deployment_service()
            except Exception as e:
                st.error(f"❌ Failed to initialize deployment service: {e}")
                st.session_state.ai_foundry_deployment_service = None
        return st.session_state.ai_foundry_deployment_service
    
    # Debug information - show service status (only load services when debug is expanded)
    with st.expander("🔧 Service Debug Info", expanded=False):
        st.write("**Service Status:**")
        st.write(f"- Discovery Service: {type(discovery_service).__name__ if discovery_service else 'Not initialized'}")
        
        # Only load other services if debug is being viewed
        try:
            rbac_service = get_rbac_service()
            ai_foundry_service = get_ai_foundry_service()
            deployment_service = get_deployment_service()
            
            st.write(f"- RBAC Service: {type(rbac_service).__name__ if rbac_service else 'Not initialized'}")
            st.write(f"- AI Foundry Service: {type(ai_foundry_service).__name__ if ai_foundry_service else 'Not initialized'}")
            st.write(f"- Deployment Service: {type(deployment_service).__name__ if deployment_service else 'Not initialized'}")
        except Exception as e:
            st.write(f"- Service initialization error: {e}")
        
        st.write("**Session State Keys:**")
        relevant_keys = [k for k in st.session_state.keys() if 'ai_foundry' in k.lower() or 'discovered' in k.lower()]
        for key in sorted(relevant_keys):
            value = st.session_state[key]
            st.write(f"- {key}: {type(value).__name__}")
    
    # Setup subscription for discovery service (completely lazy to improve performance)
    subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
    
    # Store subscription ID but don't initialize clients until actually needed
    if subscription_id:
        # Just store the subscription ID, don't call set_subscription yet (avoid slow client init)
        if discovery_service and not hasattr(discovery_service, '_subscription_id'):
            discovery_service._subscription_id = subscription_id
        st.sidebar.success(f"✅ Subscription ID ready: {subscription_id[:8]}...")
    else:
        st.sidebar.info("💡 Set AZURE_SUBSCRIPTION_ID environment variable for auto-detection")
        st.sidebar.info("🔍 Or use discovery service to list subscriptions when needed")
    
    # Create tabs for different sections
    tab_deploy_hub, tab_discover, tab_delete = st.tabs([
        "🚀 Deploy New Account",
        "🔍 Discover and Deploy Agent",
        "🗑️ Delete Deployment"
    ])
    
    # Show performance info in debug section only (calculate after tabs are created)
    total_time = time.time() - tab_start_time
    if total_time > 1.0:  # Only show if tab loading took more than 1 second
        with st.expander("⏱️ Performance Info", expanded=False):
            st.text(f"Tab load time: {total_time:.3f}s")
    
    # Tab 1: Deploy Hub - with proper error handling
    with tab_deploy_hub:
        try:
            render_ai_foundry_hub_deployment_ui()
        except Exception as e:
            st.error(f"❌ ERROR in deploy hub tab: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    # Tab 2: Discover - with proper error handling
    with tab_discover:
        try:
            render_resource_discovery_section(discovery_service)
        except Exception as e:
            st.error(f"❌ ERROR in discover tab: {e}")
            import traceback
            st.code(traceback.format_exc())

    # Tab 3: Delete Deployment - CRITICAL: This must always work
    with tab_delete:
        try:
            from app.tabs.delete_deployment_tab import render_delete_deployment_tab
            render_delete_deployment_tab(
                session_state=session_state,
                **kwargs
            )
        except Exception as e:
            st.error(f"❌ ERROR in delete deployment tab: {e}")
            import traceback
            st.code(traceback.format_exc())


def render_ai_foundry_hub_deployment_ui():
    """Render the AI Foundry Hub deployment UI with lazy loading."""
    
    # Lazy loading to avoid slow initialization during tab creation
    st.subheader("🚀 Deploy New AI Foundry Account")
    
    # Add a note about lazy loading
    st.info("💡 Account deployment UI loads when first accessed to improve performance.")
    
    # Only import and initialize when user actually wants to use it
    if st.button("🔧 Initialize Account Deployment UI", type="primary"):
        with st.spinner("Loading account deployment interface..."):
            try:
                from app.components.ai_foundry_hub_deployment_ui import AIFoundryHubDeploymentUI
                ui = AIFoundryHubDeploymentUI()
                ui.render_deployment_tab()
                st.success("✅ Account deployment UI loaded!")
                # Store in session state so it doesn't reload
                st.session_state.account_ui_loaded = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to load account deployment UI: {e}")
                st.code(str(e))
                import traceback
                st.code(traceback.format_exc())
    
    # If already loaded, show the UI
    if st.session_state.get('account_ui_loaded', False):
        try:
            from app.components.ai_foundry_hub_deployment_ui import AIFoundryHubDeploymentUI
            ui = AIFoundryHubDeploymentUI()
            ui.render_deployment_tab()
        except Exception as e:
            st.error(f"❌ Error in account deployment UI: {e}")
            import traceback
            st.code(traceback.format_exc())
            # Reset the loaded state so user can try again
            st.session_state.account_ui_loaded = False
            if st.button("🔄 Retry Loading"):
                st.rerun()


def render_resource_discovery_section(discovery_service):
    """Render the AI Foundry resource discovery section."""
    
    st.subheader("🔍 Discover and Deploy Agent")
    
    st.info("🔎 **Account Discovery Only**: This will scan for AI Foundry Accounts only (NOT Hubs) in your subscription.")
    
    st.markdown("""
    **🎯 Scanning for AI Foundry ACCOUNTS:**
    - 🏢 AI Services accounts with `.services.ai.azure.com` endpoints
    - ✅ Ready for project endpoint generation  
    - 🚀 Can be used for agent deployment
    - ❌ **NOT scanning for AI Foundry Hubs**
    """)
    
    if not discovery_service:
        st.error("❌ Discovery service not initialized. Please refresh the page.")
        return
    
    if st.button("🔄 Scan for AI Foundry Accounts", type="primary"):
        with st.spinner("Scanning subscriptions for AI Foundry Accounts..."):
            try:
                # Check if subscription ID is available from environment
                subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
                
                if subscription_id:
                    # Use the configured subscription
                    discovery_service.set_subscription(subscription_id)
                else:
                    # Auto-discover subscriptions like before
                    
                    # Initialize credentials first
                    discovery_service._ensure_credential_initialized()
                    
                    # Try to discover available subscriptions using the discovery service
                    try:
                        # Use the discovery service's list_subscriptions method instead
                        subscriptions = discovery_service.list_subscriptions()
                        
                        if subscriptions:
                            # Use the first available subscription
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
                        st.code(f"Error details: {str(sub_error)}")
                        st.stop()
                
                accounts = []
                
                # Discover AI Foundry Accounts only (NO HUBS)
                accounts = discovery_service.discover_ai_foundry_accounts()
                if accounts:
                    st.success(f"✅ Discovery completed! Found {len(accounts)} AI Foundry Account(s).")
                else:
                    st.warning("⚠️ No AI Foundry Accounts found. Check your subscription or permissions.")
                
                # Store in session state - clear any hub data
                st.session_state.discovered_accounts = accounts
                st.session_state.discovered_hubs = []  # Explicitly clear - we don't discover hubs
                st.session_state.discovery_errors = []
                
                # Success message
                if accounts:
                    st.success(f"✅ Discovery completed! Found {len(accounts)} AI Foundry Account(s).")
                else:
                    st.warning("⚠️ No AI Foundry Accounts found. Check your subscription or permissions.")
                
            except Exception as e:
                st.error(f"❌ Discovery failed: {e}")
                st.code(traceback.format_exc())
                st.session_state.discovered_accounts = []
                st.session_state.discovered_hubs = []
                st.session_state.discovery_errors = [str(e)]
    
    # Display discovered resources
    accounts = getattr(st.session_state, 'discovered_accounts', [])
    
    if accounts:
        st.markdown("### 🏢 AI Foundry Accounts")
        for i, account in enumerate(accounts):
            account_name = account.get('name', 'Unknown')
            account_location = account.get('location', 'Unknown')
            account_rg = account.get('resource_group', 'Unknown')
            
            with st.expander(f"📋 {account_name} ({account_location})", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"""
                    **Name**: {account_name}
                    **Resource Group**: {account_rg}
                    **Location**: {account_location}
                    **Type**: AI Foundry Account
                    """)
                
                with col2:
                    if st.button(f"Select", key=f"select_account_{i}"):
                        st.session_state.selected_resource = account
                        st.success(f"✅ Selected: {account_name}")
                        st.rerun()
                
                # Project endpoint generation for AI Foundry Accounts
                st.markdown("#### 🔗 Generate PROJECT_ENDPOINT")
                st.info("For AI Foundry Accounts, you need to manually specify a project name to create the endpoint.")
                
                project_name = st.text_input(
                    "Project Name",
                    key=f"project_name_{i}",
                    help="Enter the name of your project (will be created if it doesn't exist)",
                    placeholder="my-project"
                )
                
                if project_name:
                    project_endpoint = f"https://{account_name}.services.ai.azure.com/api/projects/{project_name}"
                    
                    st.markdown("**Generated PROJECT_ENDPOINT:**")
                    st.code(project_endpoint)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"📋 Copy Endpoint", key=f"copy_{i}"):
                            st.success("📋 Endpoint copied to clipboard!")
                    
                    with col2:
                        if st.button(f"🚀 Use for Agent Deployment", key=f"deploy_{i}"):
                            st.session_state.deployment_endpoint = project_endpoint
                            st.session_state.ready_for_agent_deployment = True
                            st.success("✅ Ready for agent deployment! Agent deployment is available in this tab.")
                    
                    # =================== AI FOUNDRY AGENT CREATION ===================
                    st.markdown("---")
                    st.markdown("#### 🤖 Create AI Foundry Agent")
                    st.info("💡 **Deploy Azure Functions as AI Foundry Agents** - Connect your Function Apps to AI Foundry projects")
                    
                    # Initialize deployment service (lazy loading)
                    if 'ai_foundry_deployment_service' not in st.session_state:
                        try:
                            from services.ai_foundry_agent_deployment import get_ai_foundry_agent_deployment_service
                            st.session_state.ai_foundry_deployment_service = get_ai_foundry_agent_deployment_service()
                        except Exception as e:
                            st.error(f"❌ Failed to initialize deployment service: {e}")
                            st.session_state.ai_foundry_deployment_service = None
                    
                    deployment_service = st.session_state.ai_foundry_deployment_service
                    
                    if not deployment_service:
                        st.error("❌ Deployment service not available. Check service configuration.")
                        continue
                    
                    # Load Function Apps (from the main session state)
                    func_map = getattr(st.session_state, 'func_map', {})
                    func_choices = getattr(st.session_state, 'func_choices', [])
                    
                    if not func_choices:
                        st.warning("⚠️ No Function Apps found. Please go to 'Function Config' tab first to configure your Azure Functions.")
                        if st.button("🔄 Refresh Function Apps", key=f"refresh_func_{i}"):
                            # Try to load function apps
                            try:
                                from azure_function_helper import list_function_apps
                                # Get subscription_id from discovery service or environment
                                subscription_id = discovery_service.get_subscription_id() if discovery_service else None
                                if not subscription_id:
                                    subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
                                if subscription_id:
                                    func_choices_new, func_map_new = list_function_apps(subscription_id)
                                    st.session_state.func_map = func_map_new
                                    st.session_state.func_choices = func_choices_new
                                    st.success("✅ Function Apps refreshed!")
                                    st.rerun()
                                else:
                                    st.error("❌ No subscription ID available for refreshing Function Apps")
                            except Exception as e:
                                st.error(f"❌ Failed to load Function Apps: {e}")
                    else:
                        # Function App selection dropdown (like the original)
                        st.markdown("**Function App to invoke**")
                        func_sel = st.selectbox(
                            "Function App to invoke",
                            func_choices,
                            index=0,
                            key=f"func_sel_{i}",
                            label_visibility="collapsed"
                        )
                        
                        # Choose Foundry project dropdown  
                        st.markdown("**Choose Foundry project**")
                        project_display_name = f"{account_name} - {project_name} - env"
                        st.selectbox(
                            "Choose Foundry project",
                            [project_display_name],
                            index=0,
                            key=f"project_sel_{i}",
                            disabled=True,  # Only one option available
                            label_visibility="collapsed"
                        )
                        
                        # Show endpoint info
                        st.markdown("🔗 **Endpoint:**")
                        st.text(project_endpoint)
                        
                        # Agent name input
                        st.markdown("**Agent name**")
                        agent_name = st.text_input(
                            "Agent name",
                            value="function-assistant",
                            key=f"func_agent_name_{i}",
                            label_visibility="collapsed"
                        )
                        
                        # Create Agent button
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            create_button = st.button("🚀 Create Agent", key=f"create_func_agent_{i}", type="primary")
                        
                        with col2:
                            if st.button("🧪 Test OpenAPI", key=f"test_openapi_{i}", help="Test OpenAPI tool configuration"):
                                with st.spinner("Testing OpenAPI tool configuration..."):
                                    try:
                                        if deployment_service:
                                            # Get function key for testing
                                            function_key = os.getenv('AGENT_FUNC_KEY', '')
                                            if not function_key:
                                                st.error("❌ AGENT_FUNC_KEY not set - cannot test OpenAPI tool")
                                                continue
                                            
                                            # Test function app details parsing
                                            app_name, resource_group, hostname = func_map[func_sel]
                                            func_url = f"https://{hostname}/api"
                                            
                                            # Use the new comprehensive test method
                                            success, message, test_data = deployment_service.test_openapi_tool_serialization(
                                                "test_tool", func_url, function_key
                                            )
                                            
                                            if success:
                                                st.success("✅ OpenAPI tool test completed!")
                                                
                                                # Show tool properties
                                                tool_props = test_data.get("tool_properties", {})
                                                st.markdown("**🔧 Tool Properties:**")
                                                for prop, value in tool_props.items():
                                                    st.write(f"- {prop}: {value}")
                                                
                                                # Show serialization results
                                                serial_results = test_data.get("serialization_results", {})
                                                st.markdown("**📋 Serialization Test Results:**")
                                                for method, result in serial_results.items():
                                                    st.write(f"- {method}: {result}")
                                                
                                                # Recommend best approach
                                                if serial_results.get('model_dump', '').startswith('✅'):
                                                    st.success("💡 **Recommended**: model_dump() method works - agent creation should succeed")
                                                elif serial_results.get('dict_conversion', '').startswith('✅'):
                                                    st.info("💡 **Alternative**: dict conversion works - will use fallback method")
                                                else:
                                                    st.warning("⚠️ **Issue**: OpenAPI tool serialization has problems - will use basic function tools")
                                            else:
                                                st.error(f"❌ OpenAPI test failed: {message}")
                                        else:
                                            st.error("❌ Deployment service not available")
                                    except ImportError:
                                        st.error("❌ OpenAPI tools not available - will use basic function tools")
                                    except Exception as e:
                                        st.error(f"❌ OpenAPI test failed: {e}")
                                        with st.expander("🔍 Test Error Details"):
                                            st.code(str(e))
                        
                        if create_button:
                            if func_sel and agent_name:
                                # Pre-flight checks before creating agent
                                st.markdown("**🔍 Pre-flight Checks**")
                                
                                # Check 1: Azure AI SDK availability
                                try:
                                    from azure.ai.projects import AIProjectClient
                                    st.success("✅ Azure AI SDK is available")
                                    
                                    # Check for OpenAPI tools (advanced feature)
                                    try:
                                        from azure.ai.agents.models import OpenApiTool, OpenApiAnonymousAuthDetails
                                        st.success("✅ OpenAPI tools available (advanced agent features enabled)")
                                        openapi_available = True
                                    except ImportError:
                                        st.warning("⚠️ OpenAPI tools not available (will use basic function tools)")
                                        st.info("💡 **To enable OpenAPI tools:** Ensure you have the latest azure-ai-projects package")
                                        openapi_available = False
                                        
                                except ImportError:
                                    st.error("❌ Azure AI SDK not available")
                                    st.markdown("""
                                    **To fix this issue:**
                                    ```bash
                                    pip install azure-ai-projects
                                    ```
                                    """)
                                    st.stop()
                                
                                # Check 2: MODEL_DEPLOYMENT_NAME environment variable
                                model_deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME")
                                if model_deployment_name:
                                    st.success(f"✅ MODEL_DEPLOYMENT_NAME: {model_deployment_name}")
                                else:
                                    st.error("❌ MODEL_DEPLOYMENT_NAME environment variable not set")
                                    st.markdown("""
                                    **To fix this issue:**
                                    1. Add `MODEL_DEPLOYMENT_NAME=your-model-deployment-name` to your `.env` file
                                    2. The deployment name should match a deployed model in your AI Foundry project
                                    3. Common values: `gpt-4`, `gpt-35-turbo`, or your custom deployment name
                                    """)
                                    st.stop()
                                
                                # Check 3: Function App authentication key
                                function_key = os.getenv('AGENT_FUNC_KEY', '')
                                if function_key:
                                    st.success("✅ AGENT_FUNC_KEY is set")
                                else:
                                    st.error("❌ AGENT_FUNC_KEY environment variable not set")
                                    st.markdown("""
                                    **To fix this issue:**
                                    1. Get your Function App host key from the Azure portal
                                    2. Add `AGENT_FUNC_KEY=your-function-key` to your `.env` file
                                    """)
                                    st.stop()
                                
                                st.markdown("---")
                                
                                try:
                                    with st.spinner(f"Creating AI Foundry agent '{agent_name}' from Function App '{func_sel}'..."):
                                        # Get function app details - func_map returns (name, resource_group, hostname)
                                        app_name, resource_group, hostname = func_map[func_sel]
                                        func_url = f"https://{hostname}/api"
                                        
                                        # Show what type of agent is being created
                                        st.info("🔧 **Creating agent with function tools** - Using proven working implementation")
                                        
                                        # Create AI Foundry agent using the Function App
                                        success, message, agent_data = deployment_service.create_ai_foundry_agent(
                                            project_endpoint=project_endpoint,
                                            agent_name=agent_name,
                                            base_url=func_url,
                                            function_key=function_key
                                        )
                                        
                                        if success:
                                            st.success(f"✅ {message}")
                                            st.markdown("**Agent Details:**")
                                            
                                            # Show agent summary first
                                            if agent_data:
                                                st.json({
                                                    "Agent ID": agent_data.get("id"),
                                                    "Name": agent_data.get("name"),
                                                    "Model": agent_data.get("model"),
                                                    "Tool Type": agent_data.get("metadata", {}).get("tool_type", "unknown"),
                                                    "Function URL": agent_data.get("metadata", {}).get("function_url")
                                                })
                                                
                                                # Show tools info
                                                tools = agent_data.get("tools", [])
                                                if tools:
                                                    st.markdown("**🔧 Agent Tools:**")
                                                    for i, tool in enumerate(tools):
                                                        tool_type = tool.get("type", "unknown") if isinstance(tool, dict) else str(type(tool))
                                                        st.write(f"- Tool {i+1}: {tool_type}")
                                                
                                                # Expandable full details
                                                with st.expander("📋 Full Agent Configuration", expanded=False):
                                                    st.json(agent_data)
                                            else:
                                                st.info("✅ Agent created successfully (no details returned)")
                                        else:
                                            st.error(f"❌ {message}")
                                            
                                            # Add permission check button
                                            if st.button("🔍 Check My Permissions", key=f"check_perms_{i}"):
                                                check_ai_foundry_permissions(account_name, account_rg)
                                            
                                except Exception as e:
                                    st.error(f"❌ Failed to create AI Foundry agent: {str(e)}")
                                    
                                    # Specific troubleshooting for different error types
                                    error_str = str(e).lower()
                                    if "json serializable" in error_str:
                                        st.warning("🔧 **JSON Serialization Issue Detected**")
                                        st.markdown("""
                                        **This error has been fixed in the latest version.**
                                        
                                        The issue was with OpenAPI tool serialization when returning agent details.
                                        Please try creating the agent again - the fix handles OpenAPI tool serialization properly.
                                        """)
                                    elif "openapi" in error_str or "tool" in error_str:
                                        st.warning("🔧 **OpenAPI Tool Issue Detected**")
                                        st.markdown("""
                                        **Possible solutions:**
                                        
                                        1. **Update Azure AI SDK:**
                                        ```bash
                                        pip install --upgrade azure-ai-projects
                                        ```
                                        
                                        2. **Check OpenAPI tool availability:**
                                        The agent creation requires proper OpenAPI tool configuration to expose your Function App endpoints.
                                        
                                        3. **Verify Function App endpoint:**
                                        Make sure your Function App is accessible and returns a valid response.
                                        """)
                                    
                                    with st.expander("🔍 Error Details", expanded=False):
                                        st.code(traceback.format_exc())
                            else:
                                st.warning("⚠️ Please select a Function App and provide an agent name")
    else:
        if hasattr(st.session_state, 'discovered_accounts'):
            st.info("⚠️ No AI Foundry Accounts found in your subscription")
            
            # Add a demo/test section to show what the agent deployment would look like
            with st.expander("👀 Preview: Agent Deployment UI (Demo)", expanded=False):
                st.info("📝 **This is what you would see after discovering an AI account and entering a project name:**")
                
                # Demo account info
                demo_account_name = "demo-ai-services"
                demo_project_name = "my-project"
                demo_project_endpoint = f"https://{demo_account_name}.services.ai.azure.com/api/projects/{demo_project_name}"
                
                st.markdown("#### 🔗 Generate PROJECT_ENDPOINT")
                st.code(demo_project_endpoint)
                
                st.markdown("#### 🤖 Deploy Agent to This Project")
                st.markdown("**Create New Agent**")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input("Agent Name", value="my-search-agent", disabled=True)
                with col2:
                    st.selectbox("Model", ["gpt-4", "gpt-4o", "gpt-3.5-turbo"], disabled=True)
                
                st.text_area("Agent Instructions", value="You are a helpful AI assistant...", disabled=True)
                
                with st.expander("🔍 Azure Search Integration (Optional)", expanded=False):
                    st.checkbox("Enable Azure Search Integration", disabled=True)
                    st.text_input("Azure Search Endpoint", disabled=True)
                    st.text_input("Index Name", disabled=True)
                
                st.button("🚀 Deploy Agent", disabled=True, help="This would deploy the agent to your AI Foundry project")
                
                st.success("✨ **This is the agent deployment interface that appears when you:**")
                st.markdown("""
                1. ✅ Successfully discover AI Foundry Accounts
                2. ✅ Select an account 
                3. ✅ Enter a project name
                """)
                
            # Add troubleshooting section
            with st.expander("🔧 Troubleshooting: Why No Accounts Found?", expanded=True):
                st.markdown("**Possible reasons:**")
                st.markdown("""
                1. **No AI Services accounts in subscription**
                   - Create an "Azure AI Services" resource in Azure Portal
                   - Make sure it's a multi-service account (not single-service like "Text Analytics")
                
                2. **Authentication issue**
                   - Try logging in: `az login`
                   - Check managed identity permissions if running on Azure
                
                3. **Permissions issue**
                   - Ensure you have "Reader" role on the subscription
                   - Check if Azure CLI login works: `az account show`
                
                4. **Subscription access**
                   - Verify you have access to Azure subscriptions
                   - The service auto-discovers subscriptions, but you can specify one manually if needed
                """)
                
                # Show current subscription ID for debugging
                current_sub = os.getenv('AZURE_SUBSCRIPTION_ID')
                if current_sub:
                    st.info(f"🔍 **Configured subscription**: {current_sub[:8]}...")
                    st.markdown("✅ Subscription ID is configured (will be used directly)")
                else:
                    st.info("🔍 **Subscription mode**: Auto-discovery (no manual configuration)")
                    st.markdown("✅ Service will auto-discover available subscriptions")
                
                # Quick test button
                if st.button("🧪 Test Discovery Service", type="secondary"):
                    with st.spinner("Testing discovery service..."):
                        try:
                            if not discovery_service:
                                st.error("❌ Discovery service not initialized")
                                return
                                
                            # Test credentials first
                            discovery_service._ensure_credential_initialized()
                            st.success("✅ Credentials initialized")
                            
                            # Test subscription setup
                            if current_sub:
                                discovery_service.set_subscription(current_sub)
                                st.success("✅ Using configured subscription")
                            else:
                                # Test auto-discovery using discovery service method
                                st.info("🔍 Testing subscription auto-discovery...")
                                subscriptions = discovery_service.list_subscriptions()
                                
                                if subscriptions:
                                    auto_sub = subscriptions[0]['id']
                                    discovery_service.set_subscription(auto_sub)
                                    st.success(f"✅ Auto-discovered subscription: '{subscriptions[0]['name'][:30]}...' ({auto_sub[:8]}...)")
                                else:
                                    st.error("❌ No accessible subscriptions found")
                                    return
                            
                            # Test client initialization
                            discovery_service._ensure_clients_initialized()
                            st.success("✅ Azure clients initialized")
                            
                            # Test account listing (simplified)
                            st.info("🔍 Testing account discovery...")
                            accounts = discovery_service.discover_ai_foundry_accounts()
                            
                            if accounts:
                                st.success("✅ Accounts found! Try the scan button again.")
                            else:
                                st.warning("⚠️ Still no accounts found. Check the possible reasons above.")
                                
                        except Exception as e:
                            st.error(f"❌ Test failed: {str(e)}")
                            st.code(traceback.format_exc())
        else:
            st.info("🔍 Click 'Scan for AI Foundry Accounts' above to discover resources.")


def check_ai_foundry_permissions(account_name: str, resource_group: str):
    """Check if the user has the required permissions for AI Foundry agent deployment."""
    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
        
        st.info("🔍 **Checking your Azure permissions for AI Foundry agent deployment...**")
        
        # Check 1: Azure CLI Login Status
        try:
            result = subprocess.run(['az', 'account', 'show'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                account_info = json.loads(result.stdout)
                st.success(f"✅ **Azure CLI**: Logged in as {account_info.get('user', {}).get('name', 'unknown')}")
                subscription_id = account_info.get('id')
            else:
                st.error("❌ **Azure CLI**: Not logged in. Run `az login`")
                return
        except Exception as e:
            st.warning(f"⚠️ **Azure CLI**: Could not check status: {e}")
            subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
        
        if not subscription_id:
            st.error("❌ **Subscription**: No subscription ID found")
            return
        
        st.info(f"🔍 **Subscription**: {subscription_id[:8]}...")
        
        # Check 2: Azure Authentication Scopes
        credential = DefaultAzureCredential()
        auth_scopes = [
            ("AI Foundry", "https://ai.azure.com/.default"),  # Primary scope for AI Foundry
            ("Cognitive Services", "https://cognitiveservices.azure.com/.default"),
            ("Azure ML", "https://ml.azure.com/.default"), 
            ("Management", "https://management.azure.com/.default")
        ]
        
        for scope_name, scope_url in auth_scopes:
            try:
                token = credential.get_token(scope_url)
                st.success(f"✅ **{scope_name} Token**: Valid (expires: {datetime.datetime.fromtimestamp(token.expires_on).strftime('%Y-%m-%d %H:%M')})")
            except Exception as e:
                st.error(f"❌ **{scope_name} Token**: Failed - {str(e)}")
        
        # Check 3: Resource Access
        try:
            from azure.mgmt.resource import ResourceManagementClient
            resource_client = ResourceManagementClient(credential, subscription_id)
            
            # Try to get the AI Services resource
            resource = resource_client.resources.get(
                resource_group_name=resource_group,
                resource_provider_namespace="Microsoft.CognitiveServices",
                parent_resource_path="",
                resource_type="accounts",
                resource_name=account_name,
                api_version="2023-05-01"
            )
            st.success(f"✅ **Resource Access**: Can read AI Services resource '{account_name}'")
            st.json({
                "Resource ID": resource.id,
                "Location": resource.location,
                "Kind": resource.kind
            })
            
        except Exception as e:
            st.error(f"❌ **Resource Access**: Cannot read AI Services resource - {str(e)}")
        
        # Check 4: Function Key Environment Variable
        func_key = os.getenv('AGENT_FUNC_KEY')
        if func_key:
            st.success(f"✅ **Function Key**: AGENT_FUNC_KEY is set ({len(func_key)} characters)")
        else:
            st.error("❌ **Function Key**: AGENT_FUNC_KEY environment variable not set")
            st.markdown("💡 **Fix**: Add `AGENT_FUNC_KEY=your-function-host-key` to your `.env` file")
        
        # Check 5: Required Role Assignments
        st.markdown("**💡 Required Permissions Summary:**")
        st.markdown(f"""
        **For AI Services Resource** `{account_name}`:
        - ✅ **Cognitive Services Contributor** or **Cognitive Services User**
        
        **For Function Apps** (if deploying Function App agents):
        - ✅ **Function App Contributor** or **Website Contributor**
        
        **For Resource Discovery**:
        - ✅ **Reader** on subscription or resource group
        """)
        
        # Provide Azure CLI commands to grant permissions
        with st.expander("🔧 Grant Permissions (Azure CLI Commands)", expanded=False):
            st.markdown("**To grant yourself Cognitive Services Contributor role:**")
            st.code(f"""
# Get your user ID
USER_ID=$(az ad signed-in-user show --query id -o tsv)

# Grant Cognitive Services Contributor role
az role assignment create \\
  --assignee $USER_ID \\
  --role "Cognitive Services Contributor" \\
  --scope "/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices/accounts/{account_name}"
            """)
            
            st.markdown("**To check your current role assignments:**")
            st.code(f"""
# Check role assignments on the AI Services resource
az role assignment list \\
  --scope "/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices/accounts/{account_name}" \\
  --output table
            """)
        
    except Exception as e:
        st.error(f"❌ **Permission Check Failed**: {str(e)}")
        st.code(traceback.format_exc())
