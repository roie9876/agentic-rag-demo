"""
AI Foundry Hub Deployment UI Component
-------------------------------------
UI component for deploying new AI Foundry Hubs with comprehensive configuration options.

This component provides:
- Resource selection (new vs existing)
- Network configuration
- Private endpoint configuration
- DNS configuration
- Deployment progress tracking
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import json

from services.ai_foundry_hub_deployment import (
    AIFoundryHubDeploymentService,
    AIFoundryHubDeploymentConfig,
    DeploymentResource,
    NetworkConfig
)

logger = logging.getLogger(__name__)

class AIFoundryHubDeploymentUI:
    """UI component for AI Foundry Hub deployment."""
    
    def __init__(self):
        """Initialize the deployment UI."""
        self.service = AIFoundryHubDeploymentService()
    
    def render_deployment_tab(self) -> None:
        """Render the main deployment tab."""
        st.header("🚀 Deploy New AI Foundry Account")
        
        # Template validation
        valid, msg = self.service.validate_template_path()
        if not valid:
            st.error(f"❌ Template validation failed: {msg}")
            st.info("Please ensure the bicep template is available in the correct directory.")
            return
        else:
            st.success("✅ Bicep template validated successfully")
        
        # Create deployment tabs
        config_tab, preview_tab, deploy_tab, status_tab = st.tabs([
            "⚙️ Configuration",
            "👀 Preview",
            "🚀 Deploy",
            "📊 Status"
        ])
        
        with config_tab:
            self._render_configuration_tab()
        
        with preview_tab:
            self._render_preview_tab()
        
        with deploy_tab:
            self._render_deploy_tab()
        
        with status_tab:
            self._render_status_tab()
    
    def _render_configuration_tab(self) -> None:
        """Render the configuration tab."""
        st.subheader("🔧 Deployment Configuration")
        
        # Configuration save/load section
        st.markdown("### 💾 Configuration Management")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            use_last_config = st.checkbox(
                "🔄 Use Last Configuration",
                value=False,
                help="Load the last saved configuration to avoid re-entering all parameters"
            )
        
        with col2:
            saved_configs = self.service.list_saved_configs()
            if saved_configs:
                selected_config = st.selectbox(
                    "📁 Saved Configs",
                    options=[""] + saved_configs,
                    help="Select a previously saved configuration"
                )
                
                if selected_config and st.button("📂 Load Config"):
                    loaded_config = self.service.load_deployment_config(selected_config)
                    if loaded_config:
                        st.session_state.deployment_config = loaded_config
                        st.success(f"✅ Configuration '{selected_config}' loaded successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to load configuration '{selected_config}'")
        
        with col3:
            config_name = st.text_input(
                "💾 Save As",
                value="my_deployment",
                help="Enter a name to save the current configuration"
            )
            
            if st.button("💾 Save Config"):
                if config_name.strip():
                    if hasattr(st.session_state, 'deployment_config'):
                        if self.service.save_deployment_config(st.session_state.deployment_config, config_name.strip()):
                            st.success(f"✅ Configuration saved as '{config_name.strip()}'!")
                        else:
                            st.error("❌ Failed to save configuration")
                    else:
                        st.error("❌ No configuration to save")
                else:
                    st.error("❌ Please enter a configuration name")
        
        # Load last configuration if requested
        if use_last_config and 'deployment_config' not in st.session_state:
            loaded_config = self.service.load_deployment_config("last_deployment")
            if loaded_config:
                st.session_state.deployment_config = loaded_config
                st.success("✅ Last configuration loaded successfully!")
                st.rerun()
            else:
                st.info("ℹ️ No previous configuration found")
        
        # Initialize config in session state if not exists
        if 'deployment_config' not in st.session_state:
            st.session_state.deployment_config = AIFoundryHubDeploymentConfig()
        
        config = st.session_state.deployment_config
        
        st.markdown("---")
        
        # Basic Settings
        with st.expander("📋 Basic Settings", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                config.location = st.selectbox(
                    "🌍 Location",
                    self.service.get_available_locations(),
                    index=self.service.get_available_locations().index(config.location)
                )
                
                config.ai_services_name = st.text_input(
                    "🤖 AI Services Name",
                    value=config.ai_services_name,
                    help="Base name for AI services (unique suffix will be added)"
                )
                
                config.project_name = st.text_input(
                    "📁 Project Name",
                    value=config.project_name,
                    help="Name for the initial project"
                )
            
            with col2:
                config.project_description = st.text_area(
                    "📝 Project Description",
                    value=config.project_description,
                    height=100
                )
                
                config.display_name = st.text_input(
                    "🏷️ Display Name",
                    value=config.display_name
                )
        
        # Model Configuration
        with st.expander("🧠 Model Configuration", expanded=False):
            # OpenAI Deployment Option
            config.skip_openai_deployment = st.checkbox(
                "⚠️ Skip OpenAI Model Deployment", 
                value=config.skip_openai_deployment,
                help="Check this to skip Azure OpenAI deployment (faster deployment, no models). Uncheck to deploy OpenAI models."
            )
            
            if not config.skip_openai_deployment:
                st.info("🔄 OpenAI models will be deployed (adds ~5-10 minutes to deployment)")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    config.model_name = st.selectbox(
                        "Model Name",
                        ["gpt-4o", "gpt-4", "gpt-35-turbo"],
                        index=0 if config.model_name == "gpt-4o" else 1
                    )
                    
                    config.model_format = st.selectbox(
                        "Model Format",
                        ["OpenAI"],
                        index=0
                    )
                    
                    config.model_version = st.text_input(
                        "Model Version",
                        value=config.model_version
                    )
                
                with col2:
                    config.model_sku_name = st.selectbox(
                        "Model SKU",
                        ["GlobalStandard", "Standard"],
                        index=0 if config.model_sku_name == "GlobalStandard" else 1
                    )
                    
                    config.model_capacity = st.number_input(
                        "Model Capacity (TPM)",
                        min_value=1,
                        max_value=1000,
                        value=config.model_capacity,
                        help="Tokens per minute"
                    )
            else:
                st.success("✅ OpenAI deployment will be skipped - faster Account setup!")
                st.info("💡 You can deploy models later using the Azure portal or Azure CLI")
        
        # Network Configuration
        self._render_network_config(config)
        
        # Resource Configuration
        self._render_resource_config(config)
        
        # Update session state
        st.session_state.deployment_config = config
    
    def _render_network_config(self, config: AIFoundryHubDeploymentConfig) -> None:
        """Render network configuration section."""
        with st.expander("🌐 Network Configuration", expanded=True):
            st.markdown("### Virtual Network Settings")
            
            config.network_config.create_new_vnet = st.radio(
                "VNet Configuration",
                ["Create New VNet", "Use Existing VNet"],
                index=0 if config.network_config.create_new_vnet else 1
            ) == "Create New VNet"
            
            if config.network_config.create_new_vnet:
                # New VNet settings
                col1, col2 = st.columns(2)
                
                with col1:
                    config.network_config.vnet_name = st.text_input(
                        "VNet Name",
                        value=config.network_config.vnet_name
                    )
                    
                    config.network_config.vnet_address_prefix = st.text_input(
                        "VNet Address Prefix",
                        value=config.network_config.vnet_address_prefix,
                        help="Example: 192.168.0.0/16"
                    )
                
                with col2:
                    config.network_config.agent_subnet_name = st.text_input(
                        "Agent Subnet Name",
                        value=config.network_config.agent_subnet_name
                    )
                    
                    config.network_config.agent_subnet_prefix = st.text_input(
                        "Agent Subnet Prefix",
                        value=config.network_config.agent_subnet_prefix,
                        help="Example: 192.168.0.0/24"
                    )
                
                # Private Endpoint Subnet
                col3, col4 = st.columns(2)
                
                with col3:
                    config.network_config.pe_subnet_name = st.text_input(
                        "Private Endpoint Subnet Name",
                        value=config.network_config.pe_subnet_name
                    )
                
                with col4:
                    config.network_config.pe_subnet_prefix = st.text_input(
                        "Private Endpoint Subnet Prefix",
                        value=config.network_config.pe_subnet_prefix,
                        help="Example: 192.168.1.0/24"
                    )
            
            else:
                # Existing VNet settings
                st.markdown("**Select Existing VNet:**")
                
                # Get available VNets
                vnets = self.service.get_subscription_resources("Microsoft.Network/virtualNetworks")
                
                if vnets:
                    vnet_options = {f"{vnet['name']} ({vnet['resourceGroup']})": vnet['id'] for vnet in vnets}
                    
                    # Find the current selection index based on saved configuration
                    current_index = 0
                    if config.network_config.existing_vnet_resource_id:
                        for i, (option_text, vnet_id) in enumerate(vnet_options.items()):
                            if vnet_id == config.network_config.existing_vnet_resource_id:
                                current_index = i
                                break
                    
                    selected_vnet = st.selectbox(
                        "Select VNet",
                        list(vnet_options.keys()),
                        index=current_index,
                        key="vnet_selector",
                        help="Select an existing Virtual Network"
                    )
                    
                    if selected_vnet:
                        config.network_config.existing_vnet_resource_id = vnet_options[selected_vnet]
                        
                        # Show selected VNet details
                        selected_vnet_info = next(v for v in vnets if v['id'] == config.network_config.existing_vnet_resource_id)
                        st.info(f"Selected VNet: {selected_vnet_info['name']} in {selected_vnet_info['location']}")
                        
                        # Get subnets for the selected VNet
                        st.markdown("**Subnet Configuration:**")
                        subnets = self.service.get_vnet_subnets(config.network_config.existing_vnet_resource_id)
                        
                        if subnets:
                            # Show subnet usage option
                            subnet_choice = st.radio(
                                "How would you like to configure subnets?",
                                ["Use existing subnets", "Create new subnets"],
                                index=0 if hasattr(config.network_config, 'existing_agent_subnet_id') and config.network_config.existing_agent_subnet_id else 1,
                                help="Choose whether to use existing subnets or create new ones in the VNet"
                            )
                            
                            if subnet_choice == "Use existing subnets":
                                # Clear new subnet fields when switching to existing
                                if not hasattr(config.network_config, 'existing_agent_subnet_id'):
                                    config.network_config.existing_agent_subnet_id = ""
                                    config.network_config.existing_pe_subnet_id = ""
                                
                                subnet_options = {f"{subnet['name']} ({subnet['addressPrefix']})": subnet['id'] for subnet in subnets}
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.markdown("**Agent Subnet:**")
                                    
                                    # Find current agent subnet index
                                    agent_subnet_index = 0
                                    if config.network_config.existing_agent_subnet_id:
                                        for i, (option_text, subnet_id) in enumerate(subnet_options.items()):
                                            if subnet_id == config.network_config.existing_agent_subnet_id:
                                                agent_subnet_index = i
                                                break
                                    
                                    selected_agent_subnet = st.selectbox(
                                        "Select Agent Subnet",
                                        list(subnet_options.keys()),
                                        index=agent_subnet_index,
                                        key="agent_subnet_selector",
                                        help="Subnet for AI Foundry agents and compute resources"
                                    )
                                    
                                    if selected_agent_subnet:
                                        config.network_config.existing_agent_subnet_id = subnet_options[selected_agent_subnet]
                                        # Extract subnet name from selection
                                        config.network_config.agent_subnet_name = selected_agent_subnet.split(' (')[0]
                                        
                                        # Show subnet details
                                        selected_subnet_info = next(s for s in subnets if s['id'] == config.network_config.existing_agent_subnet_id)
                                        st.success(f"✅ Agent Subnet: {selected_subnet_info['name']}")
                                        st.caption(f"Address: {selected_subnet_info['addressPrefix']}")
                                
                                with col2:
                                    st.markdown("**Private Endpoint Subnet:**")
                                    
                                    # Find current PE subnet index
                                    pe_subnet_index = 0
                                    if config.network_config.existing_pe_subnet_id:
                                        for i, (option_text, subnet_id) in enumerate(subnet_options.items()):
                                            if subnet_id == config.network_config.existing_pe_subnet_id:
                                                pe_subnet_index = i
                                                break
                                    
                                    selected_pe_subnet = st.selectbox(
                                        "Select PE Subnet",
                                        list(subnet_options.keys()),
                                        index=pe_subnet_index,
                                        key="pe_subnet_selector",
                                        help="Subnet for private endpoints"
                                    )
                                    
                                    if selected_pe_subnet:
                                        config.network_config.existing_pe_subnet_id = subnet_options[selected_pe_subnet]
                                        # Extract subnet name from selection
                                        config.network_config.pe_subnet_name = selected_pe_subnet.split(' (')[0]
                                        
                                        # Show subnet details
                                        selected_subnet_info = next(s for s in subnets if s['id'] == config.network_config.existing_pe_subnet_id)
                                        st.success(f"✅ PE Subnet: {selected_subnet_info['name']}")
                                        st.caption(f"Address: {selected_subnet_info['addressPrefix']}")
                            
                            else:  # Create new subnets
                                # Clear existing subnet IDs when switching to new
                                config.network_config.existing_agent_subnet_id = ""
                                config.network_config.existing_pe_subnet_id = ""
                                
                                st.info("ℹ️ New subnets will be created in your existing VNet")
                                
                                # Option to create new subnets with address prefixes
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.markdown("**Agent Subnet (New):**")
                                    config.network_config.agent_subnet_name = st.text_input(
                                        "Agent Subnet Name",
                                        value=config.network_config.agent_subnet_name,
                                        help="Name for new subnet for agents"
                                    )
                                    config.network_config.agent_subnet_prefix = st.text_input(
                                        "Agent Subnet Address Prefix",
                                        value=config.network_config.agent_subnet_prefix,
                                        help="Address prefix for agent subnet (e.g., 10.0.5.0/24)"
                                    )
                                
                                with col2:
                                    st.markdown("**Private Endpoint Subnet (New):**")
                                    config.network_config.pe_subnet_name = st.text_input(
                                        "Private Endpoint Subnet Name",
                                        value=config.network_config.pe_subnet_name,
                                        help="Name for new subnet for private endpoints"
                                    )
                                    config.network_config.pe_subnet_prefix = st.text_input(
                                        "Private Endpoint Subnet Address Prefix",
                                        value=config.network_config.pe_subnet_prefix,
                                        help="Address prefix for PE subnet (e.g., 10.0.6.0/24)"
                                    )
                        
                        else:
                            st.warning("No subnets found in the selected VNet")
                            st.info("ℹ️ The deployment will create new subnets in your existing VNet")
                            
                            # Clear existing subnet IDs since no subnets exist
                            config.network_config.existing_agent_subnet_id = ""
                            config.network_config.existing_pe_subnet_id = ""
                            
                            # Option to create new subnets with address prefixes
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("**Agent Subnet (New):**")
                                config.network_config.agent_subnet_name = st.text_input(
                                    "Agent Subnet Name",
                                    value=config.network_config.agent_subnet_name,
                                    help="Name for new subnet for agents"
                                )
                                config.network_config.agent_subnet_prefix = st.text_input(
                                    "Agent Subnet Address Prefix",
                                    value=config.network_config.agent_subnet_prefix,
                                    help="Address prefix for agent subnet (e.g., 10.0.5.0/24)"
                                )
                            
                            with col2:
                                st.markdown("**Private Endpoint Subnet (New):**")
                                config.network_config.pe_subnet_name = st.text_input(
                                    "Private Endpoint Subnet Name",
                                    value=config.network_config.pe_subnet_name,
                                    help="Name for new subnet for private endpoints"
                                )
                                config.network_config.pe_subnet_prefix = st.text_input(
                                    "PE Subnet Address Prefix",
                                    value=config.network_config.pe_subnet_prefix,
                                    help="Address prefix for PE subnet (e.g., 10.0.6.0/24)"
                                )
                        
                        # Add option to create new subnets even when existing subnets are found
                        if subnets:
                            st.markdown("---")
                            st.markdown("**Alternative: Create New Subnets**")
                            create_new_subnets = st.checkbox(
                                "Create new subnets instead of using existing ones",
                                key="create_new_subnets_option",
                                help="Check this to create new dedicated subnets for AI Foundry Account"
                            )
                            
                            if create_new_subnets:
                                # Clear existing subnet selections
                                config.network_config.existing_agent_subnet_id = ""
                                config.network_config.existing_pe_subnet_id = ""
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.markdown("**New Agent Subnet:**")
                                    config.network_config.agent_subnet_name = st.text_input(
                                        "New Agent Subnet Name",
                                        value="AIFoundryAgentSubnet",
                                        key="new_agent_subnet_name",
                                        help="Name for new subnet for agents"
                                    )
                                    config.network_config.agent_subnet_prefix = st.text_input(
                                        "New Agent Subnet Address Prefix",
                                        value="",
                                        key="new_agent_subnet_prefix",
                                        help="Address prefix for agent subnet (e.g., 10.0.5.0/24)"
                                    )
                                
                                with col2:
                                    st.markdown("**New Private Endpoint Subnet:**")
                                    config.network_config.pe_subnet_name = st.text_input(
                                        "New PE Subnet Name",
                                        value="AIFoundryPESubnet",
                                        key="new_pe_subnet_name",
                                        help="Name for new subnet for private endpoints"
                                    )
                                    config.network_config.pe_subnet_prefix = st.text_input(
                                        "New PE Subnet Address Prefix",
                                        value="",
                                        key="new_pe_subnet_prefix",
                                        help="Address prefix for PE subnet (e.g., 10.0.6.0/24)"
                                    )
                                
                                if config.network_config.agent_subnet_prefix and config.network_config.pe_subnet_prefix:
                                    st.success("✅ Ready to create new subnets in existing VNet")
                                else:
                                    st.warning("⚠️ Please specify address prefixes for both subnets")
                        
                        # Note: Private endpoint configuration is handled in Resource Configuration section
                        # Each resource (AI Search, Storage, Cosmos DB) has its own PE selection there
                else:
                    st.warning("No Virtual Networks found in the subscription")
                    config.network_config.existing_vnet_resource_id = st.text_input(
                        "VNet Resource ID",
                        value=config.network_config.existing_vnet_resource_id,
                        help="Enter the full resource ID of the existing VNet"
                    )
    
    def _render_resource_config(self, config: AIFoundryHubDeploymentConfig) -> None:
        """Render resource configuration section."""
        with st.expander("📦 Resource Configuration", expanded=True):
            st.markdown("### Configure Dependencies")
            st.info("Choose whether to create new resources or use existing ones for each dependency.")
            
            # Cosmos DB Configuration
            self._render_resource_section(
                "🌌 Cosmos DB",
                config.cosmos_db,
                "Microsoft.DocumentDB/databaseAccounts",
                "Azure Cosmos DB for NoSQL database for storing agent conversations and metadata"
            )
            
            # AI Search Configuration
            self._render_resource_section(
                "🔍 AI Search",
                config.ai_search,
                "Microsoft.Search/searchServices",
                "Azure AI Search service for vector search and document indexing"
            )
            
            # Storage Account Configuration
            self._render_resource_section(
                "💾 Storage Account",
                config.storage_account,
                "Microsoft.Storage/storageAccounts",
                "Azure Storage account for storing documents and artifacts"
            )
    
    def _render_resource_section(self, title: str, resource: DeploymentResource, resource_type: str, description: str) -> None:
        """Render a single resource configuration section."""
        with st.container():
            st.markdown(f"#### {title}")
            st.caption(description)
            
            # Special handling for Cosmos DB - allow skipping deployment
            if "Cosmos DB" in title:
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    deployment_option = st.radio(
                        f"{title} Deployment",
                        ["Create New", "Use Existing", "Skip Deployment"],
                        index=0 if resource.create_new else (1 if not resource.skip_deployment else 2),
                        key=f"{resource_type}_deployment_option",
                        help="Choose to create new, use existing, or skip Cosmos DB deployment entirely"
                    )
                    
                    resource.create_new = deployment_option == "Create New"
                    resource.skip_deployment = deployment_option == "Skip Deployment"
                
                with col2:
                    if deployment_option == "Skip Deployment":
                        st.info("ℹ️ Cosmos DB deployment will be skipped. You can configure it later if needed.")
                    elif deployment_option == "Use Existing":
                        self._render_existing_resource_config(resource, resource_type, title)
            else:
                # Standard resource configuration for AI Search and Storage
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    resource.create_new = st.radio(
                        f"{title} Option",
                        ["Create New", "Use Existing"],
                        index=0 if resource.create_new else 1,
                        key=f"{resource_type}_option"
                    ) == "Create New"
                
                with col2:
                    if not resource.create_new:
                        self._render_existing_resource_config(resource, resource_type, title)
            
            st.divider()
    
    def _render_existing_resource_config(self, resource: DeploymentResource, resource_type: str, title: str) -> None:
        """Render configuration for existing resources."""
        # Get available resources
        resources = self.service.get_subscription_resources(resource_type)
        
        if resources:
            resource_options = {f"{res['name']} ({res['resourceGroup']})": res['id'] for res in resources}
            selected_resource = st.selectbox(
                f"Select {title}",
                list(resource_options.keys()),
                key=f"{resource_type}_selector"
            )
            
            if selected_resource:
                resource.existing_resource_id = resource_options[selected_resource]
                
                # Show selected resource details
                selected_resource_info = next(r for r in resources if r['id'] == resource.existing_resource_id)
                st.success(f"✅ Selected: {selected_resource_info['name']} in {selected_resource_info['location']}")
        else:
            st.warning(f"No {title} resources found in the subscription")
            resource.existing_resource_id = st.text_input(
                f"{title} Resource ID",
                value=resource.existing_resource_id,
                help=f"Enter the full resource ID of the existing {title.lower()}",
                key=f"{resource_type}_manual"
            )
        
        # Enhanced Private Endpoint and DNS Configuration for existing resources
        st.markdown("**Network Configuration:**")
        
        # Check for VNet-level private endpoint selections first
        vnet_selection_key = None
        if resource_type == 'Microsoft.Search/searchServices':
            vnet_selection_key = 'ai_search_pe'
        elif resource_type == 'Microsoft.Storage/storageAccounts':
            vnet_selection_key = 'storage_pe'
        elif resource_type == 'Microsoft.DocumentDB/databaseAccounts':
            vnet_selection_key = 'cosmos_pe'
        
        # Check if there's a VNet-level selection for this resource type
        vnet_selected_pe = ""
        if (vnet_selection_key and 
            'vnet_pe_selections' in st.session_state and 
            st.session_state.vnet_pe_selections.get(vnet_selection_key)):
            vnet_selected_pe = st.session_state.vnet_pe_selections[vnet_selection_key]
            st.info(f"🔗 **VNet Selection:** {vnet_selected_pe} was selected in the network configuration above.")
        
        # Check for existing private endpoints if resource ID is provided
        existing_pe_options = []
        if resource.existing_resource_id:
            try:
                # Get the resource group from the existing resource ID
                resource_parts = resource.existing_resource_id.split('/')
                if len(resource_parts) >= 5:
                    resource_group = resource_parts[4]
                    
                    # Get private endpoint suggestions for this resource type
                    pe_suggestions = self.service.suggest_private_endpoints_for_services(
                        resource_group=resource_group,
                        ai_search_id=resource.existing_resource_id if resource_type == 'Microsoft.Search/searchServices' else "",
                        storage_id=resource.existing_resource_id if resource_type == 'Microsoft.Storage/storageAccounts' else "",
                        cosmos_id=resource.existing_resource_id if resource_type == 'Microsoft.DocumentDB/databaseAccounts' else ""
                    )
                    
                    # Get suggestions for this resource type
                    # Map from Azure resource type to internal key
                    azure_resource_type_mapping = {
                        'Microsoft.Search/searchServices': 'ai_search',
                        'Microsoft.Storage/storageAccounts': 'storage', 
                        'Microsoft.DocumentDB/databaseAccounts': 'cosmos_db'
                    }
                    
                    if resource_type in azure_resource_type_mapping:
                        key = azure_resource_type_mapping[resource_type]
                        existing_pe_options = pe_suggestions.get(key, [])
                        
                        # Also check for exact matches in the resource
                        specific_endpoints = self.service.get_existing_private_endpoints_for_resource(
                            resource.existing_resource_id
                        )
                        
                        # Merge and deduplicate
                        all_endpoints = existing_pe_options + specific_endpoints
                        seen_names = set()
                        existing_pe_options = []
                        for ep in all_endpoints:
                            if ep['name'] not in seen_names:
                                existing_pe_options.append(ep)
                                seen_names.add(ep['name'])
                        
                        logger.info(f"Found {len(existing_pe_options)} private endpoints for {resource_type}: {[ep['name'] for ep in existing_pe_options]}")
                        
            except Exception as e:
                logger.warning(f"Could not retrieve private endpoint suggestions: {e}")
                logger.debug(f"Error details for resource {resource.existing_resource_id}: {str(e)}")
                existing_pe_options = []
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Private endpoint configuration
            pe_option = st.radio(
                "Private Endpoint Configuration",
                options=["Use existing private endpoint", "Create new private endpoint", "No private endpoint"],
                index=1 if resource.create_private_endpoint else 0,
                key=f"{resource_type}_pe_option",
                help="Choose how to configure private endpoint access"
            )
            
            if pe_option == "Create new private endpoint":
                resource.create_private_endpoint = True
                resource.existing_private_endpoint_name = ""
                st.success("✅ Will create new private endpoint")
            elif pe_option == "Use existing private endpoint":
                resource.create_private_endpoint = False
                
                # Check if there's a VNet-level selection for this resource type first
                if vnet_selected_pe:
                    # Show VNet selection as priority option
                    use_vnet_selection = st.checkbox(
                        f"Use VNet selection: {vnet_selected_pe}",
                        value=True,
                        key=f"{resource_type}_use_vnet_pe",
                        help="Use the private endpoint selected in the network configuration"
                    )
                    
                    if use_vnet_selection:
                        resource.existing_private_endpoint_name = vnet_selected_pe
                        st.success(f"✅ Using VNet selection: {vnet_selected_pe}")
                        st.info("🔗 This private endpoint was selected in the network configuration above.")
                    else:
                        # Fall back to manual selection
                        if existing_pe_options:
                            # Show dropdown with existing private endpoints
                            pe_display_names = [f"{ep['name']} (subnet: {ep.get('subnet_name', 'Unknown')})" for ep in existing_pe_options]
                            pe_display_names.insert(0, "Select existing private endpoint...")
                            
                            selected_pe_index = st.selectbox(
                                "Select Existing Private Endpoint",
                                options=range(len(pe_display_names)),
                                format_func=lambda x: pe_display_names[x],
                                key=f"{resource_type}_existing_pe_select",
                                help="Select an existing private endpoint for this resource"
                            )
                            
                            if selected_pe_index > 0:
                                selected_pe = existing_pe_options[selected_pe_index - 1]
                                resource.existing_private_endpoint_name = selected_pe['name']
                                st.success(f"✅ Selected: {selected_pe['name']}")
                                
                                # Show additional info about selected endpoint
                                st.info(f"📍 Subnet: {selected_pe.get('subnet_name', 'Unknown')}")
                                if selected_pe.get('connected_resources'):
                                    st.info(f"🔗 Connected to: {', '.join(selected_pe['connected_resources'])}")
                            else:
                                resource.existing_private_endpoint_name = ""
                                st.warning("Please select an existing private endpoint")
                        else:
                            # No existing private endpoints found - allow manual entry
                            st.warning(f"No other private endpoints found for {title}")
                            resource.existing_private_endpoint_name = st.text_input(
                                "Private Endpoint Name",
                                value=getattr(resource, 'existing_private_endpoint_name', ''),
                                key=f"{resource_type}_pe_name_manual",
                                help="Enter the name of an existing private endpoint"
                            )
                
                elif existing_pe_options:
                    # No VNet selection, show dropdown with existing private endpoints
                    pe_display_names = [f"{ep['name']} (subnet: {ep.get('subnet_name', 'Unknown')})" for ep in existing_pe_options]
                    pe_display_names.insert(0, "Select existing private endpoint...")
                    
                    selected_pe_index = st.selectbox(
                        "Select Existing Private Endpoint",
                        options=range(len(pe_display_names)),
                        format_func=lambda x: pe_display_names[x],
                        key=f"{resource_type}_existing_pe_select",
                        help="Select an existing private endpoint for this resource"
                    )
                    
                    if selected_pe_index > 0:
                        selected_pe = existing_pe_options[selected_pe_index - 1]
                        resource.existing_private_endpoint_name = selected_pe['name']
                        st.success(f"✅ Selected: {selected_pe['name']}")
                        
                        # Show additional info about selected endpoint
                        st.info(f"📍 Subnet: {selected_pe.get('subnet_name', 'Unknown')}")
                        if selected_pe.get('connected_resources'):
                            st.info(f"🔗 Connected to: {', '.join(selected_pe['connected_resources'])}")
                    else:
                        resource.existing_private_endpoint_name = ""
                        st.warning("Please select an existing private endpoint")
                else:
                    # No existing private endpoints found - allow manual entry
                    st.warning(f"No existing private endpoints found for {title}")
                    resource.existing_private_endpoint_name = st.text_input(
                        "Private Endpoint Name",
                        value=getattr(resource, 'existing_private_endpoint_name', ''),
                        key=f"{resource_type}_pe_name_manual",
                        help="Enter the name of an existing private endpoint"
                    )
                    
                    if resource.existing_private_endpoint_name:
                        st.info(f"ℹ️ Will use existing private endpoint: {resource.existing_private_endpoint_name}")
                    else:
                        st.info("ℹ️ Enter private endpoint name above")
                        
            else:  # No private endpoint
                resource.create_private_endpoint = False
                resource.existing_private_endpoint_name = ""
                st.info("ℹ️ No private endpoint will be configured")
        
        with col2:
            if resource.create_private_endpoint:
                resource.create_dns_records = st.checkbox(
                    "Create DNS Records",
                    value=resource.create_dns_records,
                    key=f"{resource_type}_create_dns",
                    help="Create DNS records for the private endpoint"
                )
                
                if resource.create_dns_records:
                    st.success("✅ Will create DNS records")
                else:
                    st.info("ℹ️ Using existing DNS configuration")
            else:
                st.info("ℹ️ DNS configuration not applicable")
        
        # Explanation of what happens
        with st.expander("🔍 What does this mean?", expanded=False):
            st.markdown("**Private Endpoint Configuration:**")
            
            if resource.create_private_endpoint:
                st.markdown("✅ **Will create private endpoint**: The deployment will create a new private endpoint for this existing resource, allowing secure access from the VNet.")
            else:
                st.markdown("ℹ️ **Will use existing configuration**: The deployment will use the existing network configuration of this resource.")
            
            if resource.create_private_endpoint and resource.create_dns_records:
                st.markdown("✅ **Will create DNS records**: The deployment will create DNS records in your private DNS zone for the private endpoint.")
            elif resource.create_private_endpoint:
                st.markdown("ℹ️ **Will use existing DNS**: You'll need to configure DNS records manually or use existing ones.")
            
            st.markdown("**Note:** For new resources, private endpoints and DNS are automatically configured based on the template.")
        
        # Legacy options (for backward compatibility)
        resource.use_private_endpoint = resource.create_private_endpoint
        resource.use_dns = resource.create_dns_records
    
    def _render_preview_tab(self) -> None:
        """Render the preview tab."""
        st.subheader("👀 Deployment Preview")
        
        if 'deployment_config' not in st.session_state:
            st.warning("Please configure the deployment first in the Configuration tab.")
            return
        
        config = st.session_state.deployment_config
        
        # Validate configuration
        issues = self.service.validate_deployment_config(config)
        
        if issues:
            st.error("❌ Configuration Issues Found:")
            for issue in issues:
                st.write(f"- {issue}")
            st.warning("Please fix the issues before proceeding to deployment.")
            return
        else:
            st.success("✅ Configuration validation passed!")
        
        # Generate and display parameters
        st.markdown("### 📋 Generated Bicep Parameters")
        
        try:
            params = self.service.generate_bicep_parameters(config)
            
            # Display parameters in a nice format
            st.json(params)
            
            # Show resource summary
            st.markdown("### 📊 Resource Summary")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Resources to Create:**")
                create_count = 0
                
                if config.network_config.create_new_vnet:
                    st.write("- ✅ Virtual Network + Subnets")
                    create_count += 1
                
                if config.cosmos_db.create_new:
                    st.write("- ✅ Cosmos DB Account")
                    create_count += 1
                
                if config.ai_search.create_new:
                    st.write("- ✅ AI Search Service")
                    create_count += 1
                
                if config.storage_account.create_new:
                    st.write("- ✅ Storage Account")
                    create_count += 1
                
                # Always created
                st.write("- ✅ AI Foundry Account")
                
                if not config.skip_openai_deployment:
                    st.write("- ✅ Azure OpenAI Service")
                    st.write("- ✅ Initial Project")
                    create_count += 2
                else:
                    st.write("- ⚠️ Azure OpenAI Service (SKIPPED)")
                    st.write("- ⚠️ Initial Project (SKIPPED)")
                    st.info("💡 OpenAI deployment skipped - faster setup!")
                
                st.write("- ✅ Private Endpoints")
                st.write("- ✅ DNS Zones")
                
                base_resources = 2  # Private endpoints + DNS zones
                st.info(f"Total new resources: {create_count + base_resources}")
            
            with col2:
                st.markdown("**Existing Resources to Use:**")
                
                if not config.network_config.create_new_vnet:
                    st.write("- ♻️ Existing Virtual Network")
                
                if not config.cosmos_db.create_new:
                    st.write("- ♻️ Existing Cosmos DB")
                
                if not config.ai_search.create_new:
                    st.write("- ♻️ Existing AI Search")
                
                if not config.storage_account.create_new:
                    st.write("- ♻️ Existing Storage Account")
                
                existing_count = sum([
                    not config.network_config.create_new_vnet,
                    not config.cosmos_db.create_new,
                    not config.ai_search.create_new,
                    not config.storage_account.create_new
                ])
                
                if existing_count > 0:
                    st.success(f"Reusing {existing_count} existing resources")
                else:
                    st.info("Creating all new resources")
        
        except Exception as e:
            st.error(f"Error generating parameters: {str(e)}")
    
    def _render_deploy_tab(self) -> None:
        """Render the deploy tab."""
        st.subheader("🚀 Deploy AI Foundry Account")
        
        if 'deployment_config' not in st.session_state:
            st.warning("Please configure the deployment first in the Configuration tab.")
            return
        
        config = st.session_state.deployment_config
        
        # Validate configuration
        issues = self.service.validate_deployment_config(config)
        
        if issues:
            st.error("❌ Configuration Issues Found:")
            for issue in issues:
                st.write(f"- {issue}")
            st.warning("Please fix the issues in the Configuration tab before deploying.")
            return
        
        # Resource Group Selection
        st.markdown("### 🎯 Target Resource Group")
        
        resource_groups = self.service.get_subscription_resource_groups()
        
        if resource_groups:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                target_rg = st.selectbox(
                    "Select Resource Group",
                    resource_groups,
                    help="Select the resource group where resources will be deployed"
                )
            
            with col2:
                if st.button("🔄 Refresh RGs"):
                    st.rerun()
        else:
            st.error("No resource groups found. Please check your Azure CLI login.")
            return
        
        # Deployment Name
        deployment_name = st.text_input(
            "Deployment Name",
            value=f"ai-foundry-account-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            help="Name for this deployment (must be unique within the resource group)"
        )
        
        # Deployment Button
        st.markdown("### 🎬 Start Deployment")
        
        if st.button("🚀 Deploy AI Foundry Account", type="primary"):
            if not target_rg:
                st.error("Please select a resource group.")
                return
            
            if not deployment_name:
                st.error("Please enter a deployment name.")
                return
            
            # Auto-save configuration before deployment
            if hasattr(st.session_state, 'deployment_config'):
                self.service.save_deployment_config(st.session_state.deployment_config, "last_deployment")
                st.info("💾 Configuration auto-saved as 'last_deployment'")
            
            # Store deployment info in session state
            st.session_state.current_deployment = {
                'resource_group': target_rg,
                'deployment_name': deployment_name,
                'status': 'starting'
            }
            
            # Start deployment
            with st.spinner("🚀 Starting deployment... This may take 20-30 minutes."):
                success, message, output = self.service.deploy_ai_foundry_hub(
                    config, target_rg, deployment_name
                )
                
                if success:
                    st.success("✅ Deployment started successfully!")
                    st.session_state.current_deployment['status'] = 'completed'
                    st.session_state.current_deployment['success'] = True
                    st.session_state.current_deployment['message'] = message
                    st.session_state.current_deployment['output'] = output
                    
                    # Show deployment output
                    if output:
                        with st.expander("📋 Deployment Output", expanded=False):
                            st.code(output, language="json")
                    
                    st.balloons()
                else:
                    st.error(f"❌ Deployment failed: {message}")
                    st.session_state.current_deployment['status'] = 'failed'
                    st.session_state.current_deployment['success'] = False
                    st.session_state.current_deployment['message'] = message
                    st.session_state.current_deployment['output'] = output
                    
                    # Show error output
                    if output:
                        with st.expander("🔍 Error Details", expanded=True):
                            st.code(output, language="text")
    
    def _render_status_tab(self) -> None:
        """Render the status tab."""
        st.subheader("📊 Deployment Status")
        
        if 'current_deployment' not in st.session_state:
            st.info("No deployment in progress. Start a deployment in the Deploy tab.")
            return
        
        deployment = st.session_state.current_deployment
        
        # Display deployment info
        st.markdown("### 📋 Current Deployment")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Resource Group:** {deployment['resource_group']}")
            st.write(f"**Deployment Name:** {deployment['deployment_name']}")
            st.write(f"**Status:** {deployment['status']}")
        
        with col2:
            if deployment['status'] == 'completed':
                if deployment.get('success', False):
                    st.success("✅ Deployment Completed Successfully")
                else:
                    st.error("❌ Deployment Failed")
            elif deployment['status'] == 'starting':
                st.info("🚀 Deployment In Progress")
            else:
                st.warning("⚠️ Unknown Status")
        
        # Refresh button
        if st.button("🔄 Refresh Status"):
            success, message, deployment_info = self.service.get_deployment_status(
                deployment['resource_group'],
                deployment['deployment_name']
            )
            
            if success and deployment_info:
                st.success("✅ Status refreshed")
                
                # Update deployment info
                properties = deployment_info.get('properties', {})
                provisioning_state = properties.get('provisioningState', 'Unknown')
                
                st.session_state.current_deployment['status'] = provisioning_state.lower()
                
                # Display detailed status
                st.markdown("### 📊 Detailed Status")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Provisioning State:** {provisioning_state}")
                    st.write(f"**Timestamp:** {properties.get('timestamp', 'N/A')}")
                    st.write(f"**Mode:** {properties.get('mode', 'N/A')}")
                
                with col2:
                    if 'duration' in properties:
                        st.write(f"**Duration:** {properties['duration']}")
                    if 'correlationId' in properties:
                        st.write(f"**Correlation ID:** {properties['correlationId']}")
                
                # Show outputs if succeeded
                if provisioning_state == 'Succeeded':
                    success_outputs, msg_outputs, outputs = self.service.get_deployment_outputs(
                        deployment['resource_group'],
                        deployment['deployment_name']
                    )
                    
                    if success_outputs and outputs:
                        st.markdown("### 🎯 Deployment Outputs")
                        st.json(outputs)
                
                # Show detailed error information if failed
                elif provisioning_state == 'Failed':
                    st.markdown("### ❌ Deployment Error Details")
                    
                    # Get detailed error information
                    error_success, error_msg, error_details = self.service.get_deployment_error_details(
                        deployment['resource_group'],
                        deployment['deployment_name']
                    )
                    
                    if error_success and error_details:
                        failed_ops = error_details.get('failed_operations', [])
                        
                        if failed_ops:
                            st.error(f"🔍 Found {len(failed_ops)} failed operation(s):")
                            
                            for i, error_info in enumerate(failed_ops, 1):
                                with st.expander(f"Error {i}: {error_info.get('resource_type', 'Unknown')} - {error_info.get('resource_name', 'Unknown')}", expanded=True):
                                    st.write(f"**Resource Type:** {error_info.get('resource_type', 'Unknown')}")
                                    st.write(f"**Resource Name:** {error_info.get('resource_name', 'Unknown')}")
                                    st.write(f"**Error Code:** {error_info.get('error_code', 'Unknown')}")
                                    
                                    st.markdown("**Error Message:**")
                                    st.code(error_info.get('error_message', 'No error message available'), language="text")
                                    
                                    # Provide potential solutions based on error patterns
                                    error_message = error_info.get('error_message', '').lower()
                                    if 'conflict' in error_message or 'already exists' in error_message:
                                        st.info("💡 **Potential Solution:** Resource name conflict. Try using a different name or delete the existing resource.")
                                    elif 'quota' in error_message or 'limit' in error_message:
                                        st.info("💡 **Potential Solution:** Quota limit exceeded. Request quota increase or use a different region.")
                                    elif 'permission' in error_message or 'unauthorized' in error_message:
                                        st.info("💡 **Potential Solution:** Insufficient permissions. Check RBAC assignments for the deployment service principal.")
                                    elif 'network' in error_message or 'subnet' in error_message:
                                        st.info("💡 **Potential Solution:** Network configuration issue. Verify VNet and subnet configurations.")
                                    elif 'invalid' in error_message or 'bad request' in error_message:
                                        st.info("💡 **Potential Solution:** Invalid parameter values. Review configuration in the Configuration tab.")
                        else:
                            st.warning("No specific failed operations found. The deployment may have failed during validation.")
                            
                    else:
                        st.warning(f"Unable to get detailed error information: {error_msg}")
                        
                        # Show general error from deployment properties if available
                        if properties.get('error'):
                            st.markdown("**General Error Information:**")
                            error_obj = properties['error']
                            st.code(f"Code: {error_obj.get('code', 'Unknown')}\nMessage: {error_obj.get('message', 'No message')}", language="text")
                    
                    # Always show troubleshooting tips for failed deployments
                    st.markdown("### 🔧 Troubleshooting Tips")
                    st.info("""
                    **Common Solutions:**
                    1. **Resource Name Conflicts:** Use unique names or delete existing resources
                    2. **Permission Issues:** Ensure you have Contributor access to the resource group
                    3. **Quota Limits:** Check Azure quotas in your subscription
                    4. **Network Configuration:** Verify VNet and subnet settings
                    5. **Region Availability:** Some services may not be available in all regions
                    
                    **Next Steps:**
                    - Review error details above
                    - Fix configuration issues in the Configuration tab
                    - Save configuration and retry deployment
                    - Contact Azure support if issues persist
                    """)
                
                # Show warning for running deployments
                elif provisioning_state in ['Running', 'Accepted']:
                    st.markdown("### ⏳ Deployment Progress")
                    st.info("""
                    **Deployment is currently running...**
                    
                    ✅ Expected completion time: 10-15 minutes
                    🔄 Current status will update automatically
                    ⚠️ Do not close this page until deployment completes
                    
                    **What's happening:**
                    - Creating network infrastructure
                    - Deploying AI services
                    - Configuring private endpoints
                    - Setting up DNS records
                    - Creating AI Foundry project
                    """)
                
                # Show info for cancelled deployments
                elif provisioning_state == 'Cancelled':
                    st.markdown("### ⚠️ Deployment Cancelled")
                    st.warning("""
                    The deployment was cancelled before completion.
                    
                    **Possible reasons:**
                    - User cancelled the deployment
                    - Azure service interruption
                    - Resource group or subscription changes
                    
                    **Next steps:**
                    - Review configuration and retry deployment
                    - Check Azure service health status
                    - Contact support if cancellation was unexpected
                    """)
                    
            else:
                st.error(f"❌ Failed to refresh status: {message}")
        
        # Show deployment message and output
        if deployment.get('message'):
            st.markdown("### 📝 Deployment Message")
            if deployment.get('success', False):
                st.success(deployment['message'])
            else:
                st.error(deployment['message'])
        
        if deployment.get('output'):
            st.markdown("### 📋 Deployment Output")
            with st.expander("View Output", expanded=False):
                st.code(deployment['output'], language="json" if deployment.get('success', False) else "text")
    
    def _render_existing_private_endpoints_for_vnet(self, vnet_resource_id: str) -> None:
        """Render existing private endpoints available in the VNet's resource group."""
        try:
            # Extract resource group from VNet resource ID
            vnet_parts = vnet_resource_id.split('/')
            if len(vnet_parts) >= 5:
                resource_group = vnet_parts[4]
                
                st.markdown("### 🔗 Existing Private Endpoints")
                st.info("📍 Private endpoints found in the selected VNet's resource group that you can reference or avoid conflicts with:")
                
                # Get all private endpoints in the resource group
                all_pe_suggestions = self.service.suggest_private_endpoints_for_services(
                    resource_group=resource_group,
                    ai_search_id="",  # Get all PEs, not filtered by resource
                    storage_id="", 
                    cosmos_id=""
                )
                
                # Combine all private endpoints
                all_endpoints = []
                for category, endpoints in all_pe_suggestions.items():
                    all_endpoints.extend(endpoints)
                
                if all_endpoints:
                    st.markdown(f"**Found {len(all_endpoints)} private endpoints in resource group `{resource_group}`:**")
                    
                    # Group by service type for better display
                    pe_by_type = {
                        'ai_search': [],
                        'storage': [],
                        'cosmos_db': [],
                        'other': []
                    }
                    
                    for endpoint in all_endpoints:
                        # Categorize by connected resources or naming patterns
                        connected_resources = endpoint.get('connected_resources', [])
                        endpoint_name = endpoint['name'].lower()
                        
                        categorized = False
                        for resource in connected_resources:
                            resource_lower = resource.lower()
                            if any(pattern in resource_lower for pattern in ['search', 'cognitive']):
                                pe_by_type['ai_search'].append(endpoint)
                                categorized = True
                                break
                            elif any(pattern in resource_lower for pattern in ['storage', 'blob']):
                                pe_by_type['storage'].append(endpoint)
                                categorized = True
                                break
                            elif any(pattern in resource_lower for pattern in ['cosmos', 'documentdb']):
                                pe_by_type['cosmos_db'].append(endpoint)
                                categorized = True
                                break
                        
                        if not categorized:
                            # Try to categorize by endpoint name
                            if any(pattern in endpoint_name for pattern in ['search', 'ai-search', 'cognitive']):
                                pe_by_type['ai_search'].append(endpoint)
                            elif any(pattern in endpoint_name for pattern in ['storage', 'blob', 'file', 'queue', 'table']):
                                pe_by_type['storage'].append(endpoint)
                            elif any(pattern in endpoint_name for pattern in ['cosmos', 'documentdb']):
                                pe_by_type['cosmos_db'].append(endpoint)
                            else:
                                pe_by_type['other'].append(endpoint)
                    
                    # Display by category
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if pe_by_type['ai_search']:
                            st.markdown("**🔍 AI Search Private Endpoints:**")
                            for pe in pe_by_type['ai_search']:
                                subnet_name = pe.get('subnet_name', 'Unknown')
                                connected = ', '.join(pe.get('connected_resources', ['Unknown']))
                                st.write(f"• `{pe['name']}` (subnet: {subnet_name}, connected: {connected})")
                        
                        if pe_by_type['storage']:
                            st.markdown("**💾 Storage Private Endpoints:**")
                            for pe in pe_by_type['storage']:
                                subnet_name = pe.get('subnet_name', 'Unknown')
                                connected = ', '.join(pe.get('connected_resources', ['Unknown']))
                                st.write(f"• `{pe['name']}` (subnet: {subnet_name}, connected: {connected})")
                    
                    with col2:
                        if pe_by_type['cosmos_db']:
                            st.markdown("**🌌 Cosmos DB Private Endpoints:**")
                            for pe in pe_by_type['cosmos_db']:
                                subnet_name = pe.get('subnet_name', 'Unknown')
                                connected = ', '.join(pe.get('connected_resources', ['Unknown']))
                                st.write(f"• `{pe['name']}` (subnet: {subnet_name}, connected: {connected})")
                        
                        if pe_by_type['other']:
                            st.markdown("**🔧 Other Private Endpoints:**")
                            for pe in pe_by_type['other']:
                                subnet_name = pe.get('subnet_name', 'Unknown')
                                connected = ', '.join(pe.get('connected_resources', ['Unknown']))
                                st.write(f"• `{pe['name']}` (subnet: {subnet_name}, connected: {connected})")
                    
                    # Add interactive selection for private endpoints
                    st.markdown("---")
                    st.markdown("### 📋 Select Private Endpoints for Deployment")
                    st.info("💡 **Optional:** Select existing private endpoints to reference in your deployment and avoid conflicts.")
                    
                    # Store selections in session state if not already present
                    if 'vnet_pe_selections' not in st.session_state:
                        st.session_state.vnet_pe_selections = {
                            'ai_search_pe': "",
                            'storage_pe': "",
                            'cosmos_pe': ""
                        }
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if pe_by_type['ai_search']:
                            st.markdown("**🔍 AI Search PE:**")
                            ai_search_options = ["None (Auto-detect)"] + [pe['name'] for pe in pe_by_type['ai_search']]
                            selected_ai_search_pe = st.selectbox(
                                "Select AI Search Private Endpoint",
                                ai_search_options,
                                key="vnet_ai_search_pe",
                                help="Choose existing AI Search private endpoint to reference"
                            )
                            if selected_ai_search_pe != "None (Auto-detect)":
                                st.session_state.vnet_pe_selections['ai_search_pe'] = selected_ai_search_pe
                                st.success(f"✅ Selected: {selected_ai_search_pe}")
                            else:
                                st.session_state.vnet_pe_selections['ai_search_pe'] = ""
                    
                    with col2:
                        if pe_by_type['storage']:
                            st.markdown("**💾 Storage PE:**")
                            storage_options = ["None (Auto-detect)"] + [pe['name'] for pe in pe_by_type['storage']]
                            selected_storage_pe = st.selectbox(
                                "Select Storage Private Endpoint",
                                storage_options,
                                key="vnet_storage_pe",
                                help="Choose existing Storage private endpoint to reference"
                            )
                            if selected_storage_pe != "None (Auto-detect)":
                                st.session_state.vnet_pe_selections['storage_pe'] = selected_storage_pe
                                st.success(f"✅ Selected: {selected_storage_pe}")
                            else:
                                st.session_state.vnet_pe_selections['storage_pe'] = ""
                    
                    with col3:
                        if pe_by_type['cosmos_db']:
                            st.markdown("**🌌 Cosmos DB PE:**")
                            cosmos_options = ["None (Auto-detect)"] + [pe['name'] for pe in pe_by_type['cosmos_db']]
                            selected_cosmos_pe = st.selectbox(
                                "Select Cosmos DB Private Endpoint",
                                cosmos_options,
                                key="vnet_cosmos_pe",
                                help="Choose existing Cosmos DB private endpoint to reference"
                            )
                            if selected_cosmos_pe != "None (Auto-detect)":
                                st.session_state.vnet_pe_selections['cosmos_pe'] = selected_cosmos_pe
                                st.success(f"✅ Selected: {selected_cosmos_pe}")
                            else:
                                st.session_state.vnet_pe_selections['cosmos_pe'] = ""
                    
                    # Show summary of selections
                    if any(st.session_state.vnet_pe_selections.values()):
                        st.markdown("### 📋 Selected Private Endpoints Summary:")
                        selection_summary = []
                        if st.session_state.vnet_pe_selections['ai_search_pe']:
                            selection_summary.append(f"🔍 AI Search: `{st.session_state.vnet_pe_selections['ai_search_pe']}`")
                        if st.session_state.vnet_pe_selections['storage_pe']:
                            selection_summary.append(f"💾 Storage: `{st.session_state.vnet_pe_selections['storage_pe']}`")
                        if st.session_state.vnet_pe_selections['cosmos_pe']:
                            selection_summary.append(f"🌌 Cosmos DB: `{st.session_state.vnet_pe_selections['cosmos_pe']}`")
                        
                        if selection_summary:
                            st.info("**Selected Private Endpoints:**\n" + "\n".join(selection_summary))
                            st.success("✅ These private endpoints will be referenced in the deployment to avoid conflicts!")
                
                else:
                    st.info(f"No private endpoints found in resource group `{resource_group}`. New private endpoints will be created as needed.")
                    # Clear any previous selections
                    if 'vnet_pe_selections' in st.session_state:
                        st.session_state.vnet_pe_selections = {
                            'ai_search_pe': "",
                            'storage_pe': "",
                            'cosmos_pe': ""
                        }
                    
        except Exception as e:
            st.warning(f"Could not retrieve private endpoints for VNet: {str(e)}")
            logger.warning(f"Error getting private endpoints for VNet {vnet_resource_id}: {str(e)}")

def render_ai_foundry_hub_deployment_ui() -> None:
    """Wrapper function to render the AI Foundry Hub deployment UI."""
    deployment_ui = AIFoundryHubDeploymentUI()
    deployment_ui.render_deployment_tab()
