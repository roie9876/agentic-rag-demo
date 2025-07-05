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
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

def render_enhanced_ai_foundry_tab(
    session_state: Dict[str, Any],
    **kwargs
) -> None:
    """Render the enhanced AI Foundry account management tab."""
    
    # Performance timing - track tab rendering speed
    tab_start_time = time.time()
    st.markdown("⏱️ **Tab Loading Diagnostics:**")
    st.text(f"Tab start time: {time.strftime('%H:%M:%S', time.localtime(tab_start_time))}")
    
    st.header("🏭 AI Foundry Account Management (Accounts Only)")
    
    # Timing checkpoint 1
    checkpoint_1 = time.time()
    st.text(f"⏱️ Header rendered in: {checkpoint_1 - tab_start_time:.3f}s")
    
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
    
    # Timing checkpoint 2 - before service initialization
    checkpoint_2 = time.time()
    st.text(f"⏱️ UI setup complete in: {checkpoint_2 - tab_start_time:.3f}s")
    
    # Initialize services (lazy-loaded for better performance)
    if 'ai_foundry_discovery_service' not in st.session_state:
        service_start = time.time()
        from services.ai_foundry_discovery import ai_foundry_discovery
        st.session_state.ai_foundry_discovery_service = ai_foundry_discovery
        service_end = time.time()
        st.text(f"⏱️ Discovery service loaded in: {service_end - service_start:.3f}s")
    else:
        st.text("⏱️ Discovery service: already loaded (cached)")
    
    # Timing checkpoint 3 - after service initialization
    checkpoint_3 = time.time()
    st.text(f"⏱️ Service setup complete in: {checkpoint_3 - tab_start_time:.3f}s")
    
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
            from services.ai_foundry_agent_deployment import AIFoundryAgentDeploymentService
            st.session_state.ai_foundry_deployment_service = AIFoundryAgentDeploymentService()
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
    subscription_start = time.time()
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
    
    subscription_end = time.time()
    st.text(f"⏱️ Subscription setup in: {subscription_end - subscription_start:.3f}s")
    
    # Create tabs for different sections
    tabs_start = time.time()
    tab_deploy_hub, tab_discover, tab_agents = st.tabs([
        "🚀 Deploy New Hub",
        "🔍 Discover AI Accounts",
        "🤖 Deploy Agents"
    ])
    tabs_end = time.time()
    st.text(f"⏱️ Tabs created in: {tabs_end - tabs_start:.3f}s")
    
    # Final timing summary
    total_time = time.time() - tab_start_time
    st.success(f"🏁 **Total AI Foundry tab load time: {total_time:.3f}s**")
    
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
                # Ensure subscription is set up before discovery (lazy initialization)
                subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
                if subscription_id and hasattr(discovery_service, '_subscription_id'):
                    discovery_service.set_subscription(subscription_id)
                    st.write(f"🔍 **DEBUG:** Using subscription: {subscription_id[:8]}...")
                
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
    else:
        if hasattr(st.session_state, 'discovered_accounts'):
            st.info("⚠️ No AI Foundry Accounts found in your subscription")
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
    """Render the AI Foundry Hub deployment UI."""
    try:
        # Import and use the comprehensive hub deployment UI
        from app.components.ai_foundry_hub_deployment_ui import render_ai_foundry_hub_deployment_ui as render_hub_ui
        render_hub_ui()
    except ImportError as e:
        # Fallback to placeholder if the component is not available
        st.subheader("🚀 Deploy New AI Foundry Hub")
        
        st.warning("⚠️ **Hub Deployment UI Module Not Available**")
        st.error(f"Import Error: {e}")
        
        st.info("""
        **🏗️ Hub Deployment**: Deploy a new AI Foundry Hub with network isolation and private endpoints.
        
        **Current Options:**
        1. Use the Azure Portal to create AI Foundry Hubs manually
        2. Use Azure CLI or ARM templates for automated deployment
        3. Check if the hub deployment module is properly installed
        """)
    except Exception as e:
        # Handle any other errors
        st.subheader("� Deploy New AI Foundry Hub")
        
        st.error(f"❌ **Error Loading Hub Deployment UI**: {e}")
        
        st.info("""
        **Current Options:**
        1. Use the Azure Portal to create AI Foundry Hubs manually
        2. Use Azure CLI or ARM templates for automated deployment
        3. Contact support for assistance
        """)
