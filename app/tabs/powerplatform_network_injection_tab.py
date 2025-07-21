"""
Module: app/tabs/powerplatform_network_injection_tab.py
Purpose: Handles PowerPlatform Network Injection operations with Azure private endpoints
Dependencies: streamlit, azure cli, subprocess
"""

import streamlit as st
import subprocess
import os
import json
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


def render_powerplatform_network_injection_tab(
    session_state: Dict[str, Any],
    **kwargs
) -> None:
    """
    Render the PowerPlatform Network Injection tab with dynamic parameter collection.
    
    Args:
        session_state: Streamlit session state dictionary
        **kwargs: Additional keyword arguments
    """
    st.header("🌐 PowerPlatform Network Injection")
    
    st.markdown("""
    **🎯 Purpose**: Configure PowerPlatform subnet injection to connect to Azure with private endpoints.
    This allows PowerPlatform environments to access private Azure resources like blob storage.
    """)
    
    # Initialize session state for this tab
    _initialize_session_state()
    
    # Azure Subscription Selection
    subscription_id = render_subscription_selection()
    
    if not subscription_id:
        st.warning("⚠️ Please select or configure an Azure subscription to continue.")
        return
    
    # Network Configuration Section
    network_config = render_network_configuration_section(subscription_id)
    
    if not network_config:
        return
    
    # PowerPlatform Configuration Section
    powerplatform_config = render_powerplatform_configuration_section()
    
    # Script Operations Section
    render_script_operations_section(subscription_id, network_config, powerplatform_config)


def _initialize_session_state() -> None:
    """Initialize session state variables for the PowerPlatform tab."""
    defaults = {
        'pp_selected_subscription': None,
        'pp_resource_groups': [],
        'pp_vnets': [],
        'pp_subnets': [],
        'pp_script_output': '',
        'pp_last_operation': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_subscription_selection() -> Optional[str]:
    """Render Azure subscription selection section."""
    st.subheader("🔐 Step 1: Azure Subscription")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Check if already logged in
        try:
            result = subprocess.run(['az', 'account', 'show'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                account_info = json.loads(result.stdout)
                current_subscription = account_info.get('id', 'Unknown')
                subscription_name = account_info.get('name', 'Unknown')
                st.success(f"✅ Logged in to Azure")
                st.caption(f"**Subscription**: {subscription_name}")
                st.caption(f"**ID**: {current_subscription}")
                return current_subscription
            else:
                st.warning("⚠️ Not logged in to Azure CLI")
                return None
        except Exception as e:
            st.error(f"❌ Failed to check Azure login status: {str(e)}")
            return None
    
    with col2:
        if st.button("🔄 Login to Azure", type="primary"):
            with st.spinner("Opening Azure login..."):
                try:
                    result = subprocess.run(['az', 'login'], capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        st.success("✅ Azure login successful!")
                        st.rerun()
                    else:
                        st.error(f"❌ Azure login failed: {result.stderr}")
                except subprocess.TimeoutExpired:
                    st.error("❌ Login timeout. Please try again.")
                except Exception as e:
                    st.error(f"❌ Login error: {str(e)}")
        
        # Alternative subscription selection
        if st.button("📋 List Subscriptions"):
            with st.spinner("Loading subscriptions..."):
                try:
                    result = subprocess.run(['az', 'account', 'list'], 
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        subscriptions = json.loads(result.stdout)
                        st.session_state.available_subscriptions = subscriptions
                        st.success(f"Found {len(subscriptions)} subscriptions")
                    else:
                        st.error("Failed to list subscriptions")
                except Exception as e:
                    st.error(f"Error listing subscriptions: {str(e)}")
    
    # Subscription selection dropdown if multiple are available
    if hasattr(st.session_state, 'available_subscriptions'):
        subscription_options = [
            f"{sub['name']} ({sub['id']})" 
            for sub in st.session_state.available_subscriptions
        ]
        selected = st.selectbox("Select Subscription", [""] + subscription_options)
        if selected:
            subscription_id = selected.split('(')[-1].rstrip(')')
            # Set the subscription
            try:
                result = subprocess.run(['az', 'account', 'set', '--subscription', subscription_id],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    st.success(f"✅ Switched to subscription: {subscription_id}")
                    return subscription_id
                else:
                    st.error(f"Failed to switch subscription: {result.stderr}")
            except Exception as e:
                st.error(f"Error switching subscription: {str(e)}")
    
    return None


def render_network_configuration_section(subscription_id: str) -> Optional[Dict[str, str]]:
    """Render network configuration section with dynamic Azure resource loading."""
    st.subheader("🌐 Step 2: Network Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Resource Group Selection
        st.markdown("**Resource Group**")
        if st.button("🔄 Load Resource Groups"):
            with st.spinner("Loading resource groups..."):
                try:
                    result = subprocess.run([
                        'az', 'group', 'list', '--query', '[].name', '--output', 'json'
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        rgs = json.loads(result.stdout)
                        st.session_state.pp_resource_groups = rgs
                        st.success(f"✅ Loaded {len(rgs)} resource groups")
                    else:
                        st.error(f"Failed to load resource groups: {result.stderr}")
                except Exception as e:
                    st.error(f"Error loading resource groups: {str(e)}")
        
        resource_group = st.selectbox(
            "Select Resource Group",
            options=[""] + st.session_state.get('pp_resource_groups', []),
            key="pp_selected_rg"
        )
    
    with col2:
        # VNet Loading
        st.markdown("**Virtual Networks**")
        if resource_group and st.button("🔄 Load VNets"):
            with st.spinner(f"Loading VNets in {resource_group}..."):
                try:
                    result = subprocess.run([
                        'az', 'network', 'vnet', 'list',
                        '--resource-group', resource_group,
                        '--query', '[].name',
                        '--output', 'json'
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        vnets = json.loads(result.stdout)
                        st.session_state.pp_vnets = vnets
                        st.success(f"✅ Loaded {len(vnets)} VNets")
                    else:
                        st.error(f"Failed to load VNets: {result.stderr}")
                except Exception as e:
                    st.error(f"Error loading VNets: {str(e)}")
    
    # VNet Selection
    if resource_group:
        st.markdown("**Virtual Network Selection**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            primary_vnet = st.selectbox(
                "Primary VNet",
                options=[""] + st.session_state.get('pp_vnets', []),
                key="pp_primary_vnet"
            )
        
        with col2:
            secondary_vnet = st.selectbox(
                "Secondary VNet",
                options=[""] + st.session_state.get('pp_vnets', []),
                key="pp_secondary_vnet"
            )
        
        # Subnet Selection
        if primary_vnet:
            st.markdown("**Subnet Configuration**")
            col1, col2 = st.columns([2, 1])
            
            with col1:
                if st.button("🔄 Load Subnets"):
                    with st.spinner(f"Loading subnets in {primary_vnet}..."):
                        try:
                            result = subprocess.run([
                                'az', 'network', 'vnet', 'subnet', 'list',
                                '--resource-group', resource_group,
                                '--vnet-name', primary_vnet,
                                '--query', '[].name',
                                '--output', 'json'
                            ], capture_output=True, text=True, timeout=30)
                            
                            if result.returncode == 0:
                                subnets = json.loads(result.stdout)
                                st.session_state.pp_subnets = subnets
                                st.success(f"✅ Loaded {len(subnets)} subnets")
                            else:
                                st.error(f"Failed to load subnets: {result.stderr}")
                        except Exception as e:
                            st.error(f"Error loading subnets: {str(e)}")
                
                subnet_name = st.selectbox(
                    "Subnet Name",
                    options=[""] + st.session_state.get('pp_subnets', []),
                    key="pp_subnet_name"
                )
            
            with col2:
                st.info("💡 Same subnet will be used for both VNets")
        
        # Return configuration if all fields are filled
        if all([resource_group, primary_vnet, secondary_vnet, subnet_name]):
            return {
                'resource_group': resource_group,
                'primary_vnet': primary_vnet,
                'secondary_vnet': secondary_vnet,
                'subnet_name': subnet_name
            }
    
    return None


def render_powerplatform_configuration_section() -> Dict[str, str]:
    """Render PowerPlatform-specific configuration section."""
    st.subheader("⚡ Step 3: PowerPlatform Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        env_id = st.text_input(
            "Environment ID",
            placeholder="b98e9fde-ed33-e9cb-b7c7-b79e43946c48",
            help="Copy this from your PowerPlatform environment settings",
            key="pp_env_id"
        )
    
    with col2:
        policy_resource_group = st.text_input(
            "Policy Resource Group",
            value="powerplatform-enterprise-policies",
            help="Resource group for the PowerPlatform enterprise policy",
            key="pp_policy_rg"
        )
    
    policy_name = st.text_input(
        "Policy Name",
        value="PowerPlatformSubnetInjectionPolicy-Europe",
        help="Name of the enterprise policy for subnet injection",
        key="pp_policy_name"
    )
    
    if env_id:
        st.success("✅ PowerPlatform configuration ready")
    else:
        st.warning("⚠️ Environment ID is required")
    
    return {
        'env_id': env_id,
        'policy_resource_group': policy_resource_group,
        'policy_name': policy_name
    }


def render_script_operations_section(
    subscription_id: str, 
    network_config: Optional[Dict[str, str]], 
    powerplatform_config: Dict[str, str]
) -> None:
    """Render script operations section with Apply, Remove, and Verify functionality."""
    st.subheader("🚀 Step 4: Script Operations")
    
    if not network_config or not powerplatform_config.get('env_id'):
        st.warning("⚠️ Please complete the network and PowerPlatform configuration above.")
        return
    
    # Create tabs for the three operations
    apply_tab, remove_tab, verify_tab = st.tabs(["✅ Apply Injection", "🗑️ Remove Injection", "🔍 Verify Status"])
    
    with apply_tab:
        render_apply_injection_section(subscription_id, network_config, powerplatform_config)
    
    with remove_tab:
        render_remove_injection_section(subscription_id, network_config, powerplatform_config)
    
    with verify_tab:
        render_verify_injection_section(subscription_id, network_config, powerplatform_config)


def render_apply_injection_section(
    subscription_id: str, 
    network_config: Dict[str, str], 
    powerplatform_config: Dict[str, str]
) -> None:
    """Render the apply injection section."""
    st.markdown("### 🔧 Apply PowerPlatform Subnet Injection")
    st.info("This will create the enterprise policy, configure subnet delegations, and link your PowerPlatform environment.")
    
    # Show configuration summary
    with st.expander("📋 Configuration Summary", expanded=False):
        config_data = {
            "Parameter": [
                "Subscription ID", "Resource Group", "Primary VNet", "Secondary VNet", 
                "Subnet Name", "Environment ID", "Policy Resource Group", "Policy Name"
            ],
            "Value": [
                subscription_id, network_config['resource_group'], 
                network_config['primary_vnet'], network_config['secondary_vnet'],
                network_config['subnet_name'], powerplatform_config['env_id'],
                powerplatform_config['policy_resource_group'], powerplatform_config['policy_name']
            ]
        }
        st.dataframe(config_data, use_container_width=True, hide_index=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("**Ready to apply PowerPlatform subnet injection configuration**")
        st.caption("This will run the working_apply_powerplatform_injection.sh script")
    
    with col2:
        if st.button("🚀 Apply Injection", type="primary", use_container_width=True):
            run_powerplatform_script("apply", subscription_id, network_config, powerplatform_config)


def render_remove_injection_section(
    subscription_id: str, 
    network_config: Dict[str, str], 
    powerplatform_config: Dict[str, str]
) -> None:
    """Render the remove injection section."""
    st.markdown("### 🗑️ Remove PowerPlatform Subnet Injection")
    st.warning("This will unlink the environment, remove delegations, and delete the enterprise policy.")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("**Remove PowerPlatform subnet injection configuration**")
        st.caption("This will run the working_remove_powerplatform_injection.sh script")
    
    with col2:
        if st.button("🗑️ Remove Injection", type="secondary", use_container_width=True):
            run_powerplatform_script("remove", subscription_id, network_config, powerplatform_config)


def render_verify_injection_section(
    subscription_id: str, 
    network_config: Dict[str, str], 
    powerplatform_config: Dict[str, str]
) -> None:
    """Render the verify injection section."""
    st.markdown("### 🔍 Verify PowerPlatform Subnet Injection")
    st.info("This will check the current status of your PowerPlatform subnet injection configuration.")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("**Verify current PowerPlatform subnet injection status**")
        st.caption("This will run the working_verify_powerplatform_injection.sh script")
    
    with col2:
        if st.button("🔍 Verify Status", use_container_width=True):
            run_powerplatform_script("verify", subscription_id, network_config, powerplatform_config)


def run_powerplatform_script(
    operation: str, 
    subscription_id: str, 
    network_config: Dict[str, str], 
    powerplatform_config: Dict[str, str]
) -> None:
    """Run the appropriate PowerPlatform script with dynamic parameters."""
    
    script_map = {
        "apply": "working_apply_powerplatform_injection.sh",
        "remove": "working_remove_powerplatform_injection.sh", 
        "verify": "working_verify_powerplatform_injection.sh"
    }
    
    script_name = script_map.get(operation)
    if not script_name:
        st.error(f"Unknown operation: {operation}")
        return
    
    script_path = f"/home/azureuser/agentic-rag-demo/powerplatform-network-inject/{script_name}"
    
    if not os.path.exists(script_path):
        st.error(f"Script not found: {script_path}")
        return
    
    # Create a temporary script with dynamic parameters
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_script:
        # Read the original script
        with open(script_path, 'r') as original:
            script_content = original.read()
        
        # Replace the hardcoded variables with dynamic values
        dynamic_content = script_content.replace(
            'RESOURCE_GROUP="private-rg"',
            f'RESOURCE_GROUP="{network_config["resource_group"]}"'
        ).replace(
            'VNET_PRIMARY="PowerPlatform-Primary-vNET"',
            f'VNET_PRIMARY="{network_config["primary_vnet"]}"'
        ).replace(
            'VNET_SECONDARY="PowerPlatform-Secondart-vNET"',
            f'VNET_SECONDARY="{network_config["secondary_vnet"]}"'
        ).replace(
            'SUBNET_NAME="default"',
            f'SUBNET_NAME="{network_config["subnet_name"]}"'
        ).replace(
            'ENV_ID="b98e9fde-ed33-e9cb-b7c7-b79e43946c48"',
            f'ENV_ID="{powerplatform_config["env_id"]}"'
        ).replace(
            'POLICY_RESOURCE_GROUP="powerplatform-enterprise-policies"',
            f'POLICY_RESOURCE_GROUP="{powerplatform_config["policy_resource_group"]}"'
        ).replace(
            'POLICY_NAME="PowerPlatformSubnetInjectionPolicy-Europe"',
            f'POLICY_NAME="{powerplatform_config["policy_name"]}"'
        )
        
        # Write the dynamic content to temp file
        temp_script.write(dynamic_content)
        temp_script_path = temp_script.name
    
    try:
        # Make the script executable
        os.chmod(temp_script_path, 0o755)
        
        # Run the script
        with st.spinner(f"Running {operation} script..."):
            st.session_state.pp_last_operation = f"{operation} - {datetime.now().strftime('%H:%M:%S')}"
            
            process = subprocess.Popen(
                ['bash', temp_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Create output container
            output_container = st.container()
            output_placeholder = output_container.empty()
            
            # Stream output in real-time
            output_lines = []
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    output_lines.append(line.rstrip())
                    # Update display every few lines to avoid too many updates
                    if len(output_lines) % 3 == 0:
                        output_placeholder.code('\n'.join(output_lines[-50:]), language='bash')
            
            # Wait for process to complete
            return_code = process.wait()
            
            # Final output display
            full_output = '\n'.join(output_lines)
            output_placeholder.code(full_output, language='bash')
            
            # Store output in session state
            st.session_state.pp_script_output = full_output
            
            # Show result
            if return_code == 0:
                st.success(f"✅ {operation.capitalize()} operation completed successfully!")
            else:
                st.error(f"❌ {operation.capitalize()} operation failed with return code {return_code}")
            
    except Exception as e:
        st.error(f"❌ Failed to run script: {str(e)}")
    
    finally:
        # Clean up temporary script
        try:
            os.unlink(temp_script_path)
        except:
            pass
    
    # Show recent operation info
    if st.session_state.pp_last_operation:
        st.info(f"🕒 Last operation: {st.session_state.pp_last_operation}")
