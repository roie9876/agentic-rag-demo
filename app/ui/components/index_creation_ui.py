"""
Index Creation UI Components
============================
UI components for creating public and private vector indexes.
"""
import streamlit as st
from typing import Dict, Any, Optional
from services.index_service import index_service


def render_index_type_selector() -> tuple[str, bool]:
    """
    Render the index type selection radio buttons.
    
    Returns:
        tuple: (selected_option, is_private)
    """
    st.subheader("📋 Index Type Selection")
    
    # Index type options
    options = [
        "🌐 Create a New Public Vector Index", 
        "🔒 Create a New Private Vector Index"
    ]
    
    selected = st.radio(
        "Choose the type of vector index to create:",
        options,
        help="Public indexes use API key authentication, while private indexes use managed identity and private endpoints"
    )
    
    is_private = selected == options[1]
    return selected, is_private


def render_index_type_info(is_private: bool) -> None:
    """
    Render information about the selected index type.
    
    Args:
        is_private: Whether private index is selected
    """
    if is_private:
        st.info("🔒 **Private Vector Index**: Uses managed identity authentication and private endpoints")
        st.warning(
            "⚠️ **Requirements for Private Index:**\n"
            "- Managed identity must be enabled on your hosting service\n"
            "- RBAC roles must be assigned to the managed identity\n"
            "- Private endpoints must be configured for Azure services\n"
            "- API keys should be removed from environment variables\n"
            "- All Azure services must be in the same virtual network"
        )
        
        # Additional information about private indexes
        with st.expander("📖 Learn More About Private Indexes"):
            st.markdown("""
            **Private Vector Indexes** provide enhanced security by:
            
            1. **Network Isolation**: All traffic stays within your private network
            2. **Managed Identity Authentication**: No API keys stored in environment
            3. **RBAC Control**: Fine-grained access control through Azure RBAC
            4. **Compliance**: Better compliance with security policies
            
            **Architecture Changes:**
            - Vectorizer uses managed identity instead of API keys
            - Knowledge agents use managed identity authentication
            - Index schema remains the same as public indexes
            - Indexers run with `executionEnvironment: "private"`
            
            **Prerequisites:**
            - Azure Search service with private endpoint enabled
            - Azure OpenAI service with private endpoint enabled  
            - Managed identity with proper RBAC roles assigned
            - Virtual network configuration linking all services
            """)

        # Show informational prerequisites
        render_private_index_info()
    else:
        st.info("🌐 **Public Vector Index**: Uses managed identity authentication and standard endpoints")
        st.success(
            "✅ **Public Index Benefits:**\n"
            "- Easier to set up and configure\n"
            "- Uses standard Azure service endpoints\n"  
            "- Managed identity authentication (no API keys needed)\n"
            "- No network configuration required"
        )


def render_private_index_info() -> None:
    """
    Render informational content about private index requirements.
    This is informational only and doesn't block index creation.
    """
    st.subheader("ℹ️ Private Index Prerequisites Information")
    st.markdown("**Please ensure you have completed these prerequisites before creating a private index:**")
    
    checklist_items = [
        "Managed identity is enabled on your hosting service (App Service, Container Instance, etc.)",
        "RBAC role 'Cognitive Services User' assigned to managed identity for Azure OpenAI",
        "RBAC role 'Search Index Data Reader' assigned to managed identity for Azure Search", 
        "RBAC role 'Search Service Contributor' assigned to managed identity for Azure Search",
        "Private endpoints configured for Azure OpenAI service",
        "Private endpoints configured for Azure Search service", 
        "Virtual network properly configured to connect all services",
        "API keys removed from environment variables (AZURE_OPENAI_KEY_*, etc.)",
        "Application tested with managed identity authentication"
    ]
    
    # Display as informational list without checkboxes
    for i, item in enumerate(checklist_items, 1):
        st.markdown(f"{i}. {item}")
    
    st.info("💡 **Note:** These requirements are informational. The system will attempt to create the private index regardless, but it may fail if prerequisites are not met.")
    
    with st.expander("🔧 Troubleshooting Private Index Issues"):
        st.markdown("""
        **If private index creation fails, check:**
        
        1. **Managed Identity Status**: Verify managed identity is enabled on your hosting service
        2. **RBAC Roles**: Ensure all required roles are assigned and propagated (can take 5-10 minutes)
        3. **Private Endpoints**: Confirm private endpoints are configured and accessible
        4. **Network Connectivity**: Verify virtual network configuration connects all services
        5. **Environment Variables**: Ensure API keys are removed from environment
        6. **Azure CLI**: Test managed identity with `az account get-access-token --resource https://cognitiveservices.azure.com/`
        """)


def render_private_index_checklist() -> bool:
    """
    Legacy function - kept for compatibility but now returns True.
    Private index requirements are now shown as information only.
    """
    return True


def render_index_creation_form(
    is_private: bool, 
    root_index_client: Any,
    session_state: Dict[str, Any]
) -> None:
    """
    Render the index creation form and handle creation.
    
    Args:
        is_private: Whether to create a private index
        root_index_client: Azure Search index client
        session_state: Streamlit session state
    """
    # Index name input
    new_index_name = st.text_input(
        "New index name", 
        placeholder="e.g. agentic‑vectors‑private" if is_private else "e.g. agentic‑vectors",
        help="Choose a descriptive name for your vector index"
    )
    
    # Create button (no longer blocked by prerequisites for private indexes)
    index_type_str = "private" if is_private else "public"
    button_text = f"➕ Create {index_type_str} index"
    button_disabled = not new_index_name  # Only disabled if no name provided
    
    # Show reminder for private indexes
    if is_private and new_index_name:
        st.info("ℹ️ **Reminder**: Ensure all private index prerequisites above are met before creating the index. The system will attempt creation but may fail if requirements are not satisfied.")
    
    if st.button(button_text, disabled=button_disabled) and new_index_name:
        if root_index_client is None:
            st.error("❌ Search client not available. Check your configuration in the Health Check tab.")
            return
            
        # Show creation progress
        with st.spinner(f"Creating {index_type_str} index '{new_index_name}'..."):
            # Use the appropriate method based on index type
            if is_private:
                success = index_service.create_private_agentic_rag_index(root_index_client, new_index_name)
            else:
                success = index_service.create_agentic_rag_index(root_index_client, new_index_name)
            
            if success:
                st.success(f"✅ Successfully created {index_type_str} index '{new_index_name}'!")
                st.info(f"📝 Knowledge agent '{new_index_name}-agent' was also created")
                
                # Update session state
                session_state.selected_index = new_index_name
                if new_index_name not in session_state.available_indexes:
                    session_state.available_indexes.append(new_index_name)
                    
                # Show next steps
                st.subheader("🎯 Next Steps")
                if is_private:
                    st.markdown("""
                    **Your private index is ready!** Here's what you can do next:
                    
                    1. **🔍 Test the Index**: Go to the "Test Retrieval" tab to verify it works
                    2. **📄 Upload Documents**: Use the "Upload Documents" tab to add content
                    3. **🔗 SharePoint Integration**: Configure SharePoint connector if needed
                    4. **📊 Monitor Performance**: Check Azure portal for indexing metrics
                    """)
                else:
                    st.markdown("""
                    **Your public index is ready!** Here's what you can do next:
                    
                    1. **🔍 Test the Index**: Go to the "Test Retrieval" tab to verify it works  
                    2. **📄 Upload Documents**: Use the "Upload Documents" tab to add content
                    3. **🔗 SharePoint Integration**: Configure SharePoint connector if needed
                    """)
            else:
                st.error(f"❌ Failed to create {index_type_str} index '{new_index_name}'")
                st.error("Please check the application logs and ensure all prerequisites are met")
                
                if is_private:
                    st.info("""
                    **Troubleshooting Private Index Creation:**
                    
                    1. Verify managed identity has proper RBAC roles
                    2. Check private endpoint configuration  
                    3. Ensure virtual network connectivity
                    4. Confirm API keys are removed from environment
                    5. Test managed identity access to Azure services
                    """)


def render_index_creation_tab(
    root_index_client: Any,
    session_state: Dict[str, Any],
    health_block_func: callable
) -> None:
    """
    Render the complete index creation tab.
    
    Args:
        root_index_client: Azure Search index client
        session_state: Streamlit session state
        health_block_func: Function to render health check block
    """
    # Health check block
    health_block_func()
    
    # Main header
    st.header("🆕 Create a New Vector Index")
    
    # Index type selection
    selected_option, is_private = render_index_type_selector()
    
    # Show information about selected type
    render_index_type_info(is_private)
    
    # Index creation form
    render_index_creation_form(is_private, root_index_client, session_state)
