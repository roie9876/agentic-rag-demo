#!/usr/bin/env python3
"""
Standalone Delete Deployment Tool for Azure Resource Groups

This tool provides a direct interface to delete Azure resource groups
with advanced handling of AI Foundry agent deployments and complex dependencies.

Usage: streamlit run standalone_delete_deployment.py
"""
import streamlit as st
import subprocess
import json
import time
from typing import List, Dict, Any, Tuple, Optional

def check_azure_cli_login():
    """Check if Azure CLI is logged in and return account info."""
    try:
        result = subprocess.run(
            ["az", "account", "show"], 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        if result.returncode == 0:
            account_info = json.loads(result.stdout)
            return True, account_info
        else:
            return False, None
    except Exception:
        return False, None

def get_resource_groups() -> List[str]:
    """Get list of resource groups."""
    try:
        result = subprocess.run(
            ["az", "group", "list", "--query", "[].name", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return []
    except Exception:
        return []

def get_resources_in_rg(resource_group: str) -> List[Dict[str, Any]]:
    """Get resources in a resource group."""
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
            return []
    except Exception:
        return []

def delete_resource_group_smart(resource_group: str):
    """Smart delete with progress tracking."""
    
    progress_container = st.container()
    logs_container = st.container()
    
    def add_progress(level: str, message: str):
        with progress_container:
            if level == "success":
                st.success(f"✅ {message}")
            elif level == "warning":
                st.warning(f"⚠️ {message}")
            elif level == "error":
                st.error(f"❌ {message}")
            else:
                st.info(f"ℹ️ {message}")
    
    def add_log(message: str):
        with logs_container:
            with st.expander("📋 Detailed Logs", expanded=False):
                st.text(message)
    
    add_progress("info", f"🚀 Starting Smart Delete for resource group: {resource_group}")
    
    # Step 1: Delete AI Foundry resources
    add_progress("info", "🤖 Step 1: Deleting AI Foundry resources")
    
    try:
        # Delete AI Foundry projects and capability hosts
        result = subprocess.run([
            "az", "resource", "list",
            "--resource-group", resource_group,
            "--resource-type", "Microsoft.MachineLearningServices/workspaces",
            "--query", "[].name",
            "--output", "json"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            projects = json.loads(result.stdout)
            for project in projects:
                add_progress("info", f"  Deleting AI project: {project}")
                subprocess.run([
                    "az", "resource", "delete",
                    "--resource-group", resource_group,
                    "--name", project,
                    "--resource-type", "Microsoft.MachineLearningServices/workspaces",
                    "--yes"
                ], capture_output=True, text=True, timeout=120)
                
    except Exception as e:
        add_progress("warning", f"AI Foundry cleanup warning: {str(e)}")
    
    # Step 2: Remove service links and delegations
    add_progress("info", "🔧 Step 2: Removing service links and subnet delegations")
    
    try:
        # Get VNets
        result = subprocess.run([
            "az", "network", "vnet", "list",
            "--resource-group", resource_group,
            "--query", "[].name",
            "--output", "json"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            vnets = json.loads(result.stdout)
            for vnet in vnets:
                add_progress("info", f"  Processing VNet: {vnet}")
                
                # Force remove delegations and service links
                subnets_result = subprocess.run([
                    "az", "network", "vnet", "subnet", "list",
                    "--resource-group", resource_group,
                    "--vnet-name", vnet,
                    "--output", "json"
                ], capture_output=True, text=True, timeout=60)
                
                if subnets_result.returncode == 0:
                    subnets = json.loads(subnets_result.stdout)
                    for subnet in subnets:
                        subnet_name = subnet.get('name', '')
                        if subnet.get('delegations') or subnet.get('serviceAssociationLinks'):
                            add_progress("info", f"    Cleaning subnet: {subnet_name}")
                            
                            # Force clear delegations and service links
                            subprocess.run([
                                "az", "network", "vnet", "subnet", "update",
                                "--resource-group", resource_group,
                                "--vnet-name", vnet,
                                "--name", subnet_name,
                                "--set", "delegations=[]",
                                "--output", "none"
                            ], capture_output=True, text=True, timeout=60)
                            
                            subprocess.run([
                                "az", "network", "vnet", "subnet", "update",
                                "--resource-group", resource_group,
                                "--vnet-name", vnet,
                                "--name", subnet_name,
                                "--set", "serviceAssociationLinks=[]",
                                "--output", "none"
                            ], capture_output=True, text=True, timeout=60)
                            
    except Exception as e:
        add_progress("warning", f"Network cleanup warning: {str(e)}")
    
    # Step 3: Wait for cleanup
    add_progress("info", "⏳ Step 3: Waiting for resource cleanup")
    time.sleep(10)
    
    # Step 4: Final resource group deletion
    add_progress("info", "🗑️ Step 4: Deleting resource group")
    
    try:
        result = subprocess.run([
            "az", "group", "delete",
            "--name", resource_group,
            "--yes", "--no-wait"
        ], capture_output=True, text=True, timeout=60)
        
        add_log(f"Final deletion command: az group delete --name {resource_group} --yes --no-wait")
        add_log(f"Return code: {result.returncode}")
        add_log(f"Stdout: {result.stdout}")
        add_log(f"Stderr: {result.stderr}")
        
        if result.returncode == 0:
            add_progress("success", f"✅ Resource group deletion initiated: {resource_group}")
            add_progress("info", "ℹ️ Deletion is running in background - check Azure portal for final status")
            add_progress("info", "ℹ️ Note: Persistent service links (like legionservicelink) will be automatically removed during resource group deletion")
        else:
            add_progress("error", f"❌ Failed to delete resource group: {result.stderr}")
    
    except Exception as e:
        add_progress("error", f"❌ Error during deletion: {str(e)}")

def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Delete Deployment Tool",
        page_icon="🗑️",
        layout="wide"
    )
    
    st.title("🗑️ Azure Resource Group Deletion Tool")
    st.markdown("""
    **⚠️ DANGER ZONE**: This tool permanently deletes Azure resources and resource groups.
    
    This tool handles complex deletion scenarios including:
    - AI Foundry agent deployments with subnet delegations
    - Service association links (legionservicelink)
    - Private endpoints and DNS zones
    - Complete resource group cleanup
    """)
    
    # Check Azure CLI login
    logged_in, account_info = check_azure_cli_login()
    if not logged_in:
        st.error("❌ Please log in to Azure CLI first: `az login`")
        return
    
    st.success(f"✅ Logged in as: {account_info.get('user', {}).get('name', 'Unknown')}")
    
    # Resource Group Selection
    st.subheader("📂 Select Resource Group to Delete")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
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
            
            # Group resources by type
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
        
        # Deletion section
        st.subheader("🗑️ Deletion")
        
        st.warning("⚠️ **WARNING**: This action cannot be undone. All resources in this resource group will be permanently deleted.")
        
        # Confirmation checkboxes
        confirm1 = st.checkbox(f"✅ I understand that this will delete ALL resources in '{selected_rg}'")
        confirm2 = st.checkbox("✅ I have verified this is the correct resource group to delete")
        confirm3 = st.checkbox("✅ I understand this action cannot be undone")
        
        if confirm1 and confirm2 and confirm3:
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("🗑️ Delete Resource Group", type="primary"):
                    delete_resource_group_smart(selected_rg)
            
            with col2:
                if st.button("🔄 Preview Resources", type="secondary"):
                    st.info("Resource preview shown above ⬆️")

if __name__ == "__main__":
    main()
