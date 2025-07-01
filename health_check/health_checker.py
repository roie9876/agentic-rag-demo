#!/usr/bin/env python3
"""
Health Check Module for Agentic RAG Demo
========================================
This module contains all health check functionality extracted from the main application.
"""

import os
import logging
from typing import Tuple, Dict, Any, Optional, List, Union

# Azure imports
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from openai import AzureOpenAI

# Import RBAC manager for automated role assignment
try:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from services.azure_rbac_manager import AzureRBACManager
except ImportError as e:
    logging.warning(f"Could not import AzureRBACManager: {e}")
    AzureRBACManager = None


class HealthChecker:
    """
    Health checker for all services used by the Agentic RAG Demo.
    """
    
    def __init__(self):
        """Initialize the health checker."""
        pass
    
    def _search_credential(self) -> Union[AzureKeyCredential, DefaultAzureCredential]:
        """
        Return Azure credential based on env:
        • If AZURE_SEARCH_KEY is set → key auth
        • else → DefaultAzureCredential (AAD)
        """
        key = os.getenv("AZURE_SEARCH_KEY", "").strip()
        if key:
            return AzureKeyCredential(key)
        return DefaultAzureCredential()
    
    def _rbac_enabled(self, service_url: str) -> bool:
        """
        Quick probe: return True if Role‑based access control is enabled on the
        Search service (Authentication mode = RBAC).
        """
        try:
            import httpx
            resp = httpx.get(
                f"{service_url}/indexes",
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            # RBAC → 401; API key → 403
            return resp.status_code == 401
        except Exception:
            return False
    
    def _init_openai_for_health_check(self) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Initialize OpenAI client for health check using the same logic as the rest of the app.
        Tries all available endpoint configurations in order: _41, _4o, and base.
        """
        clients = []
        models_tried = []
        
        # Try the endpoint variations in priority order
        for suffix in ["_41", "_4o", ""]:
            endpoint = os.getenv(f"AZURE_OPENAI_ENDPOINT{suffix}", "").strip()
            key = os.getenv(f"AZURE_OPENAI_KEY{suffix}", "").strip()
            api_version = os.getenv(f"AZURE_OPENAI_API_VERSION{suffix}", "2024-05-01-preview").strip()
            deployment = os.getenv(f"AZURE_OPENAI_DEPLOYMENT{suffix}", "").strip()
            
            if endpoint and (key or os.getenv("AZURE_TENANT_ID")):
                models_tried.append(f"AZURE_OPENAI_ENDPOINT{suffix}")
                try:
                    # If key is available, use key auth
                    if key:
                        client = AzureOpenAI(
                            azure_endpoint=endpoint,
                            api_key=key,
                            api_version=api_version
                        )
                    else:
                        # Use AAD auth as fallback
                        aad = get_bearer_token_provider(
                            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
                        )
                        client = AzureOpenAI(
                            azure_endpoint=endpoint,
                            azure_ad_token_provider=aad,
                            api_version=api_version
                        )
                        
                    # Verify the client works by listing models
                    models = list(client.models.list())
                    clients.append({
                        "client": client,
                        "endpoint_var": f"AZURE_OPENAI_ENDPOINT{suffix}",
                        "endpoint": endpoint,
                        "models": models,
                        "deployment": deployment
                    })
                except Exception:
                    pass
        
        if not clients:
            return None, models_tried
        
        # Return the first working client
        return clients[0], models_tried
    
    def check_openai_health(self) -> Tuple[bool, str]:
        """Check if OpenAI service is available and responsive."""
        try:
            client_info, models_tried = self._init_openai_for_health_check()
            
            if not client_info:
                if not models_tried:
                    return False, "❌ No OpenAI endpoints configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY environment variables."
                else:
                    return False, f"❌ Could not connect to any OpenAI endpoints. Tried: {', '.join(models_tried)}"
            
            # Successfully connected
            model_count = len(client_info["models"])
            model_names = ", ".join([m.id for m in client_info["models"][:3]])
            if model_count > 3:
                model_names += f", and {model_count - 3} more"
            
            endpoint_var = client_info["endpoint_var"]
            deployment = client_info["deployment"]
            deployment_info = f" (deployment: {deployment})" if deployment else ""
            
            return True, f"✅ Connected successfully via {endpoint_var}{deployment_info}. Found {model_count} models: {model_names}"
                
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def check_ai_search_health(self) -> Tuple[bool, str]:
        """Check if Azure AI Search service is available and responsive."""
        try:
            search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").strip()
            if not search_endpoint:
                return False, "Missing AZURE_SEARCH_ENDPOINT"
            
            credential = self._search_credential()
            client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
            
            # Try to list indexes as a simple health check
            indexes = list(client.list_indexes())
            index_count = len(indexes)
            
            auth_mode = "Managed Identity (RBAC)" if not os.getenv("AZURE_SEARCH_KEY") else "API Key"
            rbac_status = "🟢 Enabled" if self._rbac_enabled(search_endpoint) else "🔴 Disabled"
            
            return True, f"✅ Connected successfully. Found {index_count} indexes. Auth: {auth_mode}, RBAC: {rbac_status}"
            
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def check_document_intelligence_health(self) -> Tuple[bool, str]:
        """Check if Document Intelligence service is available and responsive."""
        try:
            from tools.document_intelligence_client import DocumentIntelligenceClientWrapper
            
            # Check for new variable names first, fall back to legacy names
            endpoint = os.getenv("DOCUMENT_INTEL_ENDPOINT", "").strip()
            key = os.getenv("DOCUMENT_INTEL_KEY", "").strip()
            
            # Fall back to legacy variable names if needed
            if not endpoint:
                endpoint = os.getenv("AZURE_FORMREC_SERVICE", "").strip()
            if not key:
                key = os.getenv("AZURE_FORMREC_KEY", "").strip()
                
            # Only require endpoint - key is optional for managed identity
            if not endpoint:
                return False, "Missing Document Intelligence configuration. Set DOCUMENT_INTEL_ENDPOINT or the legacy AZURE_FORMREC_SERVICE environment variable."
            
            # Force reload the module to pick up env var changes
            import importlib
            import tools.document_intelligence_client
            importlib.reload(tools.document_intelligence_client)
            from tools.document_intelligence_client import DocumentIntelligenceClientWrapper
            
            # Initialize client
            docint_wrapper = DocumentIntelligenceClientWrapper()
            
            if not docint_wrapper.client:
                return False, f"❌ Failed to initialize Document Intelligence client with endpoint {endpoint}"
                
            # Get endpoint information
            api_version = "Unknown"
            if hasattr(docint_wrapper, 'api_version'):
                api_version = docint_wrapper.api_version
            
            # Check if Document Intelligence 4.0 API is available
            docint_40_status = "✅ Available" if docint_wrapper.docint_40_api else "❌ Not Available"
            
            # Build informational message
            features = []
            
            # Check document formats support
            if docint_wrapper.docint_40_api:
                features.append("DOCX/PPTX parsing supported")
            else:
                features.append("DOCX/PPTX parsing may be limited")
            
            # Check if we can analyze basic documents
            if hasattr(docint_wrapper.client, 'begin_analyze_document'):
                features.append("Basic document analysis available")
            
            # Check for layout analysis
            if hasattr(docint_wrapper.client, 'begin_analyze_layout'):
                features.append("Layout analysis available")
            
            features_str = ", ".join(features)
            
            # Format a nice message
            api_info = f"API Version: {api_version}"
            return True, f"✅ Connected successfully to {endpoint}. Doc Intelligence 4.0: {docint_40_status}. {api_info}. Features: {features_str}"
            
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def check_rbac_health(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Check RBAC configuration for Azure AI Search to Azure OpenAI vectorization.
        Returns (is_healthy, message, fix_info).
        """
        if not AzureRBACManager:
            return False, "❌ RBAC manager not available", None
            
        try:
            rbac_manager = AzureRBACManager()
            
            # Check if this is a private setup that needs RBAC
            search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").strip()
            openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT_41", "").strip()
            if not openai_endpoint:
                openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
            
            if not search_endpoint or not openai_endpoint:
                return False, "❌ Missing Azure Search or OpenAI endpoint configuration", None
            
            # Check if we're using managed identity for search (no API key)
            search_key = os.getenv("AZURE_SEARCH_KEY", "").strip()
            if search_key:
                return True, "✅ Using API key authentication - RBAC not required", None
            
            # For managed identity setups, check RBAC
            status = rbac_manager.check_rbac_status()
            
            if status["rbac_configured"]:
                return True, f"✅ RBAC properly configured - {status['message']}", status
            else:
                # RBAC is missing but can be fixed
                if status["can_fix"]:
                    return False, f"⚠️ RBAC needs configuration - {status['message']}", status
                else:
                    return False, f"❌ RBAC configuration error - {status['message']}", status
                    
        except Exception as e:
            return False, f"❌ Error checking RBAC: {str(e)}", None
    
    def check_all_services(self) -> Tuple[Dict[str, Tuple[bool, str]], bool, Dict[str, str]]:
        """
        Check all services and return results with troubleshooting information.
        Returns (results_dict, all_healthy, troubleshooting_dict).
        """
        results = {}
        troubleshooting = {}
        
        # Check OpenAI service
        status, message = self.check_openai_health()
        results["OpenAI"] = (status, message)
        if not status:
            troubleshooting["OpenAI"] = """
            **Common OpenAI Issues:**
            1. Check AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY environment variables
            2. Verify your Azure OpenAI resource is deployed and accessible
            3. Check if you have the correct API version (2024-05-01-preview recommended)
            4. For managed identity setups, ensure proper role assignments
            """
        
        # Check Azure AI Search service
        status, message = self.check_ai_search_health()
        results["Azure AI Search"] = (status, message)
        if not status:
            troubleshooting["Azure AI Search"] = """
            **Common Azure AI Search Issues:**
            1. Check AZURE_SEARCH_ENDPOINT environment variable
            2. For API key auth: Set AZURE_SEARCH_KEY
            3. For managed identity: Ensure your app has proper permissions
            4. Verify the search service is running and accessible
            """
        
        # Check Document Intelligence service
        status, message = self.check_document_intelligence_health()
        results["Document Intelligence"] = (status, message)
        if not status:
            troubleshooting["Document Intelligence"] = """
            **Common Document Intelligence Issues:**
            1. Check DOCUMENT_INTEL_ENDPOINT or AZURE_FORMREC_ENDPOINT environment variables
            2. For API key auth: Set DOCUMENT_INTEL_KEY or AZURE_FORMREC_KEY
            3. For managed identity: Ensure proper role assignments
            4. Verify your Document Intelligence resource supports your required features
            """
        
        # Check RBAC configuration (only for managed identity setups)
        search_key = os.getenv("AZURE_SEARCH_KEY", "").strip()
        if not search_key:  # Only check RBAC for managed identity setups
            status, message, rbac_info = self.check_rbac_health()
            results["RBAC Configuration"] = (status, message)
            if not status:
                troubleshooting["RBAC Configuration"] = """
                **RBAC Configuration Issues:**
                1. Azure AI Search needs roles to access Azure OpenAI in private mode
                2. Required roles: "Cognitive Services OpenAI User", "Azure AI Developer", "Reader"
                3. Use the automatic fix button below or assign roles manually
                4. Ensure Azure AI Search has managed identity enabled
                """
        
        # Determine overall health
        all_healthy = all(status for status, _ in results.values())
        
        return results, all_healthy, troubleshooting

    def fix_rbac_health(self) -> Tuple[bool, str]:
        """
        Automatically fix RBAC configuration issues.
        Returns (success, message).
        """
        if not AzureRBACManager:
            return False, "❌ RBAC manager not available"
            
        try:
            rbac_manager = AzureRBACManager()
            success, message = rbac_manager.setup_search_to_openai_rbac()
            
            if success:
                return True, f"✅ RBAC configuration fixed - {message}"
            else:
                return False, f"❌ Failed to fix RBAC - {message}"
                
        except Exception as e:
            return False, f"❌ Error fixing RBAC: {str(e)}"
