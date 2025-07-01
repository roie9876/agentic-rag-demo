#!/usr/bin/env python3
"""
Health Check UI Module for Agentic RAG Demo
===========================================
This module contains the UI components for the health check functionality.
"""

import os
import streamlit as st
import subprocess
import json
from .health_checker import HealthChecker
from .private_endpoint_health_ui import PrivateEndpointHealthCheckUI


class HealthCheckUI:
    """
    UI handler for health check functionality.
    """
    
    def __init__(self):
        """Initialize the health check UI."""
        self.health_checker = HealthChecker()
        self.private_endpoint_ui = PrivateEndpointHealthCheckUI()
    
    def render_health_check_tab(self):
        """Render the public health check tab (renamed from complete health check tab)."""
        st.header("🩺 Public Health Check & Login")
        
        st.info("💡 **Note**: For private endpoint health checks, use the dedicated **🔒 Private Health Check** tab.")
        
        # Login Section
        self._render_login_section()
        
        st.divider()
        
        # Health Check Section
        st.subheader("🩺 Service Health Check")
        
        if st.button("🔄 Check All Services"):
            with st.spinner("Checking services..."):
                results, all_healthy, troubleshooting = self.health_checker.check_all_services()
                st.session_state['health_results'] = results
                st.session_state['all_healthy'] = all_healthy
                st.session_state['troubleshooting'] = troubleshooting

        if 'health_results' in st.session_state:
            self._render_health_results()
        else:
            st.info("Run a health check before using other tabs.")
        
        # Add environment configuration validation section
        st.divider()
        self._render_environment_validation_section()
        
        # Add role configuration section
        st.divider()
        self._render_role_configuration_section()
    
    def _render_health_results(self):
        """Render the health check results."""
        results = st.session_state['health_results']
        all_healthy = st.session_state['all_healthy']
        troubleshooting = st.session_state.get('troubleshooting', None)
        
        if all_healthy:
            st.success("🎉 All services are healthy and ready!")
        else:
            st.error("⚠️ Some services have issues. Please check configuration before proceeding to other tabs.")
        
        for service_name, (status, message) in results.items():
            st.write(f"**{service_name}:** {'✅' if status else '❌'} {message}")
            
            # Show troubleshooting info for failed services
            if not status and troubleshooting and service_name in troubleshooting:
                with st.expander(f"Troubleshooting steps for {service_name}", expanded=True):
                    st.info(troubleshooting[service_name])
                    
                    # For OpenAI specifically, add environment variable inspection
                    if service_name == "OpenAI":
                        self._render_openai_env_vars()
            
            # For Document Intelligence service, add more information even if it's healthy
            if service_name == "Document Intelligence":
                self._render_document_intelligence_details()
    
    def _render_openai_env_vars(self):
        """Render OpenAI environment variables section."""
        st.subheader("Environment Variables")
        env_vars = {
            "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT", "Not set"),
            "AZURE_OPENAI_ENDPOINT_41": os.getenv("AZURE_OPENAI_ENDPOINT_41", "Not set"),
            "AZURE_OPENAI_ENDPOINT_4o": os.getenv("AZURE_OPENAI_ENDPOINT_4o", "Not set"),
            "AZURE_OPENAI_KEY": "***" if os.getenv("AZURE_OPENAI_KEY") else "Not set",
            "AZURE_OPENAI_KEY_41": "***" if os.getenv("AZURE_OPENAI_KEY_41") else "Not set",
            "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION", "Not set"),
            "AZURE_OPENAI_DEPLOYMENT": os.getenv("AZURE_OPENAI_DEPLOYMENT", "Not set"),
            "AZURE_OPENAI_DEPLOYMENT_41": os.getenv("AZURE_OPENAI_DEPLOYMENT_41", "Not set"),
        }
        st.json(env_vars)
    
    def _render_document_intelligence_details(self):
        """Render Document Intelligence details section."""
        with st.expander("Document Intelligence Details", expanded=False):
            st.markdown("""
            ### Document Intelligence API Versions
            
            **Document Intelligence 4.0 API (2023-10-31 and newer):**
            - Supports DOCX and PPTX parsing
            - Enhanced layout analysis
            - More accurate results
            - Available in 2023-10-31-preview, 2024-02-29-preview, 2024-11-30 (General Availability) API versions
            
            **Document Intelligence 3.x API:**
            - Basic document analysis features
            - PDF and image analysis
            - Limited DOCX/PPTX support
            
            If your service says "❌ Not Available" for Document Intelligence 4.0 API but you believe you have a 4.0 API resource,
            check that you're using the correct environment variables that point to your 4.0 API resource.
            """)
            
            # Show environment variables
            st.subheader("Environment Variables")
            env_vars = {
                "DOCUMENT_INTEL_ENDPOINT": os.getenv("DOCUMENT_INTEL_ENDPOINT", "Not set"),
                "DOCUMENT_INTEL_KEY": "***" if os.getenv("DOCUMENT_INTEL_KEY") else "Not set",
                "AZURE_FORMREC_SERVICE": os.getenv("AZURE_FORMREC_SERVICE", "Not set (legacy)"),
                "AZURE_FORMREC_KEY": "***" if os.getenv("AZURE_FORMREC_KEY") else "Not set (legacy)",
                "AZURE_FORMRECOGNIZER_ENDPOINT": os.getenv("AZURE_FORMRECOGNIZER_ENDPOINT", "Not set (legacy)"),
                "AZURE_FORMRECOGNIZER_KEY": "***" if os.getenv("AZURE_FORMRECOGNIZER_KEY") else "Not set (legacy)"
            }
            st.json(env_vars)
    
    def health_block(self):
        """
        Check if health check has passed and show warnings if not.
        This function can be called by other tabs to warn about potential issues.
        """
        if 'health_results' not in st.session_state:
            st.info("💡 **Tip:** Run the Health Check tab first to verify your services are properly configured.")
            return
            
        if not st.session_state.get('all_healthy', False):
            st.warning("⚠️ **Service Issues Detected:** Some services may not be properly configured. Check the Health Check tab for details.")
            
            # Show summary of failed services
            results = st.session_state.get('health_results', {})
            failed_services = [name for name, (status, _) in results.items() if not status]
            if failed_services:
                st.error(f"**Failed Services:** {', '.join(failed_services)}")
                
            with st.expander("🔧 Quick Troubleshooting", expanded=False):
                st.markdown("""
                **Common Issues:**
                - Missing environment variables
                - Incorrect API endpoints or keys
                - Network connectivity problems
                - Service authentication issues
                
                **Next Steps:**
                1. Go to the **Health Check** tab
                2. Click **Check All Services**
                3. Review any error messages and troubleshooting guides
                4. Fix the configuration issues
                5. Re-run the health check
                """)
                
            st.markdown("---")

    def _render_login_section(self):
        """Render the Azure CLI login section."""
        st.subheader("🔐 Azure CLI Authentication")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Check current login status
            login_status = self._check_azure_login()
            if login_status["logged_in"]:
                st.success(f"✅ Logged in as: **{login_status['user']}**")
                st.info(f"📍 Subscription: **{login_status['subscription_name']}** ({login_status['subscription_id']})")
                
                # Show tenant info if available
                if login_status.get('tenant_id'):
                    st.info(f"🏢 Tenant: **{login_status['tenant_id']}**")
            else:
                st.error("❌ Not logged in to Azure CLI")
                st.warning("Please log in to Azure CLI to use managed identity features.")
        
        with col2:
            if st.button("🔐 Login", help="Open Azure CLI login"):
                self._perform_azure_login()
            
            if login_status["logged_in"]:
                if st.button("🔄 Refresh", help="Refresh login status"):
                    st.rerun()
                
                if st.button("🚪 Logout", help="Logout from Azure CLI"):
                    self._perform_azure_logout()

    def _check_azure_login(self):
        """Check if user is logged in to Azure CLI."""
        try:
            result = subprocess.run(
                ["az", "account", "show", "--output", "json"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                account_info = json.loads(result.stdout)
                return {
                    "logged_in": True,
                    "user": account_info.get("user", {}).get("name", "Unknown"),
                    "subscription_id": account_info.get("id", "Unknown"),
                    "subscription_name": account_info.get("name", "Unknown"),
                    "tenant_id": account_info.get("tenantId", "Unknown")
                }
            else:
                return {"logged_in": False}
                
        except Exception as e:
            st.error(f"Error checking Azure CLI status: {e}")
            return {"logged_in": False}

    def _perform_azure_login(self):
        """Perform Azure CLI login."""
        with st.spinner("Opening Azure CLI login..."):
            try:
                # Use az login --use-device-code for better compatibility
                result = subprocess.run(
                    ["az", "login", "--use-device-code"],
                    capture_output=True, text=True, timeout=300
                )
                
                if result.returncode == 0:
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error(f"❌ Login failed: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                st.error("❌ Login timed out. Please try again.")
            except Exception as e:
                st.error(f"❌ Login error: {e}")

    def _perform_azure_logout(self):
        """Perform Azure CLI logout."""
        with st.spinner("Logging out..."):
            try:
                result = subprocess.run(
                    ["az", "logout"],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    st.success("✅ Logged out successfully!")
                    st.rerun()
                else:
                    st.error(f"❌ Logout failed: {result.stderr}")
                    
            except Exception as e:
                st.error(f"❌ Logout error: {e}")
    
    def _render_role_configuration_section(self):
        """Render the role configuration section for managed identity setup."""
        st.header("🔐 Managed Identity Role Configuration")
        st.markdown("""
        **Configure Azure RBAC roles** to enable managed identity authentication for each service.
        This allows your application to authenticate without API keys.
        """)
        
        # Get current user information
        user_principal = self._get_current_user()
        if user_principal:
            st.info(f"Current user: **{user_principal}**")
        else:
            st.warning("⚠️ Azure CLI not logged in. Please run `az login` first.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔍 Azure AI Search")
            search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
            if search_endpoint:
                st.code(search_endpoint)
                search_service = self._extract_service_name_from_url(search_endpoint)
                
                if st.button("🔧 Configure Search Roles", key="search_roles"):
                    self._configure_search_roles(search_service, user_principal)
            else:
                st.error("AZURE_SEARCH_ENDPOINT not configured")
                
            st.subheader("🧠 Azure OpenAI")
            openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            if not openai_endpoint:
                openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT_41", "")
            if openai_endpoint:
                st.code(openai_endpoint)
                openai_service = self._find_resource_name_by_endpoint(openai_endpoint, ["OpenAI"])
                
                if openai_service:
                    if st.button("🔧 Configure OpenAI Roles", key="openai_roles"):
                        self._configure_openai_roles(openai_service, user_principal)
                else:
                    st.warning("Could not find Azure OpenAI resource. Make sure you're logged in and have access.")
            else:
                st.error("AZURE_OPENAI_ENDPOINT not configured")
        
        with col2:
            st.subheader("📄 Document Intelligence")
            docint_endpoint = os.getenv("DOCUMENT_INTEL_ENDPOINT", "")
            if not docint_endpoint:
                docint_endpoint = os.getenv("AZURE_FORMREC_SERVICE", "")
            if docint_endpoint:
                st.code(docint_endpoint)
                docint_service = self._find_resource_name_by_endpoint(docint_endpoint, ["DocumentIntelligence", "FormRecognizer"])
                
                if docint_service:
                    if st.button("🔧 Configure Document Intelligence Roles", key="docint_roles"):
                        self._configure_docint_roles(docint_service, user_principal)
                else:
                    st.warning("Could not find Document Intelligence resource. Make sure you're logged in and have access.")
            else:
                st.error("DOCUMENT_INTEL_ENDPOINT not configured")
                
            st.subheader("ℹ️ Current Authentication Status")
            self._show_auth_status()

    def _get_current_user(self):
        """Get the current Azure CLI user principal."""
        try:
            result = subprocess.run(
                ["az", "account", "show", "--query", "user.name", "-o", "tsv"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def _extract_service_name_from_url(self, url):
        """Extract Azure service name from URL."""
        try:
            # Extract from URL like https://myservice.search.windows.net
            return url.split("://")[1].split(".")[0]
        except Exception:
            return None

    def _find_resource_name_by_endpoint(self, endpoint, resource_types):
        """Find Azure resource name by endpoint."""
        try:
            # Try to extract from endpoint URL
            service_name = self._extract_service_name_from_url(endpoint)
            if service_name:
                return service_name
            return None
        except Exception:
            return None

    def _configure_search_roles(self, service_name, user_principal):
        """Configure Azure Search roles."""
        with st.spinner("Configuring Azure Search roles..."):
            try:
                # Required roles for Azure Search
                roles = [
                    "Search Index Data Contributor",
                    "Search Service Contributor"
                ]
                
                success_count = 0
                for role in roles:
                    result = subprocess.run([
                        "az", "role", "assignment", "create",
                        "--role", role,
                        "--assignee", user_principal,
                        "--scope", f"/subscriptions/{self._get_subscription_id()}/resourceGroups/{self._get_resource_group(service_name)}/providers/Microsoft.Search/searchServices/{service_name}"
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        success_count += 1
                        st.success(f"✅ Assigned role: {role}")
                    else:
                        if "already exists" in result.stderr.lower():
                            st.info(f"ℹ️ Role already assigned: {role}")
                            success_count += 1
                        else:
                            st.error(f"❌ Failed to assign role {role}: {result.stderr}")
                
                if success_count == len(roles):
                    st.success("🎉 All Azure Search roles configured successfully!")
                else:
                    st.warning("⚠️ Some role assignments may have failed. Check the messages above.")
                    
            except Exception as e:
                st.error(f"❌ Error configuring roles: {e}")

    def _configure_openai_roles(self, service_name, user_principal):
        """Configure Azure OpenAI roles."""
        with st.spinner("Configuring Azure OpenAI roles..."):
            try:
                # Required roles for Azure OpenAI
                roles = [
                    "Cognitive Services OpenAI User",
                    "Cognitive Services User"
                ]
                
                success_count = 0
                for role in roles:
                    result = subprocess.run([
                        "az", "role", "assignment", "create",
                        "--role", role,
                        "--assignee", user_principal,
                        "--scope", f"/subscriptions/{self._get_subscription_id()}/resourceGroups/{self._get_resource_group(service_name)}/providers/Microsoft.CognitiveServices/accounts/{service_name}"
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        success_count += 1
                        st.success(f"✅ Assigned role: {role}")
                    else:
                        if "already exists" in result.stderr.lower():
                            st.info(f"ℹ️ Role already assigned: {role}")
                            success_count += 1
                        else:
                            st.error(f"❌ Failed to assign role {role}: {result.stderr}")
                
                if success_count == len(roles):
                    st.success("🎉 All Azure OpenAI roles configured successfully!")
                else:
                    st.warning("⚠️ Some role assignments may have failed. Check the messages above.")
                    
            except Exception as e:
                st.error(f"❌ Error configuring roles: {e}")

    def _configure_docint_roles(self, service_name, user_principal):
        """Configure Document Intelligence roles."""
        with st.spinner("Configuring Document Intelligence roles..."):
            try:
                # Required roles for Document Intelligence
                roles = [
                    "Cognitive Services User"
                ]
                
                success_count = 0
                for role in roles:
                    result = subprocess.run([
                        "az", "role", "assignment", "create",
                        "--role", role,
                        "--assignee", user_principal,
                        "--scope", f"/subscriptions/{self._get_subscription_id()}/resourceGroups/{self._get_resource_group(service_name)}/providers/Microsoft.CognitiveServices/accounts/{service_name}"
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        success_count += 1
                        st.success(f"✅ Assigned role: {role}")
                    else:
                        if "already exists" in result.stderr.lower():
                            st.info(f"ℹ️ Role already assigned: {role}")
                            success_count += 1
                        else:
                            st.error(f"❌ Failed to assign role {role}: {result.stderr}")
                
                if success_count == len(roles):
                    st.success("🎉 All Document Intelligence roles configured successfully!")
                else:
                    st.warning("⚠️ Some role assignments may have failed. Check the messages above.")
                    
            except Exception as e:
                st.error(f"❌ Error configuring roles: {e}")

    def _get_subscription_id(self):
        """Get current subscription ID."""
        try:
            result = subprocess.run(
                ["az", "account", "show", "--query", "id", "-o", "tsv"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def _get_resource_group(self, resource_name):
        """Get resource group for a given resource."""
        try:
            # Try to find the resource group by resource name
            result = subprocess.run([
                "az", "resource", "list",
                "--name", resource_name,
                "--query", "[0].resourceGroup",
                "-o", "tsv"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return "default-resource-group"  # Fallback
        except Exception:
            return "default-resource-group"  # Fallback

    def _show_auth_status(self):
        """Show current authentication status for all services."""
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

    def _render_environment_validation_section(self):
        """Render environment configuration validation section."""
        st.subheader("🔧 Environment Configuration Validation")
        
        if st.button("🔍 Validate .env Configuration"):
            with st.spinner("Validating environment configuration..."):
                # Import and use the validation from private endpoint health checker
                from .private_endpoint_health_checker import PrivateEndpointHealthChecker
                
                validator = PrivateEndpointHealthChecker()
                validation_result = validator.validate_env_configuration()
                guidance = validator.generate_env_guidance(validation_result)
                
                # Store results in session state
                st.session_state['env_validation_result'] = validation_result
                st.session_state['env_guidance'] = guidance
        
        # Display validation results if available
        if 'env_validation_result' in st.session_state:
            validation_result = st.session_state['env_validation_result']
            guidance = st.session_state['env_guidance']
            
            # Show overall status
            if validation_result['is_configuration_complete']:
                st.success("✅ Environment configuration is complete!")
            else:
                st.warning(f"⚠️ Environment configuration needs attention: {len(validation_result['missing_required'])} required variables missing")
            
            # Show summary stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Present Variables", len(validation_result['present_vars']))
            with col2:
                st.metric("Missing Required", len(validation_result['missing_required']))
            with col3:
                st.metric("Authentication Method", validation_result['auth_method'].replace('_', ' ').title())
            
            # Show guidance message
            st.markdown(guidance['guidance_message'])
            
            # Show missing variables if any
            if validation_result['missing_required']:
                with st.expander("❌ Missing Required Variables", expanded=True):
                    for var in validation_result['missing_required']:
                        var_def = validation_result['var_definitions'][var]
                        st.markdown(f"**`{var}`** - {var_def['description']}")
                        st.code(f"Example: {var}={var_def['example']}")
            
            # Show authentication recommendations
            with st.expander("🔐 Authentication Methods", expanded=False):
                for method, details in guidance['auth_recommendations'].items():
                    status = "✅ Recommended" if details['recommended'] else "ℹ️ Available"
                    st.markdown(f"**{method.replace('_', ' ').title()}** - {status}")
                    st.markdown(f"- {details['description']}")
                    st.markdown(f"- Setup: {details['setup_required']}")
                    st.markdown("")
            
            # Show sample .env content
            with st.expander("📄 Sample .env File Content", expanded=False):
                st.code(guidance['sample_env_content'], language='bash')
        else:
            st.info("Click 'Validate .env Configuration' to check your environment setup.")
