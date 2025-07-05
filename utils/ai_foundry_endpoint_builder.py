#!/usr/bin/env python3
"""
AI Foundry Endpoint Builder
Helper utilities to construct AI Foundry project endpoints from account and project names.
"""

import logging
from typing import Dict, List, Tuple, Optional
from services.ai_foundry_discovery import AIFoundryDiscoveryService

logger = logging.getLogger(__name__)

class AIFoundryEndpointBuilder:
    """Helper class for building AI Foundry project endpoints."""
    
    def __init__(self):
        """Initialize the endpoint builder."""
        self.discovery_service = AIFoundryDiscoveryService()
    
    def discover_ai_services_accounts(self) -> List[Dict[str, str]]:
        """
        Discover all AI Services accounts that could potentially host AI Foundry projects.
        
        Returns:
            List of account information dictionaries with name and endpoint
        """
        try:
            # Discover all AI Foundry accounts
            accounts = self.discovery_service.discover_ai_foundry_accounts()
            
            # Extract account names and endpoints
            ai_services_accounts = []
            for account in accounts:
                if account.get('resource_type') == 'Microsoft.CognitiveServices/accounts':
                    ai_services_accounts.append({
                        'name': account['name'],
                        'endpoint': account['endpoint'],
                        'location': account['location'],
                        'resource_group': account['resource_group']
                    })
            
            logger.info(f"Found {len(ai_services_accounts)} AI Services accounts")
            return ai_services_accounts
            
        except Exception as e:
            logger.error(f"Error discovering AI Services accounts: {e}")
            return []
    
    def build_project_endpoint(self, account_name: str, project_name: str) -> str:
        """
        Build a complete PROJECT_ENDPOINT from account name and project name.
        
        Args:
            account_name: Name of the AI Services account (e.g., 'aiagenticservicesfgtt')
            project_name: Name of the project (e.g., 'agentic-rag')
        
        Returns:
            Complete project endpoint URL
        """
        # The AI Foundry project endpoint format is always:
        # https://<account-name>.services.ai.azure.com/api/projects/<project-name>
        return f"https://{account_name}.services.ai.azure.com/api/projects/{project_name}"
    
    def validate_project_endpoint(self, project_endpoint: str) -> Tuple[bool, str]:
        """
        Validate that a constructed project endpoint is accessible.
        
        Args:
            project_endpoint: The complete project endpoint URL
        
        Returns:
            Tuple of (is_valid, message)
        """
        return self.discovery_service.validate_project_endpoint(project_endpoint)
    
    def parse_project_endpoint(self, project_endpoint: str) -> Dict[str, str]:
        """
        Parse a project endpoint to extract account name and project name.
        
        Args:
            project_endpoint: Complete project endpoint URL
        
        Returns:
            Dictionary with parsed components
        """
        return self.discovery_service.parse_project_endpoint(project_endpoint)
    
    def get_account_suggestions(self, partial_name: str = "") -> List[str]:
        """
        Get account name suggestions based on partial input.
        
        Args:
            partial_name: Partial account name for filtering
        
        Returns:
            List of matching account names
        """
        try:
            accounts = self.discover_ai_services_accounts()
            
            if not partial_name:
                return [account['name'] for account in accounts]
            
            # Filter accounts that contain the partial name
            filtered = [
                account['name'] 
                for account in accounts 
                if partial_name.lower() in account['name'].lower()
            ]
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error getting account suggestions: {e}")
            return []
    
    def build_endpoint_from_discovery(self, account_name: str, project_name: str) -> Tuple[Optional[str], str]:
        """
        Build project endpoint by first discovering the account to ensure it exists.
        
        Args:
            account_name: Name of the AI Services account
            project_name: Name of the project
        
        Returns:
            Tuple of (endpoint_url, status_message)
        """
        try:
            # First, verify the account exists
            accounts = self.discover_ai_services_accounts()
            account_found = None
            
            for account in accounts:
                if account['name'].lower() == account_name.lower():
                    account_found = account
                    break
            
            if not account_found:
                available_accounts = [acc['name'] for acc in accounts]
                return None, f"Account '{account_name}' not found. Available accounts: {available_accounts}"
            
            # Build the endpoint
            project_endpoint = self.build_project_endpoint(account_name, project_name)
            
            # Validate the endpoint is accessible
            is_valid, validation_message = self.validate_project_endpoint(project_endpoint)
            
            if is_valid:
                return project_endpoint, f"✅ Project endpoint validated successfully"
            else:
                return project_endpoint, f"⚠️ Endpoint constructed but validation failed: {validation_message}"
            
        except Exception as e:
            logger.error(f"Error building endpoint from discovery: {e}")
            return None, f"Error during endpoint construction: {str(e)}"


# Global instance for easy importing
ai_foundry_endpoint_builder = AIFoundryEndpointBuilder()
