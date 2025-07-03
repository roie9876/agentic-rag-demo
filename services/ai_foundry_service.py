"""
AI Foundry Service Module
------------------------
Service for managing AI Foundry Hubs, projects, and agents.

IMPORTANT: This service only supports AI Foundry Hubs (Microsoft.MachineLearningServices/workspaces with kind=Hub).
AI Foundry Accounts (Microsoft.CognitiveServices/accounts) are NOT supported due to lack of public APIs.

Capabilities:
- Discovery of AI Foundry Hubs
- Project management (list, create, delete) for Hubs
- RBAC permission checking
- Agent deployment and management

Note: Users with AI Foundry Accounts should use the Azure Portal for project management
or migrate to AI Foundry Hubs for programmatic access.
"""

import os
import json
import requests
import subprocess  # Still needed for Azure CLI login check
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from azure.identity import DefaultAzureCredential, AzureCliCredential
from azure.core.exceptions import ClientAuthenticationError

logger = logging.getLogger(__name__)

@dataclass
class AIFoundryHub:
    """Represents an AI Foundry Hub (Microsoft.MachineLearningServices/workspaces with kind=Hub)."""
    name: str
    location: str
    resource_group: str
    subscription_id: str
    endpoint: str
    resource_id: str
    properties: Dict[str, Any]

@dataclass
class AIFoundryProject:
    """Represents an AI Foundry project within a Hub."""
    name: str
    display_name: str
    description: str
    location: str
    resource_group: str
    endpoint: str
    parent_hub: str  # hub name
    properties: Dict[str, Any]

@dataclass
class RBACPermission:
    """Represents an RBAC permission requirement."""
    role: str
    scope: str
    required: bool
    current_status: str  # "granted", "missing", "unknown"
    description: str

class AIFoundryService:
    """Service for managing AI Foundry Hubs (ML workspaces with kind=Hub)."""
    
    def __init__(self):
        """Initialize the AI Foundry service."""
        self.credential = None
        self.cli_credential = None
        self._initialize_credentials()
    
    def _initialize_credentials(self) -> None:
        """Initialize Azure credentials."""
        try:
            self.credential = DefaultAzureCredential()
            self.cli_credential = AzureCliCredential()
            # Test credentials
            self.credential.get_token("https://management.azure.com/.default")
        except Exception as e:
            logger.warning(f"Failed to initialize credentials: {e}")
    
    def check_azure_cli_login(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if Azure CLI is logged in and return account info."""
        try:
            result = subprocess.run(
                ["az", "account", "show", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, json.loads(result.stdout)
            return False, None
        except Exception as e:
            logger.error(f"Failed to check Azure CLI login: {e}")
            return False, None
    
    def discover_ai_foundry_hubs(self) -> Tuple[List[AIFoundryHub], List[str]]:
        """
        Discover all AI Foundry Hubs accessible to the user.
        Only supports AI Foundry Hubs (Microsoft.MachineLearningServices/workspaces with kind=Hub).
        AI Foundry Accounts are not supported due to lack of public APIs.
        Returns (hubs, errors).
        """
        hubs = []
        errors = []
        
        try:
            # Get management token
            token = self.credential.get_token("https://management.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            # Get subscriptions
            subscriptions = self._get_subscriptions(headers)
            
            for sub in subscriptions:
                sub_id = sub['subscriptionId']
                
                # Get AI Foundry Hubs only (ML workspaces with kind=Hub)
                hub_list = self._get_ai_foundry_hubs(headers, sub_id)
                hubs.extend(hub_list)
                
        except Exception as e:
            error_msg = f"Failed to discover AI Foundry Hubs: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        return hubs, errors
    
    def _get_subscriptions(self, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Get accessible subscriptions."""
        try:
            response = requests.get(
                "https://management.azure.com/subscriptions",
                headers=headers,
                params={"api-version": "2020-01-01"},
                timeout=30
            )
            response.raise_for_status()
            return response.json().get('value', [])
        except Exception as e:
            logger.error(f"Failed to get subscriptions: {e}")
            return []
    
    def _get_ai_foundry_hubs(self, headers: Dict[str, str], subscription_id: str) -> List[AIFoundryHub]:
        """Get AI Foundry Hubs (ML workspaces with kind=Hub) in a subscription."""
        hubs = []
        try:
            url = f"https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.MachineLearningServices/workspaces"
            response = requests.get(
                url,
                headers=headers,
                params={"api-version": "2024-10-01"},
                timeout=30
            )
            response.raise_for_status()
            
            for workspace in response.json().get('value', []):
                if workspace.get('kind') == 'Hub':
                    properties = workspace.get('properties', {})
                    # Build endpoint for AI Foundry Hub
                    discovery_url = properties.get('discoveryUrl', '')
                    endpoint = discovery_url.replace('/discovery', '') if discovery_url else ''
                    
                    hubs.append(AIFoundryHub(
                        name=workspace['name'],
                        location=workspace['location'],
                        resource_group=workspace['id'].split('/')[4],
                        subscription_id=subscription_id,
                        endpoint=endpoint,
                        resource_id=workspace['id'],
                        properties=properties
                    ))
                    logger.info(f"Found AI Foundry Hub: {workspace['name']} with endpoint: {endpoint}")
        except Exception as e:
            logger.error(f"Failed to get AI Foundry Hubs for subscription {subscription_id}: {e}")
        
        return hubs
                        endpoint=endpoint,
                        resource_id=workspace['id'],
                        properties=properties
                    ))
        except Exception as e:
            logger.error(f"Failed to get AI Foundry hubs for subscription {subscription_id}: {e}")
        
        return hubs
    
    def check_rbac_permissions(self, hub: Union[AIFoundryHub, Dict[str, Any]]) -> List[RBACPermission]:
        """Check RBAC permissions for an AI Foundry Hub."""
        permissions = []
        
        # Convert dict to AIFoundryHub if needed
        if isinstance(hub, dict):
            hub_obj = AIFoundryHub(
                name=hub.get('name', ''),
                location=hub.get('location', ''),
                resource_group=hub.get('resource_group', ''),
                subscription_id=hub.get('subscription_id', ''),
                endpoint=hub.get('endpoint', ''),
                resource_id=hub.get('id', ''),
                properties=hub.get('properties', {})
            )
        else:
            hub_obj = hub
        
        # Define required permissions for AI Foundry Hubs
        required_roles = [
            ("AzureML Data Scientist", "For ML workspace access", True),
            ("Azure AI User", "For AI Foundry operations", True),
            ("Contributor", "For creating/managing resources", False)
        ]
        
        try:
            # Get role assignments for the resource
            token = self.credential.get_token("https://management.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            # Get current user's object ID
            user_info = self._get_current_user_info(headers)
            user_object_id = user_info.get('objectId') if user_info else None
            
            if user_object_id:
                role_assignments = self._get_role_assignments(headers, hub_obj.resource_id, user_object_id)
                assigned_roles = {ra['roleDefinitionName'] for ra in role_assignments}
            else:
                assigned_roles = set()
            
            # Check each required role
            for role_name, description, required in required_roles:
                status = "granted" if role_name in assigned_roles else "missing"
                
                permissions.append(RBACPermission(
                    role=role_name,
                    scope=hub_obj.resource_id,
                    required=required,
                    current_status=status,
                    description=description
                ))
                
        except Exception as e:
            logger.error(f"Failed to check RBAC permissions: {e}")
            # Return permissions with unknown status
            for role_name, description, required in required_roles:
                permissions.append(RBACPermission(
                    role=role_name,
                    scope=hub_obj.resource_id,
                    required=required,
                    current_status="unknown",
                    description=description
                ))
        
        return permissions
    
    def _get_current_user_info(self, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Get current user information from Microsoft Graph."""
        try:
            # Get Graph token
            graph_token = self.credential.get_token("https://graph.microsoft.com/.default")
            graph_headers = {
                'Authorization': f'Bearer {graph_token.token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=graph_headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None
    
    def _get_role_assignments(self, headers: Dict[str, str], resource_id: str, user_object_id: str) -> List[Dict[str, Any]]:
        """Get role assignments for a user on a specific resource."""
        try:
            url = f"https://management.azure.com{resource_id}/providers/Microsoft.Authorization/roleAssignments"
            response = requests.get(
                url,
                headers=headers,
                params={
                    "api-version": "2022-04-01",
                    "$filter": f"principalId eq '{user_object_id}'"
                },
                timeout=30
            )
            response.raise_for_status()
            
            role_assignments = []
            for assignment in response.json().get('value', []):
                # Get role definition name
                role_def_id = assignment['properties']['roleDefinitionId']
                role_def = self._get_role_definition(headers, role_def_id)
                
                role_assignments.append({
                    'roleDefinitionId': role_def_id,
                    'roleDefinitionName': role_def.get('roleName', 'Unknown'),
                    'principalId': assignment['properties']['principalId'],
                    'scope': assignment['properties']['scope']
                })
            
            return role_assignments
        except Exception as e:
            logger.error(f"Failed to get role assignments: {e}")
            return []
    
    def _get_role_definition(self, headers: Dict[str, str], role_definition_id: str) -> Dict[str, Any]:
        """Get role definition details."""
        try:
            response = requests.get(
                f"https://management.azure.com{role_definition_id}",
                headers=headers,
                params={"api-version": "2022-04-01"},
                timeout=30
            )
            response.raise_for_status()
            
            role_def = response.json()
            return {
                'roleName': role_def['properties']['roleName'],
                'description': role_def['properties']['description']
            }
        except Exception as e:
            logger.error(f"Failed to get role definition: {e}")
            return {'roleName': 'Unknown', 'description': 'Unknown'}
    
    def get_projects_for_hub(self, hub: Union[AIFoundryHub, Dict[str, Any]]) -> Tuple[List[AIFoundryProject], List[str]]:
        """Get projects for an AI Foundry Hub using Azure ML API."""
        projects = []
        errors = []
        
        # Convert dict to AIFoundryHub if needed
        if isinstance(hub, dict):
            hub_obj = AIFoundryHub(
                name=hub['name'],
                location=hub['location'],
                resource_group=hub['resource_group'],
                subscription_id=hub['subscription_id'],
                endpoint=hub['endpoint'],
                resource_id=hub['id'],
                properties=hub.get('properties', {})
            )
        else:
            hub_obj = hub
        
        logger.info(f"Discovering projects for AI Foundry Hub: {hub_obj.name}")
        
        # Use Azure ML API for AI Foundry Hubs
        ml_projects, ml_errors = self._discover_projects_via_ml_api(hub_obj)
        projects.extend(ml_projects)
        errors.extend(ml_errors)
        
        # Remove duplicates based on project name
        unique_projects = {}
        for project in projects:
            if project.name not in unique_projects:
                unique_projects[project.name] = project
        
        final_projects = list(unique_projects.values())
        
        if final_projects:
            logger.info(f"Found {len(final_projects)} projects for Hub {hub_obj.name}")
        else:
            logger.warning(f"No projects found for Hub {hub_obj.name}")
            if not errors:
                errors.append(f"No projects found for {hub_obj.name}. Create a project using the interface above.")
        
        return final_projects, errors
                errors.append(f"No projects found for {resource_obj.name}. Create a project using the interface above.")
        
        return final_projects, errors
    
    def _discover_projects_via_ml_api(self, hub: AIFoundryHub) -> Tuple[List[AIFoundryProject], List[str]]:
        """Discover projects using Azure ML API (for AI Foundry Hubs)."""
        projects = []
        errors = []
        
        try:
            logger.info(f"Discovering projects for Hub {hub.name} using Azure ML API...")
            
            token = self.credential.get_token("https://management.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            # Query for ML workspaces in the same resource group (potential projects)
            url = f"https://management.azure.com/subscriptions/{hub.subscription_id}/resourceGroups/{hub.resource_group}/providers/Microsoft.MachineLearningServices/workspaces"
            
            response = requests.get(
                url,
                headers=headers,
                params={"api-version": "2024-10-01"},
                timeout=30
            )
            response.raise_for_status()
            
            workspaces = response.json().get('value', [])
            
            for workspace in workspaces:
                # Check if this workspace is a project (not a hub)
                properties = workspace.get('properties', {})
                if properties.get('hubResourceId') == hub.resource_id:
                    # This is a project belonging to our hub
                    project = AIFoundryProject(
                        name=workspace['name'],
                        display_name=properties.get('friendlyName', workspace['name']),
                        description=properties.get('description', ''),
                        location=workspace['location'],
                        resource_group=workspace['id'].split('/')[4],
                        endpoint=properties.get('workspaceUrl', ''),
                        parent_hub=hub.name,
                        properties=properties
                    )
                    projects.append(project)
                    logger.info(f"Found project via ML API: {project.name}")
                    
        except Exception as e:
            error_msg = f"ML API project discovery failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        return projects, errors
    
    def create_project(self, hub: Union[AIFoundryHub, Dict[str, Any]], project_name: str, description: str = "") -> Tuple[bool, str, Optional[AIFoundryProject]]:
        """
        Create a new project in an AI Foundry Hub.
        Only supports AI Foundry Hubs - AI Foundry Accounts are not supported.
        """
        try:
            # Convert dict to AIFoundryHub if needed
            if isinstance(hub, dict):
                hub_obj = AIFoundryHub(
                    name=hub['name'],
                    location=hub['location'],
                    resource_group=hub['resource_group'],
                    subscription_id=hub['subscription_id'],
                    endpoint=hub['endpoint'],
                    resource_id=hub['id'],
                    properties=hub.get('properties', {})
                )
            else:
                hub_obj = hub
            
            return self._create_hub_project(hub_obj, project_name, description)
        except Exception as e:
            error_msg = f"Failed to create project: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
        
        logger.info(f"Creating project '{project_name}' in AI Foundry account '{account.name}'")
        logger.info(f"Account resource ID: {account.resource_id}")
        
        # Method 1: Use AI Foundry REST API (primary method)
        try:
            logger.info("Attempting project creation via AI Foundry REST API...")
            
            rest_result = self._create_project_via_rest_api(
                account, project_name, description
            )
            
            if rest_result[0]:  # Success
                logger.info(f"Project created successfully via AI Foundry REST API")
                return rest_result
            else:
                logger.warning(f"AI Foundry REST API method failed: {rest_result[1]}")
                
        except Exception as e:
            logger.warning(f"AI Foundry REST API method failed with exception: {str(e)}")
        
        # Method 2: Try ARM API as fallback (may work for some account types)
        try:
    def _create_hub_project(self, hub: AIFoundryHub, project_name: str, description: str) -> Tuple[bool, str, Optional[AIFoundryProject]]:
        """Create a project in an AI Foundry Hub using Azure ML API."""
        try:
            logger.info(f"Creating project '{project_name}' in AI Foundry Hub '{hub.name}'")
            
            token = self.credential.get_token("https://management.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            # Create ML workspace (project) that references the hub
            project_data = {
                "location": hub.location,
                "properties": {
                    "friendlyName": project_name,
                    "description": description,
                    "hubResourceId": hub.resource_id,
                    "kind": "Project"
                }
            }
            
            url = f"https://management.azure.com/subscriptions/{hub.subscription_id}/resourceGroups/{hub.resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{project_name}"
            
            response = requests.put(
                url,
                headers=headers,
                params={"api-version": "2024-10-01"},
                json=project_data,
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Project '{project_name}' created successfully")
                
                # Return the created project
                workspace_data = response.json()
                properties = workspace_data.get('properties', {})
                
                project = AIFoundryProject(
                    name=project_name,
                    display_name=project_name,
                    description=description,
                    location=hub.location,
                    resource_group=hub.resource_group,
                    endpoint=properties.get('workspaceUrl', ''),
                    parent_hub=hub.name,
                    properties=properties
                )
                
                return True, f"Project '{project_name}' created successfully in Hub '{hub.name}'", project
            else:
                error_msg = f"Failed to create project: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg, None
                
        except Exception as e:
            error_msg = f"Error creating project in Hub: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
            token = self.credential.get_token("https://management.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            workspace_data = {
                "kind": "Project",
                "location": hub.location,
                "properties": {
                    "description": description,
                    "hubResourceId": hub.resource_id,
                    "displayName": project_name
                }
            }
            
            url = f"https://management.azure.com/subscriptions/{hub.subscription_id}/resourceGroups/{hub.resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{project_name}"
            
            response = requests.put(
                url,
                headers=headers,
                json=workspace_data,
                params={"api-version": "2024-04-01"},
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                workspace_result = response.json()
                properties = workspace_result.get('properties', {})
                
                project = AIFoundryProject(
                    name=workspace_result['name'],
                    display_name=properties.get('displayName', project_name),
                    description=properties.get('description', description),
                    location=workspace_result['location'],
                    resource_group=workspace_result['id'].split('/')[4],
                    endpoint=properties.get('discoveryUrl', '').replace('/discovery', '') if properties.get('discoveryUrl') else '',
                    parent_resource=hub.name,
                    properties=properties
                )
                return True, "Project created successfully", project
            else:
                return False, f"Failed to create project: {response.status_code} - {response.text}", None
                
        except Exception as e:
            return False, f"Failed to create hub project: {str(e)}", None
    
    def _create_project_via_rest_api(self, account: AIFoundryResource, project_name: str, description: str) -> Tuple[bool, str, Optional[AIFoundryProject]]:
        """Create a project using AI Foundry REST API (for AI Foundry accounts)."""
        try:
            # Use AI Foundry REST API endpoint - correct format
            endpoint = f"https://{account.name}.services.ai.azure.com/api/projects"
            
            # Get token with AI Foundry scope
            token = self.credential.get_token("https://ai.azure.com/.default")
            
            headers = {
                "Authorization": f"Bearer {token.token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "name": project_name,
                "description": description or f"Project created programmatically"
                # Optional: add quota/network settings when API exposes them
            }
            
            logger.info(f"Creating project via AI Foundry REST API: {endpoint}")
            logger.info(f"Payload: {payload}")
            
            # Call the AI Foundry Projects REST API
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                params={"api-version": "2025-05-15-preview"},
                timeout=120
            )
            
            response.raise_for_status()
            project_data = response.json()
            
            logger.info(f"Project created successfully via AI Foundry REST API")
            logger.info(f"Response: {project_data}")
            
            # Create AIFoundryProject object from REST response
            project = AIFoundryProject(
                name=project_data.get('name', project_name),
                display_name=project_data.get('friendlyName', project_name),
                description=project_data.get('description', description),
                location=account.location,
                resource_group=account.resource_group,
                endpoint=f"https://{account.name}.services.ai.azure.com/projects/{project_name}",
                parent_resource=account.name,
                properties=project_data
            )
            
            return True, f"Project '{project_name}' created successfully via AI Foundry REST API", project
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"AI Foundry REST API error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            
            # Check for specific error conditions
            if e.response.status_code == 403:
                error_msg += "\n\nRequired: Project Administrator role (or higher) on the AI Foundry account"
            elif e.response.status_code == 409:
                error_msg += f"\n\nProject '{project_name}' may already exist"
                
            return False, error_msg, None
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: Cannot reach AI Foundry endpoint {endpoint}. The account may not support the projects API."
            logger.error(error_msg)
            return False, error_msg, None
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout error: AI Foundry endpoint {endpoint} did not respond in time"
            logger.error(error_msg)
            return False, error_msg, None
        except Exception as e:
            error_msg = f"AI Foundry REST API method failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def _create_project_via_arm_api(self, account: AIFoundryResource, project_name: str, description: str,
                                   subscription_id: str, resource_group: str) -> Tuple[bool, str, Optional[AIFoundryProject]]:
        """Create a project using ARM API (fallback method, primarily for ML workspaces)."""
        try:
            token = self.credential.get_token("https://management.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            # Create a Machine Learning workspace that works with AI Foundry
            project_resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{project_name}"
            logger.info(f"Attempting to create project via ARM API: {project_resource_id}")
            
            # Enhanced project data with full MSI support and AI Foundry compatibility
            project_data = {
                "location": account.location,
                "properties": {
                    "friendlyName": project_name,
                    "description": description,
                    # Link to the account via storageAccount property
                    "storageAccount": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Storage/storageAccounts/{account.name}storage",
                    "keyVault": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.KeyVault/vaults/{account.name}kv",
                    "applicationInsights": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Insights/components/{account.name}insights",
                    "publicNetworkAccess": "Enabled",
                    "managedNetwork": {
                        "isolationMode": "Disabled"
                    },
                    # Enable system managed identity
                    "systemDatastoresAuthMode": "identity"
                },
                "identity": {
                    "type": "SystemAssigned"
                },
                "kind": "Project",
                "sku": {
                    "name": "Basic",
                    "tier": "Basic"
                }
            }
            
            # Use Azure Resource Manager API for project creation
            arm_url = f"https://management.azure.com{project_resource_id}"
            
            response = requests.put(
                arm_url,
                headers=headers,
                json=project_data,
                params={"api-version": "2024-04-01"},
                timeout=120
            )
            
            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                logger.info(f"Project created successfully via ARM API")
                
                # Create AIFoundryProject object
                project = AIFoundryProject(
                    name=project_name,
                    display_name=project_name,
                    description=description,
                    location=account.location,
                    resource_group=resource_group,
                    endpoint=f"https://{project_name}.{account.location}.api.azureml.ms",
                    parent_resource=account.name,
                    properties=response_data.get('properties', {})
                )
                
                return True, f"Project '{project_name}' created successfully via ARM API", project
            else:
                error_msg = f"ARM API failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg, None
                
        except Exception as e:
            error_msg = f"ARM API method failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
