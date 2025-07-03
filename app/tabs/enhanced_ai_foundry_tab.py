"""
Enhanced AI Foundry Hub Tab
---------------------------
Comprehensive UI for managing AI Foundry Hubs, permissions, and agent deployment.

IMPORTANT: This interface only supports AI Foundry Hubs (Microsoft.MachineLearningServices/workspaces with kind=Hub).
AI Foundry Accounts (Microsoft.CognitiveServices/accounts) are NOT supported due to lack of public APIs.

For users with AI Foundry Accounts:
- Use the Azure Portal for project management
- Consider migrating to AI Foundry Hubs for programmatic access
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional
import logging

# Import the actual services that exist
from services.ai_foundry_discovery import AIFoundryDiscoveryService
from services.ai_foundry_rbac import AIFoundryRBACService
from services.ai_foundry_service import AIFoundryService
from services.ai_foundry_agent_deployment import AIFoundryAgentDeploymentService
from utils.ai_foundry_helpers import AIFoundryHelper

logger = logging.getLogger(__name__)

def render_enhanced_ai_foundry_tab(
    session_state: Dict[str, Any],
    **kwargs
) -> None:
    """Render the enhanced AI Foundry Hub management tab."""
    
    st.header("🏭 AI Foundry Hub Management")
    
    # Add important notice about supported resources
    st.info("""
    **📋 Supported Resources**: This interface only supports **AI Foundry Hubs** (ML workspaces with kind=Hub).
    
    **❌ Not Supported**: AI Foundry Accounts (CognitiveServices) due to lack of public project management APIs.
    
    **💡 For AI Foundry Account users**: Use the Azure Portal for project management or migrate to Hubs for programmatic access.
    """)
    
    # Add refresh button to clear cached services
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄 Refresh Services", help="Clear cached services and reload"):
            # Clear all AI Foundry services from session state
            keys_to_remove = [
                'ai_foundry_discovery_service',
                'ai_foundry_rbac_service', 
                'ai_foundry_service',
                'ai_foundry_deployment_service',
                'ai_foundry_hubs',
                'current_projects'
            ]
            for key in keys_to_remove:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("✅ Services refreshed!")
            st.rerun()
    
    st.markdown("---")
    
    # Initialize services (always create new instances to ensure latest code)
    if 'ai_foundry_discovery_service' not in st.session_state:
        st.session_state.ai_foundry_discovery_service = AIFoundryDiscoveryService()
    
    if 'ai_foundry_rbac_service' not in st.session_state:
        st.session_state.ai_foundry_rbac_service = AIFoundryRBACService()
    
    if 'ai_foundry_service' not in st.session_state:
        st.session_state.ai_foundry_service = AIFoundryService()
    
    if 'ai_foundry_deployment_service' not in st.session_state:
        st.session_state.ai_foundry_deployment_service = AIFoundryAgentDeploymentService()
    
    # Get services from session state
    discovery_service = st.session_state.ai_foundry_discovery_service
    rbac_service = st.session_state.ai_foundry_rbac_service
    ai_foundry_service = st.session_state.ai_foundry_service
    deployment_service = st.session_state.ai_foundry_deployment_service
    
    # Debug information - show service status
    with st.expander("🔧 Service Debug Info", expanded=False):
        st.write("**Service Status:**")
        st.write(f"- Discovery Service: {type(discovery_service).__name__}")
        st.write(f"- RBAC Service: {type(rbac_service).__name__}")
        st.write(f"- AI Foundry Service: {type(ai_foundry_service).__name__}")
        st.write(f"- Deployment Service: {type(deployment_service).__name__}")
        
        # Check if the create_project method has been updated
        import inspect
        create_project_source = inspect.getsource(ai_foundry_service.create_project)
        if "management.azure.com" in create_project_source:
            st.success("✅ Service is using updated MSI-compatible create_project method")
        else:
            st.error("❌ Service is using old create_project method")
        
        if st.button("🧪 Test Service Method"):
            try:
                # Quick test of the method signature and source
                sig = inspect.signature(ai_foundry_service.create_project)
                st.write(f"Method signature: {sig}")
                
                # Check actual source
                source = inspect.getsource(ai_foundry_service.create_project)
                st.write("**Method source snippet:**")
                st.code(source[:500] + "...", language="python")
                
                # Check _create_account_project
                if hasattr(ai_foundry_service, '_create_account_project'):
                    account_source = inspect.getsource(ai_foundry_service._create_account_project)
                    if "management.azure.com" in account_source:
                        st.success("✅ _create_account_project uses management.azure.com")
                    else:
                        st.error("❌ _create_account_project does NOT use management.azure.com")
                else:
                    st.error("❌ _create_account_project method not found")
                
                st.success("✅ Service method accessible")
            except Exception as e:
                st.error(f"❌ Service method error: {e}")
    
    # Setup subscription for discovery service
    try:
        # Get subscription from environment or Azure CLI
        import os
        subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
        
        if not subscription_id:
            # Try to get from Azure CLI or discovery service
            subscriptions = discovery_service.list_subscriptions()
            if subscriptions:
                subscription_id = subscriptions[0]['id']
        
        if subscription_id:
            discovery_service.set_subscription(subscription_id)
            st.sidebar.success(f"🎯 Using subscription: {subscription_id[:8]}...")
    except Exception as e:
        st.sidebar.warning(f"⚠️ Subscription setup issue: {e}")
    
    # Create tabs for different sections
    tab_discover, tab_permissions, tab_projects, tab_agents = st.tabs([
        "🔍 Discover Resources",
        "🔐 Check Permissions", 
        "📋 Manage Projects",
        "🤖 Deploy Agents"
    ])
    
    with tab_discover:
        render_resource_discovery_section(discovery_service)
    
    with tab_permissions:
        render_permissions_section(rbac_service)
    
    with tab_projects:
        render_project_management_section(ai_foundry_service)
    
    with tab_agents:
        render_agent_deployment_section(deployment_service)

def render_resource_discovery_section(discovery_service):
    """Render the AI Foundry Hub discovery section."""
    st.subheader("🔍 Discover AI Foundry Hubs")
    
    st.info("🔎 **Hub Discovery**: This will scan for AI Foundry Hubs (ML workspaces with kind=Hub) only.")
    
    if st.button("🔄 Scan for AI Foundry Hubs", type="primary"):
        with st.spinner("Scanning subscriptions for AI Foundry Hubs..."):
            try:
                # Use the hub-only discovery method
                hubs = discovery_service.discover_ai_foundry_hubs()
                
                # Store results in session state with proper formatting
                st.session_state.discovered_hubs = hubs
                st.session_state.discovery_errors = []
                
                if hubs:
                    st.success(f"✅ Found {len(hubs)} AI Foundry Hubs")
                else:
                    st.warning("⚠️ No AI Foundry Hubs found. Make sure you have:")
                    st.markdown("""
                    - **AI Foundry Hubs**: ML workspaces configured as Hubs (kind=Hub)
                    - **Proper RBAC permissions**: Reader or Contributor role on the subscription
                    - **Hub deployment**: Some regions may not have AI Foundry Hubs available yet
                    """)
                    
            except Exception as e:
                st.error(f"❌ Hub discovery failed: {str(e)}")
                st.session_state.discovered_hubs = []
                st.session_state.discovery_errors = [str(e)]
    
    # Display discovered hubs
    if hasattr(st.session_state, 'discovered_hubs') and st.session_state.discovered_hubs:
        st.markdown("### 📊 Discovered Resources")
        
        # Separate accounts and hubs
        accounts = [r for r in st.session_state.discovered_resources if r['type'] == "AI Foundry Account"]
        hubs = [r for r in st.session_state.discovered_resources if r['type'] == "AI Foundry Hub"]
        
        if accounts:
            st.markdown("#### 🏢 AI Foundry Accounts")
            accounts_data = []
            for account in accounts:
                accounts_data.append({
                    "Name": account['name'],
                    "Location": account['location'],
                    "Resource Group": account['resource_group'],
                    "Kind": account['kind'],
                    "Endpoint": account['endpoint'][:50] + "..." if account['endpoint'] and len(account['endpoint']) > 50 else account['endpoint']
                })
            
            df_accounts = pd.DataFrame(accounts_data)
            st.dataframe(df_accounts, use_container_width=True)
        
        if hubs:
            st.markdown("#### 🏭 AI Foundry Hubs")
            hubs_data = []
            for hub in hubs:
                hubs_data.append({
                    "Name": hub['name'],
                    "Location": hub['location'],
                    "Resource Group": hub['resource_group'],
                    "Kind": hub['kind'],
                    "Endpoint": hub['endpoint'][:50] + "..." if hub['endpoint'] and len(hub['endpoint']) > 50 else hub['endpoint']
                })
            
            df_hubs = pd.DataFrame(hubs_data)
            st.dataframe(df_hubs, use_container_width=True)
        
        # Store selected resource for other tabs
        all_resources = st.session_state.discovered_resources
        resource_labels = [f"{r['name']} ({r['type']}) - {r['location']}" for r in all_resources]
        
        if resource_labels:
            selected_idx = st.selectbox(
                "🎯 Select Resource for Management:",
                range(len(resource_labels)),
                format_func=lambda x: resource_labels[x],
                key="selected_resource_idx"
            )
            st.session_state.selected_resource = all_resources[selected_idx]
            
            # Enhanced resource type guidance
            resource = st.session_state.selected_resource
            resource_type = resource['resource_type']
            resource_id = resource.get('id', '')
            
            # Determine actual resource capabilities
            is_cognitive_services = (
                'CognitiveServices' in resource_type or 
                'Microsoft.CognitiveServices' in resource_id or
                resource_type == 'account'
            )
            is_ml_workspace = (
                'MachineLearningServices' in resource_type or
                'Microsoft.MachineLearningServices' in resource_id or
                resource_type == 'hub'
            )
            
            if is_cognitive_services:
                st.info(
                    f"ℹ️ **Cognitive Services Account Selected:** {resource['name']}\n\n"
                    "**Capabilities:**\n"
                    "✅ Provides AI services (OpenAI, Speech, Vision, etc.)\n"
                    "✅ Can be connected as a resource to projects\n"
                    "✅ Project creation via Azure CLI (same as Portal)\n"
                    "⚠️ ARM API may have limitations\n\n"
                    "**Project creation will attempt multiple methods for best compatibility.**"
                )
            elif is_ml_workspace:
                st.success(
                    f"✅ **AI Foundry Hub Selected:** {resource['name']}\n\n"
                    "**Capabilities:**\n"
                    "✅ Can host AI Foundry projects\n"
                    "✅ Supports programmatic project creation\n"
                    "✅ Can contain multiple projects and agents\n\n"
                    "**This resource type supports all AI Foundry operations.**"
                )
            else:
                st.info(f"📋 **Selected:** {resource['name']} ({resource_type})")
            
            # Add resource details in an expander
            with st.expander(f"📊 Resource Details: {resource['name']}", expanded=False):
                st.json(resource)

def render_permissions_section(rbac_service):
    """Render the permissions checking section."""
    st.subheader("🔐 Check RBAC Permissions")
    
    if not hasattr(st.session_state, 'selected_resource'):
        st.info("👆 Please discover and select a resource first in the 'Discover Resources' tab.")
        return
    
    resource = st.session_state.selected_resource
    st.markdown(f"**Checking permissions for:** {resource['name']} ({resource['resource_type']})")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔍 Check My Permissions", type="primary"):
            with st.spinner("Checking RBAC permissions..."):
                try:
                    permissions, errors = rbac_service.check_resource_permissions(
                        resource['id'], 
                        resource['resource_type']
                    )
                    
                    # Validate that permissions is a list
                    if not isinstance(permissions, list):
                        st.error(f"❌ Expected permissions list, got {type(permissions)}: {permissions}")
                        permissions = []
                    
                    # Validate each permission item
                    validated_permissions = []
                    for i, perm in enumerate(permissions):
                        if isinstance(perm, dict):
                            validated_permissions.append(perm)
                        else:
                            st.warning(f"⚠️ Invalid permission at index {i}: {type(perm)} - {perm}")
                    
                    st.session_state.current_permissions = validated_permissions
                    st.session_state.permission_errors = errors
                    
                    if errors:
                        for error in errors:
                            st.error(f"❌ {error}")
                            
                except Exception as e:
                    st.error(f"❌ Unexpected error during permission check: {str(e)}")
                    st.session_state.current_permissions = []
                    st.session_state.permission_errors = [str(e)]
    
    with col2:
        if st.button("🛠️ Validate CLI Setup"):
            with st.spinner("Validating Azure CLI setup..."):
                cli_ok, cli_checks = rbac_service.validate_cli_setup()
            
            st.markdown("**CLI Setup Status:**")
            for check in cli_checks:
                st.markdown(f"- {check}")
    
    # Display permission results
    if hasattr(st.session_state, 'current_permissions'):
        permissions = st.session_state.current_permissions
        
        if permissions:
            st.markdown("### 📋 Permission Status")
            
            # Validate permissions structure
            valid_permissions = []
            for i, perm in enumerate(permissions):
                if isinstance(perm, dict) and all(key in perm for key in ['status', 'required', 'role_name', 'description']):
                    valid_permissions.append(perm)
                else:
                    st.error(f"❌ Invalid permission structure at index {i}: {type(perm)} - {perm}")
                    continue
            
            if valid_permissions:
                # Create permission status table
                perm_data = []
                for perm in valid_permissions:
                    status_icon = "✅" if perm['status'] == "granted" else "❌"
                    required_icon = "🔴" if perm['required'] else "🟡"
                    
                    perm_data.append({
                        "Status": f"{status_icon} {perm['status'].title()}",
                        "Required": f"{required_icon} {'Yes' if perm['required'] else 'Optional'}",
                        "Role": perm['role_name'],
                        "Description": perm['description']
                    })
                
                df_perms = pd.DataFrame(perm_data)
                st.dataframe(df_perms, use_container_width=True)
                
                # Use valid_permissions for further processing
                permissions = valid_permissions
            else:
                st.warning("⚠️ No valid permission data to display")
            
            # Check if any required permissions are missing
            missing_required = [p for p in permissions if p['required'] and p['status'] == 'missing']
            
            if missing_required:
                st.error("❌ **Missing Required Permissions**")
                st.markdown("You need the following permissions to proceed:")
                
                for perm in missing_required:
                    st.markdown(f"- **{perm['role_name']}**: {perm['description']}")
                
                # Generate assignment commands
                try:
                    missing_role_names = [p['role_name'] for p in missing_required]
                    commands = rbac_service.generate_rbac_assignment_commands(
                        resource['id'],
                        resource['resource_type'],
                        {'missing_required': missing_role_names}
                    )
                except Exception as e:
                    commands = [f"# Error generating commands: {str(e)}"]
                
                if commands and commands[0] != "# No missing required permissions found.":
                    st.markdown("### 🔧 Assignment Commands")
                    st.markdown("Run these commands to assign missing permissions:")
                    
                    for cmd in commands:
                        st.code(cmd, language="bash")
                    
                    st.markdown("**Alternative: Manual Assignment**")
                    guide = rbac_service.get_rbac_setup_guide(resource['resource_type'])
                    
                    for step in guide.get('manual_steps', []):
                        st.markdown(f"- {step}")
            else:
                st.success("✅ **All required permissions are granted!**")
    
    # Display errors if any
    if hasattr(st.session_state, 'permission_errors') and st.session_state.permission_errors:
        st.markdown("### ⚠️ Permission Check Errors")
        for error in st.session_state.permission_errors:
            st.error(f"❌ {error}")

def render_project_management_section(ai_foundry_service):
    """Render the project management section."""
    st.subheader("📋 Manage Projects")
    
    if not hasattr(st.session_state, 'selected_resource'):
        st.info("👆 Please discover and select a resource first in the 'Discover Resources' tab.")
        return
    
    resource = st.session_state.selected_resource
    st.markdown(f"**Managing projects for:** {resource['name']} ({resource['resource_type']})")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("📋 Load Projects", type="primary"):
            with st.spinner("Loading projects..."):
                projects, errors = ai_foundry_service.get_projects_for_resource(resource)
            
            st.session_state.current_projects = projects
            st.session_state.project_errors = errors
            
            if errors:
                st.warning("⚠️ Some errors occurred:")
                for error in errors:
                    st.error(error)
    
    with col2:
        if st.button("➕ Create New Project"):
            st.session_state.show_create_project = True
    
    # Show create project form
    if hasattr(st.session_state, 'show_create_project') and st.session_state.show_create_project:
        # Check if selected resource supports project creation
        resource_type = resource.get('resource_type', '')
        resource_id = resource.get('id', '')
        
        # Enhanced resource type detection
        is_cognitive_services = (
            'CognitiveServices' in resource_type or 
            'Microsoft.CognitiveServices' in resource_id or
            resource.get('resource_type') == 'account'
        )
        
        if is_cognitive_services:
            st.info(
                "ℹ️ **Cognitive Services Account Selected**\n\n"
                f"**Selected Resource:** {resource.get('name', 'Unknown')} (Cognitive Services Account)\n\n"
                "**Project Creation Methods:**\n"
                "• ✅ **Azure CLI** - Uses same APIs as Azure Portal (will be tried first)\n"
                "• ⚠️ **ARM API** - May have limitations for Cognitive Services accounts (fallback)\n\n"
                "**If creation fails:**\n"
                "• Ensure Azure CLI is installed and logged in (`az login`)\n"
                "• Try creating manually in Azure Portal\n"
                "• Consider using an AI Foundry Hub for guaranteed programmatic support\n\n"
                "**Proceeding with creation attempt...**"
            )
            
            # Add helpful guidance but don't block
            with st.expander("📋 About AI Foundry Resource Types", expanded=False):
                st.markdown("""
                **Understanding the Difference:**
                
                1. **AI Foundry Accounts (Cognitive Services)**
                   - Provide AI services like OpenAI, Speech, Vision
                   - Resource ID contains: `Microsoft.CognitiveServices/accounts`
                   - Project creation via Azure CLI (same as Portal)
                   - May have ARM API limitations
                
                2. **AI Foundry Hubs (ML Workspaces)**
                   - Project hosting environments
                   - Resource ID contains: `Microsoft.MachineLearningServices/workspaces`
                   - Full programmatic support via all methods
                   - Can contain multiple projects
                
                **Our Approach:**
                1. Try Azure CLI first (works for both types)
                2. Fall back to ARM API if needed
                3. Provide clear feedback on what worked/failed
                """)
        else:
            st.success(
                f"✅ **AI Foundry Hub Selected:** {resource.get('name', 'Unknown')}\n\n"
                "This resource type has full programmatic support for project creation via both Azure CLI and ARM API."
            )
            
        with st.expander("➕ Create New Project", expanded=True):
            with st.form("create_project_form"):
                project_name = st.text_input(
                    "Project Name",
                    placeholder="my-ai-project",
                    help="Use lowercase letters, numbers, and hyphens only"
                )
                project_description = st.text_area(
                    "Description (Optional)",
                    placeholder="Description of your AI project"
                )
                
                submitted = st.form_submit_button("🚀 Create Project")
                
                if submitted and project_name:
                    with st.spinner("Creating project..."):
                        # Add debug logging
                        st.write("🔍 **Debug Info:**")
                        st.write(f"- Resource type: {resource.get('resource_type', 'unknown')}")
                        st.write(f"- Resource name: {resource.get('name', 'unknown')}")
                        st.write(f"- Project name: {project_name}")
                        
                        # Check service method before calling
                        import inspect
                        method_source = inspect.getsource(ai_foundry_service.create_project)
                        
                        # Check if the service has the updated delegator method
                        if "_create_account_project" in method_source and "_create_hub_project" in method_source:
                            st.write("✅ Service has updated create_project delegator method")
                            
                            # Check the actual implementation methods
                            try:
                                account_source = inspect.getsource(ai_foundry_service._create_account_project)
                                if "management.azure.com" in account_source:
                                    st.write("✅ _create_account_project uses management.azure.com")
                                else:
                                    st.write("❌ _create_account_project does NOT use management.azure.com")
                            except:
                                st.write("⚠️ Could not check _create_account_project method")
                        else:
                            st.write("❌ Service has old create_project method")
                            
                        # Show credential type
                        cred_type = type(ai_foundry_service.credential).__name__
                        st.write(f"- Credential type: {cred_type}")
                        
                        success, message, project = ai_foundry_service.create_project(
                            resource, project_name, project_description
                        )
                    
                    if success:
                        st.success(f"✅ **Project Created Successfully!**")
                        st.success(f"Project '{project_name}' is now available in {resource.get('name', 'the selected resource')}")
                        st.session_state.show_create_project = False
                        # Refresh projects list
                        projects, _ = ai_foundry_service.get_projects_for_resource(resource)
                        st.session_state.current_projects = projects
                        st.rerun()
                    else:
                        st.error(f"❌ **Project Creation Failed**")
                        
                        # Enhanced error display with detailed messaging
                        if "does not support programmatic project creation" in message:
                            st.error("**Root Cause:** Cognitive Services accounts don't support programmatic project creation")
                            
                            with st.expander("📋 Why this happened & how to fix it", expanded=True):
                                st.markdown(f"""
                                **Error Details:**
                                ```
                                {message}
                                ```
                                
                                **What happened:**
                                You selected a Cognitive Services account instead of an AI Foundry Hub. While the Azure Portal can create projects in Cognitive Services accounts using internal APIs, this functionality is not available programmatically.
                                
                                **How to fix it:**
                                1. **Select an AI Foundry Hub** from the resource dropdown above
                                2. **Look for resources with type "hub"** instead of "account"
                                3. **Or create the project manually** in the Azure Portal
                                
                                **Understanding the difference:**
                                - **Accounts** = Service endpoints (OpenAI, Speech, etc.)
                                - **Hubs** = Project hosting environments
                                """)
                        else:
                            # Display the full error message for other types of errors
                            with st.expander("📋 Error Details", expanded=True):
                                st.code(message)
                                
                                if "MSI" in message:
                                    st.markdown("""
                                    **This appears to be an MSI (Managed Service Identity) related error.**
                                    
                                    Common causes:
                                    - Resource type doesn't support programmatic creation
                                    - Insufficient permissions on the resource
                                    - Authentication issues with Azure services
                                    """)
                        
                        # Add action buttons
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("🔄 Try Different Resource"):
                                st.session_state.show_create_project = False
                                st.rerun()
                        with col2:
                            if st.button("📖 View Documentation"):
                                st.markdown("[Azure AI Foundry Documentation](https://docs.microsoft.com/azure/ai-services/)")
                        with col3:
                            if st.button("🆘 Get Help"):
                                st.info("Check the Azure Portal or contact your Azure administrator for assistance.")
                                
                elif submitted and not project_name:
                    st.warning("⚠️ Please enter a project name.")
            
            if st.button("❌ Cancel"):
                st.session_state.show_create_project = False
                st.rerun()
    
    # Display current projects
    if hasattr(st.session_state, 'current_projects'):
        projects = st.session_state.current_projects
        
        if projects:
            st.markdown("### 📊 Current Projects")
            
            project_data = []
            for project in projects:
                project_data.append({
                    "Name": project.name,
                    "Display Name": project.display_name,
                    "Description": project.description,
                    "Location": project.location,
                    "Endpoint": project.endpoint
                })
            
            df_projects = pd.DataFrame(project_data)
            st.dataframe(df_projects, use_container_width=True)
            
            # Project selection for agent deployment
            project_labels = [f"{p.display_name} ({p.name})" for p in projects]
            selected_project_idx = st.selectbox(
                "🎯 Select Project for Agent Deployment:",
                range(len(project_labels)),
                format_func=lambda x: project_labels[x],
                key="selected_project_idx"
            )
            st.session_state.selected_project = projects[selected_project_idx]
            st.info(f"Selected project: **{st.session_state.selected_project.display_name}**")
        else:
            st.info("ℹ️ No projects found. Create a new project to get started.")

def render_agent_deployment_section(deployment_service):
    """Render the agent deployment section."""
    st.subheader("🤖 Deploy Agents")
    
    if not hasattr(st.session_state, 'selected_project'):
        st.info("👆 Please select a project first in the 'Manage Projects' tab.")
        return
    
    project = st.session_state.selected_project
    st.markdown(f"**Deploying to project:** {project.display_name}")
    
    # Check function configuration
    func_map = st.session_state.get("func_map", {})
    func_choices = st.session_state.get("func_choices", [])
    
    if not func_choices:
        st.warning("⚠️ **Function Configuration Required**")
        st.markdown("Please configure your Azure Function in the **Function Config** tab first.")
        return
    
    # Create tabs for agent operations
    agent_tab1, agent_tab2, agent_tab3 = st.tabs([
        "📋 Current Agents",
        "➕ Deploy New Agent",
        "🔧 Agent Details"
    ])
    
    with agent_tab1:
        render_current_agents_section(project, deployment_service)
    
    with agent_tab2:
        render_deploy_agent_section(project, func_map, func_choices, deployment_service)
    
    with agent_tab3:
        render_agent_details_section(project, deployment_service)

def render_current_agents_section(project, deployment_service):
    """Render the current agents section."""
    st.markdown("#### 📋 Current Agents")
    
    if st.button("🔄 Refresh Agents", type="primary"):
        with st.spinner("Loading agents..."):
            agents, errors = deployment_service.list_agents_in_project(project.endpoint)
        
        st.session_state.current_agents = agents
        st.session_state.agent_errors = errors
        
        if errors:
            st.warning("⚠️ Some errors occurred:")
            for error in errors:
                st.error(error)
    
    # Display current agents
    if hasattr(st.session_state, 'current_agents'):
        agents = st.session_state.current_agents
        
        if agents:
            st.success(f"✅ Found {len(agents)} agents")
            
            agent_data = []
            for agent in agents:
                agent_data.append({
                    "Name": agent.display_name,
                    "ID": agent.agent_id,
                    "Model": agent.model,
                    "Status": agent.status,
                    "Created": agent.created_at
                })
            
            df_agents = pd.DataFrame(agent_data)
            st.dataframe(df_agents, use_container_width=True)
            
            # Agent selection for details
            if agents:
                agent_labels = [f"{a.display_name} ({a.agent_id[:8]}...)" for a in agents]
                selected_agent_idx = st.selectbox(
                    "🎯 Select Agent for Details:",
                    range(len(agent_labels)),
                    format_func=lambda x: agent_labels[x],
                    key="selected_agent_idx"
                )
                st.session_state.selected_agent = agents[selected_agent_idx]
        else:
            st.info("ℹ️ No agents found in this project.")

def render_deploy_agent_section(project, func_map, func_choices):
    """Render the deploy new agent section."""
    st.markdown("#### ➕ Deploy New Agent")
    
    with st.form("deploy_agent_form"):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            agent_name = st.text_input(
                "Agent Name",
                placeholder="my-search-agent",
                help="Use lowercase letters, numbers, and hyphens only"
            )
            
            agent_display_name = st.text_input(
                "Display Name",
                placeholder="My Search Agent",
                help="Human-readable name for the agent"
            )
            
            model_deployment = st.text_input(
                "Model Deployment",
                value="gpt-4",
                help="Name of the model deployment to use"
            )
        
        with col2:
            func_selection = st.selectbox(
                "Azure Function to Connect",
                func_choices,
                help="Select the Azure Function this agent will call"
            )
            
            agent_description = st.text_area(
                "Agent Description",
                placeholder="This agent helps users search and retrieve information from documents...",
                help="Describe what this agent does"
            )
        
        agent_instructions = st.text_area(
            "Agent Instructions",
            placeholder="You are a helpful assistant that can search through documents and provide accurate information...",
            help="Instructions that guide the agent's behavior",
            height=150
        )
        
        submitted = st.form_submit_button("🚀 Deploy Agent", type="primary")
        
        if submitted and agent_name and agent_display_name:
            # Get function details
            func_name, func_rg = func_map[func_selection]
            base_url = f"https://{func_name}.azurewebsites.net/api"
            function_key = st.session_state.get("FUNCTION_KEY", "")
            
            if not function_key:
                st.error("❌ Function key not found. Please configure it in the Function Config tab.")
                return
            
            # Create agent configuration
            tools = [
                deployment_service.create_function_tool_config(
                    "agentic_retrieval", base_url, function_key
                )
            ]
            
            agent_config = AgentConfig(
                name=agent_name,
                display_name=agent_display_name,
                description=agent_description,
                model_deployment=model_deployment,
                instructions=agent_instructions,
                tools=tools,
                additional_properties={}
            )
            
            with st.spinner("Deploying agent..."):
                success, message, deployed_agent = deployment_service.create_agent(
                    project.endpoint, agent_config
                )
            
            if success:
                st.success(f"✅ Agent '{agent_display_name}' deployed successfully!")
                st.markdown(f"**Agent ID:** {deployed_agent.agent_id}")
                st.markdown(f"**Endpoint:** {deployed_agent.endpoint}")
                
                # Refresh agents list
                agents, _ = deployment_service.list_agents_in_project(project.endpoint)
                st.session_state.current_agents = agents
            else:
                st.error(f"❌ Failed to deploy agent: {message}")

def render_agent_details_section(project, deployment_service):
    """Render the agent details section."""
    st.markdown("#### 🔧 Agent Details")
    
    if not hasattr(st.session_state, 'selected_agent'):
        st.info("👆 Please select an agent from the 'Current Agents' tab.")
        return
    
    agent = st.session_state.selected_agent
    st.markdown(f"**Agent:** {agent.display_name}")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔄 Refresh Details", type="primary"):
            with st.spinner("Loading agent details..."):
                detailed_agent, errors = deployment_service.get_agent_details(
                    project.endpoint, agent.agent_id
                )
            
            if detailed_agent:
                st.session_state.detailed_agent = detailed_agent
            
            if errors:
                st.session_state.agent_detail_errors = errors
    
    with col2:
        if st.button("🗑️ Delete Agent", type="secondary"):
            if st.session_state.get('confirm_delete_agent'):
                with st.spinner("Deleting agent..."):
                    success, message = deployment_service.delete_agent(
                        project.endpoint, agent.agent_id
                    )
                
                if success:
                    st.success(f"✅ Agent deleted successfully!")
                    # Refresh agents list
                    agents, _ = deployment_service.list_agents_in_project(project.endpoint)
                    st.session_state.current_agents = agents
                    if 'selected_agent' in st.session_state:
                        del st.session_state.selected_agent
                    st.session_state.confirm_delete_agent = False
                    st.rerun()
                else:
                    st.error(f"❌ Failed to delete agent: {message}")
            else:
                st.session_state.confirm_delete_agent = True
                st.warning("⚠️ Click 'Delete Agent' again to confirm deletion.")
                st.rerun()
    
    # Display detailed agent information
    if hasattr(st.session_state, 'detailed_agent'):
        detailed_agent = st.session_state.detailed_agent
        
        st.markdown("### 📊 Agent Information")
        
        info_data = {
            "Property": [
                "Agent ID", "Name", "Display Name", "Description", 
                "Model", "Status", "Endpoint", "Created At"
            ],
            "Value": [
                detailed_agent.agent_id,
                detailed_agent.name,
                detailed_agent.display_name,
                detailed_agent.description,
                detailed_agent.model,
                detailed_agent.status,
                detailed_agent.endpoint,
                detailed_agent.created_at
            ]
        }
        
        df_info = pd.DataFrame(info_data)
        st.dataframe(df_info, use_container_width=True)
        
        # Show raw properties if available
        if detailed_agent.properties:
            with st.expander("🔍 Raw Agent Properties"):
                st.json(detailed_agent.properties)
    
    # Display errors if any
    if hasattr(st.session_state, 'agent_detail_errors') and st.session_state.agent_detail_errors:
        st.markdown("### ⚠️ Agent Detail Errors")
        for error in st.session_state.agent_detail_errors:
            st.error(error)
