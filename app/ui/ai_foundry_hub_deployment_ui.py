"""
AI Foundry Hub Deployment UI Component
-------------------------------------
Streamlit UI component for deploying new AI Foundry Hubs using bicep templates.

This component provides:
- Configuration form for deployment parameters
- Resource selection (new vs existing)
- Network configuration options
- Private endpoint and DNS settings
- Deployment execution and monitoring
"""

import streamlit as st
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from services.ai_foundry_hub_deployment import (
    AIFoundryHubDeploymentService,
    AIFoundryHubDeploymentConfig,
    NetworkConfig,
    DeploymentResource
)

logger = logging.getLogger(__name__)

class AIFoundryHubDeploymentUI:
    """UI component for AI Foundry Hub deployment."""
    
    def __init__(self):
        """Initialize the UI component."""
        self.service = AIFoundryHubDeploymentService()
        self.deployment_key = "ai_foundry_hub_deployment"
    
    def render_deployment_form(self) -> Optional[AIFoundryHubDeploymentConfig]:
        """Render the deployment configuration form."""
        st.subheader("🚀 Deploy New AI Foundry Hub")
        
        # Validate template first
        valid, msg = self.service.validate_template_path()
        if not valid:
            st.error(f"❌ Template validation failed: {msg}")
            return None
        
        st.success("✅ Bicep template validated successfully")
        
        # Create configuration form
        with st.form("ai_foundry_hub_config"):
            st.markdown("### Basic Configuration")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Location selection
                locations = self.service.get_available_locations()
                location = st.selectbox(
                    "🌍 Location",
                    locations,
                    index=locations.index("eastus2") if "eastus2" in locations else 0,
                    help="Select the Azure region for deployment"
                )
                
                # AI Services name
                ai_services_name = st.text_input(
                    "🤖 AI Services Name",
                    value="aiservices",
                    help="Name for the AI Services resource"
                )
                
                # Project name
                project_name = st.text_input(
                    "📁 Project Name",
                    value="project",
                    help="Name for the AI Foundry project"
                )
            
            with col2:
                # Display name
                display_name = st.text_input(
                    "🏷️ Display Name",
                    value="Network Secured Agent Project",
                    help="Display name for the project"
                )
                
                # Model configuration
                model_name = st.selectbox(
                    "🧠 Model Name",
                    ["gpt-4o", "gpt-4", "gpt-35-turbo"],
                    help="Select the AI model to deploy"
                )
                
                # Model capacity
                model_capacity = st.number_input(
                    "⚡ Model Capacity",
                    min_value=1,
                    max_value=100,
                    value=30,
                    help="Model capacity in TPM (thousands of tokens per minute)"
                )
            
            # Project description
            project_description = st.text_area(
                "📝 Project Description",
                value="A project for the AI Foundry account with network secured deployed Agent",
                help="Description of the AI Foundry project"
            )
            
            # Network Configuration
            st.markdown("### 🌐 Network Configuration")
            
            create_new_vnet = st.checkbox(
                "Create New Virtual Network",
                value=True,
                help="Create a new VNet or use an existing one"
            )
            
            if create_new_vnet:
                col1, col2 = st.columns(2)
                with col1:
                    vnet_name = st.text_input(
                        "VNet Name",
                        value="agent-vnet-test",
                        help="Name for the new virtual network"
                    )
                    vnet_address_prefix = st.text_input(
                        "VNet Address Prefix",
                        value="192.168.0.0/16",
                        help="Address space for the virtual network"
                    )
                with col2:
                    agent_subnet_name = st.text_input(
                        "Agent Subnet Name",
                        value="agent-subnet",
                        help="Name for the agent subnet"
                    )
                    agent_subnet_prefix = st.text_input(
                        "Agent Subnet Prefix",
                        value="192.168.0.0/24",
                        help="Address space for the agent subnet"
                    )
                
                col1, col2 = st.columns(2)
                with col1:
                    pe_subnet_name = st.text_input(
                        "Private Endpoint Subnet Name",
                        value="pe-subnet",
                        help="Name for the private endpoint subnet"
                    )
                with col2:
                    pe_subnet_prefix = st.text_input(
                        "Private Endpoint Subnet Prefix",
                        value="192.168.1.0/24",
                        help="Address space for the private endpoint subnet"
                    )
                
                existing_vnet_resource_id = ""
            else:
                # Get available VNets
                vnets = self.service.get_subscription_resources("Microsoft.Network/virtualNetworks")
                if vnets:
                    vnet_options = {f"{vnet['name']} ({vnet['resourceGroup']})": vnet['id'] for vnet in vnets}
                    selected_vnet = st.selectbox(
                        "Select Existing Virtual Network",
                        options=list(vnet_options.keys()),
                        help="Select an existing virtual network"
                    )
                    existing_vnet_resource_id = vnet_options.get(selected_vnet, "")
                    
                    # Use default names for existing VNet
                    vnet_name = "existing-vnet"
                    vnet_address_prefix = "192.168.0.0/16"
                    agent_subnet_name = st.text_input(
                        "Agent Subnet Name",
                        value="agent-subnet",
                        help="Name of the agent subnet in the existing VNet"
                    )
                    agent_subnet_prefix = st.text_input(
                        "Agent Subnet Prefix",
                        value="192.168.0.0/24",
                        help="Address space for the agent subnet"
                    )
                    pe_subnet_name = st.text_input(
                        "Private Endpoint Subnet Name",
                        value="pe-subnet",
                        help="Name of the private endpoint subnet in the existing VNet"
                    )
                    pe_subnet_prefix = st.text_input(
                        "Private Endpoint Subnet Prefix",
                        value="192.168.1.0/24",
                        help="Address space for the private endpoint subnet"
                    )
                else:
                    st.warning("No existing virtual networks found. Creating new VNet.")
                    create_new_vnet = True
                    existing_vnet_resource_id = ""
                    vnet_name = "agent-vnet-test"
                    vnet_address_prefix = "192.168.0.0/16"
                    agent_subnet_name = "agent-subnet"
                    agent_subnet_prefix = "192.168.0.0/24"
                    pe_subnet_name = "pe-subnet"
                    pe_subnet_prefix = "192.168.1.0/24"
            
            # Resource Configuration
            st.markdown("### 📦 Resource Configuration")
            
            # Cosmos DB Configuration
            st.markdown("#### 🗃️ Cosmos DB")
            create_new_cosmos = st.checkbox(
                "Create New Cosmos DB",
                value=True,
                key="create_cosmos",
                help="Create a new Cosmos DB or use an existing one"
            )
            
            cosmos_resource_id = ""
            if not create_new_cosmos:
                cosmos_resources = self.service.get_subscription_resources("Microsoft.DocumentDB/databaseAccounts")
                if cosmos_resources:
                    cosmos_options = {f"{res['name']} ({res['resourceGroup']})": res['id'] for res in cosmos_resources}
                    selected_cosmos = st.selectbox(
                        "Select Existing Cosmos DB",
                        options=list(cosmos_options.keys()),
                        help="Select an existing Cosmos DB account"
                    )
                    cosmos_resource_id = cosmos_options.get(selected_cosmos, "")
                else:
                    st.warning("No existing Cosmos DB accounts found. Creating new Cosmos DB.")
                    create_new_cosmos = True
            
            # AI Search Configuration
            st.markdown("#### 🔍 AI Search")
            create_new_search = st.checkbox(
                "Create New AI Search",
                value=True,
                key="create_search",
                help="Create a new AI Search service or use an existing one"
            )
            
            search_resource_id = ""
            if not create_new_search:
                search_resources = self.service.get_subscription_resources("Microsoft.Search/searchServices")
                if search_resources:
                    search_options = {f"{res['name']} ({res['resourceGroup']})": res['id'] for res in search_resources}
                    selected_search = st.selectbox(
                        "Select Existing AI Search",
                        options=list(search_options.keys()),
                        help="Select an existing AI Search service"
                    )
                    search_resource_id = search_options.get(selected_search, "")
                else:
                    st.warning("No existing AI Search services found. Creating new AI Search.")
                    create_new_search = True
            
            # Storage Account Configuration
            st.markdown("#### 🗂️ Storage Account")
            create_new_storage = st.checkbox(
                "Create New Storage Account",
                value=True,
                key="create_storage",
                help="Create a new Storage Account or use an existing one"
            )
            
            storage_resource_id = ""
            if not create_new_storage:
                storage_resources = self.service.get_subscription_resources("Microsoft.Storage/storageAccounts")
                if storage_resources:
                    storage_options = {f"{res['name']} ({res['resourceGroup']})": res['id'] for res in storage_resources}
                    selected_storage = st.selectbox(
                        "Select Existing Storage Account",
                        options=list(storage_options.keys()),
                        help="Select an existing Storage Account"
                    )
                    storage_resource_id = storage_options.get(selected_storage, "")
                else:
                    st.warning("No existing Storage Accounts found. Creating new Storage Account.")
                    create_new_storage = True
            
            # Submit button
            submitted = st.form_submit_button("🚀 Deploy AI Foundry Hub", use_container_width=True)
            
            if submitted:
                # Create configuration
                network_config = NetworkConfig(
                    create_new_vnet=create_new_vnet,
                    existing_vnet_resource_id=existing_vnet_resource_id,
                    vnet_name=vnet_name,
                    vnet_address_prefix=vnet_address_prefix,
                    agent_subnet_name=agent_subnet_name,
                    agent_subnet_prefix=agent_subnet_prefix,
                    pe_subnet_name=pe_subnet_name,
                    pe_subnet_prefix=pe_subnet_prefix
                )
                
                cosmos_db = DeploymentResource(
                    name="cosmos-db",
                    resource_type="Microsoft.DocumentDB/databaseAccounts",
                    create_new=create_new_cosmos,
                    existing_resource_id=cosmos_resource_id
                )
                
                ai_search = DeploymentResource(
                    name="ai-search",
                    resource_type="Microsoft.Search/searchServices",
                    create_new=create_new_search,
                    existing_resource_id=search_resource_id
                )
                
                storage_account = DeploymentResource(
                    name="storage-account",
                    resource_type="Microsoft.Storage/storageAccounts",
                    create_new=create_new_storage,
                    existing_resource_id=storage_resource_id
                )
                
                config = AIFoundryHubDeploymentConfig(
                    location=location,
                    ai_services_name=ai_services_name,
                    project_name=project_name,
                    project_description=project_description,
                    display_name=display_name,
                    model_name=model_name,
                    model_capacity=model_capacity,
                    network_config=network_config,
                    cosmos_db=cosmos_db,
                    ai_search=ai_search,
                    storage_account=storage_account
                )
                
                return config
        
        return None
    
    def render_deployment_execution(self, config: AIFoundryHubDeploymentConfig):
        """Render the deployment execution interface."""
        st.subheader("🎯 Deployment Execution")
        
        # Validate configuration
        issues = self.service.validate_deployment_config(config)
        if issues:
            st.error("❌ Configuration validation failed:")
            for issue in issues:
                st.error(f"• {issue}")
            return
        
        st.success("✅ Configuration validated successfully")
        
        # Resource group selection
        resource_groups = self.service.get_subscription_resource_groups()
        if not resource_groups:
            st.error("❌ No resource groups found. Please create a resource group first.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_rg = st.selectbox(
                "🏗️ Resource Group",
                resource_groups,
                help="Select the resource group for deployment"
            )
        
        with col2:
            deployment_name = st.text_input(
                "📋 Deployment Name",
                value=f"ai-foundry-hub-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                help="Name for the deployment"
            )
        
        # Show deployment configuration summary
        with st.expander("📋 Deployment Configuration Summary"):
            st.json({
                "location": config.location,
                "ai_services_name": config.ai_services_name,
                "project_name": config.project_name,
                "model_name": config.model_name,
                "model_capacity": config.model_capacity,
                "create_new_vnet": config.network_config.create_new_vnet,
                "create_new_cosmos": config.cosmos_db.create_new,
                "create_new_search": config.ai_search.create_new,
                "create_new_storage": config.storage_account.create_new
            })
        
        # Deployment button
        if st.button("🚀 Start Deployment", type="primary", use_container_width=True):
            self._execute_deployment(config, selected_rg, deployment_name)
    
    def _execute_deployment(self, config: AIFoundryHubDeploymentConfig, resource_group: str, deployment_name: str):
        """Execute the deployment with progress tracking."""
        # Initialize deployment state
        deployment_state = {
            "status": "starting",
            "start_time": datetime.now().isoformat(),
            "resource_group": resource_group,
            "deployment_name": deployment_name,
            "config": config.__dict__
        }
        
        # Store deployment state in session
        if self.deployment_key not in st.session_state:
            st.session_state[self.deployment_key] = {}
        
        st.session_state[self.deployment_key][deployment_name] = deployment_state
        
        # Create progress containers
        progress_container = st.container()
        log_container = st.container()
        
        with progress_container:
            st.info("🚀 Starting deployment...")
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        with log_container:
            log_placeholder = st.empty()
        
        try:
            # Update progress
            progress_bar.progress(10)
            status_text.text("Initializing deployment...")
            
            # Start deployment
            success, message, output = self.service.deploy_ai_foundry_hub(
                config, resource_group, deployment_name
            )
            
            if success:
                progress_bar.progress(100)
                status_text.text("Deployment completed successfully!")
                st.success(f"✅ {message}")
                
                # Update deployment state
                deployment_state["status"] = "completed"
                deployment_state["end_time"] = datetime.now().isoformat()
                deployment_state["success"] = True
                deployment_state["message"] = message
                
                # Show deployment outputs
                if output:
                    with st.expander("📋 Deployment Output"):
                        st.text(output)
                
                # Get deployment outputs
                success_outputs, msg_outputs, outputs = self.service.get_deployment_outputs(
                    resource_group, deployment_name
                )
                
                if success_outputs and outputs:
                    with st.expander("📊 Deployment Results"):
                        st.json(outputs)
            else:
                progress_bar.progress(0)
                status_text.text("Deployment failed!")
                st.error(f"❌ {message}")
                
                # Update deployment state
                deployment_state["status"] = "failed"
                deployment_state["end_time"] = datetime.now().isoformat()
                deployment_state["success"] = False
                deployment_state["message"] = message
                
                # Show deployment output for debugging
                if output:
                    with st.expander("🔍 Deployment Output (for debugging)"):
                        st.text(output)
        
        except Exception as e:
            progress_bar.progress(0)
            status_text.text("Deployment error!")
            st.error(f"❌ Deployment error: {str(e)}")
            
            # Update deployment state
            deployment_state["status"] = "error"
            deployment_state["end_time"] = datetime.now().isoformat()
            deployment_state["success"] = False
            deployment_state["message"] = str(e)
        
        # Update session state
        st.session_state[self.deployment_key][deployment_name] = deployment_state
    
    def render_deployment_history(self):
        """Render deployment history and status."""
        st.subheader("📊 Deployment History")
        
        if (self.deployment_key not in st.session_state or 
            not st.session_state[self.deployment_key]):
            st.info("No deployments found.")
            return
        
        deployments = st.session_state[self.deployment_key]
        
        for deployment_name, deployment_state in deployments.items():
            with st.expander(f"📋 {deployment_name}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Status:** {deployment_state['status']}")
                    st.write(f"**Resource Group:** {deployment_state['resource_group']}")
                
                with col2:
                    st.write(f"**Start Time:** {deployment_state['start_time']}")
                    if 'end_time' in deployment_state:
                        st.write(f"**End Time:** {deployment_state['end_time']}")
                
                with col3:
                    if deployment_state['status'] == 'completed':
                        st.success("✅ Completed")
                    elif deployment_state['status'] == 'failed':
                        st.error("❌ Failed")
                    elif deployment_state['status'] == 'error':
                        st.error("💥 Error")
                    else:
                        st.info("⏳ In Progress")
                
                # Show message if available
                if 'message' in deployment_state:
                    st.write(f"**Message:** {deployment_state['message']}")
                
                # Show deployment status button
                if st.button(f"🔍 Check Status", key=f"status_{deployment_name}"):
                    self._check_deployment_status(
                        deployment_state['resource_group'],
                        deployment_name
                    )
    
    def _check_deployment_status(self, resource_group: str, deployment_name: str):
        """Check and display deployment status."""
        success, message, deployment_info = self.service.get_deployment_status(
            resource_group, deployment_name
        )
        
        if success and deployment_info:
            st.json(deployment_info)
        else:
            st.error(f"❌ Failed to get deployment status: {message}")
    
    def render(self):
        """Main render method for the AI Foundry Hub deployment UI."""
        st.title("🏗️ AI Foundry Hub Deployment")
        
        # Create tabs for different sections
        tab1, tab2 = st.tabs(["🚀 New Deployment", "📊 Deployment History"])
        
        with tab1:
            # Render deployment form
            config = self.render_deployment_form()
            
            if config:
                st.markdown("---")
                # Render deployment execution
                self.render_deployment_execution(config)
        
        with tab2:
            # Render deployment history
            self.render_deployment_history()

def render_ai_foundry_hub_deployment_ui():
    """Render the AI Foundry Hub deployment UI."""
    ui = AIFoundryHubDeploymentUI()
    ui.render()
