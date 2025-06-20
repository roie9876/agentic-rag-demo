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
            
            auth_mode = "Azure AD" if not os.getenv("AZURE_SEARCH_KEY") else "API Key"
            rbac_status = "🟢 Enabled" if self._rbac_enabled(search_endpoint) else "🔴 Disabled"
            
            return True, f"✅ Connected successfully. Found {index_count} indexes. Auth: {auth_mode}, RBAC: {rbac_status}"
            
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def check_document_intelligence_health(self) -> Tuple[bool, str]:
        """Check if Document Intelligence service is available and responsive."""
        try:
            from tools.document_intelligence_client import DocumentIntelligenceClientWrapper
            import importlib
            
            # Force reload the module to pick up our changes
            import tools.document_intelligence_client
            importlib.reload(tools.document_intelligence_client)
            from tools.document_intelligence_client import DocumentIntelligenceClientWrapper
            
            docint_wrapper = DocumentIntelligenceClientWrapper()
            
            if not docint_wrapper.client:
                return False, "❌ Document Intelligence not configured (missing endpoint/key)"
            
            # Get endpoint information
            endpoint = (
                os.getenv("DOCUMENT_INTEL_ENDPOINT") or
                os.getenv("AZURE_FORMREC_SERVICE") or
                os.getenv("AZURE_FORMRECOGNIZER_ENDPOINT") or
                "Unknown"
            )
            
            # Try to get API version information
            api_version = "Unknown"
            if hasattr(docint_wrapper.client, '_config') and hasattr(docint_wrapper.client._config, 'api_version'):
                api_version = getattr(docint_wrapper.client._config, 'api_version', 'Unknown')
            
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
    
    def check_all_services(self) -> Tuple[Dict[str, Tuple[bool, str]], bool, Optional[Dict[str, str]]]:
        """Check health of all services and return summary."""
        results = {
            "OpenAI": self.check_openai_health(),
            "AI Search": self.check_ai_search_health(), 
            "Document Intelligence": self.check_document_intelligence_health()
        }
        
        all_healthy = all(status for status, _ in results.values())
        
        # Add troubleshooting info for failed services
        troubleshooting_info = {}
        if not results["OpenAI"][0]:
            troubleshooting_info["OpenAI"] = (
                "Check that your OpenAI environment variables are set correctly:\n"
                "- Either AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_ENDPOINT_41 should be set\n"
                "- AZURE_OPENAI_KEY should be set\n"
                "- Your app is using AZURE_OPENAI_ENDPOINT_41, ensure the health check can access it\n"
                "- Verify your network connection and firewall settings\n"
                "- Check the API version matches what your endpoint supports\n\n"
                "The app will use the suffix (_41, _4o) endpoints if available, falling back to the base variables."
            )
        if not results["AI Search"][0]:
            troubleshooting_info["AI Search"] = (
                "Check that AZURE_SEARCH_ENDPOINT is set correctly. "
                "If using API key authentication, ensure AZURE_SEARCH_KEY is set."
            )
        if not results["Document Intelligence"][0]:
            troubleshooting_info["Document Intelligence"] = (
                "Check that DOCUMENT_INTEL_ENDPOINT/DOCUMENT_INTEL_KEY or the legacy "
                "AZURE_FORMREC_SERVICE/AZURE_FORMREC_KEY environment variables are set correctly."
            )
        
        return results, all_healthy, troubleshooting_info if troubleshooting_info else None
