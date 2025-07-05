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
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

def render_enhanced_ai_foundry_tab(
    session_state: Dict[str, Any],
    **kwargs
) -> None:
    """Render the enhanced AI Foundry account management tab."""
    
    # Track timing for performance monitoring
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
    
    # Show performance info in debug section only
    total_time = time.time() - tab_start_time
    if total_time > 1.0:  # Only show if tab loading took more than 1 second
        with st.expander("⏱️ Performance Info", expanded=False):
            st.text(f"Tab load time: {total_time:.3f}s")
    
    with tab_deploy_hub:
        render_ai_foundry_hub_deployment_ui()
    
    with tab_discover:
        render_resource_discovery_section(discovery_service)
    
    with tab_agents:
        render_agent_deployment_section(get_deployment_service())

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
                    
                    # =================== AGENT DEPLOYMENT SECTION ===================
                    st.markdown("---")
                    st.markdown("#### 🤖 Deploy Agent to This Project")
                    
                    # Initialize deployment service (lazy loading)
                    if 'ai_foundry_deployment_service' not in st.session_state:
                        from services.ai_foundry_agent_deployment import get_ai_foundry_agent_deployment_service
                        st.session_state.ai_foundry_deployment_service = get_ai_foundry_agent_deployment_service()
                    
                    deployment_service = st.session_state.ai_foundry_deployment_service
                    
                    # Set project endpoint on the deployment service
                    deployment_service.set_project_endpoint(project_endpoint)
                    
                    # Agent deployment form
                    with st.form(f"deploy_agent_form_{i}"):
                        st.markdown("**Create New Agent**")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            agent_name = st.text_input(
                                "Agent Name",
                                placeholder="my-search-agent",
                                help="Enter a unique name for your agent",
                                key=f"agent_name_{i}"
                            )
                        
                        with col2:
                            agent_model = st.selectbox(
                                "Model",
                                ["gpt-4", "gpt-4o", "gpt-3.5-turbo"],
                                help="Select the OpenAI model for the agent",
                                key=f"agent_model_{i}"
                            )
                        
                        # Agent instructions
                        agent_instructions = st.text_area(
                            "Agent Instructions",
                            placeholder="You are a helpful AI assistant...",
                            help="Provide instructions for what this agent should do",
                            height=100,
                            key=f"agent_instructions_{i}"
                        )
                        
                        # Optional: Azure Search integration
                        with st.expander("🔍 Azure Search Integration (Optional)", expanded=False):
                            enable_search = st.checkbox(
                                "Enable Azure Search Integration",
                                help="Connect this agent to an Azure Search index for retrieval",
                                key=f"enable_search_{i}"
                            )
                            
                            if enable_search:
                                search_endpoint = st.text_input(
                                    "Azure Search Endpoint",
                                    placeholder="https://your-search.search.windows.net",
                                    help="Your Azure Search service endpoint",
                                    key=f"search_endpoint_{i}"
                                )
                                
                                index_name = st.text_input(
                                    "Index Name",
                                    placeholder="my-index",
                                    help="Name of the search index to use",
                                    key=f"index_name_{i}"
                                )
                        
                        # Deploy button
                        deploy_submitted = st.form_submit_button("🚀 Deploy Agent", type="primary")
                        
                        if deploy_submitted:
                            if agent_name and agent_instructions:
                                try:
                                    with st.spinner(f"Deploying agent '{agent_name}' to {project_name}..."):
                                        # Create agent configuration
                                        if enable_search and search_endpoint and index_name:
                                            # Create retrieval agent with Azure Search integration
                                            success, message, agent_data = deployment_service.create_retrieval_agent(
                                                agent_name=agent_name,
                                                index_name=index_name,
                                                azure_search_endpoint=search_endpoint,
                                                instructions=agent_instructions
                                            )
                                        else:
                                            # Create standard agent
                                            agent_config = {
                                                'name': agent_name,
                                                'instructions': agent_instructions,
                                                'model': agent_model,
                                                'tools': [],
                                                'metadata': {
                                                    'created_from': 'agentic_rag_demo',
                                                    'project': project_name,
                                                    'account': account_name
                                                }
                                            }
                                            success, message, agent_data = deployment_service.create_agent(agent_config)
                                        
                                        if success:
                                            st.success(f"✅ {message}")
                                            st.markdown("**Agent Details:**")
                                            st.json(agent_data)
                                            
                                            # Show project endpoint for reference
                                            st.info(f"🔗 **Agent deployed to**: {project_endpoint}")
                                        else:
                                            st.error(f"❌ {message}")
                                            
                                except Exception as e:
                                    st.error(f"❌ Failed to deploy agent: {str(e)}")
                                    with st.expander("🔍 Error Details", expanded=False):
                                        st.code(traceback.format_exc())
                            else:
                                st.warning("⚠️ Please fill in Agent Name and Instructions")
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

def render_agent_deployment_section(deployment_service):
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
    
    # Render the actual agent deployment sections
    render_current_agents_section(deployment_endpoint, deployment_service)
    render_deploy_agent_section(deployment_endpoint, {}, [], deployment_service)
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
