"""
Enhanced AI Foundry Tab

Comprehensive UI for managing AI Foundry Accounts and agent deployment.

Features:
- 🔍 Resource Discovery: Discover AI Foundry Accounts only
- 🤖 Agent Management: Deploy and manage agents
- 🚀 Hub Deployment: Deploy new AI Foundry Hubs (manual process)
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
    
    st.header("🏭 AI Foundry Account Management (Accounts Only)")
    
    # Add important notice about supported resources
    st.info("""
    **📋 Resource Support**: 
    
    **✅ AI Foundry Accounts**: Supported for project endpoint generation and agent deployment
    
    **ℹ️ AI Foundry Hubs**: Use the Deploy New Hub tab for manual hub creation guidance
    
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
    
    # Initialize services (lazy-loaded for better performance)
    if 'ai_foundry_discovery_service' not in st.session_state:
        from services.ai_foundry_discovery import ai_foundry_discovery
        st.session_state.ai_foundry_discovery_service = ai_foundry_discovery
    
    # Only initialize other services when needed to improve tab loading speed
    discovery_service = st.session_state.ai_foundry_discovery_service
    
    # Initialize other services only when first accessed
    def get_rbac_service():
        if 'ai_foundry_rbac_service' not in st.session_state:
            from services.azure_rbac_manager import AzureRBACManager
            st.session_state.ai_foundry_rbac_service = AzureRBACManager()
        return st.session_state.ai_foundry_rbac_service
    
    def get_ai_foundry_service():
        if 'ai_foundry_service' not in st.session_state:
            from services.ai_foundry_service import AIFoundryService
            st.session_state.ai_foundry_service = AIFoundryService()
        return st.session_state.ai_foundry_service
    
    def get_deployment_service():
        if 'ai_foundry_deployment_service' not in st.session_state:
            from services.ai_foundry_agent_deployment import get_ai_foundry_agent_deployment_service
            st.session_state.ai_foundry_deployment_service = get_ai_foundry_agent_deployment_service()
        return st.session_state.ai_foundry_deployment_service
    
    # Debug information - show service status (only load services when debug is expanded)
    with st.expander("🔧 Service Debug Info", expanded=False):
        st.write("**Service Status:**")
        st.write(f"- Discovery Service: {type(discovery_service).__name__}")
        
        # Only load other services if debug is being viewed
        rbac_service = get_rbac_service()
        ai_foundry_service = get_ai_foundry_service()
        deployment_service = get_deployment_service()
        
        st.write(f"- RBAC Service: {type(rbac_service).__name__}")
        st.write(f"- AI Foundry Service: {type(ai_foundry_service).__name__}")
        st.write(f"- Deployment Service: {type(deployment_service).__name__}")
        
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
        if not hasattr(discovery_service, '_subscription_id'):
            discovery_service._subscription_id = subscription_id
        st.sidebar.success(f"✅ Subscription ID ready: {subscription_id[:8]}...")
    else:
        st.sidebar.info("💡 Set AZURE_SUBSCRIPTION_ID environment variable for auto-detection")
        st.sidebar.info("🔍 Or use discovery service to list subscriptions when needed")
    
    # Create tabs for different sections
    tab_deploy_hub, tab_discover, tab_agents = st.tabs([
        "🚀 Deploy New Hub",
        "🔍 Discover AI Accounts",
        "🤖 Deploy Agents"
    ])
    
    # Show performance info in debug section only (calculate after tabs are created)
    total_time = time.time() - tab_start_time
    if total_time > 1.0:  # Only show if tab loading took more than 1 second
        with st.expander("⏱️ Performance Info", expanded=False):
            st.text(f"Tab load time: {total_time:.3f}s")
    
    with tab_deploy_hub:
        render_ai_foundry_hub_deployment_ui()
    
    with tab_discover:
        render_resource_discovery_section(discovery_service)
    
    with tab_agents:
        st.subheader("🤖 Deploy Agents")
        st.info("🎯 **Agent deployment is now integrated into the 'Discover AI Accounts' tab!**")
        st.markdown("""
        **How to deploy agents:**
        
        1. **Go to 'Discover AI Accounts' tab**
        2. **Scan for AI Foundry Accounts** 
        3. **Select an account** and enter a **project name**
        4. **Use the 'Create AI Foundry Agent' section** to deploy Function Apps as agents
        
        **What you need:**
        - ✅ Azure Function App (configured in 'Function Config' tab)
        - ✅ AI Foundry Account discovered
        - ✅ Project name specified
        - ✅ `AGENT_FUNC_KEY` environment variable set
        """)
        
        # Show current function apps for reference
        func_choices = getattr(st.session_state, 'func_choices', [])
        if func_choices:
            st.success(f"✅ **{len(func_choices)} Function App(s) ready for deployment:**")
            for func in func_choices:
                st.markdown(f"• {func}")
        else:
            st.warning("⚠️ **No Function Apps configured.** Go to 'Function Config' tab first.")
            
        # Quick link to discovery tab
        st.markdown("---")
        st.markdown("🚀 **Ready to deploy?** Click 'Discover AI Accounts' tab above to start!")

def render_resource_discovery_section(discovery_service):
    """Render the AI Foundry resource discovery section."""
    st.subheader("🔍 Discover AI Foundry Accounts")
    
    # Force UI refresh with timestamp
    import datetime
    st.caption(f"🕒 Code reloaded: {datetime.datetime.now().strftime('%H:%M:%S')} - ACCOUNTS ONLY")
    
    # VERY OBVIOUS MARKER - IF YOU SEE OLD TEXT, THIS FILE IS NOT BEING USED!
    st.success("✅ NEW FILE LOADED - ACCOUNTS ONLY VERSION ACTIVE!")
    
    st.info("🔎 **Account Discovery Only**: This will scan for AI Foundry Accounts only (NOT Hubs) in your subscription.")
    
    st.markdown("""
    **🎯 Scanning for AI Foundry ACCOUNTS:**
    - 🏢 AI Services accounts with `.services.ai.azure.com` endpoints
    - ✅ Ready for project endpoint generation  
    - 🚀 Can be used for agent deployment
    - ❌ **NOT scanning for AI Foundry Hubs**
    """)
    
    if st.button("🔄 Scan for AI Foundry Accounts", type="primary"):
        with st.spinner("Scanning subscriptions for AI Foundry Accounts..."):
            try:
                # Check if subscription ID is available from environment
                subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
                
                if subscription_id:
                    # Use the configured subscription
                    discovery_service.set_subscription(subscription_id)
                    st.write(f"🔍 **DEBUG:** Using configured subscription: {subscription_id[:8]}...")
                else:
                    # Auto-discover subscriptions like before
                    st.write("🔍 **DEBUG:** No AZURE_SUBSCRIPTION_ID configured, auto-discovering subscriptions...")
                    
                    # Initialize credentials first
                    discovery_service._ensure_credential_initialized()
                    
                    # Try to discover available subscriptions using the discovery service
                    try:
                        # Use the discovery service's list_subscriptions method instead
                        st.write("🔍 **DEBUG:** Listing available subscriptions...")
                        subscriptions = discovery_service.list_subscriptions()
                        
                        if subscriptions:
                            # Use the first available subscription
                            auto_subscription_id = subscriptions[0]['id']
                            discovery_service.set_subscription(auto_subscription_id)
                            st.write(f"🔍 **DEBUG:** Auto-discovered subscription: {auto_subscription_id[:8]}...")
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
                st.write("🔍 **DEBUG:** Starting AI Foundry Account discovery (hubs excluded)...")
                accounts = discovery_service.discover_ai_foundry_accounts()
                st.write(f"🔍 **DEBUG:** Raw accounts discovered: {len(accounts)}")
                if accounts:
                    st.write("🔍 **DEBUG:** Sample account data:")
                    st.json(accounts[0])
                else:
                    st.write("🔍 **DEBUG:** No accounts found")
                
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
    
    # 🔍 DEBUG: Enhanced debugging for discovery issue
    st.write("🔍 **DEBUG ENHANCED:** Session state analysis:")
    st.write(f"   - accounts from session_state: {len(accounts)} items")
    st.write(f"   - accounts type: {type(accounts)}")
    st.write(f"   - session_state.discovered_accounts exists: {hasattr(st.session_state, 'discovered_accounts')}")
    
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
                            st.success("✅ Ready for agent deployment! Go to 'Deploy Agents' tab.")
                    
                    # =================== AI FOUNDRY AGENT CREATION ===================
                    st.markdown("---")
                    st.markdown("#### 🤖 Create AI Foundry Agent")
                    st.info("💡 **Deploy Azure Functions as AI Foundry Agents** - Connect your Function Apps to AI Foundry projects")
                    
                    # Initialize deployment service (lazy loading)
                    if 'ai_foundry_deployment_service' not in st.session_state:
                        from services.ai_foundry_agent_deployment import get_ai_foundry_agent_deployment_service
                        st.session_state.ai_foundry_deployment_service = get_ai_foundry_agent_deployment_service()
                    
                    deployment_service = st.session_state.ai_foundry_deployment_service
                    
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
                        if st.button("🚀 Create Agent", key=f"create_func_agent_{i}", type="primary"):
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
                                    except ImportError:
                                        st.warning("⚠️ OpenAPI tools not available (will use basic function tools)")
                                        
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
                                        # Get function app details
                                        app_name, resource_group = func_map[func_sel]
                                        
                                        # Build function URL (basic pattern - may need adjustment based on function structure)
                                        func_url = f"https://{app_name}.azurewebsites.net/api"
                                        
                                        # Create AI Foundry agent using the Function App
                                        print(f"🔍 DEBUG: Creating agent with parameters:")
                                        print(f"   - project_endpoint: {project_endpoint}")
                                        print(f"   - agent_name: {agent_name}")
                                        print(f"   - base_url: {func_url}")
                                        print(f"   - function_key: {'***' if function_key else 'NOT SET'}")
                                        
                                        success, message, agent_data = deployment_service.create_ai_foundry_agent(
                                            project_endpoint=project_endpoint,
                                            agent_name=agent_name,
                                            base_url=func_url,
                                            function_key=function_key
                                        )
                                        
                                        print(f"🔍 DEBUG: Agent creation result:")
                                        print(f"   - success: {success}")
                                        print(f"   - message: {message}")
                                        print(f"   - agent_data: {agent_data}")
                                        
                                        if success:
                                            st.success(message)
                                            st.markdown("**🎉 Agent Created Successfully!**")
                                            
                                            # Show agent details
                                            st.markdown("**Agent Details:**")
                                            agent_info = {
                                                "Agent Name": agent_name,
                                                "Function App": func_sel,
                                                "Function URL": func_url,
                                                "Project Endpoint": project_endpoint,
                                                "Type": "Function App Agent"
                                            }
                                            st.json(agent_info)
                                            
                                            # Show usage instructions
                                            st.markdown("**💬 How to use this agent:**")
                                            st.markdown(f"""
                                            1. Go to [Azure AI Foundry Studio]({project_endpoint.replace('/api/projects/', '/studio/projects/')})
                                            2. Find your agent: **{agent_name}**
                                            3. Start a conversation - the agent will automatically call your Function App for answers
                                            4. Your RAG system (via the Function App) will provide responses with citations
                                            """)
                                            
                                        else:
                                            st.error(message)
                                            
                                            # Add specific guidance for 401 errors
                                            if "401" in message or "unauthorized" in message.lower():
                                                st.error("🔒 **401 Unauthorized Error Detected!**")
                                                st.markdown("""
                                                **This means you don't have permission to create agents in this AI Foundry project.**
                                                
                                                **🔧 Quick Fix:**
                                                1. **Grant yourself permissions** using the commands below
                                                2. **Or ask your Azure admin** to grant you `Cognitive Services Contributor` role
                                                3. **Try the permission checker** to diagnose the issue
                                                """)
                                                
                                                # Show the exact Azure CLI command to fix the issue
                                                subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID') or discovery_service.get_subscription_id()
                                                if subscription_id:
                                                    st.markdown("**🚀 Run this command to fix the issue:**")
                                                    st.code(f"""
# Grant yourself Cognitive Services Contributor role
az role assignment create \\
  --assignee $(az ad signed-in-user show --query id -o tsv) \\
  --role "Cognitive Services Contributor" \\
  --scope "/subscriptions/{subscription_id}/resourceGroups/{account_rg}/providers/Microsoft.CognitiveServices/accounts/{account_name}"
                                                    """)
                                            
                                            st.markdown("**🔍 Troubleshooting:**")
                                            st.markdown("""
                                            - Ensure your Function App is running and accessible
                                            - Check that AGENT_FUNC_KEY is correctly set
                                            - Verify Azure CLI is logged in: `az login`
                                            - Confirm you have permissions to create agents in the AI Foundry project
                                            """)
                                            
                                            # Add permission diagnostic button
                                            if st.button("🔍 Check My Permissions", key=f"check_perms_{i}"):
                                                with st.spinner("Checking Azure permissions..."):
                                                    check_ai_foundry_permissions(account_name, account_rg)
                                            
                                except Exception as e:
                                    st.error(f"❌ Failed to create AI Foundry agent: {str(e)}")
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
                            discovery_service = st.session_state.ai_foundry_discovery_service
                            
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
                            st.write(f"🔍 **Raw discovery result**: {len(accounts)} accounts found")
                            
                            if accounts:
                                st.success("✅ Accounts found! Try the scan button again.")
                            else:
                                st.warning("⚠️ Still no accounts found. Check the possible reasons above.")
                                
                        except Exception as e:
                            st.error(f"❌ Test failed: {str(e)}")
                            st.code(traceback.format_exc())
        else:
            st.info("🔍 Click 'Scan for AI Foundry Accounts' above to discover resources.")

def render_agent_deployment_section(deployment_service, discovery_service):
    """Render the agent deployment section."""
    st.subheader("🤖 Deploy Agents")
    
    # Check if we have a generated endpoint from Discover and Deploy Agent
    has_generated_endpoint = hasattr(st.session_state, 'ready_for_agent_deployment') and st.session_state.ready_for_agent_deployment
    
    deployment_endpoint = None
    deployment_source = None
    
    if has_generated_endpoint:
        deployment_endpoint = st.session_state.deployment_endpoint
        deployment_source = "Generated from Discover AI Accounts"
        st.success(f"✅ **Ready to deploy!** Using endpoint from Discover AI Accounts")
        st.code(deployment_endpoint)
        
    else:
        # Allow manual endpoint input as fallback
        st.info("🎯 **Agent Deployment Options:**")
        st.markdown("""
        **Option 1:** Use **Discover AI Accounts** tab → Select AI Foundry Account → Generate PROJECT_ENDPOINT
        
        **Option 2:** Enter a PROJECT_ENDPOINT manually below
        
        **Option 3:** Use Function Apps to deploy agents (advanced)
        """)
        
        # Manual endpoint input
        with st.expander("✍️ Manual Endpoint Input", expanded=True):
            manual_endpoint = st.text_input(
                "PROJECT_ENDPOINT",
                placeholder="https://your-account.services.ai.azure.com/api/projects/your-project",
                help="Enter your AI Foundry project endpoint manually"
            )
            
            if manual_endpoint:
                if st.button("🚀 Use This Endpoint"):
                    st.session_state.deployment_endpoint = manual_endpoint
                    st.session_state.ready_for_agent_deployment = True
                    st.success("✅ Manual endpoint set! You can now deploy agents.")
                    st.rerun()
        
        # If no endpoint is available, show current agent deployment sections but with limited functionality
        if not has_generated_endpoint:
            st.warning("⚠️ **No deployment endpoint configured.** Some features may be limited.")
            deployment_endpoint = None
            deployment_source = "No endpoint configured"
    
    # Show deployment details
    st.markdown("---")
    st.markdown("### 📄 Deployment Details")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Source**: {deployment_source}")
    with col2:
        if deployment_endpoint:
            st.markdown(f"**Endpoint**: `{deployment_endpoint[:50]}...`")
        else:
            st.markdown("**Endpoint**: Not configured")
    
    # Add Function Apps section for advanced deployment
    st.markdown("---")
    st.markdown("### 🔧 Advanced: Deploy via Function Apps")
    
    with st.expander("🚀 Function App Agent Deployment", expanded=False):
        render_function_app_agent_deployment(discovery_service, deployment_endpoint)
    
    # Get Function Apps data if available
    func_map = st.session_state.get('function_apps', {}).get('map', {})
    func_choices = st.session_state.get('function_apps', {}).get('choices', [])
    
    # Render the actual agent deployment sections
    render_current_agents_section(deployment_endpoint, deployment_service)
    render_deploy_agent_section(deployment_endpoint, func_map, func_choices, deployment_service)
    render_agent_details_section(deployment_endpoint, deployment_service)

def render_current_agents_section(deployment_endpoint, deployment_service):
    """Render the current agents management section."""
    st.markdown("### 🤖 Current Agents")
    
    if not deployment_endpoint:
        st.warning("⚠️ **No deployment endpoint configured.** Please set up an endpoint first.")
        return
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh Agents"):
            # Force refresh of agents
            if 'current_agents' in st.session_state:
                del st.session_state['current_agents']
            st.rerun()
    
    # Load and display current agents
    try:
        if 'current_agents' not in st.session_state:
            with st.spinner("Loading current agents..."):
                agents = deployment_service.list_agents(deployment_endpoint)
                st.session_state.current_agents = agents
        
        agents = st.session_state.current_agents
        
        if agents:
            for agent in agents:
                agent_name = agent.get('name', 'Unknown')
                agent_type = agent.get('type', 'Unknown')
                
                with st.expander(f"🤖 {agent_name}", expanded=False):
                    st.markdown(f"**Type**: {agent_type}")
                    st.markdown(f"**Details**: {agent}")
                    
                    if st.button(f"🗑️ Delete {agent_name}", key=f"delete_{agent_name}"):
                        try:
                            deployment_service.delete_agent(deployment_endpoint, agent_name)
                            st.success(f"✅ Agent {agent_name} deleted!")
                            # Refresh agents list
                            del st.session_state['current_agents']
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to delete agent: {e}")
        else:
            st.info("ℹ️ No agents found. Deploy an agent to get started.")
            
    except Exception as e:
        st.error(f"❌ Failed to load agents: {e}")
        st.code(str(e))

def render_deploy_agent_section(deployment_endpoint, func_map, func_choices, deployment_service):
    """Render the deploy new agent section."""
    st.markdown("### ➕ Deploy New Agent")
    
    if not deployment_endpoint:
        st.warning("⚠️ **No deployment endpoint configured.** Please set up an endpoint first.")
        return
    
    with st.form("deploy_agent_form"):
        agent_name = st.text_input(
            "Agent Name",
            help="Enter a unique name for your agent"
        )
        
        agent_description = st.text_area(
            "Agent Description",
            help="Describe what this agent does"
        )
        
        agent_type = st.selectbox(
            "Agent Type",
            ["knowledge-agent", "chat-agent", "task-agent"],
            help="Select the type of agent to deploy"
        )
        
        deploy_submitted = st.form_submit_button("🚀 Deploy Agent")
        
        if deploy_submitted:
            if agent_name and agent_description:
                try:
                    with st.spinner(f"Deploying agent {agent_name}..."):
                        result = deployment_service.deploy_agent(
                            deployment_endpoint=deployment_endpoint,
                            agent_name=agent_name,
                            agent_description=agent_description,
                            agent_type=agent_type
                        )
                        st.success(f"✅ Agent {agent_name} deployed successfully!")
                        st.json(result)
                        
                        # Refresh agents list
                        if 'current_agents' in st.session_state:
                            del st.session_state['current_agents']
                        
                except Exception as e:
                    st.error(f"❌ Failed to deploy agent: {e}")
                    st.code(str(e))
            else:
                st.error("❌ Please provide both agent name and description.")

def render_agent_details_section(deployment_endpoint, deployment_service):
    """Render agent details and testing section."""
    st.markdown("### 🔍 Agent Details & Testing")
    
    if not deployment_endpoint:
        st.warning("⚠️ **No deployment endpoint configured.** Please set up an endpoint first.")
        return
    
    # Agent selection for details
    try:
        if 'current_agents' in st.session_state:
            agents = st.session_state.current_agents
            
            if agents:
                agent_names = [agent.get('name', 'Unknown') for agent in agents]
                selected_agent = st.selectbox(
                    "Select agent for details:",
                    agent_names,
                    key="agent_details_selection"
                )
                
                if selected_agent:
                    with st.spinner("Loading agent details..."):
                        try:
                            details = deployment_service.get_agent_details(deployment_endpoint, selected_agent)
                            st.json(details)
                        except Exception as e:
                            st.error(f"❌ Failed to load agent details: {e}")
            else:
                st.info("ℹ️ No agents available for details view.")
        else:
            st.info("ℹ️ Load agents first using the refresh button above.")
            
    except Exception as e:
        st.error(f"❌ Error in agent details section: {e}")

def render_ai_foundry_hub_deployment_ui():
    """Render the AI Foundry Hub deployment UI with lazy loading."""
    # Lazy loading to avoid slow initialization during tab creation
    st.subheader("🚀 Deploy New AI Foundry Hub")
    
    # Add a note about lazy loading
    st.info("💡 Hub deployment UI loads when first accessed to improve performance.")
    
    # Only import and initialize when user actually wants to use it
    if st.button("🔧 Initialize Hub Deployment UI", type="primary"):
        with st.spinner("Loading hub deployment interface..."):
            try:
                from app.components.ai_foundry_hub_deployment_ui import render_ai_foundry_hub_deployment_ui as render_hub_ui
                st.success("✅ Hub deployment UI loaded!")
                # Store in session state so it doesn't reload
                st.session_state.hub_ui_loaded = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to load hub deployment UI: {e}")
                st.code(str(e))
    
    # If already loaded, show the UI
    if st.session_state.get('hub_ui_loaded', False):
        try:
            from app.components.ai_foundry_hub_deployment_ui import render_ai_foundry_hub_deployment_ui as render_hub_ui
            render_hub_ui()
        except Exception as e:
            st.error(f"❌ Error in hub deployment UI: {e}")
            # Reset the loaded state so user can try again
            st.session_state.hub_ui_loaded = False
            if st.button("🔄 Retry Loading"):
                st.rerun()

def render_function_app_agent_deployment(discovery_service, deployment_endpoint):
    """Render the Function App agent deployment section."""
    st.subheader("🔧 Deploy Function Apps as AI Foundry Agents")
    
    st.info("""
    **Advanced Feature**: Deploy your Azure Function Apps as AI Foundry agents.
    This allows your functions to be called by AI assistants in conversations.
    """)
    
    if not deployment_endpoint:
        st.warning("⚠️ **Function App deployment requires a project endpoint.** Please configure one first.")
        return
    
    # Get subscription ID for Function App discovery
    subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
    if not subscription_id:
        # Try to get from discovery service
        try:
            discovery_service._ensure_credential_initialized()
            subscriptions = discovery_service.list_subscriptions()
            if subscriptions:
                subscription_id = subscriptions[0]['id']
            else:
                st.error("❌ No subscription found. Set AZURE_SUBSCRIPTION_ID or ensure you have access to subscriptions.")
                return
        except Exception as e:
            st.error(f"❌ Failed to get subscription: {e}")
            return
    
    # Load Function Apps
    if 'function_apps' not in st.session_state:
        with st.spinner("Loading Function Apps..."):
            try:
                from azure_function_helper import list_function_apps
                func_choices, func_map = list_function_apps(subscription_id)
                st.session_state.function_apps = {
                    'choices': func_choices,
                    'map': func_map
                }
            except Exception as e:
                st.error(f"❌ Failed to load Function Apps: {e}")
                st.session_state.function_apps = {'choices': [], 'map': {}}
                return
    
    func_choices = st.session_state.function_apps['choices']
    func_map = st.session_state.function_apps['map']
    
    if not func_choices:
        st.warning("⚠️ No Function Apps found in your subscription.")
        if st.button("🔄 Refresh Function Apps"):
            if 'function_apps' in st.session_state:
                del st.session_state['function_apps']
            st.rerun()
        return
    
    # Function App selection and deployment
    with st.form("function_app_agent_form"):
        st.markdown("**Select Function App to Deploy as Agent**")
        
        func_sel = st.selectbox(
            "Function App to Deploy",
            func_choices,
            index=0,
            help="Select an Azure Function App to deploy as an AI Foundry agent"
        )
        
        # Custom agent name (optional)
        custom_agent_name = st.text_input(
            "Custom Agent Name (Optional)",
            placeholder="Leave empty to use function app name",
            help="Customize the agent name, or leave empty to use the function app name"
        )
        
        # Agent description
        agent_description = st.text_area(
            "Agent Description",
            placeholder="Describe what this function does and when to use it...",
            help="Provide a description of the function's purpose and capabilities",
            height=100
        )
        
        deploy_func_submitted = st.form_submit_button("🚀 Deploy Function App as Agent", type="primary")
        
        if deploy_func_submitted:
            if func_sel and agent_description:
                try:
                    with st.spinner(f"Deploying {func_sel} as AI Foundry agent..."):
                        # Get function app details
                        app_name, resource_group = func_map[func_sel]
                        
                        # Build function URL (basic pattern - may need adjustment based on function structure)
                        func_url = f"https://{app_name}.azurewebsites.net/api"
                        
                        # Use custom name or function app name
                        agent_name = custom_agent_name.strip() if custom_agent_name.strip() else f"{app_name}-agent"
                        
                        # Get deployment service
                        deployment_service = st.session_state.ai_foundry_deployment_service
                        deployment_service.set_project_endpoint(deployment_endpoint)
                        
                        # Get function key from environment
                        function_key = os.getenv('AGENT_FUNC_KEY', '')
                        if not function_key:
                            st.error("❌ AGENT_FUNC_KEY environment variable not set. This is required for Function App authentication.")
                            st.markdown("💡 **Solution**: Set `AGENT_FUNC_KEY` in your `.env` file with your Function App host key")
                            return  # Exit the function if no key is provided
                        
                        # Deploy the function as an agent
                        print(f"🔍 DEBUG: [Advanced Section] Creating agent with parameters:")
                        print(f"   - project_endpoint: {deployment_endpoint}")
                        print(f"   - agent_name: {agent_name}")
                        print(f"   - base_url: {func_url}")
                        print(f"   - function_key: {'***' if function_key else 'NOT SET'}")
                        
                        success, message, agent_data = deployment_service.create_ai_foundry_agent(
                            project_endpoint=deployment_endpoint,
                            agent_name=agent_name,
                            base_url=func_url,
                            function_key=function_key
                        )
                        
                        print(f"🔍 DEBUG: [Advanced Section] Agent creation result:")
                        print(f"   - success: {success}")
                        print(f"   - message: {message}")
                        print(f"   - agent_data: {agent_data}")
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.markdown("**Agent Details:**")
                            st.json(agent_data)
                            
                            # Show deployment info
                            st.info(f"""
                            **Deployment Summary:**
                            - **Function App**: {app_name} (Resource Group: {resource_group})
                            - **Agent Name**: {agent_name}
                            - **Project Endpoint**: {deployment_endpoint}
                            - **Function URL**: {func_url}
                            """)
                            
                            # Clear agents cache to refresh
                            if 'current_agents' in st.session_state:
                                del st.session_state['current_agents']
                                
                        else:
                            st.error(f"❌ {message}")
                            
                except Exception as e:
                    st.error(f"❌ Failed to deploy Function App as agent: {str(e)}")
                    with st.expander("🔍 Error Details", expanded=False):
                        st.code(str(e))
            else:
                st.warning("⚠️ Please select a Function App and provide a description")

def check_ai_foundry_permissions(account_name: str, resource_group: str):
    """Check if the user has the required permissions for AI Foundry agent deployment."""
    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
        import subprocess
        import json
        
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
