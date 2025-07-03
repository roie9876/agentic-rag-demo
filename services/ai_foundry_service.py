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
        """Initialize Azure credentials with MSI support."""
        try:
            # Try DefaultAzureCredential first (includes MSI)
            self.credential = DefaultAzureCredential(
                exclude_interactive_browser_credential=True,  # Don't prompt for browser auth
                exclude_visual_studio_code_credential=True,   # Don't use VS Code auth
                exclude_azure_powershell_credential=True,     # Don't use PowerShell auth
                exclude_shared_token_cache_credential=True,   # Don't use shared cache
                # This will prioritize: MSI -> Azure CLI -> Environment variables
            )
            
            # Also try CLI credential as fallback
            self.cli_credential = AzureCliCredential()
            
            # Test MSI credential first
            try:
                token = self.credential.get_token("https://management.azure.com/.default")
                logger.info("Successfully authenticated with DefaultAzureCredential (MSI support)")
            except Exception as msi_error:
                logger.warning(f"DefaultAzureCredential failed: {msi_error}")
                # Fallback to CLI credential
                try:
                    token = self.cli_credential.get_token("https://management.azure.com/.default")
                    self.credential = self.cli_credential
                    logger.info("Successfully authenticated with AzureCliCredential")
                except Exception as cli_error:
                    logger.error(f"Both credential methods failed: MSI={msi_error}, CLI={cli_error}")
                    raise
                    
        except Exception as e:
            logger.warning(f"Failed to initialize credentials: {e}")
            raise
    
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
        Create a new project in an AI Foundry Hub with MSI support.
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
            
            logger.info(f"Creating project '{project_name}' in AI Foundry Hub '{hub_obj.name}' with MSI support")
            return self._create_hub_project(hub_obj, project_name, description)
            
        except Exception as e:
            error_msg = f"Failed to create project: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def _create_hub_project(self, hub: AIFoundryHub, project_name: str, description: str) -> Tuple[bool, str, Optional[AIFoundryProject]]:
        """Create a project in an AI Foundry Hub using Azure ML API with MSI support."""
        try:
            logger.info(f"Creating project '{project_name}' in AI Foundry Hub '{hub.name}' with MSI support")
            
            # Check credential type and MSI availability
            credential_info = self.get_credential_info()
            logger.info(f"Credential info: {credential_info}")
            
            token = self.credential.get_token("https://management.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json',
                'User-Agent': 'agentic-rag-demo/1.0'
            }
            
            # Create comprehensive ML workspace (project) payload with all required dependencies
            # This addresses the "Missing dependent resources in workspace json" error
            project_data = {
                "location": hub.location,
                "identity": {
                    "type": "SystemAssigned"
                },
                "properties": {
                    "friendlyName": project_name,
                    "description": description,
                    "hubResourceId": hub.resource_id,
                    "kind": "Project",
                    # Essential properties for project creation
                    "managedNetwork": {
                        "isolationMode": "Disabled"
                    },
                    "publicNetworkAccess": "Enabled",
                    "hbiWorkspace": False,
                    "v1LegacyMode": False,
                    "allowPublicAccessWhenBehindVnet": False,
                    # Include hub's storage account if available
                    "storageAccount": hub.properties.get("storageAccount", ""),
                    "keyVault": hub.properties.get("keyVault", ""),
                    "applicationInsights": hub.properties.get("applicationInsights", ""),
                    "containerRegistry": hub.properties.get("containerRegistry", ""),
                    # Add dependent resources section to prevent "Missing dependent resources" error
                    "dependentResources": [
                        {
                            "resourceId": hub.resource_id,
                            "resourceType": "Microsoft.MachineLearningServices/workspaces"
                        }
                    ]
                },
                "tags": {
                    "createdBy": "agentic-rag-demo",
                    "msiEnabled": "true",
                    "parentHub": hub.name,
                    "projectType": "aiFoundry"
                }
            }
            
            # Clean up empty strings from dependent resources
            if not project_data["properties"]["storageAccount"]:
                project_data["properties"].pop("storageAccount", None)
            if not project_data["properties"]["keyVault"]:
                project_data["properties"].pop("keyVault", None)
            if not project_data["properties"]["applicationInsights"]:
                project_data["properties"].pop("applicationInsights", None)
            if not project_data["properties"]["containerRegistry"]:
                project_data["properties"].pop("containerRegistry", None)
            
            # Use the latest stable API version that supports MSI
            # Note: Using 2024-10-01 which is the latest available version
            url = f"https://management.azure.com/subscriptions/{hub.subscription_id}/resourceGroups/{hub.resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{project_name}"
            
            logger.info(f"Creating project with comprehensive MSI-compatible payload:")
            logger.info(f"API version: 2024-10-01")
            logger.info(f"Hub resource ID: {hub.resource_id}")
            logger.info(f"Project payload keys: {list(project_data.keys())}")
            logger.info(f"Project properties keys: {list(project_data['properties'].keys())}")
            
            response = requests.put(
                url,
                headers=headers,
                params={"api-version": "2024-10-01"},
                json=project_data,
                timeout=120  # Increased timeout for MSI configuration
            )
            
            logger.info(f"Project creation response: {response.status_code}")
            
            if response.status_code not in [200, 201]:
                error_response = response.text
                logger.error(f"Project creation failed with response: {error_response}")
                
                # Check for specific error types
                if "Missing dependent resources in workspace json" in error_response:
                    logger.error("Dependency error - attempting with minimal payload")
                    # Try with minimal payload
                    return self._create_hub_project_minimal(hub, project_name, description)
                elif "MSI" in error_response or "Managed Service Identity" in error_response:
                    error_msg = f"MSI-related error during project creation: {error_response}"
                    logger.error(error_msg)
                    # Try alternative MSI approach
                    return self._create_hub_project_alternative_msi(hub, project_name, description)
                else:
                    return False, f"Project creation failed: {response.status_code} - {error_response}", None
            
            if response.status_code in [200, 201]:
                logger.info(f"Project '{project_name}' created successfully with MSI support")
                
                # Return the created project
                workspace_data = response.json()
                properties = workspace_data.get('properties', {})
                
                project = AIFoundryProject(
                    name=project_name,
                    display_name=properties.get('friendlyName', project_name),
                    description=properties.get('description', description),
                    location=hub.location,
                    resource_group=hub.resource_group,
                    endpoint=properties.get('workspaceUrl', ''),
                    parent_hub=hub.name,
                    properties=properties
                )
                
                return True, f"Project '{project_name}' created successfully in Hub '{hub.name}' with MSI support", project
            else:
                error_msg = f"Failed to create project: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg, None
                
        except Exception as e:
            error_msg = f"Error creating project in Hub with MSI support: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def _create_hub_project_minimal(self, hub: AIFoundryHub, project_name: str, description: str) -> Tuple[bool, str, Optional[AIFoundryProject]]:
        """Create a project with minimal payload to avoid dependency issues."""
        try:
            logger.info(f"Creating project '{project_name}' with minimal payload")
            
            token = self.credential.get_token("https://management.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json',
                'User-Agent': 'agentic-rag-demo/1.0'
            }
            
            # Minimal payload to avoid dependency issues
            minimal_payload = {
                "location": hub.location,
                "identity": {
                    "type": "SystemAssigned"
                },
                "properties": {
                    "friendlyName": project_name,
                    "description": description,
                    "hubResourceId": hub.resource_id,
                    "kind": "Project",
                    "publicNetworkAccess": "Enabled",
                    "hbiWorkspace": False
                }
            }
            
            url = f"https://management.azure.com/subscriptions/{hub.subscription_id}/resourceGroups/{hub.resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{project_name}"
            
            logger.info(f"Minimal payload: {json.dumps(minimal_payload, indent=2)}")
            
            response = requests.put(
                url,
                headers=headers,
                params={"api-version": "2024-10-01"},
                json=minimal_payload,
                timeout=120
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Project '{project_name}' created successfully with minimal payload")
                
                workspace_data = response.json()
                properties = workspace_data.get('properties', {})
                
                project = AIFoundryProject(
                    name=project_name,
                    display_name=properties.get('friendlyName', project_name),
                    description=properties.get('description', description),
                    location=hub.location,
                    resource_group=hub.resource_group,
                    endpoint=properties.get('workspaceUrl', ''),
                    parent_hub=hub.name,
                    properties=properties
                )
                
                return True, f"Project '{project_name}' created successfully with minimal payload", project
            else:
                error_msg = f"Minimal payload creation failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg, None
                
        except Exception as e:
            error_msg = f"Minimal payload creation failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def _create_hub_project_alternative_msi(self, hub: AIFoundryHub, project_name: str, description: str) -> Tuple[bool, str, Optional[AIFoundryProject]]:
        """Alternative method for creating a project with MSI using Azure CLI approach."""
        try:
            logger.info(f"Attempting alternative MSI project creation for '{project_name}' in Hub '{hub.name}'")
            
            # Method 1: Try with Azure CLI if available
            if self.check_azure_cli_login()[0]:
                logger.info("Attempting project creation via Azure CLI with MSI support...")
                
                # Create project using Azure CLI
                cli_command = [
                    "az", "ml", "workspace", "create",
                    "--resource-group", hub.resource_group,
                    "--name", project_name,
                    "--location", hub.location,
                    "--display-name", project_name,
                    "--description", description,
                    "--hub-id", hub.resource_id,
                    "--kind", "project",
                    "--identity-type", "SystemAssigned",
                    "--subscription", hub.subscription_id
                ]
                
                try:
                    result = subprocess.run(
                        cli_command,
                        capture_output=True,
                        text=True,
                        timeout=180
                    )
                    
                    if result.returncode == 0:
                        logger.info("Project created successfully via Azure CLI with MSI")
                        
                        # Parse the CLI output to create project object
                        try:
                            project_data = json.loads(result.stdout)
                            project = AIFoundryProject(
                                name=project_name,
                                display_name=project_data.get('display_name', project_name),
                                description=project_data.get('description', description),
                                location=hub.location,
                                resource_group=hub.resource_group,
                                endpoint=project_data.get('workspace_url', ''),
                                parent_hub=hub.name,
                                properties=project_data
                            )
                            return True, f"Project '{project_name}' created successfully via Azure CLI with MSI", project
                        except json.JSONDecodeError:
                            # CLI succeeded but couldn't parse output, still consider it success
                            project = AIFoundryProject(
                                name=project_name,
                                display_name=project_name,
                                description=description,
                                location=hub.location,
                                resource_group=hub.resource_group,
                                endpoint='',
                                parent_hub=hub.name,
                                properties={}
                            )
                            return True, f"Project '{project_name}' created successfully via Azure CLI with MSI", project
                    else:
                        logger.error(f"Azure CLI project creation failed: {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    logger.error("Azure CLI project creation timed out")
                except Exception as cli_error:
                    logger.error(f"Azure CLI project creation failed with exception: {str(cli_error)}")
            
            # Method 2: Try with simplified REST API payload
            logger.info("Attempting simplified REST API approach with MSI...")
            
            token = self.credential.get_token("https://management.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json',
                'User-Agent': 'agentic-rag-demo/1.0'
            }
            
            # Simplified payload focusing on MSI essentials
            simple_payload = {
                "location": hub.location,
                "identity": {
                    "type": "SystemAssigned"
                },
                "properties": {
                    "friendlyName": project_name,
                    "description": description,
                    "hubResourceId": hub.resource_id,
                    "kind": "Project"
                }
            }
            
            url = f"https://management.azure.com/subscriptions/{hub.subscription_id}/resourceGroups/{hub.resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{project_name}"
            
            logger.info(f"Simplified MSI payload: {json.dumps(simple_payload, indent=2)}")
            
            response = requests.put(
                url,
                headers=headers,
                params={"api-version": "2024-04-01"},  # Try earlier API version
                json=simple_payload,
                timeout=120
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Project '{project_name}' created successfully with simplified MSI approach")
                
                workspace_data = response.json()
                properties = workspace_data.get('properties', {})
                
                project = AIFoundryProject(
                    name=project_name,
                    display_name=properties.get('friendlyName', project_name),
                    description=properties.get('description', description),
                    location=hub.location,
                    resource_group=hub.resource_group,
                    endpoint=properties.get('workspaceUrl', ''),
                    parent_hub=hub.name,
                    properties=properties
                )
                
                return True, f"Project '{project_name}' created successfully with simplified MSI approach", project
            else:
                error_msg = f"Simplified MSI approach failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg, None
                
        except Exception as e:
            error_msg = f"Alternative MSI project creation failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None

    def check_msi_availability(self) -> Tuple[bool, str]:
        """Check if Managed Service Identity (MSI) is available and working."""
        try:
            from azure.identity import ManagedIdentityCredential
            
            # Try to get a token using MSI directly
            msi_credential = ManagedIdentityCredential()
            token = msi_credential.get_token("https://management.azure.com/.default")
            
            if token and token.token:
                return True, f"MSI is available and working. Token expires: {token.expires_on}"
            else:
                return False, "MSI credential returned empty token"
                
        except Exception as e:
            return False, f"MSI not available or failed: {str(e)}"
    
    def get_credential_info(self) -> Dict[str, Any]:
        """Get information about the current credential configuration."""
        credential_info = {
            "credential_type": type(self.credential).__name__ if self.credential else "None",
            "msi_available": False,
            "cli_available": False,
            "token_working": False
        }
        
        # Check MSI availability
        msi_available, msi_message = self.check_msi_availability()
        credential_info["msi_available"] = msi_available
        credential_info["msi_message"] = msi_message
        
        # Check CLI availability
        cli_available, cli_account = self.check_azure_cli_login()
        credential_info["cli_available"] = cli_available
        if cli_account:
            credential_info["cli_account"] = cli_account.get("user", {}).get("name", "Unknown")
        
        # Test current credential
        if self.credential:
            try:
                token = self.credential.get_token("https://management.azure.com/.default")
                credential_info["token_working"] = bool(token and token.token)
                credential_info["token_expires"] = str(token.expires_on) if token else "N/A"
            except Exception as e:
                credential_info["token_error"] = str(e)
        
        return credential_info

    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Get comprehensive diagnostic information for troubleshooting."""
        diagnostics = {
            "credential_info": self.get_credential_info(),
            "service_methods": [],
            "api_availability": {},
            "common_issues": []
        }
        
        # Check available methods
        methods = [method for method in dir(self) if not method.startswith('__')]
        diagnostics["service_methods"] = methods
        
        # Check API availability
        try:
            token = self.credential.get_token("https://management.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            # Test Management API
            response = requests.get(
                "https://management.azure.com/subscriptions",
                headers=headers,
                params={"api-version": "2020-01-01"},
                timeout=10
            )
            diagnostics["api_availability"]["management_api"] = {
                "status": response.status_code,
                "accessible": response.status_code == 200
            }
            
        except Exception as e:
            diagnostics["api_availability"]["management_api"] = {
                "status": "error",
                "error": str(e),
                "accessible": False
            }
        
        # Check for common issues
        credential_info = diagnostics["credential_info"]
        
        if not credential_info.get("token_working", False):
            diagnostics["common_issues"].append("Authentication token not working")
        
        if not credential_info.get("msi_available", False):
            diagnostics["common_issues"].append("MSI not available (expected if not running in Azure)")
        
        if not credential_info.get("cli_available", False):
            diagnostics["common_issues"].append("Azure CLI not logged in")
        
        if not diagnostics["api_availability"].get("management_api", {}).get("accessible", False):
            diagnostics["common_issues"].append("Azure Management API not accessible")
        
        return diagnostics
    
    def validate_hub_for_project_creation(self, hub: Union[AIFoundryHub, Dict[str, Any]]) -> Tuple[bool, List[str], List[str]]:
        """Validate that a hub is suitable for project creation."""
        issues = []
        warnings = []
        
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
        
        # Check required fields
        if not hub_obj.name:
            issues.append("Hub name is missing")
        if not hub_obj.location:
            issues.append("Hub location is missing")
        if not hub_obj.resource_group:
            issues.append("Hub resource group is missing")
        if not hub_obj.subscription_id:
            issues.append("Hub subscription ID is missing")
        if not hub_obj.resource_id:
            issues.append("Hub resource ID is missing")
        
        # Check hub properties
        if not hub_obj.properties:
            warnings.append("Hub properties are missing (may cause dependency issues)")
        else:
            # Check for essential dependent resources
            if not hub_obj.properties.get('storageAccount'):
                warnings.append("Hub storage account not found (may cause dependency issues)")
            if not hub_obj.properties.get('keyVault'):
                warnings.append("Hub key vault not found (may cause dependency issues)")
        
        # Check if this is actually a hub
        if hub_obj.properties.get('kind') != 'Hub':
            issues.append(f"Resource is not a Hub (kind: {hub_obj.properties.get('kind', 'unknown')})")
        
        is_valid = len(issues) == 0
        return is_valid, issues, warnings
