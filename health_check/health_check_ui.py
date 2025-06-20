#!/usr/bin/env python3
"""
Health Check UI Module for Agentic RAG Demo
===========================================
This module contains the UI components for the health check functionality.
"""

import os
import streamlit as st
from .health_checker import HealthChecker


class HealthCheckUI:
    """
    UI handler for health check functionality.
    """
    
    def __init__(self):
        """Initialize the health check UI."""
        self.health_checker = HealthChecker()
    
    def render_health_check_tab(self):
        """Render the complete health check tab."""
        st.header("🩺 Service Health Check")
        
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
