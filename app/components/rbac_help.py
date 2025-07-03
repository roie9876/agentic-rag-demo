"""
RBAC Help Component for AI Foundry Tab
--------------------------------------
Provides comprehensive guidance on RBAC permissions for AI Foundry resources.
"""

import streamlit as st
from typing import Dict, List, Any


def render_rbac_help_section(resource_type: str = "hub") -> None:
    """Render a comprehensive RBAC help section."""
    
    st.markdown("### 📚 RBAC Permissions Guide")
    
    # Create tabs for different help sections
    help_tab1, help_tab2, help_tab3, help_tab4 = st.tabs([
        "📋 Required Roles",
        "🔧 Common Issues", 
        "🛠️ Troubleshooting",
        "🔗 Resources"
    ])
    
    with help_tab1:
        st.markdown("#### Required Azure RBAC Roles")
        
        if resource_type == "hub":
            st.markdown("""
            **For AI Foundry Hub Resources:**
            
            ✅ **Azure AI Developer** (Recommended)
            - Full access to AI Foundry projects and agents
            - Can create, manage, and deploy AI solutions
            - Required for most operations
            
            ✅ **AzureML Data Scientist**
            - Access to ML workspace features
            - Required for data science operations
            - Needed for model training and deployment
            
            ⚠️ **Machine Learning Workspace Contributor** (Optional)
            - Full workspace management capabilities
            - Only needed for advanced admin operations
            """)
        else:
            st.markdown("""
            **For AI Foundry Account Resources:**
            
            ✅ **Azure AI User**
            - Basic access to AI Foundry account operations
            - Required for project access
            
            ✅ **Cognitive Services User**
            - Access to AI services and APIs
            - Required for AI model interactions
            
            ⚠️ **Contributor** (Optional)
            - Full resource management capabilities
            - Only needed for resource creation/deletion
            """)
    
    with help_tab2:
        st.markdown("#### Common Issues and Solutions")
        
        st.markdown("""
        **🚫 "403 Forbidden" Error**
        - **Cause**: Missing basic read permissions
        - **Solution**: Assign "Azure AI Developer" or "Cognitive Services User" role
        
        **🔍 "404 Not Found" for Existing Resources**
        - **Cause**: Cannot see the hub or project due to permissions
        - **Solution**: Check if you have access to the resource group
        
        **⚠️ "Authentication Failed" Error**
        - **Cause**: Token scope issues or expired authentication
        - **Solution**: Run `az login` and try again
        
        **🔄 "Role Assignment Already Exists" Warning**
        - **Cause**: Role is already assigned but not yet propagated
        - **Solution**: Wait 5-10 minutes for Azure to propagate changes
        
        **🚨 "Insufficient Privileges" Error**
        - **Cause**: You don't have permission to assign roles
        - **Solution**: Ask an administrator to assign roles for you
        """)
    
    with help_tab3:
        st.markdown("#### Troubleshooting Steps")
        
        st.markdown("""
        **Step 1: Verify Azure CLI Setup**
        ```bash
        # Check if Azure CLI is installed
        az --version
        
        # Check if you're logged in
        az account show
        
        # Login if needed
        az login
        ```
        
        **Step 2: Check Current Permissions**
        ```bash
        # List your role assignments
        az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv)
        
        # Check specific resource permissions
        az role assignment list --scope "<resource-id>"
        ```
        
        **Step 3: Test Resource Access**
        ```bash
        # Test if you can see the resource
        az resource show --id "<resource-id>"
        
        # Test if you can list sub-resources
        az resource list --resource-group "<resource-group>"
        ```
        
        **Step 4: Verify Role Assignment Propagation**
        - Wait 5-10 minutes after role assignment
        - Clear browser cache and refresh
        - Try from a different browser or incognito mode
        """)
    
    with help_tab4:
        st.markdown("#### Helpful Resources")
        
        st.markdown("""
        **📖 Official Documentation**
        - [Azure AI Studio RBAC](https://docs.microsoft.com/en-us/azure/ai-studio/concepts/rbac-ai-studio)
        - [Azure Built-in Roles](https://docs.microsoft.com/en-us/azure/role-based-access-control/built-in-roles)
        - [Azure CLI Role Assignment](https://docs.microsoft.com/en-us/cli/azure/role/assignment)
        
        **🛠️ Azure CLI Commands**
        ```bash
        # List all available roles
        az role definition list --query "[?contains(roleName, 'AI') || contains(roleName, 'Cognitive')]"
        
        # Get role definition details
        az role definition show --name "Azure AI Developer"
        
        # Create custom role (if needed)
        az role definition create --role-definition role-definition.json
        ```
        
        **🆘 Getting Help**
        - Azure Support Portal
        - Stack Overflow (azure-ai-services tag)
        - Microsoft Q&A Platform
        - Azure Community Forums
        """)


def render_permission_summary(permissions: List[Dict[str, Any]]) -> None:
    """Render a summary of permission status."""
    
    if not permissions:
        st.warning("No permission data available")
        return
    
    # Count permissions by status
    granted = sum(1 for p in permissions if p.get('status') == 'granted')
    missing = sum(1 for p in permissions if p.get('status') == 'missing')
    required_missing = sum(1 for p in permissions if p.get('status') == 'missing' and p.get('required', False))
    
    # Create metrics display
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("✅ Granted", granted)
    
    with col2:
        st.metric("❌ Missing", missing)
    
    with col3:
        st.metric("🔴 Required Missing", required_missing, delta=f"-{required_missing}" if required_missing > 0 else None)
    
    with col4:
        total = len(permissions)
        completion_rate = (granted / total * 100) if total > 0 else 0
        st.metric("📊 Completion", f"{completion_rate:.1f}%")
    
    # Show status indicator
    if required_missing == 0:
        st.success("🎉 All required permissions are granted!")
    elif required_missing <= 2:
        st.warning(f"⚠️ {required_missing} required permission(s) missing")
    else:
        st.error(f"❌ {required_missing} required permissions missing")


def render_rbac_status_card(
    resource_name: str, 
    resource_type: str, 
    permissions: List[Dict[str, Any]], 
    last_checked: str = None
) -> None:
    """Render a status card for RBAC permissions."""
    
    st.markdown(f"""
    <div style="
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
        background-color: #f9f9f9;
    ">
        <h4 style="margin: 0 0 8px 0;">🔐 RBAC Status</h4>
        <p style="margin: 0;"><strong>Resource:</strong> {resource_name}</p>
        <p style="margin: 0;"><strong>Type:</strong> {resource_type}</p>
        {f'<p style="margin: 0;"><strong>Last Checked:</strong> {last_checked}</p>' if last_checked else ''}
    </div>
    """, unsafe_allow_html=True)
    
    # Show permission summary
    render_permission_summary(permissions)
