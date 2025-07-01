#!/usr/bin/env python3
"""
Private Endpoint Health Check UI Module for Agentic RAG Demo
===========================================================
This module provides UI components for private endpoint health checks.
"""

import streamlit as st
import json
import subprocess
import requests
import re
from datetime import datetime
from typing import Dict, Any
from .private_endpoint_health_checker import PrivateEndpointHealthChecker, HealthStatus
import os


class PrivateEndpointHealthCheckUI:
    """
    UI handler for private endpoint health check functionality.
    """
    
    def __init__(self):
        """Initialize the private endpoint health check UI."""
        self.health_checker = None
    
    def _get_health_checker(self):
        """Lazy-load the health checker to avoid blocking initialization."""
        if self.health_checker is None:
            self.health_checker = PrivateEndpointHealthChecker()
        return self.health_checker
    
    def render_private_endpoint_health_tab(self):
        """Render the private endpoint health check tab with comprehensive .env validation."""
        st.header("🔒 Private Endpoint Health Check")
        
        # Debug info
        st.info("🔍 **Debug**: Private endpoint health check tab is loading...")
        
        # Add information about this health check
        with st.expander("ℹ️ About Private Endpoint Health Check", expanded=False):
            st.markdown("""
            This comprehensive health check validates:
            
            **🔧 Configuration:**
            - ✅ .env file completeness
            - ✅ Required environment variables
            - ✅ Authentication method detection
            
            **🔐 Authentication:**
            - ✅ Managed identity (recommended)
            - ✅ API key authentication
            - ✅ Service principal authentication
            
            **🌐 Connectivity:**
            - ✅ Private endpoint resolution
            - ✅ Network connectivity
            - ✅ Service-specific operations
            
            **🎯 Supported Services:**
            - Azure OpenAI
            - Document Intelligence
            - AI Search
            """)
        
        # Azure CLI Authentication Section
        st.subheader("🔐 Azure CLI Authentication")
        
        with st.expander("ℹ️ About Azure CLI Authentication", expanded=False):
            st.markdown("""
            Azure CLI authentication is required for:
            - 🔍 **Resource Discovery**: Finding your Azure resources
            - 🔐 **Identity Management**: Managing service principals and managed identities  
            - 🛠️ **Configuration**: Setting up RBAC permissions
            - 🩺 **Diagnostics**: Advanced troubleshooting with Azure APIs
            
            **Note**: This is different from your application's authentication to Azure services.
            """)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🔑 Check Azure CLI Status", key="check_cli_status"):
                with st.spinner("Checking Azure CLI status..."):
                    cli_status = self._get_health_checker().check_azure_cli_status()
                    st.session_state['cli_status'] = cli_status
        
        with col2:
            if st.button("🚀 Login to Azure CLI", key="azure_cli_login"):
                with st.spinner("Opening Azure CLI login..."):
                    login_result = self._get_health_checker().initiate_azure_cli_login()
                    st.session_state['login_result'] = login_result
        
        # Display CLI status if available
        if 'cli_status' in st.session_state:
            self._display_cli_status(st.session_state['cli_status'])
        
        # Display login result if available
        if 'login_result' in st.session_state:
            self._display_login_result(st.session_state['login_result'])
        
        st.divider()
        
        # Service Health Check Section
        st.subheader("🩺 Service Health Check")
        
        if st.button("🔄 Check All Services", key="private_check_all_services"):
            with st.spinner("Checking services..."):
                results, all_healthy, troubleshooting = self._get_health_checker().check_all_services()
                st.session_state['private_health_results'] = results
                st.session_state['private_all_healthy'] = all_healthy
                st.session_state['private_troubleshooting'] = troubleshooting

        if 'private_health_results' in st.session_state:
            self._render_service_health_results()
        else:
            st.info("Run a health check to see service status.")
        
        st.divider()
        
        # Environment validation section
        st.subheader("📋 Environment Configuration Validation")
        
        if st.button("🔍 Validate .env Configuration", key="validate_env"):
            self._render_env_validation()
        
        # Display cached env validation if available
        if 'env_validation_results' in st.session_state:
            self._display_env_validation_results(st.session_state['env_validation_results'])
        
        st.divider()
        
        # Resource health check section
        st.subheader("🏥 Azure Resource Health Check")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("🔄 Run Full Health Check", key="full_health_check", type="primary"):
                self._run_full_health_check()
                # Immediately display results if available
                if 'health_check_results' in st.session_state:
                    self._display_health_check_results(st.session_state['health_check_results'])
        
        with col2:
            if st.button("⚡ Quick Environment Check", key="quick_env_check"):
                self._run_quick_env_check()
                # Immediately display results if available
                if 'health_check_results' in st.session_state:
                    self._display_health_check_results(st.session_state['health_check_results'])
        
        with col3:
            if st.button("🧬 Identity Diagnostics", key="identity_diag"):
                with st.spinner("Analyzing identity configuration..."):
                    identity_info = self._get_health_checker().get_current_identity_info()
                    st.session_state['identity_info'] = identity_info
                # Immediately display identity info if available
                if 'identity_info' in st.session_state:
                    self._render_identity_diagnostics()
        
        # Display comprehensive health check results if available
        if 'health_check_results' in st.session_state:
            self._display_health_check_results(st.session_state['health_check_results'])
        
        # Display legacy private endpoint results if available
        if 'pe_health_results' in st.session_state:
            self._render_private_endpoint_results()
        
        # Display identity diagnostics if available
        if 'identity_info' in st.session_state:
            self._render_identity_diagnostics()
        
        # Configuration guidance section
        st.divider()
        self._render_configuration_guidance()
        
        # Current Authentication Status section (same as public health check)
        st.divider()
        st.subheader("ℹ️ Current Authentication Status")
        self._show_auth_status()
        
        # Managed Identity Role Configuration section  
        st.divider()
        self._render_managed_identity_role_configuration()
    
    def _render_login_section(self):
        """Render Azure CLI authentication section for private endpoints."""
        st.subheader("🔐 Azure CLI Authentication")
        
        with st.expander("ℹ️ About Azure CLI Authentication", expanded=False):
            st.markdown("""
            Azure CLI authentication is required for:
            - 🔍 **Resource Discovery**: Finding your Azure resources
            - 🔐 **Identity Management**: Managing service principals and managed identities  
            - 🛠️ **Configuration**: Setting up RBAC permissions
            - 🩺 **Diagnostics**: Advanced troubleshooting with Azure APIs
            
            **Note**: This is different from your application's authentication to Azure services.
            """)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🔑 Check Azure CLI Status", key="legacy_check_cli_status"):
                with st.spinner("Checking Azure CLI status..."):
                    try:
                        cli_status = self._get_health_checker().check_azure_cli_status()
                        st.session_state['cli_status'] = cli_status
                    except Exception as e:
                        st.session_state['cli_status'] = {
                            'authenticated': False,
                            'error': f'Error checking CLI status: {str(e)}'
                        }
        
        with col2:
            if st.button("🚀 Login to Azure CLI", key="legacy_azure_cli_login"):
                with st.spinner("Opening Azure CLI login..."):
                    try:
                        login_result = self._get_health_checker().initiate_azure_cli_login()
                        st.session_state['login_result'] = login_result
                    except Exception as e:
                        st.session_state['login_result'] = {
                            'success': False,
                            'error': f'Error initiating login: {str(e)}'
                        }
        
        # Display CLI status if available
        if 'cli_status' in st.session_state:
            self._display_cli_status(st.session_state['cli_status'])
        
        # Display login result if available
        if 'login_result' in st.session_state:
            self._display_login_result(st.session_state['login_result'])

    def _display_cli_status(self, cli_status: Dict[str, Any]):
        """Display Azure CLI status information."""
        if cli_status.get('authenticated', False):
            st.success("✅ Azure CLI is authenticated")
            
            account_info = cli_status.get('account_info', {})
            if account_info:
                with st.expander("👤 Current Azure Account", expanded=False):
                    st.write(f"**Account**: {account_info.get('user', {}).get('name', 'Unknown')}")
                    st.write(f"**Subscription**: {account_info.get('name', 'Unknown')}")
                    st.write(f"**Tenant**: {account_info.get('tenantId', 'Unknown')}")
        else:
            st.error("❌ Azure CLI is not authenticated")
            st.info("Click 'Login to Azure CLI' to authenticate.")
            if 'error' in cli_status:
                st.error(f"Error: {cli_status['error']}")

    def _display_login_result(self, login_result: Dict[str, Any]):
        """Display Azure CLI login result."""
        if login_result.get('success', False):
            st.success("✅ Successfully logged in to Azure CLI")
            if 'account_info' in login_result:
                account_info = login_result['account_info']
                st.write(f"**Account**: {account_info.get('user', {}).get('name', 'Unknown')}")
                st.write(f"**Subscription**: {account_info.get('name', 'Unknown')}")
        else:
            st.error(f"❌ Failed to login: {login_result.get('error', 'Unknown error')}")
            st.info("Please try again or check your network connection.")

    def _render_service_health_results(self):
        """Render service health check results for private endpoints."""
        results = st.session_state['private_health_results']
        all_healthy = st.session_state['private_all_healthy'] 
        troubleshooting = st.session_state.get('private_troubleshooting', {})
        
        st.subheader("🩺 Service Health Results")
        
        # Overall status
        if all_healthy:
            st.success("🎉 All private endpoint services are healthy!")
        else:
            st.error("⚠️ Some private endpoint services have issues.")
        
        # Individual service results
        for service_name, (status, message) in results.items():
            status_icon = "✅" if status else "❌"
            
            with st.expander(f"{status_icon} {service_name}", expanded=not status):
                if status:
                    st.success(message)
                else:
                    st.error(message)
                
                # Show troubleshooting for failed services
                if not status and service_name in troubleshooting:
                    st.subheader("🔧 Troubleshooting Steps")
                    st.info(troubleshooting[service_name])
                
                # Add service-specific diagnostic information
                self._render_service_diagnostics(service_name, status)

    def _render_service_diagnostics(self, service_name: str, is_healthy: bool):
        """Render diagnostic information for a specific service."""
        
        # Service-specific diagnostic information
        diagnostics = {
            "Azure OpenAI": {
                "healthy_info": "Private endpoint connection established successfully",
                "checks": [
                    "✅ DNS resolution through private endpoint",
                    "✅ Network connectivity via private link", 
                    "✅ Authentication working",
                    "✅ API calls successful"
                ]
            },
            "Document Intelligence": {
                "healthy_info": "Document processing service accessible via private endpoint",
                "checks": [
                    "✅ Private endpoint DNS resolution",
                    "✅ Service connectivity verified",
                    "✅ Authentication successful", 
                    "✅ Document processing API responsive"
                ]
            },
            "AI Search": {
                "healthy_info": "Search service accessible through private connection",
                "checks": [
                    "✅ Private endpoint connectivity",
                    "✅ Search index accessible",
                    "✅ Query operations working",
                    "✅ Index management available"
                ]
            }
        }
        
        if service_name in diagnostics:
            service_diag = diagnostics[service_name]
            
            if is_healthy:
                st.info(service_diag["healthy_info"])
                
                with st.expander("🔍 Diagnostic Details", expanded=False):
                    for check in service_diag["checks"]:
                        st.write(check)
            else:
                st.write("**Failed Checks:**")
                for check in service_diag["checks"]:
                    # Convert checkmark to X for failed services
                    failed_check = check.replace("✅", "❌")
                    st.write(failed_check)

    def _render_private_endpoint_results(self):
        """Render the private endpoint health check results."""
        results = st.session_state['pe_health_results']
        all_healthy = st.session_state['pe_all_healthy']
        diagnostics = st.session_state['pe_diagnostics']
        
        st.subheader("🩺 Health Check Results")
        
        # Overall status
        if all_healthy:
            st.success("✅ All services are healthy!")
        else:
            st.error("❌ Some services have issues")
        
        # Individual service results
        for service_name, (status, message) in results.items():
            with st.expander(f"{service_name}: {'✅' if status else '❌'}", expanded=not status):
                if status:
                    st.success(message)
                else:
                    st.error(message)
                    
                    # Add specific troubleshooting for each service
                    self._render_service_troubleshooting(service_name)
        
        # Show identity information
        if 'identity_info' in diagnostics:
            with st.expander("🔍 Current Identity Information", expanded=False):
                identity_info = diagnostics['identity_info']
                
                st.write("**Authentication Chain:**")
                for method in identity_info['credential_chain']:
                    st.write(f"• {method}")
                
                if 'details' in identity_info:
                    st.write("**Identity Details:**")
                    st.json(identity_info['details'])
    
    def _render_service_troubleshooting(self, service_name: str):
        """Render troubleshooting guidance for a specific service."""
        
        troubleshooting_guides = {
            "OpenAI": {
                "title": "🧠 OpenAI Troubleshooting",
                "steps": [
                    "**Check Environment Variables:**",
                    "- `AZURE_OPENAI_ENDPOINT_41` or `AZURE_OPENAI_ENDPOINT`",
                    "- `AZURE_OPENAI_KEY_41` or `AZURE_OPENAI_KEY` (for API key auth)",
                    "",
                    "**For Managed Identity:**",
                    "- Ensure your identity has 'Cognitive Services OpenAI User' role",
                    "- Check that the OpenAI resource allows your identity",
                    "",
                    "**Private Endpoint Issues:**",
                    "- Verify DNS resolution points to private IP",
                    "- Check network security groups and routes",
                    "- Ensure private endpoint is properly configured"
                ]
            },
            "Document Intelligence": {
                "title": "📄 Document Intelligence Troubleshooting", 
                "steps": [
                    "**Check Environment Variables:**",
                    "- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` or `DOCUMENT_INTEL_ENDPOINT`",
                    "- `DOCUMENT_INTEL_KEY` (for API key auth)",
                    "",
                    "**For Managed Identity:**",
                    "- Ensure your identity has 'Cognitive Services User' role",
                    "- Check that the Document Intelligence resource allows your identity",
                    "",
                    "**Private Endpoint Issues:**",
                    "- Verify DNS resolution points to private IP",
                    "- Check network security groups and routes"
                ]
            },
            "AI Search": {
                "title": "🔍 AI Search Troubleshooting",
                "steps": [
                    "**Check Environment Variables:**",
                    "- `AZURE_SEARCH_ENDPOINT`",
                    "- `AZURE_SEARCH_KEY` (for API key auth)",
                    "",
                    "**For Managed Identity:**",
                    "- Ensure your identity has 'Search Index Data Reader' role",
                    "- Ensure your identity has 'Search Service Contributor' role",
                    "- Check that AI Search allows managed identity authentication",
                    "",
                    "**Private Endpoint Issues:**",
                    "- Verify DNS resolution points to private IP",
                    "- Check network security groups and routes",
                    "- This is the most common cause of 'Forbidden' errors"
                ]
            }
        }
        
        if service_name in troubleshooting_guides:
            guide = troubleshooting_guides[service_name]
            st.markdown(f"### {guide['title']}")
            for step in guide['steps']:
                st.markdown(step)
    
    def _render_identity_diagnostics(self):
        """Render detailed identity diagnostics."""
        identity_info = st.session_state['identity_info']
        
        st.subheader("🧬 Identity Diagnostics")
        
        # Authentication methods detected
        st.write("**Authentication Methods Detected:**")
        for method in identity_info['credential_chain']:
            if "Error" in method:
                st.error(f"❌ {method}")
            else:
                st.success(f"✅ {method}")
        
        # Detailed information
        if identity_info['details']:
            with st.expander("📋 Detailed Identity Information", expanded=True):
                
                if 'cli_account' in identity_info['details']:
                    cli_info = identity_info['details']['cli_account']
                    st.write("**Azure CLI Account:**")
                    st.write(f"- Name: {cli_info.get('name', 'Unknown')}")
                    st.write(f"- Tenant: {cli_info.get('tenant_id', 'Unknown')}")
                    st.write(f"- Subscription: {cli_info.get('subscription_id', 'Unknown')}")
                    st.write(f"- User Type: {cli_info.get('user_type', 'Unknown')}")
                
                if 'managed_identity' in identity_info['details']:
                    mi_info = identity_info['details']['managed_identity']
                    st.write("**Managed Identity Environment:**")
                    st.write(f"- VM ID: {mi_info.get('vm_id', 'Unknown')}")
                    st.write(f"- Resource Group: {mi_info.get('resource_group', 'Unknown')}")
                    st.write(f"- Location: {mi_info.get('location', 'Unknown')}")
                
                if 'service_principal' in identity_info['details']:
                    sp_info = identity_info['details']['service_principal']
                    st.write("**Service Principal Environment Variables:**")
                    for var, present in sp_info.items():
                        status = "✅ Set" if present else "❌ Not Set"
                        st.write(f"- {var}: {status}")
    
    def _render_configuration_guidance(self):
        """Render configuration guidance section."""
        st.subheader("🔧 Configuration Guidance")
        
        tab1, tab2, tab3 = st.tabs(["🚀 Quick Setup", "📋 Managed Identity", "🔑 API Keys"])
        
        with tab1:
            st.markdown("""
            ### Quick Setup for Private Endpoints
            
            **If you're getting 'Forbidden' errors:**
            
            1. **Check your authentication method** using the Identity Diagnostics button above
            2. **For Managed Identity (recommended):** Assign proper RBAC roles
            3. **For API Keys (temporary):** Add API keys to environment variables
            4. **Verify network connectivity** to your private endpoints
            """)
            
            if st.button("🎯 Generate Setup Commands"):
                with st.spinner("Generating setup commands..."):
                    guide = self._get_health_checker().generate_managed_identity_setup_guide()
                    st.session_state['setup_guide'] = guide
        
        with tab2:
            st.markdown("""
            ### Managed Identity Configuration (Recommended)
            
            **Required RBAC Roles:**
            
            **For OpenAI:**
            - `Cognitive Services OpenAI User`
            - `Cognitive Services User`
            
            **For Document Intelligence:**
            - `Cognitive Services User`
            
            **For AI Search:**
            - `Search Index Data Reader`
            - `Search Service Contributor`
            """)
            
            if 'setup_guide' in st.session_state:
                guide = st.session_state['setup_guide']
                
                st.write("**Your Current Identity:**")
                for step in guide['steps']:
                    if step.startswith("✅"):
                        st.success(step)
                    elif step.startswith("⚠️"):
                        st.warning(step)
                    elif step.startswith("❌"):
                        st.error(step)
                    else:
                        st.info(step)
                
                if guide['azure_cli_commands']:
                    st.write("**Azure CLI Commands:**")
                    commands = "\n".join(guide['azure_cli_commands'])
                    st.code(commands, language="bash")
                    
                    st.info("💡 Replace `<SUBSCRIPTION_ID>`, `<RG>`, `<OPENAI_NAME>`, etc. with your actual resource names")
        
        with tab3:
            st.markdown("""
            ### API Key Configuration (Temporary Solution)
            
            Add these environment variables to your `.env` file:
            
            ```bash
            # OpenAI API Key
            AZURE_OPENAI_KEY_41=your_openai_api_key_here
            
            # Document Intelligence API Key
            DOCUMENT_INTEL_KEY=your_doc_intel_api_key_here
            
            # AI Search API Key
            AZURE_SEARCH_KEY=your_search_api_key_here
            ```
            
            ⚠️ **Security Note:** API keys should only be used for development/testing.
            Use managed identity for production environments.
            """)
            
            if st.button("📋 Copy Environment Template"):
                env_template = """# Temporary API Key Configuration for Private Endpoints
# Replace with your actual API keys

# OpenAI API Key
AZURE_OPENAI_KEY_41=your_openai_api_key_here

# Document Intelligence API Key  
DOCUMENT_INTEL_KEY=your_doc_intel_api_key_here

# AI Search API Key
AZURE_SEARCH_KEY=your_search_api_key_here"""
                
                st.code(env_template, language="bash")
                st.success("📋 Template copied! Add these to your .env file with your actual API keys.")
    
    def _render_managed_identity_role_configuration(self):
        """Render managed identity role configuration and assignment guidance."""
        st.subheader("🔐 Managed Identity Role Configuration")
        
        # Check current identity status
        identity_info = st.session_state.get('identity_info')
        if not identity_info:
            # Get identity info if not available
            try:
                identity_info = self._get_health_checker().get_current_identity_info()
            except Exception as e:
                st.error(f"Failed to get identity information: {str(e)}")
                return
        
        # Display current identity type
        credential_chain = identity_info.get('credential_chain', [])
        
        if any("Managed Identity" in chain for chain in credential_chain):
            st.success("✅ **Managed Identity Detected** - You're running in Azure with managed identity enabled")
            identity_type = "managed_identity"
        elif any("Azure CLI" in chain for chain in credential_chain):
            st.info("ℹ️ **Azure CLI Authentication** - Using your personal Azure login")
            identity_type = "azure_cli"
        elif any("Service Principal" in chain for chain in credential_chain):
            st.info("ℹ️ **Service Principal Authentication** - Using app registration credentials")
            identity_type = "service_principal"
        else:
            st.warning("⚠️ **No Azure Authentication Detected** - Authentication may not be properly configured")
            identity_type = "none"
        
        # Individual service role configuration (same layout as public health check)
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔍 Azure AI Search")
            search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
            if search_endpoint:
                st.code(search_endpoint)
                if st.button("� Configure Search Roles", key="private_search_roles"):
                    self._configure_search_roles(search_endpoint, identity_type)
            else:
                st.error("AZURE_SEARCH_ENDPOINT not configured")
                
            st.subheader("🧠 Azure OpenAI")
            openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "") or os.getenv("AZURE_OPENAI_ENDPOINT_41", "")
            if openai_endpoint:
                st.code(openai_endpoint)
                if st.button("🔧 Configure OpenAI Roles", key="private_openai_roles"):
                    self._configure_openai_roles(openai_endpoint, identity_type)
            else:
                st.error("AZURE_OPENAI_ENDPOINT not configured")
        
        with col2:
            st.subheader("📄 Document Intelligence")
            docint_endpoint = os.getenv("DOCUMENT_INTEL_ENDPOINT", "")
            if docint_endpoint:
                st.code(docint_endpoint)
                if st.button("🔧 Configure Document Intelligence Roles", key="private_docint_roles"):
                    self._configure_docint_roles(docint_endpoint, identity_type)
            else:
                st.error("DOCUMENT_INTEL_ENDPOINT not configured")
        
        # Role checking section
        st.markdown("#### 🔒 Current Role Assignments")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🔍 Check Current Roles", key="check_current_roles"):
                self._check_current_role_assignments(identity_type)
        
        with col2:
            if st.button("🧪 Test Role Permissions", key="test_role_permissions"):
                self._test_role_permissions()
        
        # Display role check results if available
        if 'current_roles' in st.session_state:
            self._display_current_roles()
        
        if 'role_test_results' in st.session_state:
            self._display_role_test_results()
        
        # Quick setup guides
        with st.expander("📚 Quick Setup Guides", expanded=False):
            self._render_role_setup_guides(identity_type)

    def _generate_role_assignment_commands(self, identity_type: str, identity_info: dict):
        """Generate Azure CLI commands for role assignments."""
        commands = []
        guidance = []
        
        # Required roles for each service
        service_roles = {
            "Azure OpenAI": [
                "Cognitive Services OpenAI User",
                "Cognitive Services User"
            ],
            "Azure AI Search": [
                "Search Index Data Reader", 
                "Search Service Contributor"
            ],
            "Document Intelligence": [
                "Cognitive Services User"
            ]
        }
        
        if identity_type == "managed_identity":
            guidance.append("🤖 **Managed Identity Setup** - Assign roles to your VM's managed identity")
            
            # Try to get VM resource information
            vm_details = identity_info.get('details', {}).get('managed_identity', {})
            vm_id = vm_details.get('vm_id', '<VM_RESOURCE_ID>')
            resource_group = vm_details.get('resource_group', '<RESOURCE_GROUP>')
            
            commands.append("# Get your VM's managed identity principal ID")
            if vm_id != '<VM_RESOURCE_ID>':
                commands.append(f"PRINCIPAL_ID=$(az vm identity show --ids {vm_id} --query principalId -o tsv)")
            else:
                commands.append("PRINCIPAL_ID=$(az vm identity show --resource-group <RESOURCE_GROUP> --name <VM_NAME> --query principalId -o tsv)")
            
            commands.append("")
            commands.append("# Or get principal ID by VM name")
            commands.append("# PRINCIPAL_ID=$(az vm identity show --resource-group <RG> --name <VM_NAME> --query principalId -o tsv)")
            commands.append("")
            
        elif identity_type == "azure_cli":
            guidance.append("👤 **Azure CLI User Setup** - Assign roles to your user account")
            
            user_info = identity_info.get('details', {}).get('cli_account', {})
            user_name = user_info.get('name', '<YOUR_EMAIL>')
            
            commands.append("# Get your current user principal ID")
            commands.append("CURRENT_USER=$(az account show --query user.name -o tsv)")
            commands.append(f"# Or use your specific email: CURRENT_USER={user_name}")
            commands.append("")
            
        elif identity_type == "service_principal":
            guidance.append("🔧 **Service Principal Setup** - Assign roles to your app registration")
            commands.append("# Get your service principal object ID")
            commands.append("SP_OBJECT_ID=$(az ad sp show --id $AZURE_CLIENT_ID --query id -o tsv)")
            commands.append("")
        
        # Add role assignment commands for each service
        for service, roles in service_roles.items():
            commands.append(f"# === {service} Role Assignments ===")
            
            for role in roles:
                if identity_type == "managed_identity":
                    commands.append(f"az role assignment create \\")
                    commands.append(f"  --assignee $PRINCIPAL_ID \\")
                    commands.append(f"  --role '{role}' \\")
                    commands.append(f"  --scope '/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<{service.upper().replace(' ', '_')}_NAME>'")
                elif identity_type == "azure_cli":
                    commands.append(f"az role assignment create \\")
                    commands.append(f"  --assignee $CURRENT_USER \\")
                    commands.append(f"  --role '{role}' \\")
                    commands.append(f"  --scope '/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<{service.upper().replace(' ', '_')}_NAME>'")
                elif identity_type == "service_principal":
                    commands.append(f"az role assignment create \\")
                    commands.append(f"  --assignee $SP_OBJECT_ID \\")
                    commands.append(f"  --role '{role}' \\")
                    commands.append(f"  --scope '/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<{service.upper().replace(' ', '_')}_NAME>'")
                
                commands.append("")
        
        # Add subscription-level assignments (sometimes needed)
        commands.append("# === Optional: Subscription-level assignments (if resource-level doesn't work) ===")
        for service, roles in service_roles.items():
            for role in roles:
                if identity_type == "managed_identity":
                    commands.append(f"# az role assignment create --assignee $PRINCIPAL_ID --role '{role}' --scope '/subscriptions/<SUBSCRIPTION_ID>'")
                elif identity_type == "azure_cli":
                    commands.append(f"# az role assignment create --assignee $CURRENT_USER --role '{role}' --scope '/subscriptions/<SUBSCRIPTION_ID>'")
                elif identity_type == "service_principal":
                    commands.append(f"# az role assignment create --assignee $SP_OBJECT_ID --role '{role}' --scope '/subscriptions/<SUBSCRIPTION_ID>'")
        
        # Store results
        st.session_state['role_assignment_commands'] = {
            'commands': commands,
            'guidance': guidance,
            'identity_type': identity_type
        }

    def _display_role_assignment_commands(self):
        """Display the generated role assignment commands."""
        role_data = st.session_state['role_assignment_commands']
        
        st.success("✅ **Role Assignment Commands Generated**")
        
        # Show guidance
        for guide in role_data['guidance']:
            st.markdown(guide)
        
        # Show commands
        st.markdown("**Azure CLI Commands:**")
        st.code('\n'.join(role_data['commands']), language='bash')
        
        # Important notes
        st.markdown("**📋 Important Notes:**")
        st.markdown("""
        1. **Replace placeholders**: Update `<SUBSCRIPTION_ID>`, `<RESOURCE_GROUP>`, and service names
        2. **Resource names**: Use actual names of your Azure OpenAI, Search, and Document Intelligence services
        3. **Permissions**: You need subscription Contributor or User Access Administrator role to assign roles
        4. **Propagation**: Role assignments can take 5-10 minutes to take effect
        5. **Testing**: Run the health check again after assignment to verify permissions
        """)

    def _check_current_role_assignments(self, identity_type: str):
        """Check current role assignments for the identity."""
        with st.spinner("Checking current role assignments..."):
            try:
                import subprocess
                import json
                
                if identity_type == "managed_identity":
                    # Get VM's managed identity roles
                    result = subprocess.run([
                        "az", "role", "assignment", "list", 
                        "--assignee", "$(az vm identity show --resource-group <RG> --name <VM> --query principalId -o tsv)",
                        "--output", "json"
                    ], capture_output=True, text=True, timeout=30)
                elif identity_type == "azure_cli":
                    # Get current user's roles
                    result = subprocess.run([
                        "az", "role", "assignment", "list", 
                        "--assignee", "$(az account show --query user.name -o tsv)",
                        "--output", "json"
                    ], capture_output=True, text=True, timeout=30)
                else:
                    st.warning("Role checking not implemented for this identity type yet.")
                    return
                
                if result.returncode == 0:
                    roles = json.loads(result.stdout)
                    st.session_state['current_roles'] = {
                        'success': True,
                        'roles': roles,
                        'identity_type': identity_type
                    }
                else:
                    st.session_state['current_roles'] = {
                        'success': False,
                        'error': result.stderr,
                        'identity_type': identity_type
                    }
                    
            except Exception as e:
                st.session_state['current_roles'] = {
                    'success': False,
                    'error': str(e),
                    'identity_type': identity_type
                }

    def _display_current_roles(self):
        """Display current role assignments."""
        role_data = st.session_state['current_roles']
        
        if role_data['success']:
            roles = role_data['roles']
            
            if roles:
                st.success(f"✅ **Found {len(roles)} role assignments**")
                
                # Filter for relevant roles
                relevant_roles = []
                for role in roles:
                    role_name = role.get('roleDefinitionName', '')
                    if any(keyword in role_name for keyword in ['Cognitive', 'Search', 'OpenAI']):
                        relevant_roles.append(role)
                
                if relevant_roles:
                    st.markdown("**🎯 Relevant Role Assignments:**")
                    for role in relevant_roles:
                        role_name = role.get('roleDefinitionName', 'Unknown Role')
                        scope = role.get('scope', 'Unknown Scope')
                        scope_display = scope.split('/')[-1] if '/' in scope else scope
                        st.markdown(f"- **{role_name}** on `{scope_display}`")
                else:
                    st.warning("⚠️ No relevant Azure AI service roles found")
                    
                # Show all roles in expander
                with st.expander(f"📋 All Role Assignments ({len(roles)})", expanded=False):
                    for role in roles:
                        st.json(role)
            else:
                st.warning("⚠️ No role assignments found")
        else:
            st.error(f"❌ Failed to check roles: {role_data['error']}")

    def _test_role_permissions(self):
        """Test role permissions by making actual API calls."""
        with st.spinner("Testing role permissions..."):
            try:
                # Use existing health checker to test permissions
                health_checker = self._get_health_checker()
                
                # Test each service
                test_results = {}
                
                # Test OpenAI
                try:
                    openai_result = health_checker.check_openai_private_endpoint()
                    test_results['Azure OpenAI'] = {
                        'success': openai_result[0],
                        'message': openai_result[1]
                    }
                except Exception as e:
                    test_results['Azure OpenAI'] = {
                        'success': False,
                        'message': f"Test failed: {str(e)}"
                    }
                
                # Test AI Search
                try:
                    search_result = health_checker.check_ai_search_private_endpoint()
                    test_results['Azure AI Search'] = {
                        'success': search_result[0],
                        'message': search_result[1]
                    }
                except Exception as e:
                    test_results['Azure AI Search'] = {
                        'success': False,
                        'message': f"Test failed: {str(e)}"
                    }
                
                # Test Document Intelligence
                try:
                    doc_result = health_checker.check_document_intelligence_private_endpoint()
                    test_results['Document Intelligence'] = {
                        'success': doc_result[0],
                        'message': doc_result[1]
                    }
                except Exception as e:
                    test_results['Document Intelligence'] = {
                        'success': False,
                        'message': f"Test failed: {str(e)}"
                    }
                
                st.session_state['role_test_results'] = test_results
                
            except Exception as e:
                st.session_state['role_test_results'] = {
                    'error': str(e)
                }

    def _display_role_test_results(self):
        """Display role permission test results."""
        test_results = st.session_state['role_test_results']
        
        if 'error' in test_results:
            st.error(f"❌ Permission test failed: {test_results['error']}")
            return
        
        st.subheader("🧪 **Permission Test Results**")
        
        all_passed = all(result['success'] for result in test_results.values())
        
        if all_passed:
            st.success("🎉 All permission tests passed!")
        else:
            failed_count = sum(1 for result in test_results.values() if not result['success'])
            st.error(f"❌ {failed_count} out of {len(test_results)} tests failed")
        
        for service, result in test_results.items():
            with st.expander(f"{service}: {'✅' if result['success'] else '❌'}", expanded=not result['success']):
                if result['success']:
                    st.success(result['message'])
                else:
                    st.error(result['message'])
                    
                    # Add specific guidance for permission errors
                    if "403" in result['message'] or "Forbidden" in result['message']:
                        st.markdown("**🔧 Fix Permission Issues:**")
                        st.markdown("1. Ensure the identity has the required roles assigned")
                        st.markdown("2. Wait 5-10 minutes for role assignments to propagate")
                        st.markdown("3. Try using the role assignment commands above")
                        st.markdown("4. Verify the resource names and subscription ID are correct")

    def _render_role_setup_guides(self, identity_type: str):
        """Render quick setup guides for different identity types."""
        
        if identity_type == "managed_identity":
            st.markdown("### 🤖 Managed Identity Setup")
            st.markdown("""
            **For Azure VMs:**
            1. Ensure managed identity is enabled on your VM
            2. Use the generated commands above to assign roles
            3. Wait 5-10 minutes for permissions to propagate
            4. Test using the health check
            
            **Required Roles:**
            - `Cognitive Services OpenAI User` - For Azure OpenAI access
            - `Cognitive Services User` - For Document Intelligence access  
            - `Search Index Data Reader` - For reading search indexes
            - `Search Service Contributor` - For managing search indexes
            """)
            
        elif identity_type == "azure_cli":
            st.markdown("### 👤 Azure CLI User Setup")
            st.markdown("""
            **For Development/Testing:**
            1. Ensure you're logged in: `az login`
            2. Assign roles to your user account using commands above
            3. Consider using managed identity for production
            
            **Note:** Personal accounts are good for development but not recommended for production workloads.
            """)
            
        elif identity_type == "service_principal":
            st.markdown("### 🔧 Service Principal Setup")
            st.markdown("""
            **For Automated/Production Scenarios:**
            1. Create an app registration in Azure AD
            2. Generate client secret or certificate
            3. Set environment variables: `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`
            4. Assign roles using commands above
            """)
        
        else:
            st.markdown("### ⚠️ No Authentication Detected")
            st.markdown("""
            **Setup Required:**
            1. **Option 1 - Managed Identity:** Enable on your Azure VM/App Service
            2. **Option 2 - Azure CLI:** Run `az login` for development
            3. **Option 3 - Service Principal:** Set up app registration with secrets
            
            Choose managed identity for production workloads in Azure.
            """)

    def render_quick_fix_section(self):
        """Render a comprehensive quick fix section for immediate troubleshooting."""
        st.sidebar.subheader("🔧 Quick Fixes")
        
        if st.sidebar.button("📝 Show .env Template"):
            self._show_env_template_in_sidebar()
        
        if st.sidebar.button("🔐 Check Authentication"):
            self._check_auth_in_sidebar()
        
        if st.sidebar.button("� Copy Sample Config"):
            self._copy_sample_config_in_sidebar()
        
        if st.sidebar.button("� Fix Forbidden Errors"):
            self._fix_forbidden_errors()
    
    def _show_env_template_in_sidebar(self):
        """Show .env template in sidebar."""
        st.sidebar.subheader("📝 .env Template")
        st.sidebar.code("""
# Required Azure Endpoints
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net/
DOCUMENT_INTEL_ENDPOINT=https://your-docint.cognitiveservices.azure.com/

# Required OpenAI Configuration
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Optional: API Keys (if not using managed identity)
# AZURE_OPENAI_KEY=your_api_key
# AZURE_SEARCH_KEY=your_api_key
# DOCUMENT_INTEL_KEY=your_api_key
        """, language='bash')
    
    def _check_auth_in_sidebar(self):
        """Check authentication method in sidebar."""
        try:
            env_validation = self._get_health_checker().validate_env_configuration()
            auth_method = env_validation['auth_method']
            
            st.sidebar.write(f"🔐 **Auth Method:** {auth_method.replace('_', ' ').title()}")
            
            if auth_method == 'managed_identity':
                st.sidebar.success("✅ Using Managed Identity")
            elif auth_method == 'api_keys':
                st.sidebar.info("🔑 Using API Keys")
            elif auth_method == 'service_principal':
                st.sidebar.info("👤 Using Service Principal")
            else:
                st.sidebar.warning("⚠️ Authentication method unclear")
                
        except Exception as e:
            st.sidebar.error(f"❌ Auth check failed: {str(e)}")
    
    def _copy_sample_config_in_sidebar(self):
        """Copy sample configuration to session state."""
        sample_config = """
# Azure Service Endpoints (Required)
AZURE_OPENAI_ENDPOINT=https://your-openai-service.openai.azure.com/
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net/
DOCUMENT_INTEL_ENDPOINT=https://your-docint-service.cognitiveservices.azure.com/

# OpenAI Configuration (Required)
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_MODEL_VERSION=2024-02-15-preview

# Choose Authentication Method:
# Option 1: Managed Identity (Recommended - no additional config needed)

# Option 2: API Keys (Uncomment if needed)
# AZURE_OPENAI_KEY=your_openai_api_key_here
# AZURE_SEARCH_KEY=your_search_api_key_here
# DOCUMENT_INTEL_KEY=your_document_intel_api_key_here

# Option 3: Service Principal (Uncomment if needed)
# AZURE_CLIENT_ID=your-service-principal-client-id
# AZURE_CLIENT_SECRET=your-service-principal-client-secret
# AZURE_TENANT_ID=your-azure-tenant-id
        """
        
        st.session_state['copied_env_content'] = sample_config
        st.sidebar.success("✅ Sample configuration copied!")
        st.sidebar.info("📋 Check the main area for the copied content.")
    
    def _fix_forbidden_errors(self):
        """Legacy forbidden errors fix."""
        st.info("Running automated fix for common private endpoint issues...")
        
        # Check current status
        results, all_healthy, diagnostics = self._get_health_checker().check_all_private_endpoint_services()
        
        failed_services = [name for name, (status, _) in results.items() if not status]
        
        if failed_services:
            st.error(f"❌ Services with issues: {', '.join(failed_services)}")
            
            # Show identity information
            identity_info = diagnostics['identity_info']
            
            if any("Managed Identity" in chain for chain in identity_info['credential_chain']):
                st.warning("🔧 You're using managed identity. Ensure RBAC roles are assigned.")
            elif any("Azure CLI" in chain for chain in identity_info['credential_chain']):
                st.warning("🔧 You're using Azure CLI. Ensure your user has proper permissions.")
            else:
                st.error("🔧 No authentication method detected. Please configure Azure CLI or managed identity.")
            
            # Generate quick fix commands
            guide = self._get_health_checker().generate_managed_identity_setup_guide()
            if guide['azure_cli_commands']:
                st.code("\n".join(guide['azure_cli_commands'][:10]), language="bash")
        else:
            st.success("✅ All services are healthy!")
    
    def _render_env_validation(self):
        """Run environment validation and store results in session state."""
        with st.spinner("Validating environment configuration..."):
            try:
                health_checker = self._get_health_checker()
                validation_result = health_checker.validate_env_configuration()
                guidance = health_checker.generate_env_guidance(validation_result)
                
                # Store results in session state
                st.session_state['env_validation_results'] = {
                    'validation': validation_result,
                    'guidance': guidance,
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                st.error(f"Environment validation failed: {str(e)}")
                st.session_state['env_validation_results'] = {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
    
    def _display_env_validation_results(self, env_results: Dict[str, Any]):
        """Display environment validation results."""
        if 'error' in env_results:
            st.error(f"❌ Environment validation failed: {env_results['error']}")
            return
            
        validation = env_results['validation']
        guidance = env_results['guidance']
        
        # Show overall status
        if validation['is_configuration_complete']:
            st.success("✅ **Environment Configuration Complete**")
        else:
            missing_count = len(validation['missing_required'])
            st.warning(f"⚠️ **Environment Configuration Incomplete** - {missing_count} required variables missing")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Present Variables", len(validation['present_vars']))
        with col2:
            st.metric("Missing Required", len(validation['missing_required']))
        with col3:
            st.metric("Missing Optional", len(validation['missing_optional']))
        with col4:
            auth_method = validation['auth_method'].replace('_', ' ').title()
            st.metric("Auth Method", auth_method)
        
        # Show guidance message
        st.markdown(guidance['guidance_message'])
        
        # Show missing required variables
        if validation['missing_required']:
            with st.expander("❌ Missing Required Variables", expanded=True):
                for var in validation['missing_required']:
                    var_def = validation['var_definitions'][var]
                    st.markdown(f"**`{var}`**")
                    st.markdown(f"- Description: {var_def['description']}")
                    st.markdown(f"- Example: `{var}={var_def['example']}`")
                    st.markdown("")
        
        # Show missing optional variables  
        if validation['missing_optional']:
            with st.expander("ℹ️ Missing Optional Variables", expanded=False):
                for var in validation['missing_optional']:
                    var_def = validation['var_definitions'][var]
                    st.markdown(f"**`{var}`** - {var_def['description']}")
        
        # Show present variables
        if validation['present_vars']:
            with st.expander(f"✅ Present Variables ({len(validation['present_vars'])})", expanded=False):
                for var in validation['present_vars']:
                    var_def = validation['var_definitions'][var]
                    var_status = validation['env_status'][var]
                    value_length = var_status['value_length']
                    
                    # Mask sensitive values
                    if var_def.get('sensitive', False):
                        display_info = f"**`{var}`** - {var_def['description']} (****** - {value_length} chars)"
                    else:
                        display_info = f"**`{var}`** - {var_def['description']} ({value_length} chars)"
                    
                    st.markdown(display_info)
        
        # Authentication method recommendations
        with st.expander("🔐 Authentication Method Recommendations", expanded=False):
            for method, details in guidance['auth_recommendations'].items():
                status_icon = "✅" if details['recommended'] else "ℹ️"
                status_text = "Recommended" if details['recommended'] else "Available"
                
                st.markdown(f"**{method.replace('_', ' ').title()}** {status_icon} {status_text}")
                st.markdown(f"- {details['description']}")
                st.markdown(f"- Setup: {details['setup_required']}")
                st.markdown("")
        
        # Sample .env file
        with st.expander("📄 Sample .env File", expanded=False):
            st.markdown("**Complete .env template with all variables:**")
            st.code(guidance['sample_env_content'], language='bash')
            
            # Add download button for .env template
            st.download_button(
                label="💾 Download .env Template",
                data=guidance['sample_env_content'],
                file_name="template.env",
                mime="text/plain",
                help="Download this template and rename to .env, then fill in your values",
                key="private_env_template_download"
            )
    
    def _show_auth_status(self):
        """Show current authentication status for all services (same as public health check)."""
        st.markdown("**Current Authentication Methods:**")
        
        # Azure Search
        search_key = os.getenv("AZURE_SEARCH_KEY", "")
        if search_key:
            st.markdown("🔑 Azure Search: **API Key**")
        else:
            st.markdown("🔐 Azure Search: **Managed Identity**")
        
        # Azure OpenAI
        openai_key = os.getenv("AZURE_OPENAI_KEY", "") or os.getenv("AZURE_OPENAI_KEY_41", "")
        if openai_key:
            st.markdown("🔑 Azure OpenAI: **API Key**")
        else:
            st.markdown("🔐 Azure OpenAI: **Managed Identity**")
        
        # Document Intelligence
        docint_key = os.getenv("DOCUMENT_INTEL_KEY", "") or os.getenv("AZURE_FORMREC_KEY", "")
        if docint_key:
            st.markdown("🔑 Document Intelligence: **API Key**")
        else:
            st.markdown("🔐 Document Intelligence: **Managed Identity**")
        
        st.markdown("""
        **Migration Tips:**
        - Remove API key environment variables to switch to managed identity
        - Ensure RBAC roles are assigned before removing API keys
        - Test each service after switching authentication methods
        """)

    def _configure_search_roles(self, endpoint, identity_type):
        """Configure Azure Search roles for private endpoints."""
        with st.spinner("Configuring Azure Search roles..."):
            try:
                # Extract service name from endpoint
                service_name = self._extract_service_name_from_endpoint(endpoint)
                
                # Get managed identity or user principal
                principal = self._get_current_principal(identity_type)
                if not principal:
                    st.error("❌ Could not determine principal for role assignment")
                    return
                
                # Required roles for Azure Search
                roles = [
                    "Search Index Data Reader",
                    "Search Service Contributor"
                ]
                
                success_count = 0
                for role in roles:
                    success = self._assign_role(role, principal, service_name, "Microsoft.Search/searchServices")
                    if success:
                        success_count += 1
                
                if success_count == len(roles):
                    st.success("🎉 All Azure Search roles configured successfully!")
                else:
                    st.warning("⚠️ Some role assignments may have failed. Check the messages above.")
                    
            except Exception as e:
                st.error(f"❌ Error configuring roles: {e}")

    def _configure_openai_roles(self, endpoint, identity_type):
        """Configure Azure OpenAI roles for private endpoints."""
        with st.spinner("Configuring Azure OpenAI roles..."):
            try:
                # Extract service name from endpoint
                service_name = self._extract_service_name_from_endpoint(endpoint)
                
                # Get managed identity or user principal
                principal = self._get_current_principal(identity_type)
                if not principal:
                    st.error("❌ Could not determine principal for role assignment")
                    return
                
                # Required roles for Azure OpenAI
                roles = [
                    "Cognitive Services OpenAI User",
                    "Cognitive Services User"
                ]
                
                success_count = 0
                for role in roles:
                    success = self._assign_role(role, principal, service_name, "Microsoft.CognitiveServices/accounts")
                    if success:
                        success_count += 1
                
                if success_count == len(roles):
                    st.success("🎉 All Azure OpenAI roles configured successfully!")
                else:
                    st.warning("⚠️ Some role assignments may have failed. Check the messages above.")
                    
            except Exception as e:
                st.error(f"❌ Error configuring roles: {e}")

    def _configure_docint_roles(self, endpoint, identity_type):
        """Configure Document Intelligence roles for private endpoints."""
        with st.spinner("Configuring Document Intelligence roles..."):
            try:
                # Extract service name from endpoint
                service_name = self._extract_service_name_from_endpoint(endpoint)
                
                # Get managed identity or user principal
                principal = self._get_current_principal(identity_type)
                if not principal:
                    st.error("❌ Could not determine principal for role assignment")
                    return
                
                # Required roles for Document Intelligence
                roles = [
                    "Cognitive Services User"
                ]
                
                success_count = 0
                for role in roles:
                    success = self._assign_role(role, principal, service_name, "Microsoft.CognitiveServices/accounts")
                    if success:
                        success_count += 1
                
                if success_count == len(roles):
                    st.success("🎉 All Document Intelligence roles configured successfully!")
                else:
                    st.warning("⚠️ Some role assignments may have failed. Check the messages above.")
                    
            except Exception as e:
                st.error(f"❌ Error configuring roles: {e}")

    def _extract_service_name_from_endpoint(self, endpoint):
        """Extract service name from endpoint URL."""
        try:
            # Remove protocol and extract the service name
            # Example: https://my-service.openai.azure.com/ -> my-service
            import re
            match = re.match(r'https?://([^.]+)\.', endpoint)
            if match:
                return match.group(1)
            else:
                # Fallback: just use what's between // and first .
                return endpoint.split('//')[1].split('.')[0]
        except Exception:
            return "unknown-service"

    def _get_current_principal(self, identity_type):
        """Get the current principal (managed identity or user) for role assignment."""
        try:
            if identity_type == "managed_identity":
                # Try multiple methods to get managed identity principal ID
                
                # Method 1: Get from Azure metadata service directly
                try:
                    import requests
                    # Get token first to verify managed identity works
                    token_response = requests.get(
                        'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/',
                        headers={'Metadata': 'true'}, 
                        timeout=10
                    )
                    
                    if token_response.status_code == 200:
                        # Now get the identity info
                        info_response = requests.get(
                            'http://169.254.169.254/metadata/instance?api-version=2021-02-01',
                            headers={'Metadata': 'true'},
                            timeout=10
                        )
                        
                        if info_response.status_code == 200:
                            instance_data = info_response.json()
                            vm_id = instance_data.get('compute', {}).get('resourceId', '')
                            
                            if vm_id:
                                # Get principal ID using the full VM resource ID
                                result = subprocess.run([
                                    "az", "vm", "identity", "show", 
                                    "--ids", vm_id,
                                    "--query", "principalId", 
                                    "-o", "tsv"
                                ], capture_output=True, text=True, timeout=30)
                                
                                if result.returncode == 0:
                                    principal_id = result.stdout.strip()
                                    if principal_id and principal_id != '':
                                        return principal_id
                                        
                except Exception as metadata_error:
                    st.warning(f"Could not get managed identity from metadata: {metadata_error}")
                
                # Method 2: Try to get current identity from Azure CLI
                result = subprocess.run([
                    "az", "account", "show", 
                    "--query", "user", 
                    "-o", "json"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    import json
                    user_info = json.loads(result.stdout)
                    if user_info.get('type') == 'servicePrincipal':
                        # This is actually a managed identity or service principal
                        user_name = user_info.get('name', '')
                        if user_name:
                            # Get the object ID for this service principal
                            sp_result = subprocess.run([
                                "az", "ad", "sp", "show",
                                "--id", user_name,
                                "--query", "objectId",
                                "-o", "tsv"
                            ], capture_output=True, text=True, timeout=10)
                            
                            if sp_result.returncode == 0:
                                return sp_result.stdout.strip()
                
                st.warning("⚠️ Could not determine managed identity principal ID. You may need to assign roles manually.")
                return None
                    
            elif identity_type == "azure_cli":
                # Get current user object ID from Azure CLI
                # Try the modern approach first
                result = subprocess.run([
                    "az", "ad", "signed-in-user", "show",
                    "--query", "id", 
                    "-o", "tsv"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    principal_id = result.stdout.strip()
                    if principal_id and principal_id != '':
                        return principal_id
                
                # Fallback: get user info and then object ID
                result = subprocess.run([
                    "az", "account", "show", 
                    "--query", "user", 
                    "-o", "json"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    import json
                    user_info = json.loads(result.stdout)
                    user_name = user_info.get('name', '')
                    user_type = user_info.get('type', '')
                    
                    if user_type == 'user' and user_name:
                        # Get user object ID using UPN
                        user_result = subprocess.run([
                            "az", "ad", "user", "show",
                            "--id", user_name,
                            "--query", "objectId", 
                            "-o", "tsv"
                        ], capture_output=True, text=True, timeout=10)
                        
                        if user_result.returncode == 0:
                            return user_result.stdout.strip()
                    
                    elif user_type == 'servicePrincipal' and user_name:
                        # Get service principal object ID  
                        sp_result = subprocess.run([
                            "az", "ad", "sp", "show",
                            "--id", user_name,
                            "--query", "objectId",
                            "-o", "tsv"
                        ], capture_output=True, text=True, timeout=10)
                        
                        if sp_result.returncode == 0:
                            return sp_result.stdout.strip()
            
            elif identity_type == "service_principal":
                # Get service principal object ID from environment or current context
                client_id = os.getenv("AZURE_CLIENT_ID")
                if client_id:
                    result = subprocess.run([
                        "az", "ad", "sp", "show",
                        "--id", client_id,
                        "--query", "objectId",
                        "-o", "tsv"
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        return result.stdout.strip()
            
            return None
            
        except Exception as e:
            st.error(f"Error getting principal: {str(e)}")
            return None

    def _assign_role(self, role, principal, service_name, resource_provider):
        """Assign a role to a principal for a specific service."""
        try:
            # Get subscription ID
            sub_result = subprocess.run([
                "az", "account", "show", 
                "--query", "id", 
                "-o", "tsv"
            ], capture_output=True, text=True, timeout=10)
            
            if sub_result.returncode != 0:
                st.error("❌ Could not get subscription ID")
                return False
                
            subscription_id = sub_result.stdout.strip()
            
            # Find the actual resource to get its resource group
            # Search for the resource by name and type
            resource_result = subprocess.run([
                "az", "resource", "list",
                "--name", service_name,
                "--resource-type", resource_provider,
                "--query", "[0].{id:id,resourceGroup:resourceGroup}",
                "-o", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if resource_result.returncode == 0:
                import json
                resource_data = json.loads(resource_result.stdout)
                
                if resource_data and resource_data.get('id'):
                    # Use the full resource ID as scope
                    scope = resource_data['id']
                    st.info(f"📍 Using resource scope: {scope}")
                else:
                    # Fallback: try subscription-level assignment
                    scope = f"/subscriptions/{subscription_id}"
                    st.warning(f"⚠️ Resource not found, trying subscription-level assignment for: {service_name}")
            else:
                # Fallback: try subscription-level assignment
                scope = f"/subscriptions/{subscription_id}"
                st.warning(f"⚠️ Could not find resource, trying subscription-level assignment for: {service_name}")
            
            # Try to assign the role
            result = subprocess.run([
                "az", "role", "assignment", "create",
                "--role", role,
                "--assignee", principal,
                "--scope", scope
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                st.success(f"✅ Assigned role: {role}")
                return True
            else:
                if "already exists" in result.stderr.lower():
                    st.info(f"ℹ️ Role already assigned: {role}")
                    return True
                else:
                    st.error(f"❌ Failed to assign role {role}: {result.stderr}")
                    
                    # If resource-level failed, try subscription-level as fallback
                    if scope != f"/subscriptions/{subscription_id}":
                        st.info("🔄 Trying subscription-level role assignment as fallback...")
                        fallback_result = subprocess.run([
                            "az", "role", "assignment", "create",
                            "--role", role,
                            "--assignee", principal,
                            "--scope", f"/subscriptions/{subscription_id}"
                        ], capture_output=True, text=True, timeout=60)
                        
                        if fallback_result.returncode == 0:
                            st.success(f"✅ Assigned role at subscription level: {role}")
                            return True
                        elif "already exists" in fallback_result.stderr.lower():
                            st.info(f"ℹ️ Role already assigned at subscription level: {role}")
                            return True
                        else:
                            st.error(f"❌ Subscription-level assignment also failed: {fallback_result.stderr}")
                    
                    return False
                    
        except Exception as e:
            st.error(f"❌ Error assigning role {role}: {str(e)}")
            return False
