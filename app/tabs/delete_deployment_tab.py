"""
Delete Deployment Tab - Handle complex Azure resource deletion including VNets with delegations
"""
import streamlit as st
import subprocess
import json
import time
from typing import List, Dict, Any, Tuple, Optional
from utils.azure_helpers import get_az_logged_user, check_azure_cli_login


def render_delete_deployment_tab(
    session_state: Dict[str, Any],
    **kwargs
) -> None:
    """Render the Delete Deployment tab."""
    st.header("🗑️ Delete Deployment")
    st.markdown("""
    **⚠️ DANGER ZONE**: This will permanently delete Azure resources and resource groups.
    
    This tool handles complex deletion scenarios including:
    - VNets with delegated subnets (AI Foundry agents)
    - Service association links
    - Private endpoints and DNS zones
    - Complete resource group cleanup
    """)
    
    # Check Azure CLI login
    logged_in, account_info = check_azure_cli_login()
    if not logged_in:
        st.error("❌ Please log in to Azure CLI first: `az login`")
        return
    
    st.success(f"✅ Logged in as: {account_info.get('user', {}).get('name', 'Unknown')}")
    
    # Initialize session state
    if 'delete_progress' not in st.session_state:
        st.session_state.delete_progress = []
    if 'delete_logs' not in st.session_state:
        st.session_state.delete_logs = []
    
    # Resource Group Selection
    st.subheader("📂 Select Resource Group to Delete")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Get list of resource groups
        resource_groups = get_resource_groups()
        if not resource_groups:
            st.error("❌ No resource groups found or failed to fetch resource groups")
            return
        
        selected_rg = st.selectbox(
            "Choose Resource Group",
            options=resource_groups,
            help="Select the resource group containing your AI Foundry deployment"
        )
    
    with col2:
        if st.button("🔄 Refresh List", help="Refresh the resource group list"):
            st.rerun()
    
    if selected_rg:
        # Show resource group details
        st.subheader(f"📋 Resource Group: {selected_rg}")
        
        # Get resources in the resource group
        resources = get_resources_in_rg(selected_rg)
        if resources:
            st.write(f"**Found {len(resources)} resources:**")
            
            # Group resources by type for better display
            resource_types = {}
            for resource in resources:
                resource_type = resource.get('type', 'Unknown')
                if resource_type not in resource_types:
                    resource_types[resource_type] = []
                resource_types[resource_type].append(resource)
            
            # Display resources grouped by type
            for resource_type, type_resources in resource_types.items():
                with st.expander(f"{resource_type} ({len(type_resources)} resources)"):
                    for resource in type_resources:
                        st.write(f"• **{resource.get('name', 'Unknown')}** - {resource.get('location', 'Unknown')}")
        else:
            st.info("ℹ️ No resources found in this resource group")
        
        # Deletion options
        st.subheader("🗑️ Deletion Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            delete_mode = st.radio(
                "Deletion Strategy",
                options=[
                    "Smart Delete (Recommended)",
                    "Force Delete Resource Group",
                    "Preview Only (Dry Run)"
                ],
                help="""
                - **Smart Delete**: Handles delegations and dependencies automatically
                - **Force Delete**: Attempts to delete everything forcefully
                - **Preview Only**: Shows what would be deleted without actually deleting
                """
            )
        
        with col2:
            if delete_mode != "Preview Only (Dry Run)":
                confirm_delete = st.checkbox(
                    "⚠️ I understand this will permanently delete resources",
                    help="This action cannot be undone"
                )
                
                if confirm_delete:
                    confirm_text = st.text_input(
                        "Type the resource group name to confirm:",
                        placeholder=selected_rg
                    )
                    
                    delete_confirmed = confirm_text == selected_rg
                else:
                    delete_confirmed = False
            else:
                delete_confirmed = True
        
        # Deletion button
        st.subheader("🚀 Execute Deletion")
        
        if delete_mode == "Preview Only (Dry Run)":
            if st.button("👀 Preview Deletion Steps", type="primary"):
                preview_deletion(selected_rg)
        else:
            if delete_confirmed:
                if st.button(f"🗑️ {delete_mode}", type="primary"):
                    execute_deletion(selected_rg, delete_mode)
            else:
                st.button(f"🗑️ {delete_mode}", disabled=True, help="Please confirm deletion first")
        
        # Show deletion progress and logs
        if st.session_state.delete_progress:
            st.subheader("📊 Deletion Progress")
            for step in st.session_state.delete_progress:
                if step['status'] == 'success':
                    st.success(f"✅ {step['message']}")
                elif step['status'] == 'error':
                    st.error(f"❌ {step['message']}")
                elif step['status'] == 'warning':
                    st.warning(f"⚠️ {step['message']}")
                else:
                    st.info(f"ℹ️ {step['message']}")
        
        if st.session_state.delete_logs:
            with st.expander("📋 Detailed Logs", expanded=False):
                for log in st.session_state.delete_logs:
                    st.code(log, language="bash")


def get_resource_groups() -> List[str]:
    """Get list of resource groups in the current subscription."""
    try:
        result = subprocess.run(
            ["az", "group", "list", "--query", "[].name", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            st.error(f"Failed to get resource groups: {result.stderr}")
            return []
    except Exception as e:
        st.error(f"Error getting resource groups: {str(e)}")
        return []


def get_resources_in_rg(resource_group: str) -> List[Dict[str, Any]]:
    """Get all resources in a resource group."""
    try:
        result = subprocess.run(
            [
                "az", "resource", "list",
                "--resource-group", resource_group,
                "--output", "json"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            st.error(f"Failed to get resources: {result.stderr}")
            return []
    except Exception as e:
        st.error(f"Error getting resources: {str(e)}")
        return []


def preview_deletion(resource_group: str) -> None:
    """Preview what would be deleted without actually deleting."""
    st.session_state.delete_progress = []
    st.session_state.delete_logs = []
    
    add_progress("info", f"🔍 Analyzing resource group: {resource_group}")
    
    # Get all resources
    resources = get_resources_in_rg(resource_group)
    if not resources:
        add_progress("warning", "No resources found to delete")
        return
    
    # Analyze VNets and subnets
    vnets = [r for r in resources if r['type'] == 'Microsoft.Network/virtualNetworks']
    
    if vnets:
        add_progress("info", f"Found {len(vnets)} Virtual Network(s)")
        
        # Analyze service association links first
        analyze_service_association_links(resource_group)
        
        for vnet in vnets:
            vnet_name = vnet['name']
            add_progress("info", f"📋 Analyzing VNet: {vnet_name}")
            
            # Get subnet details
            subnets = get_vnet_subnets(resource_group, vnet_name)
            
            for subnet in subnets:
                subnet_name = subnet.get('name', 'Unknown')
                delegations = subnet.get('delegations', [])
                service_links = subnet.get('serviceAssociationLinks', [])
                
                if delegations or service_links:
                    add_progress("warning", f"⚠️ Subnet '{subnet_name}' has delegations/service links")
                    if delegations:
                        for delegation in delegations:
                            service_name = delegation.get('serviceName', 'Unknown')
                            add_progress("info", f"  - Delegation: {service_name}")
                    if service_links:
                        for link in service_links:
                            link_name = link.get('name', 'Unknown')
                            add_progress("info", f"  - Service Link: {link_name}")
    
    # Show deletion order
    add_progress("info", "🗂️ Proposed deletion order:")
    add_progress("info", "1. Delete AI Foundry capability hosts and projects (removes service association links)")
    add_progress("info", "2. Remove subnet delegations")
    add_progress("info", "3. Retry delegation removal after service links are cleared")
    add_progress("info", "4. Delete private endpoints")
    add_progress("info", "5. Delete remaining Azure resources")
    add_progress("info", "6. Delete VNets and subnets")
    add_progress("info", "7. Delete resource group")
    
    add_progress("success", "✅ Preview completed - no resources were deleted")


def execute_deletion(resource_group: str, delete_mode: str) -> None:
    """Execute the actual deletion process."""
    st.session_state.delete_progress = []
    st.session_state.delete_logs = []
    
    add_progress("info", f"🚀 Starting {delete_mode} for resource group: {resource_group}")
    
    if delete_mode == "Smart Delete (Recommended)":
        smart_delete_resource_group(resource_group)
    elif delete_mode == "Force Delete Resource Group":
        force_delete_resource_group(resource_group)


def smart_delete_resource_group(resource_group: str) -> None:
    """Smart deletion that handles delegations and dependencies."""
    
    # Step 1: Delete AI Foundry resources first (they create service association links)
    add_progress("info", "🤖 Step 1: Deleting AI Foundry resources")
    delete_ai_foundry_resources(resource_group)
    
    # Step 2: Remove subnet delegations and service association links
    add_progress("info", "🔧 Step 2: Removing subnet delegations and service links")
    
    vnets = get_vnets_in_rg(resource_group)
    for vnet_name in vnets:
        clean_vnet_delegations(resource_group, vnet_name)
    
    # Step 3: Retry delegation removal after AI Foundry cleanup
    add_progress("info", "🔄 Step 3: Retrying delegation removal")
    time.sleep(10)  # Wait for service links to be fully removed
    
    for vnet_name in vnets:
        retry_delegation_removal(resource_group, vnet_name)
    
    # Step 4: Delete private endpoints
    add_progress("info", "🔗 Step 4: Deleting private endpoints")
    delete_private_endpoints(resource_group)
    
    # Step 5: Wait for cleanup
    add_progress("info", "⏳ Step 5: Waiting for resource cleanup")
    time.sleep(30)  # Give Azure time to clean up dependencies
    
    # Step 6: Final resource group deletion
    add_progress("info", "🗑️ Step 6: Deleting resource group")
    add_progress("info", "ℹ️ Note: Any remaining persistent service links (like legionservicelink) will be automatically removed during resource group deletion")
    delete_resource_group_final(resource_group)


def force_delete_resource_group(resource_group: str) -> None:
    """Force delete the entire resource group."""
    add_progress("warning", "⚠️ Force deleting resource group - this may fail if dependencies exist")
    
    try:
        result = subprocess.run(
            [
                "az", "group", "delete",
                "--name", resource_group,
                "--yes", "--no-wait"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        add_log(f"az group delete --name {resource_group} --yes --no-wait")
        add_log(f"Return code: {result.returncode}")
        add_log(f"Stdout: {result.stdout}")
        add_log(f"Stderr: {result.stderr}")
        
        if result.returncode == 0:
            add_progress("success", f"✅ Resource group deletion initiated: {resource_group}")
            add_progress("info", "ℹ️ Deletion is running in background - check Azure portal for status")
        else:
            add_progress("error", f"❌ Failed to delete resource group: {result.stderr}")
    
    except Exception as e:
        add_progress("error", f"❌ Error during force delete: {str(e)}")


def get_vnets_in_rg(resource_group: str) -> List[str]:
    """Get list of VNet names in resource group."""
    try:
        result = subprocess.run(
            [
                "az", "network", "vnet", "list",
                "--resource-group", resource_group,
                "--query", "[].name",
                "--output", "json"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return []
    except Exception:
        return []


def get_vnet_subnets(resource_group: str, vnet_name: str) -> List[Dict[str, Any]]:
    """Get detailed subnet information for a VNet."""
    try:
        result = subprocess.run(
            [
                "az", "network", "vnet", "subnet", "list",
                "--resource-group", resource_group,
                "--vnet-name", vnet_name,
                "--output", "json"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return []
    except Exception:
        return []


def clean_vnet_delegations(resource_group: str, vnet_name: str) -> None:
    """Remove delegations and service association links from VNet subnets."""
    add_progress("info", f"🧹 Cleaning delegations for VNet: {vnet_name}")
    
    subnets = get_vnet_subnets(resource_group, vnet_name)
    
    for subnet in subnets:
        subnet_name = subnet.get('name', '')
        delegations = subnet.get('delegations', [])
        service_links = subnet.get('serviceAssociationLinks', [])
        
        # First, handle service association links
        if service_links:
            add_progress("info", f"  Removing service links from subnet: {subnet_name}")
            for service_link in service_links:
                remove_service_association_link(resource_group, vnet_name, subnet_name, service_link)
        
        # Wait a moment for service links to be fully removed
        if service_links:
            add_progress("info", f"  Waiting for service links to be fully removed...")
            time.sleep(5)
        
        # Then remove delegations (only if no service links remain)
        if delegations:
            add_progress("info", f"  Removing delegations from subnet: {subnet_name}")
            # Check if service links are actually gone before removing delegations
            updated_subnets = get_vnet_subnets(resource_group, vnet_name)
            updated_subnet = next((s for s in updated_subnets if s.get('name') == subnet_name), None)
            
            if updated_subnet and not updated_subnet.get('serviceAssociationLinks', []):
                for delegation in delegations:
                    remove_subnet_delegation(resource_group, vnet_name, subnet_name, delegation)
            else:
                add_progress("warning", f"  ⚠️ Service links still exist on {subnet_name}, will retry delegation removal later")


def remove_subnet_delegation(resource_group: str, vnet_name: str, subnet_name: str, delegation: Dict[str, Any]) -> None:
    """Remove a specific delegation from a subnet."""
    try:
        delegation_name = delegation.get('name', '')
        
        result = subprocess.run(
            [
                "az", "network", "vnet", "subnet", "update",
                "--resource-group", resource_group,
                "--vnet-name", vnet_name,
                "--name", subnet_name,
                "--remove", "delegations",
                "--output", "none"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        add_log(f"Removing delegation from {subnet_name}: {result.stderr}")
        
        if result.returncode == 0:
            add_progress("success", f"  ✅ Removed delegation from {subnet_name}")
        else:
            add_progress("warning", f"  ⚠️ Could not remove delegation from {subnet_name}: {result.stderr}")
    
    except Exception as e:
        add_progress("error", f"  ❌ Error removing delegation: {str(e)}")


def remove_service_association_link(resource_group: str, vnet_name: str, subnet_name: str, service_link: Dict[str, Any]) -> None:
    """Remove a service association link from a subnet with aggressive retry logic."""
    try:
        link_name = service_link.get('name', '')
        link_id = service_link.get('id', '')
        
        add_progress("info", f"    Attempting to remove service association link: {link_name}")
        
        # For legionservicelink specifically, use a more aggressive approach
        if link_name == 'legionservicelink':
            # Method 1: Try to delete the service association link directly
            if link_id:
                result = subprocess.run(
                    [
                        "az", "resource", "delete",
                        "--ids", link_id,
                        "--output", "none"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    add_progress("success", f"    ✅ Removed service association link: {link_name}")
                    return
                else:
                    add_progress("warning", f"    ⚠️ Direct deletion failed for {link_name}: {result.stderr}")
            
            # Method 2: Try using REST API approach for legionservicelink
            add_progress("info", f"    Trying REST API approach for {link_name}")
            
            # Get subscription ID from resource group
            rg_info_result = subprocess.run(
                ["az", "group", "show", "--name", resource_group, "--query", "id", "-o", "tsv"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if rg_info_result.returncode == 0:
                subscription_id = rg_info_result.stdout.strip().split('/')[2]
                
                # Use REST API to delete the service association link
                rest_result = subprocess.run(
                    [
                        "az", "rest",
                        "--method", "DELETE",
                        "--url", f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Network/virtualNetworks/{vnet_name}/subnets/{subnet_name}/serviceAssociationLinks/{link_name}?api-version=2023-05-01",
                        "--output", "none"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if rest_result.returncode == 0:
                    add_progress("success", f"    ✅ Removed {link_name} via REST API")
                    return
                else:
                    add_progress("warning", f"    ⚠️ REST API deletion failed for {link_name}: {rest_result.stderr}")
            
            # Method 3: Force subnet update to remove all service association links
            add_progress("info", f"    Force updating subnet to remove all service links")
            
            force_result = subprocess.run(
                [
                    "az", "network", "vnet", "subnet", "update",
                    "--resource-group", resource_group,
                    "--vnet-name", vnet_name,
                    "--name", subnet_name,
                    "--set", "serviceAssociationLinks=[]",
                    "--output", "none"
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if force_result.returncode == 0:
                add_progress("success", f"    ✅ Force removed all service links from {subnet_name}")
                return
            else:
                add_progress("warning", f"    ⚠️ Force subnet update failed: {force_result.stderr}")
            
            # Method 4: Try to disable the delegation first, then remove the link
            add_progress("info", f"    Trying to disable delegation first for {link_name}")
            
            # Remove delegations first
            disable_result = subprocess.run(
                [
                    "az", "network", "vnet", "subnet", "update",
                    "--resource-group", resource_group,
                    "--vnet-name", vnet_name,
                    "--name", subnet_name,
                    "--set", "delegations=[]",
                    "--output", "none"
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if disable_result.returncode == 0:
                add_progress("info", f"    ✅ Disabled delegations on {subnet_name}")
                time.sleep(2)  # Wait a moment
                
                # Now try to remove service links again
                cleanup_result = subprocess.run(
                    [
                        "az", "network", "vnet", "subnet", "update",
                        "--resource-group", resource_group,
                        "--vnet-name", vnet_name,
                        "--name", subnet_name,
                        "--set", "serviceAssociationLinks=[]",
                        "--output", "none"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if cleanup_result.returncode == 0:
                    add_progress("success", f"    ✅ Removed {link_name} after disabling delegations")
                    return
                else:
                    add_progress("warning", f"    ⚠️ Still could not remove {link_name} after disabling delegations")
            
            # If all methods fail for legionservicelink, that's expected - it will be removed with resource group deletion
            add_progress("warning", f"    ⚠️ {link_name} is persistent - will be removed with resource group deletion")
            
        else:
            # For other service links, use standard approach
            if link_id:
                result = subprocess.run(
                    [
                        "az", "resource", "delete",
                        "--ids", link_id,
                        "--output", "none"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    add_progress("success", f"    ✅ Removed service association link: {link_name}")
                else:
                    add_progress("warning", f"    ⚠️ Could not remove service association link {link_name}: {result.stderr}")
                    
                    # Alternative approach: try using network commands
                    alt_result = subprocess.run(
                        [
                            "az", "network", "vnet", "subnet", "update",
                            "--resource-group", resource_group,
                            "--vnet-name", vnet_name,
                            "--name", subnet_name,
                            "--remove", "serviceAssociationLinks",
                            "--output", "none"
                        ],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    if alt_result.returncode == 0:
                        add_progress("success", f"    ✅ Removed service association link via subnet update: {link_name}")
                    else:
                        add_progress("error", f"    ❌ Failed to remove service association link {link_name}: {alt_result.stderr}")
            else:
                add_progress("warning", f"    ⚠️ No ID found for service association link: {link_name}")
            
    except Exception as e:
        add_progress("error", f"    ❌ Exception removing service association link {link_name}: {str(e)}")


def delete_ai_foundry_resources(resource_group: str) -> None:
    """Delete AI Foundry specific resources that might hold references."""
    add_progress("info", "🤖 Deleting AI Foundry capability hosts and projects")
    
    # First delete capability hosts which might be holding service association links
    delete_capability_hosts(resource_group)
    
    # Wait for capability hosts to fully delete
    time.sleep(10)
    
    # Then delete AI projects
    delete_ai_projects(resource_group)
    
    # Finally delete AI accounts
    delete_ai_accounts(resource_group)


def delete_capability_hosts(resource_group: str) -> None:
    """Delete AI Foundry capability hosts which may create service association links."""
    try:
        add_progress("info", "  🔍 Finding and deleting capability hosts...")
        
        # Get all cognitive services accounts
        result = subprocess.run(
            [
                "az", "cognitiveservices", "account", "list",
                "--resource-group", resource_group,
                "--output", "json"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            accounts = json.loads(result.stdout)
            for account in accounts:
                account_name = account.get('name', '')
                add_progress("info", f"    Checking account: {account_name}")
                
                # List projects for this account
                try:
                    projects_result = subprocess.run(
                        [
                            "az", "rest",
                            "--method", "GET",
                            "--url", f"https://management.azure.com/subscriptions/{get_subscription_id()}/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices/accounts/{account_name}/projects?api-version=2025-04-01-preview"
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if projects_result.returncode == 0:
                        projects_data = json.loads(projects_result.stdout)
                        projects = projects_data.get('value', [])
                        
                        for project in projects:
                            project_name = project.get('name', '')
                            add_progress("info", f"      Found project: {project_name}")
                            
                            # Delete capability hosts for this project
                            delete_project_capability_hosts(resource_group, account_name, project_name)
                            
                except Exception as e:
                    add_progress("warning", f"    ⚠️ Could not list projects for {account_name}: {str(e)}")
    
    except Exception as e:
        add_progress("warning", f"  ⚠️ Error finding AI accounts: {str(e)}")


def delete_project_capability_hosts(resource_group: str, account_name: str, project_name: str) -> None:
    """Delete capability hosts for a specific project."""
    try:
        add_progress("info", f"        Deleting capability hosts for project: {project_name}")
        
        # List capability hosts
        result = subprocess.run(
            [
                "az", "rest",
                "--method", "GET", 
                "--url", f"https://management.azure.com/subscriptions/{get_subscription_id()}/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices/accounts/{account_name}/projects/{project_name}/capabilityHosts?api-version=2025-04-01-preview"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            hosts_data = json.loads(result.stdout)
            hosts = hosts_data.get('value', [])
            
            for host in hosts:
                host_name = host.get('name', '')
                add_progress("info", f"          Deleting capability host: {host_name}")
                
                # Delete the capability host
                delete_result = subprocess.run(
                    [
                        "az", "rest",
                        "--method", "DELETE",
                        "--url", f"https://management.azure.com/subscriptions/{get_subscription_id()}/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices/accounts/{account_name}/projects/{project_name}/capabilityHosts/{host_name}?api-version=2025-04-01-preview"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if delete_result.returncode == 0:
                    add_progress("success", f"          ✅ Deleted capability host: {host_name}")
                else:
                    add_progress("warning", f"          ⚠️ Could not delete capability host {host_name}: {delete_result.stderr}")
        
    except Exception as e:
        add_progress("warning", f"        ⚠️ Error deleting capability hosts for {project_name}: {str(e)}")


def get_subscription_id() -> str:
    """Get the current subscription ID."""
    try:
        result = subprocess.run(
            ["az", "account", "show", "--query", "id", "--output", "tsv"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def delete_ai_projects(resource_group: str) -> None:
    """Delete AI Foundry projects."""
    add_progress("info", "🤖 Deleting AI Foundry projects")
    # Projects are typically sub-resources of AI accounts and deleted with the parent


def delete_ai_accounts(resource_group: str) -> None:
    """Delete AI Services accounts."""
    try:
        result = subprocess.run(
            [
                "az", "cognitiveservices", "account", "list",
                "--resource-group", resource_group,
                "--output", "json"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            accounts = json.loads(result.stdout)
            for account in accounts:
                account_name = account.get('name', '')
                add_progress("info", f"  Deleting AI account: {account_name}")
                
                delete_result = subprocess.run(
                    [
                        "az", "cognitiveservices", "account", "delete",
                        "--name", account_name,
                        "--resource-group", resource_group,
                        "--yes"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if delete_result.returncode == 0:
                    add_progress("success", f"  ✅ Deleted AI account: {account_name}")
                else:
                    add_progress("warning", f"  ⚠️ Could not delete AI account {account_name}: {delete_result.stderr}")
    
    except Exception as e:
        add_progress("error", f"❌ Error deleting AI accounts: {str(e)}")


def delete_private_endpoints(resource_group: str) -> None:
    """Delete private endpoints."""
    try:
        result = subprocess.run(
            [
                "az", "network", "private-endpoint", "list",
                "--resource-group", resource_group,
                "--output", "json"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            endpoints = json.loads(result.stdout)
            for endpoint in endpoints:
                endpoint_name = endpoint.get('name', '')
                add_progress("info", f"  Deleting private endpoint: {endpoint_name}")
                
                delete_result = subprocess.run(
                    [
                        "az", "network", "private-endpoint", "delete",
                        "--name", endpoint_name,
                        "--resource-group", resource_group,
                        "--yes"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if delete_result.returncode == 0:
                    add_progress("success", f"  ✅ Deleted private endpoint: {endpoint_name}")
                else:
                    add_progress("warning", f"  ⚠️ Could not delete private endpoint {endpoint_name}: {delete_result.stderr}")
    
    except Exception as e:
        add_progress("error", f"❌ Error deleting private endpoints: {str(e)}")


def delete_resource_group_final(resource_group: str) -> None:
    """Final resource group deletion."""
    try:
        result = subprocess.run(
            [
                "az", "group", "delete",
                "--name", resource_group,
                "--yes", "--no-wait"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        add_log(f"Final deletion command: az group delete --name {resource_group} --yes --no-wait")
        add_log(f"Return code: {result.returncode}")
        add_log(f"Stdout: {result.stdout}")
        add_log(f"Stderr: {result.stderr}")
        
        if result.returncode == 0:
            add_progress("success", f"✅ Resource group deletion initiated: {resource_group}")
            add_progress("info", "ℹ️ Deletion is running in background - check Azure portal for final status")
        else:
            add_progress("error", f"❌ Failed to delete resource group: {result.stderr}")
    
    except Exception as e:
        add_progress("error", f"❌ Error during final deletion: {str(e)}")


def add_progress(status: str, message: str) -> None:
    """Add a progress message to the session state."""
    st.session_state.delete_progress.append({
        'status': status,
        'message': message,
        'timestamp': time.time()
    })


def add_log(message: str) -> None:
    """Add a log message to the session state."""
    st.session_state.delete_logs.append(message)


def retry_delegation_removal(resource_group: str, vnet_name: str) -> None:
    """Retry removing delegations with aggressive approach for persistent service links."""
    add_progress("info", f"🔄 Retrying delegation removal for VNet: {vnet_name}")
    
    subnets = get_vnet_subnets(resource_group, vnet_name)
    
    for subnet in subnets:
        subnet_name = subnet.get('name', '')
        delegations = subnet.get('delegations', [])
        service_links = subnet.get('serviceAssociationLinks', [])
        
        if delegations:
            if not service_links:
                add_progress("info", f"  ✅ No service links, removing delegations for subnet: {subnet_name}")
                for delegation in delegations:
                    remove_subnet_delegation(resource_group, vnet_name, subnet_name, delegation)
            else:
                # Check if we only have legionservicelink (which is often persistent)
                persistent_links = [link for link in service_links if link.get('name') == 'legionservicelink']
                non_persistent_links = [link for link in service_links if link.get('name') != 'legionservicelink']
                
                if len(service_links) == len(persistent_links):
                    # Only legionservicelink remains - try aggressive delegation removal
                    add_progress("warning", f"  ⚠️ Only persistent service links remain on {subnet_name}, forcing delegation removal")
                    
                    # Try to force remove delegations even with legionservicelink present
                    for delegation in delegations:
                        force_remove_subnet_delegation(resource_group, vnet_name, subnet_name, delegation)
                else:
                    add_progress("warning", f"  ⚠️ Subnet {subnet_name} still has non-persistent service links:")
                    for link in non_persistent_links:
                        link_name = link.get('name', 'Unknown')
                        add_progress("warning", f"    Non-persistent service link: {link_name}")
                        # Try to remove non-persistent links again
                        remove_service_association_link(resource_group, vnet_name, subnet_name, link)


def force_remove_subnet_delegation(resource_group: str, vnet_name: str, subnet_name: str, delegation: Dict[str, Any]) -> None:
    """Force remove a delegation even if service links exist (for persistent links like legionservicelink)."""
    try:
        delegation_name = delegation.get('name', '')
        service_name = delegation.get('serviceName', '')
        
        add_progress("info", f"    🔧 Force removing delegation: {delegation_name} ({service_name})")
        
        # Method 1: Try to remove delegation by setting empty array
        result = subprocess.run(
            [
                "az", "network", "vnet", "subnet", "update",
                "--resource-group", resource_group,
                "--vnet-name", vnet_name,
                "--name", subnet_name,
                "--set", "delegations=[]",
                "--output", "none"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        add_log(f"Force removing delegations from {subnet_name}: {result.stderr}")
        
        if result.returncode == 0:
            add_progress("success", f"    ✅ Force removed all delegations from {subnet_name}")
            return
        else:
            add_progress("warning", f"    ⚠️ Method 1 failed for {subnet_name}: {result.stderr}")
        
        # Method 2: Try using --remove with specific delegation
        result2 = subprocess.run(
            [
                "az", "network", "vnet", "subnet", "update",
                "--resource-group", resource_group,
                "--vnet-name", vnet_name,
                "--name", subnet_name,
                "--remove", "delegations",
                "--output", "none"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result2.returncode == 0:
            add_progress("success", f"    ✅ Removed delegations using --remove from {subnet_name}")
            return
        else:
            add_progress("warning", f"    ⚠️ Method 2 failed for {subnet_name}: {result2.stderr}")
        
        # Method 3: Try REST API approach for stubborn delegations
        add_progress("info", f"    🌐 Trying REST API approach for delegation removal")
        
        # Get subscription ID from resource group
        rg_info_result = subprocess.run(
            ["az", "group", "show", "--name", resource_group, "--query", "id", "-o", "tsv"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if rg_info_result.returncode == 0:
            subscription_id = rg_info_result.stdout.strip().split('/')[2]
            
            # Get current subnet configuration
            subnet_show_result = subprocess.run(
                [
                    "az", "network", "vnet", "subnet", "show",
                    "--resource-group", resource_group,
                    "--vnet-name", vnet_name,
                    "--name", subnet_name,
                    "--output", "json"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if subnet_show_result.returncode == 0:
                try:
                    subnet_config = json.loads(subnet_show_result.stdout)
                    # Remove delegations from the config
                    subnet_config.pop('delegations', None)
                    subnet_config.pop('serviceAssociationLinks', None)  # Also try to clear service links
                    
                    # Create a minimal update payload
                    update_payload = {
                        "properties": {
                            "addressPrefix": subnet_config.get("addressPrefix", ""),
                            "delegations": [],
                            "serviceAssociationLinks": []
                        }
                    }
                    
                    # Write payload to temp file
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        json.dump(update_payload, f)
                        temp_file = f.name
                    
                    # Use REST API to update subnet
                    rest_result = subprocess.run(
                        [
                            "az", "rest",
                            "--method", "PUT",
                            "--url", f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Network/virtualNetworks/{vnet_name}/subnets/{subnet_name}?api-version=2023-05-01",
                            "--body", f"@{temp_file}",
                            "--output", "none"
                        ],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    # Clean up temp file
                    import os
                    os.unlink(temp_file)
                    
                    if rest_result.returncode == 0:
                        add_progress("success", f"    ✅ Force removed delegation using REST API from {subnet_name}")
                        return
                    else:
                        add_progress("warning", f"    ⚠️ REST API method failed: {rest_result.stderr}")
                
                except json.JSONDecodeError as e:
                    add_progress("warning", f"    ⚠️ Failed to parse subnet config: {str(e)}")
        
        # If we get here, all methods failed - but that's OK for legionservicelink
        add_progress("warning", f"    ⚠️ Could not force remove delegation from {subnet_name} - will be cleaned up with resource group deletion")
    
    except Exception as e:
        add_progress("warning", f"    ⚠️ Exception during force delegation removal: {str(e)}")


def analyze_service_association_links(resource_group: str) -> None:
    """Analyze what resources are creating service association links."""
    add_progress("info", "🔍 Analyzing service association links...")
    
    vnets = get_vnets_in_rg(resource_group)
    for vnet_name in vnets:
        subnets = get_vnet_subnets(resource_group, vnet_name)
        
        for subnet in subnets:
            subnet_name = subnet.get('name', '')
            service_links = subnet.get('serviceAssociationLinks', [])
            
            if service_links:
                add_progress("warning", f"⚠️ Subnet '{subnet_name}' has service association links:")
                for link in service_links:
                    link_name = link.get('name', 'Unknown')
                    link_type = link.get('type', 'Unknown')
                    linked_resource = link.get('linkedResourceType', 'Unknown')
                    
                    add_progress("info", f"  - Link: {link_name}")
                    add_progress("info", f"    Type: {link_type}")
                    add_progress("info", f"    Linked Resource: {linked_resource}")
                    
                    # Provide specific guidance based on link type
                    if 'legionservicelink' in link_name.lower():
                        add_progress("info", f"    💡 This appears to be an AI Foundry Agent service link")
                        add_progress("info", f"    💡 Will be removed by deleting AI Foundry capability hosts first")
