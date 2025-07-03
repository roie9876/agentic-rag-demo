#!/usr/bin/env python3
"""
AI Foundry Discovery Service
Handles discovery and management of AI Foundry resources including accounts, hubs, and projects.
"""

import os
import logging
import requests
from typing import Dict, List, Any, Optional, Tuple
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.resource import ResourceManagementClient
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class AIFoundryDiscoveryService:
    """Service for discovering AI Foundry accounts, hubs, and projects."""
    
    def __init__(self):
        """Initialize the AI Foundry Discovery Service."""
        self.credential = DefaultAzureCredential()
        self._subscription_id = None
        self._cognitive_services_client = None
        self._resource_client = None
    
    def set_subscription(self, subscription_id: str) -> None:
        """Set the subscription ID and initialize clients."""
        self._subscription_id = subscription_id
        if subscription_id:
            self._cognitive_services_client = CognitiveServicesManagementClient(
                self.credential, subscription_id
            )
            self._resource_client = ResourceManagementClient(
                self.credential, subscription_id
            )
    
    def get_subscription_id(self) -> Optional[str]:
        """Get the current subscription ID."""
        return self._subscription_id
    
    def list_subscriptions(self) -> List[Dict[str, Any]]:
        """List available Azure subscriptions."""
        try:
            # Get token for Azure Management API
            token = self.credential.get_token("https://management.azure.com/.default")
            
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                'https://management.azure.com/subscriptions?api-version=2020-01-01',
                headers=headers
            )
            
            if response.status_code == 200:
                subscriptions = response.json().get('value', [])
                return [
                    {
                        'id': sub['subscriptionId'],
                        'name': sub['displayName'],
                        'state': sub['state']
                    }
                    for sub in subscriptions
                    if sub['state'] == 'Enabled'
                ]
            else:
                logger.error(f"Failed to list subscriptions: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing subscriptions: {e}")
            return []
    
    def discover_ai_foundry_accounts(self) -> List[Dict[str, Any]]:
        """Discover AI Foundry accounts in the current subscription."""
        if not self._cognitive_services_client:
            return []
        
        try:
            accounts = []
            
            # Get Cognitive Services accounts
            for account in self._cognitive_services_client.accounts.list():
                # Check if it's an AI Services account (multi-service)
                if account.kind in ['AIServices', 'CognitiveServices']:
                    # Get the endpoint - AI Foundry accounts have specific endpoint patterns
                    endpoint = account.properties.endpoint if hasattr(account.properties, 'endpoint') else None
                    
                    # AI Foundry accounts typically have .services.ai.azure.com domains
                    is_ai_foundry = (
                        endpoint and 
                        ('.services.ai.azure.com' in endpoint or 
                         'aiservices' in account.name.lower() or
                         'aifoundry' in account.name.lower() or
                         'foundry' in account.name.lower() or
                         'agentic' in account.name.lower())
                    )
                    
                    if is_ai_foundry or account.kind == 'AIServices':
                        # Transform the endpoint for AI Foundry API format
                        ai_foundry_endpoint = self._transform_to_ai_foundry_endpoint(endpoint, account.name)
                        
                        account_info = {
                            'name': account.name,
                            'resource_group': account.id.split('/')[4],
                            'location': account.location,
                            'kind': account.kind,
                            'sku': account.sku.name if account.sku else 'Unknown',
                            'endpoint': ai_foundry_endpoint,
                            'original_endpoint': endpoint,
                            'type': 'AI Foundry Account',
                            'resource_type': 'Microsoft.CognitiveServices/accounts',
                            'id': account.id,
                            'subscription_id': self._subscription_id,
                            'status': 'Available'
                        }
                        accounts.append(account_info)
            
            logger.info(f"Discovered {len(accounts)} AI Foundry accounts")
            return accounts
            
        except Exception as e:
            logger.error(f"Error discovering AI Foundry accounts: {e}")
            return []
    
    def discover_ai_foundry_hubs(self) -> List[Dict[str, Any]]:
        """Discover AI Foundry hubs (ML workspaces) in the current subscription."""
        if not self._resource_client:
            return []
        
        try:
            hubs = []
            
            # Look for Machine Learning workspaces which can be AI Foundry hubs
            resources = self._resource_client.resources.list(
                filter="resourceType eq 'Microsoft.MachineLearningServices/workspaces'"
            )
            
            for resource in resources:
                # Get detailed resource information
                try:
                    resource_details = self._resource_client.resources.get_by_id(
                        resource.id, api_version='2023-04-01'
                    )
                    
                    # Extract endpoint if available
                    endpoint = None
                    if hasattr(resource_details, 'properties') and resource_details.properties:
                        endpoint = getattr(resource_details.properties, 'mlFlowTrackingUri', None)
                        if not endpoint:
                            endpoint = getattr(resource_details.properties, 'workspaceUrl', None)
                
                    hub_info = {
                        'name': resource.name,
                        'resource_group': resource.id.split('/')[4],
                        'location': resource.location,
                        'type': 'AI Foundry Hub',
                        'resource_type': 'Microsoft.MachineLearningServices/workspaces',
                        'id': resource.id,
                        'kind': getattr(resource, 'kind', 'MLWorkspace'),
                        'endpoint': endpoint,
                        'subscription_id': self._subscription_id,
                        'status': 'Available'
                    }
                    hubs.append(hub_info)
                    
                except Exception as detail_error:
                    logger.warning(f"Could not get details for hub {resource.name}: {detail_error}")
                    # Add basic info anyway
                    hub_info = {
                        'name': resource.name,
                        'resource_group': resource.id.split('/')[4],
                        'location': resource.location,
                        'type': 'AI Foundry Hub',
                        'resource_type': 'Microsoft.MachineLearningServices/workspaces',
                        'id': resource.id,
                        'kind': getattr(resource, 'kind', 'MLWorkspace'),
                        'endpoint': None,
                        'subscription_id': self._subscription_id,
                        'status': 'Available'
                    }
                    hubs.append(hub_info)
            
            logger.info(f"Discovered {len(hubs)} AI Foundry hubs")
            return hubs
            
        except Exception as e:
            logger.error(f"Error discovering AI Foundry hubs: {e}")
            return []
    
    def get_projects_for_account(self, account_endpoint: str) -> List[Dict[str, Any]]:
        """Get projects for a specific AI Foundry account."""
        try:
            # Get token for AI Foundry
            token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
            
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            # Try different API endpoints for projects
            project_endpoints = [
                f"{account_endpoint}/api/projects",
                f"{account_endpoint}/projects",
                f"{account_endpoint}/api/v1/projects"
            ]
            
            for endpoint in project_endpoints:
                try:
                    response = requests.get(endpoint, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        projects_data = response.json()
                        
                        # Handle different response formats
                        if isinstance(projects_data, list):
                            projects = projects_data
                        elif isinstance(projects_data, dict) and 'value' in projects_data:
                            projects = projects_data['value']
                        elif isinstance(projects_data, dict) and 'projects' in projects_data:
                            projects = projects_data['projects']
                        else:
                            projects = []
                        
                        return [
                            {
                                'name': project.get('name', 'Unknown'),
                                'id': project.get('id', ''),
                                'description': project.get('description', ''),
                                'created_at': project.get('createdAt', ''),
                                'endpoint': f"{account_endpoint}/api/projects/{project.get('name', '')}"
                            }
                            for project in projects
                        ]
                        
                except requests.RequestException:
                    continue
            
            # If no projects found, return empty list (not an error)
            return []
            
        except Exception as e:
            logger.error(f"Error getting projects for account {account_endpoint}: {e}")
            return []
    
    def get_projects_for_hub(self, hub_resource_id: str) -> List[Dict[str, Any]]:
        """Get projects for a specific AI Foundry hub."""
        try:
            # For ML workspaces, we need to use the ML management API
            # This is a placeholder - implement based on actual ML workspace API
            logger.info(f"Getting projects for hub: {hub_resource_id}")
            
            # TODO: Implement actual hub project discovery
            # This would typically involve calling the ML workspace API
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting projects for hub {hub_resource_id}: {e}")
            return []
    
    def validate_project_endpoint(self, project_endpoint: str) -> Tuple[bool, str]:
        """Validate that a project endpoint is accessible."""
        try:
            # Get token for AI Foundry
            token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
            
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            # Try to access the project endpoint
            response = requests.get(project_endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return True, "Project endpoint is accessible"
            elif response.status_code == 404:
                return False, "Project not found or does not exist"
            elif response.status_code == 403:
                return False, "Access denied - check RBAC permissions"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:100]}"
                
        except requests.RequestException as e:
            return False, f"Connection error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def parse_project_endpoint(self, endpoint: str) -> Dict[str, str]:
        """Parse a project endpoint to extract components."""
        try:
            # Example: https://aiagenticservicesfgtt.services.ai.azure.com/api/projects/agentic-rag
            parts = endpoint.split('/')
            
            if len(parts) < 4:
                return {}
            
            # Extract the foundry hostname
            foundry_hostname = parts[2]
            
            # Extract project name from the last part
            project_name = parts[-1] if parts[-1] else "unknown"
            
            # Extract foundry name (first part of hostname)
            foundry_name = foundry_hostname.split('.')[0]
            
            return {
                'foundry_hostname': foundry_hostname,
                'foundry_name': foundry_name,
                'project_name': project_name,
                'base_url': f"https://{foundry_hostname}",
                'projects_api': f"https://{foundry_hostname}/api/projects"
            }
            
        except Exception as e:
            logger.error(f"Error parsing endpoint {endpoint}: {e}")
            return {}
    
    def create_project_endpoint_url(self, foundry_hostname: str, project_name: str) -> str:
        """Create a project endpoint URL from components."""
        return f"https://{foundry_hostname}/api/projects/{project_name}"
    
    def get_account_info(self, account_endpoint: str) -> Dict[str, Any]:
        """Get detailed information about an AI Foundry account."""
        try:
            # Get token for AI Foundry
            token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
            
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            # Try to get account info
            response = requests.get(account_endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            logger.error(f"Error getting account info for {account_endpoint}: {e}")
            return {'error': str(e)}
    
    def _transform_to_ai_foundry_endpoint(self, endpoint: str, account_name: str) -> str:
        """Transform a Cognitive Services endpoint to AI Foundry format."""
        if not endpoint:
            # If no endpoint, try to construct one based on account name
            return f"https://{account_name}.services.ai.azure.com"
        
        # If it's already an AI Foundry endpoint, return as is
        if '.services.ai.azure.com' in endpoint:
            return endpoint
        
        # Transform from cognitiveservices.azure.com to services.ai.azure.com
        if '.cognitiveservices.azure.com' in endpoint:
            # Extract the account name from the endpoint
            account_from_endpoint = endpoint.split('//')[1].split('.')[0]
            return f"https://{account_from_endpoint}.services.ai.azure.com"
        
        # If it's a different format, try to use the account name
        return f"https://{account_name}.services.ai.azure.com"
    
    def discover_all_ai_foundry_resources(self) -> List[Dict[str, Any]]:
        """Discover both AI Foundry accounts and hubs."""
        all_resources = []
        
        # Discover accounts
        accounts = self.discover_ai_foundry_accounts()
        all_resources.extend(accounts)
        
        # Discover hubs
        hubs = self.discover_ai_foundry_hubs()
        all_resources.extend(hubs)
        
        logger.info(f"Total AI Foundry resources discovered: {len(all_resources)}")
        return all_resources


# Global instance
ai_foundry_discovery = AIFoundryDiscoveryService()
