"""
AI Foundry Helper Utilities
Utility functions and classes to support AI Foundry operations
"""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

class AIFoundryHelper:
    """Helper class for AI Foundry operations"""
    
    @staticmethod
    def parse_project_endpoint(endpoint: str) -> Dict[str, str]:
        """
        Parse an AI Foundry project endpoint URL
        
        Args:
            endpoint: Project endpoint URL like https://aiagenticservicesfgtt.services.ai.azure.com/api/projects/agentic-rag
            
        Returns:
            Dict with parsed components: foundry_name, hostname, project_name, base_url
        """
        try:
            parsed = urlparse(endpoint)
            hostname = parsed.hostname
            
            # Extract foundry name (first part of hostname)
            foundry_name = hostname.split('.')[0] if hostname else ""
            
            # Extract project name from path
            path_parts = parsed.path.strip('/').split('/')
            project_name = path_parts[-1] if path_parts else ""
            
            # Base API URL
            base_url = f"{parsed.scheme}://{hostname}"
            
            return {
                "foundry_name": foundry_name,
                "hostname": hostname,
                "project_name": project_name,
                "base_url": base_url,
                "full_endpoint": endpoint
            }
        except Exception as e:
            logger.error(f"Error parsing project endpoint {endpoint}: {e}")
            return {}
    
    @staticmethod
    def build_ai_foundry_urls(foundry_name: str, project_name: str = None) -> Dict[str, str]:
        """
        Build AI Foundry service URLs
        
        Args:
            foundry_name: Name of the AI Foundry account
            project_name: Optional project name
            
        Returns:
            Dict with various AI Foundry URLs
        """
        base_url = f"https://{foundry_name}.services.ai.azure.com"
        
        urls = {
            "base": base_url,
            "projects": f"{base_url}/api/projects",
            "agents": f"{base_url}/api/agents"
        }
        
        if project_name:
            urls.update({
                "project": f"{base_url}/api/projects/{project_name}",
                "project_agents": f"{base_url}/api/projects/{project_name}/agents"
            })
        
        return urls
    
    @staticmethod
    def extract_foundry_name_from_endpoint(endpoint: str) -> str:
        """Extract foundry name from an endpoint URL"""
        parsed = AIFoundryHelper.parse_project_endpoint(endpoint)
        return parsed.get("foundry_name", "")
    
    @staticmethod
    def extract_project_name_from_endpoint(endpoint: str) -> str:
        """Extract project name from an endpoint URL"""
        parsed = AIFoundryHelper.parse_project_endpoint(endpoint)
        return parsed.get("project_name", "")
    
    @staticmethod
    def validate_foundry_endpoint(endpoint: str) -> Tuple[bool, str]:
        """
        Validate that an endpoint looks like a valid AI Foundry URL
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not endpoint:
            return False, "Endpoint is empty"
        
        if not endpoint.startswith("https://"):
            return False, "Endpoint must start with https://"
        
        parsed = AIFoundryHelper.parse_project_endpoint(endpoint)
        if not parsed.get("hostname"):
            return False, "Invalid URL format"
        
        if not parsed.get("hostname", "").endswith(".services.ai.azure.com"):
            return False, "Endpoint must be an AI Foundry services URL (*.services.ai.azure.com)"
        
        return True, "Valid AI Foundry endpoint"
    
    @staticmethod
    def get_azure_token_for_ai_foundry() -> Optional[str]:
        """
        Get Azure access token for AI Foundry operations
        
        Returns:
            Access token string or None if failed
        """
        try:
            credential = DefaultAzureCredential()
            
            # Try different scopes for AI Foundry
            scopes_to_try = [
                "https://cognitiveservices.azure.com/.default",
                "https://ml.azure.com/.default",
                "https://management.azure.com/.default"
            ]
            
            for scope in scopes_to_try:
                try:
                    token = credential.get_token(scope)
                    logger.info(f"Successfully got token with scope: {scope}")
                    return token.token
                except Exception as scope_error:
                    logger.debug(f"Failed with scope {scope}: {scope_error}")
                    continue
            
            logger.error("All token scopes failed")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get Azure token: {e}")
            return None
    
    @staticmethod
    def format_resource_name(name: str) -> str:
        """Format a resource name for display"""
        if not name:
            return "Unknown"
        
        # Replace underscores and hyphens with spaces, capitalize words
        formatted = name.replace("_", " ").replace("-", " ")
        return " ".join(word.capitalize() for word in formatted.split())
    
    @staticmethod
    def mask_sensitive_value(value: str, mask_char: str = "•", visible_chars: int = 4) -> str:
        """
        Mask sensitive values like API keys for display
        
        Args:
            value: Value to mask
            mask_char: Character to use for masking
            visible_chars: Number of characters to show at the end
            
        Returns:
            Masked value
        """
        if not value or len(value) <= visible_chars:
            return mask_char * 8
        
        return mask_char * (len(value) - visible_chars) + value[-visible_chars:]
    
    @staticmethod
    def get_subscription_from_resource_id(resource_id: str) -> str:
        """Extract subscription ID from Azure resource ID"""
        if not resource_id:
            return ""
        
        # Resource ID format: /subscriptions/{subscription-id}/resourceGroups/{resource-group}/...
        parts = resource_id.split('/')
        try:
            sub_index = parts.index('subscriptions')
            if sub_index + 1 < len(parts):
                return parts[sub_index + 1]
        except (ValueError, IndexError):
            pass
        
        return ""
    
    @staticmethod
    def format_api_error(error_response: Dict[str, Any]) -> str:
        """Format API error response for user display"""
        if not error_response:
            return "Unknown API error"
        
        # Extract error message from common API error formats
        if 'error' in error_response:
            error = error_response['error']
            if isinstance(error, dict):
                message = error.get('message', '')
                code = error.get('code', '')
                if message and code:
                    return f"{code}: {message}"
                elif message:
                    return message
                elif code:
                    return f"Error: {code}"
        
        # Fallback to status or generic message
        if 'message' in error_response:
            return error_response['message']
        
        if 'status' in error_response:
            return f"HTTP {error_response['status']}"
        
        return "API error occurred"

# Compatibility aliases
ai_foundry_helper = AIFoundryHelper()

def parse_project_endpoint(endpoint: str) -> Dict[str, str]:
    """Compatibility function"""
    return AIFoundryHelper.parse_project_endpoint(endpoint)

def validate_foundry_endpoint(endpoint: str) -> Tuple[bool, str]:
    """Compatibility function"""
    return AIFoundryHelper.validate_foundry_endpoint(endpoint)

def get_azure_token_for_ai_foundry() -> Optional[str]:
    """Compatibility function"""
    return AIFoundryHelper.get_azure_token_for_ai_foundry()
