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
        
        # Show current Azure CLI context with detailed information
        try:
            context_info = self.service.get_subscription_context_info()
            
            if context_info['subscription_id'] != 'Not logged in' and context_info['subscription_id'] != 'Error':
                # Create a nice context display
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.success(f"🌟 **Azure CLI Context**: {context_info['subscription_name']}")
                    st.caption(f"📋 Subscription ID: `{context_info['subscription_id']}`")
                
                with col2:
                    st.info(f"👤 **User**: {context_info['user_name']}")
                    st.caption(f"🔐 Type: {context_info['user_type']}")
                
                with col3:
                    st.info(f"� **Tenant**: {context_info['tenant_id'][:8]}...")
                    st.caption(f"📊 State: {context_info['state']}")
                    
                # Add a refresh context button
                if st.button("🔄 Refresh Context", help="Refresh Azure CLI context information", key="refresh_context_top"):
                    st.rerun()
                    
            else:
                st.error("❌ **Not logged in to Azure CLI**")
                st.warning("Please run `az login` or use the subscription switcher below to authenticate.")
                
                if st.button("🔐 Login to Azure CLI", help="Open Azure CLI login", key="azure_cli_login_top"):
                    with st.spinner("Opening Azure CLI login..."):
                        try:
                            import subprocess
                            result = subprocess.run(['az', 'login'], capture_output=True, text=True, timeout=300)
                            if result.returncode == 0:
                                st.success("✅ Login successful! Please refresh the page.")
                                st.rerun()
                            else:
                                st.error(f"❌ Login failed: {result.stderr}")
                        except Exception as e:
                            st.error(f"❌ Login error: {e}")
                            
        except Exception as e:
            st.warning(f"⚠️ Could not determine current Azure CLI context: {e}")
            st.info("💡 **Tip**: Ensure Azure CLI is installed and you have network connectivity.")
        
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
                key="config_mgmt_use_last_config",
                help="Load the last saved configuration to avoid re-entering all parameters"
            )
        
        with col2:
            saved_configs = self.service.list_saved_configs()
            if saved_configs:
                selected_config = st.selectbox(
                    "📁 Saved Configs",
                    options=[""] + saved_configs,
                    key="config_mgmt_saved_configs",
                    help="Select a previously saved configuration"
                )
                
                if selected_config and st.button("📂 Load Config", key="config_mgmt_load_button"):
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
                key="config_mgmt_save_name",
                help="Enter a name to save the current configuration"
            )
            
            if st.button("💾 Save Config", key="config_mgmt_save_button"):
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
                # Location selection with proper session state management
                available_locations = self.service.get_available_locations()
                
                # Find current location index safely
                try:
                    current_location_index = available_locations.index(config.location)
                except ValueError:
                    # If location not found, default to first location
                    current_location_index = 0
                    config.location = available_locations[0] if available_locations else "eastus"
                
                selected_location = st.selectbox(
                    "🌍 Location",
                    available_locations,
                    index=current_location_index,
                    key="basic_settings_location",
                    help="Azure region where resources will be deployed"
                )
                
                # Update config only if changed
                if selected_location != config.location:
                    config.location = selected_location
                
                config.ai_services_name = st.text_input(
                    "🤖 AI Services Name",
                    value=config.ai_services_name,
                    key="basic_settings_ai_services_name",
                    help="Base name for AI services (unique suffix will be added)"
                )
                
                config.project_name = st.text_input(
                    "📁 Project Name",
                    value=config.project_name,
                    key="basic_settings_project_name",
                    help="Name for the initial project"
                )
            
            with col2:
                config.project_description = st.text_area(
                    "📝 Project Description",
                    value=config.project_description,
                    height=100,
                    key="basic_settings_project_description"
                )
                
                config.display_name = st.text_input(
                    "🏷️ Display Name",
                    value=config.display_name,
                    key="basic_settings_display_name"
                )
        
        # Model Configuration
        with st.expander("🧠 Model Configuration", expanded=False):
            # OpenAI Deployment Option
            config.skip_openai_deployment = st.checkbox(
                "⚠️ Skip OpenAI Model Deployment", 
                value=config.skip_openai_deployment,
                key="model_config_skip_openai",
                help="Check this to skip Azure OpenAI deployment (faster deployment, no models). By default, OpenAI models will be deployed."
            )
            
            if not config.skip_openai_deployment:
                st.info("� OpenAI models will be deployed by default (adds ~5-10 minutes to deployment)")
                
                # Fixed model configuration - display only, no user selection
                st.markdown("**Fixed Model Configuration:**")
                col1, col2 = st.columns(2)
                
                with col1:
                    # Set fixed values and display them as read-only
                    config.model_name = "gpt-4.1"
                    st.text_input(
                        "Model Name",
                        value="gpt-4.1",
                        disabled=True,
                        key="model_config_model_name",
                        help="Fixed model configuration for this deployment"
                    )
                    
                    config.model_format = "OpenAI"
                    st.text_input(
                        "Model Format",
                        value="OpenAI",
                        disabled=True,
                        key="model_config_model_format",
                        help="Fixed model format"
                    )
                    
                    config.model_version = "2025-04-14"
                    st.text_input(
                        "Model Version",
                        value="2025-04-14",
                        disabled=True,
                        key="model_config_model_version",
                        help="Fixed model version"
                    )
                
                with col2:
                    config.model_sku_name = "GlobalStandard"
                    st.text_input(
                        "Model SKU",
                        value="GlobalStandard",
                        disabled=True,
                        key="model_config_model_sku",
                        help="Fixed SKU configuration"
                    )
                    
                    config.model_capacity = 30
                    st.number_input(
                        "Model Capacity (TPM)",
                        value=30,
                        disabled=True,
                        key="model_config_model_capacity",
                        help="Fixed capacity: 30 tokens per minute"
                    )
                
                st.info("ℹ️ Model configuration is fixed to ensure consistency: gpt-4.1, version 2025-04-14, GlobalStandard SKU, 30 TPM")
            else:
                st.success("✅ OpenAI deployment will be skipped - faster Account setup!")
                st.info("💡 You can deploy models later using the Azure portal or Azure CLI")
        
        # DNS Zone Configuration
        self._render_dns_zone_config(config)
        
        # Network Configuration
        self._render_network_config(config)
        
        # Resource Configuration
        self._render_resource_config(config)
        
        # Update session state
        st.session_state.deployment_config = config
    
    def _render_dns_zone_config(self, config: AIFoundryHubDeploymentConfig) -> None:
        """Render DNS zone configuration section."""
        with st.expander("🔗 Private DNS Zone Configuration", expanded=True):
            st.markdown("Configure where your private DNS zones are located. These zones are required for private endpoint connectivity.")
            
            # Add enterprise context and common scenarios
            with st.expander("📚 Common DNS Zone Configuration Scenarios", expanded=False):
                st.markdown("""
                **🏢 Enterprise Hub-Spoke Model**:
                - **Network Hub Subscription**: Contains centrally managed Private DNS zones
                - **Application Spoke Subscriptions**: Contains AI Foundry Account and related resources  
                - **Benefit**: Centralized DNS management, consistent naming resolution across all spokes
                
                **🏠 Single Subscription Model**:
                - **Same Subscription**: DNS zones and AI Foundry resources in same subscription
                - **private-rg Resource Group**: Standard location for DNS zones
                - **Benefit**: Simpler management, good for smaller environments
                
                **🆕 Greenfield Development**:
                - **New DNS Zones**: Create fresh DNS zones alongside your AI Foundry deployment
                - **Same Resource Group**: DNS zones created in deployment resource group
                - **Benefit**: Self-contained, no dependencies on existing infrastructure
                """)
            
            st.info("""
            **🏢 Enterprise Scenario**: In most enterprise environments, Private DNS zones are managed centrally in a "Network Hub" subscription, 
            while applications are deployed to separate "Spoke" subscriptions. Select the appropriate configuration below.
            """)
            
            # DNS zone location option - restructured for enterprise scenarios
            # Use session state to maintain radio selection
            if 'dns_zone_option' not in st.session_state:
                st.session_state.dns_zone_option = "🏠 Simple: Use existing DNS zones in private-rg (same subscription)"
            
            dns_zone_option = st.radio(
                "🎯 DNS Zone Location Strategy",
                options=[
                    "🏢 Enterprise: DNS zones in different subscription (Hub-Spoke)", 
                    "🏠 Simple: Use existing DNS zones in private-rg (same subscription)",
                    "🆕 Development: Create new zones in deployment location"
                ],
                index=["🏢 Enterprise: DNS zones in different subscription (Hub-Spoke)", 
                       "🏠 Simple: Use existing DNS zones in private-rg (same subscription)",
                       "🆕 Development: Create new zones in deployment location"].index(st.session_state.dns_zone_option),
                help="Choose the DNS zone strategy that matches your environment",
                key="dns_zone_strategy_selector"
            )
            
            # Update session state
            st.session_state.dns_zone_option = dns_zone_option
            
            if dns_zone_option == "🏢 Enterprise: DNS zones in different subscription (Hub-Spoke)":
                st.markdown("### 🏢 Enterprise Hub-Spoke Configuration")
                st.info("**Scenario**: DNS zones are managed in a central 'Network Hub' subscription, while resources are deployed to 'Application Spoke' subscriptions.")
                
                # Get available subscriptions with current subscription prioritized
                subscriptions = self.service.get_prioritized_subscriptions()
                
                if subscriptions:
                    # Subscription selection with better labeling and current subscription highlighted
                    subscription_options = {}
                    current_sub_info = self.service.get_current_subscription_info()
                    current_sub_id = current_sub_info['subscription_id'] if current_sub_info else None
                    
                    for sub in subscriptions:
                        if sub['state'] == 'Enabled':
                            label = f"{sub['display_name']} ({sub['subscription_id']})"
                            if sub['subscription_id'] == current_sub_id:
                                label = f"🌟 {label} (Current)"
                            subscription_options[label] = sub['subscription_id']
                    
                    if subscription_options:
                        st.markdown("#### 🎯 DNS Zone Subscription Selection")
                        
                        # Initialize DNS zone subscription session state
                        if 'dns_zone_subscription_id' not in st.session_state:
                            st.session_state.dns_zone_subscription_id = current_sub_id or list(subscription_options.values())[0]
                        
                        # Find current selection index
                        dns_sub_index = 0
                        subscription_list = list(subscription_options.items())
                        for i, (label, sub_id) in enumerate(subscription_list):
                            if sub_id == st.session_state.dns_zone_subscription_id:
                                dns_sub_index = i
                                break
                        
                        def on_dns_subscription_change():
                            """Handle DNS subscription selection change."""
                            selected_key = st.session_state.dns_zone_subscription_selector
                            if selected_key in subscription_options:
                                new_subscription_id = subscription_options[selected_key]
                                old_subscription_id = st.session_state.get('dns_zone_subscription_id')
                                
                                # Only switch if the subscription actually changed
                                if new_subscription_id != old_subscription_id:
                                    st.session_state.dns_zone_subscription_id = new_subscription_id
                                    
                                    # Switch Azure CLI context for DNS zone operations
                                    with st.spinner(f"Switching to DNS subscription {new_subscription_id}..."):
                                        success, message = self.service.switch_subscription_context(new_subscription_id)
                                        if success:
                                            st.success(message)
                                        else:
                                            st.error(message)
                                            # Revert to previous subscription on failure
                                            if old_subscription_id:
                                                st.session_state.dns_zone_subscription_id = old_subscription_id
                                    
                                    # Clear resource group selection when subscription changes
                                    if 'dns_zone_resource_group' in st.session_state:
                                        del st.session_state['dns_zone_resource_group']
                        
                        selected_subscription_display = st.selectbox(
                            "Select the subscription containing your Private DNS zones",
                            options=list(subscription_options.keys()),
                            index=dns_sub_index,
                            help="🌟 = Current subscription. Typically select your 'Network Hub' or 'Shared Services' subscription where DNS zones are centrally managed",
                            key="dns_zone_subscription_selector",
                            on_change=on_dns_subscription_change
                        )
                        
                        # Update config with session state value
                        config.dns_zone_subscription_id = st.session_state.dns_zone_subscription_id
                        
                        # Show selected subscription info
                        selected_sub_id = config.dns_zone_subscription_id
                        is_current = selected_sub_id == current_sub_id
                        if is_current:
                            st.success(f"✅ **DNS Zone Subscription**: {selected_subscription_display} (Same as deployment subscription)")
                        else:
                            st.info(f"🔄 **DNS Zone Subscription**: {selected_subscription_display} (Cross-subscription configuration)")
                            
                            # Add DNS subscription authentication section
                            st.markdown("---")
                            st.markdown("#### 🔐 DNS Subscription Authentication")
                            
                            col_dns_auth1, col_dns_auth2 = st.columns([2, 1])
                            
                            with col_dns_auth1:
                                st.info(f"🔄 **Action Required**: Switch to DNS subscription for zone management")
                                st.markdown(f"**DNS Target**: `{config.dns_zone_subscription_id}`")
                            
                            with col_dns_auth2:
                                if st.button(
                                    "🔐 Switch to DNS Sub",
                                    help="Sign in and switch to the DNS subscription",
                                    key="auth_and_switch_dns_subscription",
                                    type="secondary"
                                ):
                                    with st.spinner(f"🔐 Switching to DNS subscription {config.dns_zone_subscription_id}..."):
                                        success, message = self.service.authenticate_and_switch_subscription(
                                            config.dns_zone_subscription_id
                                        )
                                        
                                        if success:
                                            st.success(message)
                                            st.rerun()
                                        else:
                                            st.error(message)
                        
                        # Resource group selection with intelligent suggestions
                        if config.dns_zone_subscription_id:
                            st.markdown("#### 📁 DNS Zone Resource Group Selection")
                            
                            with st.spinner(f"Loading resource groups from subscription {config.dns_zone_subscription_id[:8]}..."):
                                resource_groups = self.service.suggest_dns_zone_resource_groups(config.dns_zone_subscription_id)
                            
                            if resource_groups:
                                st.info(f"✅ Found {len(resource_groups)} resource groups in subscription")
                                
                                # Format resource group options with hints
                                rg_options = []
                                for rg in resource_groups:
                                    rg_lower = rg.lower()
                                    if any(pattern in rg_lower for pattern in ['private', 'dns', 'network', 'hub', 'connectivity']):
                                        rg_options.append(f"⭐ {rg}")
                                    else:
                                        rg_options.append(rg)
                                
                                # Initialize DNS zone resource group session state
                                dns_rg_key = f"dns_zone_rg_{config.dns_zone_subscription_id}"
                                if dns_rg_key not in st.session_state and rg_options:
                                    # Prefer a likely DNS resource group as default
                                    default_rg = next((rg for rg in rg_options if rg.startswith("⭐")), rg_options[0])
                                    st.session_state[dns_rg_key] = default_rg
                                
                                # Find current selection index
                                dns_rg_index = 0
                                if dns_rg_key in st.session_state and st.session_state[dns_rg_key] in rg_options:
                                    dns_rg_index = rg_options.index(st.session_state[dns_rg_key])
                                
                                def on_dns_rg_change():
                                    """Handle DNS resource group selection change."""
                                    st.session_state[dns_rg_key] = st.session_state.dns_zone_rg_selector
                                
                                selected_rg = st.selectbox(
                                    "Select the resource group containing your Private DNS zones",
                                    options=rg_options,
                                    index=dns_rg_index,
                                    help="⭐ = Likely DNS resource group. This is typically a resource group dedicated to network resources and DNS zones",
                                    key="dns_zone_rg_selector",
                                    on_change=on_dns_rg_change
                                )
                                
                                # Add refresh button
                                col_rg1, col_rg2 = st.columns([4, 1])
                                with col_rg2:
                                    if st.button("🔄 Refresh", key="refresh_dns_rgs", help="Refresh resource group list"):
                                        st.rerun()
                                
                                # Update session state and config
                                st.session_state[dns_rg_key] = selected_rg
                                config.dns_zone_resource_group_name = selected_rg.replace("⭐ ", "")
                                st.success(f"✅ **DNS Zone Resource Group**: {config.dns_zone_resource_group_name}")
                                
                                # Validate DNS zones
                                if config.dns_zone_resource_group_name:
                                    st.markdown("#### 🔍 DNS Zone Validation")
                                    with st.spinner("Validating DNS zones in the selected location..."):
                                        zone_status = self.service.validate_dns_zones_exist(
                                            config.dns_zone_subscription_id, 
                                            config.dns_zone_resource_group_name
                                        )
                                    
                                    if zone_status:
                                        all_zones_exist = all(zone_status.values())
                                        
                                        col1, col2 = st.columns([2, 1])
                                        with col1:
                                            st.markdown("**Required DNS Zones Status:**")
                                            for zone_name, exists in zone_status.items():
                                                if exists:
                                                    st.success(f"✅ {zone_name}")
                                                else:
                                                    st.error(f"❌ {zone_name}")
                                        
                                        with col2:
                                            if all_zones_exist:
                                                st.markdown("**🎉 Status**")
                                                st.success("All zones found!")
                                                config.create_dns_zones_if_not_exist = False
                                            else:
                                                st.markdown("**⚠️ Action Required**")
                                                config.create_dns_zones_if_not_exist = st.checkbox(
                                                    "Create missing zones",
                                                    value=config.create_dns_zones_if_not_exist,
                                                    help="Create missing DNS zones in the selected subscription/resource group"
                                                )
                                        
                                        # Summary box
                                        if all_zones_exist:
                                            st.success("🎯 **Configuration Ready**: All required DNS zones found in the selected location!")
                                        elif config.create_dns_zones_if_not_exist:
                                            st.info("💡 **Auto-Creation Enabled**: Missing DNS zones will be created during deployment")
                                        else:
                                            st.warning("⚠️ **Action Required**: Please create the missing DNS zones or enable auto-creation")
                                    else:
                                        st.error("❌ Unable to validate DNS zones")
                                        
                                    # DNS Zone Debug Section
                                    st.markdown("---")
                                    col_debug1, col_debug2, col_debug3 = st.columns([2, 2, 1])
                                    
                                    with col_debug1:
                                        if st.button("🔄 Re-check DNS Zones", key="recheck_dns_zones"):
                                            st.rerun()
                                    
                                    with col_debug2:
                                        if st.button("🐛 Debug DNS Discovery", key="debug_dns_discovery"):
                                            st.markdown("**🔍 DNS Zone Discovery Debug:**")
                                            
                                            with st.spinner("Testing DNS zone discovery..."):
                                                try:
                                                    import subprocess
                                                    import json
                                                    
                                                    # Test DNS zone listing with Azure CLI
                                                    cmd = [
                                                        "az", "network", "private-dns", "zone", "list",
                                                        "--subscription", config.dns_zone_subscription_id,
                                                        "--resource-group", config.dns_zone_resource_group_name
                                                    ]
                                                    
                                                    st.code(" ".join(cmd))
                                                    
                                                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                                                    
                                                    if result.returncode == 0:
                                                        try:
                                                            zones_data = json.loads(result.stdout)
                                                            zone_names = [zone.get('name', 'Unknown') for zone in zones_data]
                                                            
                                                            st.success(f"✅ Found {len(zone_names)} private DNS zones")
                                                            if zone_names:
                                                                st.markdown("**Existing DNS Zones:**")
                                                                for i, zone in enumerate(zone_names[:10], 1):  # Show first 10
                                                                    st.write(f"{i}. {zone}")
                                                                if len(zone_names) > 10:
                                                                    st.info(f"... and {len(zone_names) - 10} more zones")
                                                                
                                                                # Check which required zones exist
                                                                required_zones = [
                                                                    "privatelink.services.ai.azure.com",
                                                                    "privatelink.openai.azure.com", 
                                                                    "privatelink.cognitiveservices.azure.com",
                                                                    "privatelink.search.windows.net",
                                                                    "privatelink.blob.core.windows.net",
                                                                    "privatelink.documents.azure.com"
                                                                ]
                                                                
                                                                st.markdown("**Required Zone Check:**")
                                                                for req_zone in required_zones:
                                                                    if req_zone in zone_names:
                                                                        st.success(f"✅ {req_zone}")
                                                                    else:
                                                                        st.error(f"❌ {req_zone}")
                                                            else:
                                                                st.warning("No private DNS zones found in the resource group")
                                                                
                                                        except json.JSONDecodeError as e:
                                                            st.error(f"❌ Failed to parse zones JSON: {e}")
                                                            st.text("Raw output:")
                                                            st.code(result.stdout[:1000])
                                                    else:
                                                        st.error(f"❌ Failed to list DNS zones")
                                                        st.error(f"Error: {result.stderr}")
                                                        st.markdown("**Possible causes:**")
                                                        st.markdown("- Resource group doesn't exist")  
                                                        st.markdown("- No permissions to list private DNS zones")
                                                        st.markdown("- Azure CLI authentication issue")
                                                        
                                                except subprocess.TimeoutExpired:
                                                    st.error("❌ Timeout - DNS zone discovery took too long")
                                                except Exception as e:
                                                    st.error(f"❌ Debug failed: {e}")
                                                    
                                    with col_debug3:
                                        st.markdown("")  # Spacer
                            else:
                                st.error(f"❌ No resource groups found in selected subscription")
                                st.markdown("**🔍 Troubleshooting:**")
                                st.markdown(f"- **Subscription ID**: `{config.dns_zone_subscription_id}`")
                                st.markdown("- **Possible causes:**")
                                st.markdown("  - No resource groups exist in this subscription")
                                st.markdown("  - Access permissions issue")
                                st.markdown("  - Azure CLI not logged in or expired")
                                
                                # Debug button
                                if st.button("🐛 Test Subscription Access", key="test_dns_sub_access"):
                                    with st.spinner("Testing subscription access..."):
                                        try:
                                            # Test Azure CLI access
                                            import subprocess
                                            result = subprocess.run(
                                                ["az", "account", "show", "--subscription", config.dns_zone_subscription_id],
                                                capture_output=True,
                                                text=True,
                                                timeout=10
                                            )
                                            
                                            if result.returncode == 0:
                                                st.success("✅ Azure CLI can access the subscription")
                                                # Try to list resource groups again with debug
                                                result2 = subprocess.run(
                                                    ["az", "group", "list", "--subscription", config.dns_zone_subscription_id],
                                                    capture_output=True,
                                                    text=True,
                                                    timeout=15
                                                )
                                                if result2.returncode == 0:
                                                    import json
                                                    rgs = json.loads(result2.stdout)
                                                    st.info(f"✅ Found {len(rgs)} resource groups via direct Azure CLI call")
                                                    if rgs:
                                                        st.json([rg['name'] for rg in rgs[:5]])  # Show first 5
                                                else:
                                                    st.error(f"❌ Azure CLI list groups failed: {result2.stderr}")
                                            else:
                                                st.error(f"❌ Cannot access subscription: {result.stderr}")
                                        except Exception as e:
                                            st.error(f"❌ Debug test failed: {e}")
                    else:
                        st.error("❌ No enabled subscriptions found")
                else:
                    st.error("❌ Unable to load subscriptions")
                    
            elif dns_zone_option == "🏠 Simple: Use existing DNS zones in private-rg (same subscription)":
                st.markdown("### � Simple Configuration")
                st.info("**Scenario**: DNS zones are in the same subscription as your deployment, in the 'private-rg' resource group.")
                
                # Default to private-rg resource group
                config.dns_zone_subscription_id = ""  # Current subscription
                config.dns_zone_resource_group_name = "private-rg"
                config.create_dns_zones_if_not_exist = False
                
                st.success("✅ **Configuration**: Using DNS zones in current subscription → private-rg resource group")
                
                # Validate DNS zones exist in private-rg
                with st.spinner("Validating DNS zones in private-rg..."):
                    zone_status = self.service.validate_dns_zones_exist("", "private-rg")
                
                if zone_status:
                    st.markdown("#### 🔍 DNS Zone Validation")
                    all_zones_exist = all(zone_status.values())
                    
                    for zone_name, exists in zone_status.items():
                        if exists:
                            st.success(f"✅ {zone_name}")
                        else:
                            st.error(f"❌ {zone_name}")
                    
                    if not all_zones_exist:
                        st.error("⚠️ Some required DNS zones are missing in private-rg. Please create them or use a different configuration.")
                    else:
                        st.success("🎉 All required DNS zones found in private-rg!")
                        
            else:  # Development: Create new zones
                st.markdown("### 🆕 Development Configuration")
                st.info("**Scenario**: New DNS zones will be created in the same resource group as your deployment.")
                
                # Create new zones in deployment location
                config.dns_zone_subscription_id = ""
                config.dns_zone_resource_group_name = ""
                config.create_dns_zones_if_not_exist = True
                
                st.warning("⚠️ **Note**: DNS zones will be created in your deployment resource group")
                st.info("ℹ️ This is suitable for development environments or when you want self-contained deployments")

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
                # New VNet will be created in the deployment subscription - no selection needed
                st.info("🏗️ **New VNet**: Will be created in the deployment subscription")
                
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
                # Existing VNet settings with subscription selection
                st.markdown("**🔄 VNet Location Subscription**")
                self._render_subscription_selector("vnet", "Virtual Network", for_new_resource=False)
                
                st.markdown("**Select Existing VNet:**")
                
                # Get the selected subscription for VNet
                vnet_subscription_id = st.session_state.get("vnet_subscription_id")
                
                if vnet_subscription_id:
                    # Cache key for VNets in this subscription
                    vnet_cache_key = f"vnet_resources_{vnet_subscription_id}"
                    
                    # Get available VNets from the target subscription
                    if vnet_cache_key not in st.session_state:
                        with st.spinner("Loading VNets from selected subscription..."):
                            # Temporarily switch context if needed
                            current_sub = self.service.get_current_subscription_info()
                            current_sub_id = current_sub['subscription_id'] if current_sub else None
                            
                            if vnet_subscription_id != current_sub_id:
                                switch_success, _ = self.service.switch_subscription_context(vnet_subscription_id)
                                if not switch_success:
                                    st.error("❌ Failed to switch to VNet subscription")
                                    return
                            
                            # Get VNets
                            vnets = self.service.get_subscription_resources("Microsoft.Network/virtualNetworks")
                            st.session_state[vnet_cache_key] = vnets
                            
                            # Switch back if needed
                            if vnet_subscription_id != current_sub_id and current_sub_id:
                                self.service.switch_subscription_context(current_sub_id)
                    
                    vnets = st.session_state.get(vnet_cache_key, [])
                    
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
                            help="Select an existing Virtual Network from the chosen subscription"
                        )
                        
                        # Add refresh button for VNets
                        if st.button("🔄 Refresh VNet List", key="refresh_vnet_list"):
                            if vnet_cache_key in st.session_state:
                                del st.session_state[vnet_cache_key]
                            st.rerun()
                        
                        if selected_vnet:
                            config.network_config.existing_vnet_resource_id = vnet_options[selected_vnet]
                            
                            # Show selected VNet details
                            selected_vnet_info = next(v for v in vnets if v['id'] == config.network_config.existing_vnet_resource_id)
                            st.info(f"Selected VNet: {selected_vnet_info['name']} in {selected_vnet_info['location']}")
                            
                            # Show cross-subscription info if applicable
                            current_sub = self.service.get_current_subscription_info()
                            current_sub_id = current_sub['subscription_id'] if current_sub else None
                            if vnet_subscription_id != current_sub_id:
                                st.info(f"🔄 VNet will be accessed from subscription: {vnet_subscription_id}")
                            
                            # Get subnets for the selected VNet
                            st.markdown("**Subnet Configuration:**")
                            
                            # Get subnets (may need to switch context again)
                            subnet_cache_key = f"subnets_{config.network_config.existing_vnet_resource_id.replace('/', '_')}"
                            
                            if subnet_cache_key not in st.session_state:
                                with st.spinner("Loading subnets..."):
                                    # Switch context if needed for subnet query
                                    if vnet_subscription_id != current_sub_id:
                                        switch_success, _ = self.service.switch_subscription_context(vnet_subscription_id)
                                        if not switch_success:
                                            st.error("❌ Failed to switch to VNet subscription for subnet query")
                                            return
                                    
                                    subnets = self.service.get_vnet_subnets(config.network_config.existing_vnet_resource_id)
                                    st.session_state[subnet_cache_key] = subnets
                                    
                                    # Switch back if needed
                                    if vnet_subscription_id != current_sub_id and current_sub_id:
                                        self.service.switch_subscription_context(current_sub_id)
                            
                            subnets = st.session_state.get(subnet_cache_key, [])
                            
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
            st.info("Choose whether to create new resources or use existing ones for each dependency. You can also select different subscriptions for each resource.")
            
            # Cosmos DB Configuration
            self._render_resource_section_with_subscription(
                "🌌 Cosmos DB",
                config.cosmos_db,
                "Microsoft.DocumentDB/databaseAccounts",
                "Azure Cosmos DB for NoSQL database for storing agent conversations and metadata",
                "cosmos_db"
            )
            
            # AI Search Configuration
            self._render_resource_section_with_subscription(
                "🔍 AI Search",
                config.ai_search,
                "Microsoft.Search/searchServices",
                "Azure AI Search service for vector search and document indexing",
                "ai_search"
            )
            
            # Storage Account Configuration
            self._render_resource_section_with_subscription(
                "💾 Storage Account",
                config.storage_account,
                "Microsoft.Storage/storageAccounts",
                "Azure Storage account for storing documents and artifacts",
                "storage_account"
            )
    
    def _render_resource_section_with_subscription(self, title: str, resource: DeploymentResource, resource_type: str, description: str, resource_key: str) -> None:
        """Render a single resource configuration section with subscription selection."""
        with st.container():
            st.markdown(f"#### {title}")
            st.caption(description)
            
            # All resources now support skip deployment option
            col1, col2 = st.columns([2, 3])
            
            with col1:
                deployment_option = st.radio(
                    f"{title} Deployment",
                    ["Create New", "Use Existing", "Skip Deployment"],
                    index=0 if resource.create_new else (1 if not resource.skip_deployment else 2),
                    key=f"{resource_type}_deployment_option",
                    help=f"Choose to create new, use existing, or skip {title} deployment entirely"
                )
                
                resource.create_new = deployment_option == "Create New"
                resource.skip_deployment = deployment_option == "Skip Deployment"
            
            with col2:
                if deployment_option == "Skip Deployment":
                    st.info(f"ℹ️ {title} deployment will be skipped. You can configure it later if needed.")
                elif deployment_option == "Use Existing":
                    # Add subscription selection for existing resources
                    self._render_subscription_selector(resource_key, title)
                    self._render_existing_resource_config_with_subscription(resource, resource_type, title, resource_key)
                elif deployment_option == "Create New":
                    # Add subscription selection for new resources as well
                    self._render_subscription_selector(resource_key, title, for_new_resource=True)
            
            st.divider()
    
    def _render_subscription_selector(self, resource_key: str, resource_title: str, for_new_resource: bool = False) -> None:
        """Render subscription selector for a specific resource."""
        st.markdown("**🔄 Subscription Selection**")
        
        # Get available subscriptions
        subscriptions = self.service.get_prioritized_subscriptions()
        current_sub_info = self.service.get_current_subscription_info()
        current_sub_id = current_sub_info['subscription_id'] if current_sub_info else None
        
        if not subscriptions:
            st.error("❌ No subscriptions available")
            return
        
        # Create subscription options with enhanced labeling
        subscription_options = {}
        for sub in subscriptions:
            if sub['state'] == 'Enabled':
                label = f"{sub['display_name']} ({sub['subscription_id']})"
                if sub['subscription_id'] == current_sub_id:
                    label = f"🌟 {label} (Current)"
                subscription_options[label] = sub['subscription_id']
        
        if not subscription_options:
            st.error("❌ No enabled subscriptions found")
            return
        
        # Session state key for this resource's subscription
        subscription_state_key = f"{resource_key}_subscription_id"
        
        # Initialize with current subscription if not set
        if subscription_state_key not in st.session_state:
            st.session_state[subscription_state_key] = current_sub_id or list(subscription_options.values())[0]
        
        # Find current selection index
        selected_subscription_id = st.session_state[subscription_state_key]
        subscription_index = 0
        subscription_list = list(subscription_options.items())
        for i, (label, sub_id) in enumerate(subscription_list):
            if sub_id == selected_subscription_id:
                subscription_index = i
                break
        
        # Callback for subscription change
        def on_subscription_change():
            selected_key = st.session_state[f"{resource_key}_subscription_selector"]
            if selected_key in subscription_options:
                new_subscription_id = subscription_options[selected_key]
                old_subscription_id = st.session_state.get(subscription_state_key)
                
                # Only switch if the subscription actually changed
                if new_subscription_id != old_subscription_id:
                    st.session_state[subscription_state_key] = new_subscription_id
                    
                    # Clear any cached resources for this subscription
                    cache_key = f"{resource_key}_resources_{new_subscription_id}"
                    if cache_key in st.session_state:
                        del st.session_state[cache_key]
                    
                    # Show success message
                    st.success(f"✅ Switched to subscription: {selected_key}")
        
        # Subscription selector
        action_text = "deploy to" if for_new_resource else "select from"
        selected_subscription = st.selectbox(
            f"Select subscription to {action_text} for {resource_title}",
            options=list(subscription_options.keys()),
            index=subscription_index,
            help=f"🌟 = Current subscription. Choose which subscription to {action_text} for {resource_title}",
            key=f"{resource_key}_subscription_selector",
            on_change=on_subscription_change
        )
        
        # Show current selection status
        selected_sub_id = st.session_state[subscription_state_key]
        is_current = selected_sub_id == current_sub_id
        
        if is_current:
            st.success(f"✅ **{resource_title} Subscription**: Same as deployment subscription")
        else:
            st.info(f"🔄 **{resource_title} Subscription**: Cross-subscription configuration")
            
            # Add authentication button for different subscription
            col_auth1, col_auth2 = st.columns([3, 1])
            with col_auth1:
                st.caption(f"Target: `{selected_sub_id}`")
            with col_auth2:
                if st.button(
                    "🔐 Switch", 
                    help=f"Switch Azure CLI context to {resource_title} subscription",
                    key=f"switch_to_{resource_key}_subscription",
                    type="secondary"
                ):
                    with st.spinner(f"Switching to {resource_title} subscription..."):
                        success, message = self.service.switch_subscription_context(selected_sub_id)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
    
    def _render_existing_resource_config_with_subscription(self, resource: DeploymentResource, resource_type: str, title: str, resource_key: str) -> None:
        """Render configuration for existing resources with subscription awareness."""
        # Get the selected subscription for this resource
        subscription_state_key = f"{resource_key}_subscription_id"
        target_subscription_id = st.session_state.get(subscription_state_key)
        
        if not target_subscription_id:
            st.warning(f"Please select a subscription for {title} first")
            return
        
        # Cache key for resources in this subscription
        cache_key = f"{resource_key}_resources_{target_subscription_id}"
        
        # Get available resources from the target subscription
        if cache_key not in st.session_state:
            with st.spinner(f"Loading {title} resources from selected subscription..."):
                # Temporarily switch context if needed to get resources
                current_sub = self.service.get_current_subscription_info()
                current_sub_id = current_sub['subscription_id'] if current_sub else None
                
                if target_subscription_id != current_sub_id:
                    # Switch to target subscription
                    switch_success, _ = self.service.switch_subscription_context(target_subscription_id)
                    if not switch_success:
                        st.error(f"❌ Failed to switch to target subscription for {title}")
                        return
                
                # Get resources
                resources = self.service.get_subscription_resources(resource_type)
                st.session_state[cache_key] = resources
                
                # Switch back to original subscription if needed
                if target_subscription_id != current_sub_id and current_sub_id:
                    self.service.switch_subscription_context(current_sub_id)
        
        resources = st.session_state.get(cache_key, [])
        
        if resources:
            resource_options = {f"{res['name']} ({res['resourceGroup']})": res['id'] for res in resources}
            
            # Find current selection if any
            current_selection = 0
            if resource.existing_resource_id:
                for i, (display_name, resource_id) in enumerate(resource_options.items()):
                    if resource_id == resource.existing_resource_id:
                        current_selection = i
                        break
            
            selected_resource = st.selectbox(
                f"Select {title}",
                list(resource_options.keys()),
                index=current_selection,
                key=f"{resource_type}_selector"
            )
            
            if selected_resource:
                resource.existing_resource_id = resource_options[selected_resource]
                
                # Show selected resource details
                selected_resource_info = next(r for r in resources if r['id'] == resource.existing_resource_id)
                st.success(f"✅ Selected: {selected_resource_info['name']} in {selected_resource_info['location']}")
                
                # Show subscription info
                if target_subscription_id != self.service.get_current_subscription_info().get('subscription_id'):
                    st.info(f"🔄 Resource will be accessed from subscription: {target_subscription_id}")
        else:
            st.warning(f"No {title} resources found in the selected subscription")
            resource.existing_resource_id = st.text_input(
                f"{title} Resource ID",
                value=resource.existing_resource_id,
                help=f"Enter the full resource ID of the existing {title.lower()} from the selected subscription",
                key=f"{resource_type}_manual"
            )
        
        # Add refresh button for resources
        if st.button(f"🔄 Refresh {title} List", key=f"refresh_{resource_key}_resources"):
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            st.rerun()
        
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
        
        # Deployment Target Selection
        st.markdown("### 🎯 Deployment Target")
        st.info("Select the subscription and resource group where the AI Foundry Account and related resources will be deployed.")
        
        # Subscription Selection
        st.markdown("#### 🎯 Target Subscription")
        
        # Add enterprise context
        with st.expander("📚 Subscription Selection Guide", expanded=False):
            st.markdown("""
            **🏢 Enterprise Deployment Patterns**:
            - **Hub Subscription**: Central networking and shared services (DNS zones, connectivity)
            - **Spoke Subscription**: Application workloads and AI Foundry resources
            - **Production Subscription**: Production AI workloads and foundry instances
            - **Development Subscription**: Development and testing environments
            
            **🔒 Required Permissions**:
            - **Contributor** or **Owner** role in the target subscription
            - **Network Contributor** for VNet and subnet operations
            - **DNS Zone Contributor** for DNS zone operations (if cross-subscription)
            """)
        
        # Get available subscriptions with current subscription prioritized
        subscriptions = self.service.get_prioritized_subscriptions()
        
        if subscriptions:
            # Subscription selection with better labeling and current subscription highlighted
            subscription_options = {}
            current_sub_info = self.service.get_current_subscription_info()
            current_sub_id = current_sub_info['subscription_id'] if current_sub_info else None
            
            for sub in subscriptions:
                if sub['state'] == 'Enabled':
                    label = f"{sub['display_name']} ({sub['subscription_id']})"
                    if sub['subscription_id'] == current_sub_id:
                        label = f"🌟 {label} (Current)"
                    subscription_options[label] = sub['subscription_id']
            
            if subscription_options:
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    # Initialize session state for deployment subscription if not exists
                    if 'deployment_subscription_id' not in st.session_state:
                        st.session_state.deployment_subscription_id = current_sub_id or list(subscription_options.values())[0]
                    
                    # Find current selection index based on saved subscription ID
                    current_selection_index = 0
                    subscription_list = list(subscription_options.items())
                    
                    for i, (label, sub_id) in enumerate(subscription_list):
                        if sub_id == st.session_state.deployment_subscription_id:
                            current_selection_index = i
                            break
                    
                    # Use a callback to handle subscription changes
                    def on_subscription_change():
                        """Handle subscription selection change."""
                        selected_key = st.session_state.deploy_subscription_selector
                        if selected_key in subscription_options:
                            new_subscription_id = subscription_options[selected_key]
                            old_subscription_id = st.session_state.get('deployment_subscription_id')
                            
                            # Only switch if the subscription actually changed
                            if new_subscription_id != old_subscription_id:
                                st.session_state.deployment_subscription_id = new_subscription_id
                                
                                # Switch Azure CLI context
                                with st.spinner(f"Switching to subscription {new_subscription_id}..."):
                                    success, message = self.service.switch_subscription_context(new_subscription_id)
                                    if success:
                                        st.success(message)
                                    else:
                                        st.error(message)
                                        # Revert to previous subscription on failure
                                        if old_subscription_id:
                                            st.session_state.deployment_subscription_id = old_subscription_id
                                
                                # Clear resource group selection when subscription changes
                                if 'deployment_resource_group' in st.session_state:
                                    del st.session_state['deployment_resource_group']
                    
                    selected_subscription_display = st.selectbox(
                        "Select the subscription for deployment",
                        options=list(subscription_options.keys()),
                        index=current_selection_index,
                        help="🌟 = Current subscription. Choose where to deploy the AI Foundry Account and resources",
                        key="deploy_subscription_selector",
                        on_change=on_subscription_change
                    )
                    
                    # Ensure session state is updated (fallback)
                    if selected_subscription_display in subscription_options:
                        st.session_state.deployment_subscription_id = subscription_options[selected_subscription_display]
                    
                    # Show selection confirmation with enhanced information
                    is_current = st.session_state.deployment_subscription_id == current_sub_id
                    selected_sub_info = next((sub for sub in subscriptions if sub['subscription_id'] == st.session_state.deployment_subscription_id), None)
                    
                    if is_current:
                        st.success(f"✅ **Deployment Subscription**: {selected_subscription_display} (Same as current)")
                        st.info("ℹ️ **Configuration**: Single subscription deployment (recommended for development)")
                    else:
                        st.info(f"🔄 **Deployment Subscription**: {selected_subscription_display} (Cross-subscription deployment)")
                        st.warning("⚠️ **Cross-subscription deployment**: Ensure you have proper permissions in the target subscription")
                        st.info("ℹ️ **Configuration**: Multi-subscription deployment (common in enterprise environments)")
                    
                    # Show additional subscription information
                    if selected_sub_info:
                        st.caption(f"📋 **Subscription State**: {selected_sub_info.get('state', 'Unknown')}")
                        if selected_sub_info.get('tenantId'):
                            st.caption(f"🏢 **Tenant ID**: {selected_sub_info['tenantId']}")
                    
                    # Add subscription context switching section
                    if not is_current and st.session_state.deployment_subscription_id:
                        st.markdown("---")
                        st.markdown("#### 🔐 Subscription Authentication")
                        
                        col_auth1, col_auth2 = st.columns([2, 1])
                        
                        with col_auth1:
                            st.info(f"🔄 **Action Required**: Switch Azure CLI context to target subscription")
                            st.markdown(f"**Target**: `{st.session_state.deployment_subscription_id}`")
                            
                            # Show current context
                            try:
                                context_info = self.service.get_subscription_context_info()
                                st.markdown("**Current Azure CLI Context:**")
                                st.code(f"""
Subscription: {context_info['subscription_name']} ({context_info['subscription_id']})
User: {context_info['user_name']} ({context_info['user_type']})
Tenant: {context_info['tenant_id']}
State: {context_info['state']}
""")
                            except Exception as e:
                                st.warning(f"Could not get current context: {e}")
                        
                        with col_auth2:
                            if st.button(
                                "🔐 Sign In & Switch",
                                help="Sign in to Azure and switch to the selected subscription",
                                key="auth_and_switch_subscription",
                                type="primary"
                            ):
                                with st.spinner(f"🔐 Authenticating to subscription {st.session_state.deployment_subscription_id}..."):
                                    success, message = self.service.authenticate_and_switch_subscription(
                                        st.session_state.deployment_subscription_id
                                    )
                                    
                                    if success:
                                        st.success(message)
                                        st.balloons()
                                        
                                        # Update context display
                                        try:
                                            new_context = self.service.get_subscription_context_info()
                                            st.success("🎉 **Authentication Successful!**")
                                            st.info(f"**New Context**: {new_context['subscription_name']} ({new_context['subscription_id']})")
                                        except Exception as e:
                                            st.warning(f"Context updated but could not retrieve details: {e}")
                                        
                                        # Trigger a rerun to update the UI
                                        st.rerun()
                                    else:
                                        st.error(message)
                                        st.info("💡 **Tip**: If login failed, you may need to:")
                                        st.markdown("""
                                        - Check your internet connection
                                        - Ensure you have access to the target subscription
                                        - Contact your Azure administrator for permissions
                                        """)
                
                with col2:
                    if st.button("🔄 Refresh", help="Refresh subscription list", key="refresh_subscriptions_deploy"):
                        # Clear cached services to force refresh
                        if 'ai_foundry_deployment_service' in st.session_state:
                            del st.session_state['ai_foundry_deployment_service']
                        st.rerun()
                    
                    # Add validation button for cross-subscription scenarios
                    if not is_current:
                        if st.button("🔍 Validate", help="Validate permissions in target subscription", key="validate_target_subscription"):
                            with st.spinner("Validating permissions..."):
                                try:
                                    # Try to list resource groups as a basic permission test
                                    test_rgs = self.service.get_subscription_resource_groups(st.session_state.deployment_subscription_id)
                                    if test_rgs is not None:
                                        st.success(f"✅ Access validated ({len(test_rgs)} resource groups found)")
                                    else:
                                        st.error("❌ Unable to access target subscription")
                                except Exception as e:
                                    st.error(f"❌ Permission error: {str(e)}")
                                    st.warning("Please ensure you have Contributor role in the target subscription")
            else:
                st.error("❌ No enabled subscriptions found")
                return
        else:
            st.error("❌ Unable to load subscriptions. Please check your Azure CLI login and permissions.")
            return
        
        # Resource Group Selection
        st.markdown("#### 📁 Target Resource Group")
        
        # Get resource groups for the selected subscription
        selected_subscription_id = st.session_state.deployment_subscription_id
        
        # Get resource groups from the selected subscription
        try:
            resource_groups = self.service.get_subscription_resource_groups(selected_subscription_id)
            
            if resource_groups:
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Initialize resource group session state
                    rg_key = f"deployment_resource_group_{selected_subscription_id}"
                    if rg_key not in st.session_state and resource_groups:
                        st.session_state[rg_key] = resource_groups[0]
                    
                    # Find current selection index
                    rg_index = 0
                    if rg_key in st.session_state and st.session_state[rg_key] in resource_groups:
                        rg_index = resource_groups.index(st.session_state[rg_key])
                    
                    def on_rg_change():
                        """Handle resource group selection change."""
                        st.session_state[rg_key] = st.session_state[f"deploy_rg_selector_{selected_subscription_id}"]
                    
                    target_rg = st.selectbox(
                        f"Select Resource Group (in subscription {selected_subscription_id[:8]}...)",
                        resource_groups,
                        index=rg_index,
                        help=f"Select the resource group where resources will be deployed in subscription {selected_subscription_id[:8]}...",
                        key=f"deploy_rg_selector_{selected_subscription_id}",
                        on_change=on_rg_change
                    )
                    
                    # Update session state
                    st.session_state[rg_key] = target_rg
                
                with col2:
                    if st.button("🔄 Refresh RGs", key=f"refresh_rgs_deploy_{selected_subscription_id}"):
                        # Clear the cached resource group selection when refreshing
                        if rg_key in st.session_state:
                            del st.session_state[rg_key]
                        st.rerun()
                        
                if selected_subscription_id == current_sub_id:
                    st.success(f"✅ **Target Resource Group**: {target_rg} (in current subscription)")
                else:
                    st.success(f"✅ **Target Resource Group**: {target_rg} (in target subscription {selected_subscription_id[:8]}...)")
            else:
                st.warning(f"⚠️ No resource groups found in subscription {selected_subscription_id[:8]}...")
                
                # Manual input for empty subscription or error scenarios
                manual_rg_key = f"manual_rg_{selected_subscription_id}"
                target_rg = st.text_input(
                    "Resource Group Name",
                    value=st.session_state.get(manual_rg_key, ""),
                    help="Enter the name of the resource group (it will be created if it doesn't exist)",
                    placeholder="e.g., rg-ai-foundry-prod",
                    key=manual_rg_key
                )
                
                if target_rg:
                    st.info(f"📝 **Target Resource Group**: {target_rg} (will be created if it doesn't exist)")
                else:
                    st.info("📝 Please enter the resource group name")
                
        except Exception as e:
            st.error(f"❌ Error accessing subscription {selected_subscription_id[:8]}...: {str(e)}")
            st.warning("Please ensure you have proper permissions in the target subscription.")
            
            # Fallback to manual input
            target_rg = st.text_input(
                "Resource Group Name (Manual Entry)",
                value="",
                help="Enter the name of the resource group in the target subscription",
                placeholder="e.g., rg-ai-foundry-prod"
            )
            
            if target_rg:
                st.info(f"📝 **Target Resource Group**: {target_rg} (manual entry - ensure it exists or will be created)")
            else:
                st.warning("📝 Please enter the resource group name")
        
        # Deployment Configuration Summary
        if target_rg and st.session_state.deployment_subscription_id:
            st.markdown("### 📋 Deployment Summary")
            
            with st.expander("🔍 Review Deployment Configuration", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**🎯 Deployment Target:**")
                    st.write(f"• **Subscription**: {st.session_state.deployment_subscription_id[:8]}...")
                    st.write(f"• **Resource Group**: {target_rg}")
                    st.write(f"• **Location**: {config.location}")
                    st.write(f"• **AI Services Name**: {config.ai_services_name}")
                    
                    st.markdown("**🌐 Network Configuration:**")
                    if config.network_config.create_new_vnet:
                        st.write(f"• **VNet**: Create new ({config.network_config.vnet_name})")
                        st.write(f"• **VNet CIDR**: {config.network_config.vnet_address_prefix}")
                    else:
                        st.write(f"• **VNet**: Use existing")
                        if config.network_config.existing_vnet_resource_id:
                            vnet_name = config.network_config.existing_vnet_resource_id.split('/')[-1]
                            st.write(f"• **VNet Name**: {vnet_name}")
                
                with col2:
                    st.markdown("**🔗 DNS Configuration:**")
                    if config.dns_zone_subscription_id:
                        st.write(f"• **DNS Subscription**: {config.dns_zone_subscription_id[:8]}...")
                    else:
                        st.write(f"• **DNS Subscription**: Same as deployment")
                    
                    if config.dns_zone_resource_group_name:
                        st.write(f"• **DNS Resource Group**: {config.dns_zone_resource_group_name}")
                    else:
                        st.write(f"• **DNS Resource Group**: Same as deployment")
                    
                    st.write(f"• **Create DNS Zones**: {'Yes' if config.create_dns_zones_if_not_exist else 'No'}")
                    
                    st.markdown("**🧠 Model Configuration:**")
                    if config.skip_openai_deployment:
                        st.write("• **OpenAI Models**: Skipped")
                    else:
                        st.write(f"• **OpenAI Models**: {config.model_name}")
                        st.write(f"• **Model Capacity**: {config.model_capacity} TPM")
                    
                    st.markdown("**📦 Resources:**")
                    resources_status = []
                    if not config.cosmos_db.skip_deployment:
                        status = "Create New" if config.cosmos_db.create_new else "Use Existing"
                        resources_status.append(f"• **Cosmos DB**: {status}")
                    if not config.ai_search.skip_deployment:
                        status = "Create New" if config.ai_search.create_new else "Use Existing"
                        resources_status.append(f"• **AI Search**: {status}")
                    if not config.storage_account.skip_deployment:
                        status = "Create New" if config.storage_account.create_new else "Use Existing"
                        resources_status.append(f"• **Storage Account**: {status}")
                    
                    for status in resources_status:
                        st.write(status)
        
        # Deployment Name
        deployment_name = st.text_input(
            "Deployment Name",
            value=f"ai-foundry-account-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            help="Name for this deployment (must be unique within the resource group)"
        )
        
        # Important deployment notes
        if st.session_state.deployment_subscription_id != current_sub_id:
            st.warning("""
            ⚠️ **Cross-Subscription Deployment Notes:**
            - Ensure you have **Contributor** or **Owner** permissions in the target subscription
            - DNS zone configuration should point to accessible DNS zones
            - Network resources should be properly configured for cross-subscription access
            - Deployment may take longer due to cross-subscription operations
            """)
        
        # Deployment Button
        st.markdown("### 🎬 Start Deployment")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            deploy_button_text = "🚀 Deploy AI Foundry Account"
            if st.session_state.deployment_subscription_id != current_sub_id:
                deploy_button_text += " (Cross-Subscription)"
        
        if st.button(deploy_button_text, type="primary"):
            if not target_rg:
                st.error("Please select or enter a resource group.")
                return
            
            if not deployment_name:
                st.error("Please enter a deployment name.")
                return
            
            # Validation for cross-subscription deployment
            if st.session_state.deployment_subscription_id != current_sub_id:
                if not target_rg.strip():
                    st.error("Please enter a valid resource group name for cross-subscription deployment.")
                    return
                
                st.info("🔄 **Cross-subscription deployment initiated**. Please ensure proper permissions are configured.")
            
            # Auto-save configuration before deployment
            if hasattr(st.session_state, 'deployment_config'):
                self.service.save_deployment_config(st.session_state.deployment_config, "last_deployment")
                st.info("💾 Configuration auto-saved as 'last_deployment'")
            
            # Store deployment info in session state including subscription
            st.session_state.current_deployment = {
                'subscription_id': st.session_state.deployment_subscription_id,
                'resource_group': target_rg,
                'deployment_name': deployment_name,
                'status': 'starting',
                'cross_subscription': st.session_state.deployment_subscription_id != current_sub_id
            }
            
            # Start deployment with subscription context
            deployment_message = "🚀 Starting deployment..."
            if st.session_state.deployment_subscription_id != current_sub_id:
                deployment_message += f" (Target subscription: {st.session_state.deployment_subscription_id[:8]}...)"
            deployment_message += " This may take 20-30 minutes."
            
            with st.spinner(deployment_message):
                success, message, output = self.service.deploy_ai_foundry_hub(
                    config, 
                    target_rg, 
                    deployment_name,
                    subscription_id=st.session_state.deployment_subscription_id
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
            if deployment['status'] in ['completed', 'succeeded']:
                if deployment.get('success', False):
                    st.success("✅ Deployment Completed Successfully")
                else:
                    st.error("❌ Deployment Failed")
            elif deployment['status'] in ['starting', 'running', 'accepted']:
                st.info("🚀 Deployment In Progress")
            elif deployment['status'] in ['failed']:
                st.error("❌ Deployment Failed")
            elif deployment['status'] in ['cancelled']:
                st.warning("⚠️ Deployment Cancelled")
            else:
                st.warning(f"⚠️ Status: {deployment['status']}")
        
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
                st.session_state.current_deployment['success'] = (provisioning_state == 'Succeeded')
                
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
