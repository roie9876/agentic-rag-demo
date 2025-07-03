#!/usr/bin/env python3
"""
AI Foundry RBAC Service
Handles RBAC (Role-Based Access Control) management for AI Foundry resources.
"""

import os
import logging
import requests
import subprocess
import json
import base64
from typing import Dict, List, Any, Optional, Tuple
from azure.identity import DefaultAzureCredential
from azure.mgmt.authorization import AuthorizationManagementClient
from azure.mgmt.authorization.models import RoleAssignmentCreateParameters
import uuid

logger = logging.getLogger(__name__)

class AIFoundryRBACService:
    """Service for managing RBAC permissions for AI Foundry resources."""
    
    # Role definitions for AI Foundry
    ROLE_DEFINITIONS = {
        'Azure AI User': '/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/64702f94-c441-49e6-a78b-ef80e0188fee',
        'Azure AI Administrator': '/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/d1b70e2c-4a3b-4a8e-a638-8a3ba3c87f8a',
        'Azure AI Developer': '/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/64702f94-c441-49e6-a78b-ef80e0188fee',  # Same as AI User for now
        'Cognitive Services OpenAI User': '/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/5e0bd9bd-7b93-4f28-af87-19fc36ad61bd',
        'Cognitive Services OpenAI Contributor': '/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/a001fd3d-188f-4b5d-821b-7da978bf7442',
        'Search Index Data Contributor': '/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/8ebe5a00-799e-43f5-93ac-243d3dce84a7',
        'Search Service Contributor': '/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/7ca78c08-252a-4471-8644-bb5ff32d4ba0',
        'Owner': '/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/8e3af657-a8ff-443c-a75c-2fe8c4bcb635',
        'Contributor': '/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/b24988ac-6180-42a0-ab88-20f7382dd24c',
        'Reader': '/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/acdd72a7-3385-48ef-bd42-f606fba81ae7'
    }
    
    # Required permissions for different operations
    REQUIRED_PERMISSIONS = {
        'ai_foundry_account_access': [
            'Azure AI User',
            'Cognitive Services OpenAI User'
        ],
        'ai_foundry_account_admin': [
            'Azure AI Administrator',
            'Cognitive Services OpenAI Contributor'
        ],
        'project_creation': [
            'Azure AI Administrator',
            'Contributor'
        ],
        'agent_deployment': [
            'Azure AI User',
            'Cognitive Services OpenAI User'
        ],
        'search_integration': [
            'Search Index Data Contributor',
            'Search Service Contributor'
        ],
        'assign_roles': [
            'User Access Administrator',
            'Owner'
        ]
    }
    
    def __init__(self):
        """Initialize the AI Foundry RBAC Service."""
        self.credential = DefaultAzureCredential()
        self._subscription_id = None
        self._auth_client = None
    
    def set_subscription(self, subscription_id: str) -> None:
        """Set the subscription ID and initialize the authorization client."""
        self._subscription_id = subscription_id
        if subscription_id:
            self._auth_client = AuthorizationManagementClient(
                self.credential, subscription_id
            )
    
    def check_user_permissions(self, user_principal_id: str, resource_scope: str) -> Dict[str, Any]:
        """Check what permissions a user has on a specific resource."""
        if not self._auth_client:
            return {'error': 'Authorization client not initialized'}
        
        try:
            # Get role assignments for the user on the resource
            role_assignments = list(self._auth_client.role_assignments.list_for_scope(
                scope=resource_scope,
                filter=f"principalId eq '{user_principal_id}'"
            ))
            
            # Get role definitions to map role assignment IDs to names
            user_roles = []
            for assignment in role_assignments:
                try:
                    role_def = self._auth_client.role_definitions.get_by_id(
                        assignment.role_definition_id
                    )
                    user_roles.append({
                        'role_name': role_def.role_name,
                        'role_id': assignment.role_definition_id,
                        'assignment_id': assignment.id,
                        'scope': assignment.scope
                    })
                except Exception as e:
                    logger.warning(f"Could not get role definition for {assignment.role_definition_id}: {e}")
            
            return {
                'user_principal_id': user_principal_id,
                'resource_scope': resource_scope,
                'roles': user_roles,
                'role_count': len(user_roles)
            }
            
        except Exception as e:
            logger.error(f"Error checking user permissions: {e}")
            return {'error': str(e)}
    
    def check_required_permissions(self, user_principal_id: str, resource_scope: str, 
                                   operation: str) -> Dict[str, Any]:
        """Check if a user has the required permissions for a specific operation."""
        if operation not in self.REQUIRED_PERMISSIONS:
            return {'error': f'Unknown operation: {operation}'}
        
        # Get user's current permissions
        current_perms = self.check_user_permissions(user_principal_id, resource_scope)
        if 'error' in current_perms:
            return current_perms
        
        # Get required roles for the operation
        required_roles = self.REQUIRED_PERMISSIONS[operation]
        user_role_names = [role['role_name'] for role in current_perms['roles']]
        
        # Check if user has any of the required roles
        has_permission = any(role in user_role_names for role in required_roles)
        
        # Check for Owner/Contributor which grant most permissions
        has_admin_role = any(role in user_role_names for role in ['Owner', 'Contributor'])
        
        missing_roles = [role for role in required_roles if role not in user_role_names]
        
        return {
            'operation': operation,
            'has_permission': has_permission or has_admin_role,
            'has_admin_role': has_admin_role,
            'user_roles': user_role_names,
            'required_roles': required_roles,
            'missing_roles': missing_roles if not (has_permission or has_admin_role) else [],
            'resource_scope': resource_scope
        }
    
    def get_current_user_principal_id(self) -> Optional[str]:
        """Get the current user's principal ID using multiple fallback methods."""
        try:
            # Method 1: Try Microsoft Graph API with proper token
            try:
                graph_token = self.credential.get_token("https://graph.microsoft.com/.default")
                headers = {
                    'Authorization': f'Bearer {graph_token.token}',
                    'Content-Type': 'application/json'
                }
                
                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me',
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    user_info = response.json()
                    principal_id = user_info.get('id')
                    if principal_id:
                        logger.info("Successfully obtained user principal ID from Graph API")
                        return principal_id
                else:
                    logger.warning(f"Graph API returned status {response.status_code}: {response.text}")
            except Exception as e:
                logger.warning(f"Graph API method failed: {e}")
            
            # Method 2: Try Azure CLI approach
            try:
                import subprocess
                import json
                
                # Get signed-in user info from Azure CLI
                result = subprocess.run(
                    ['az', 'ad', 'signed-in-user', 'show'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    user_info = json.loads(result.stdout)
                    principal_id = user_info.get('id')
                    if principal_id:
                        logger.info("Successfully obtained user principal ID from Azure CLI")
                        return principal_id
                else:
                    logger.warning(f"Azure CLI user lookup failed: {result.stderr}")
            except Exception as e:
                logger.warning(f"Azure CLI method failed: {e}")
            
            # Method 3: Try to get from current account context
            try:
                result = subprocess.run(
                    ['az', 'account', 'show'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    account_info = json.loads(result.stdout)
                    user_info = account_info.get('user', {})
                    
                    # Try different field names
                    for field in ['objectId', 'id', 'oid']:
                        if field in user_info:
                            principal_id = user_info[field]
                            if principal_id:
                                logger.info(f"Successfully obtained user principal ID from account context ({field})")
                                return principal_id
                else:
                    logger.warning(f"Azure CLI account show failed: {result.stderr}")
            except Exception as e:
                logger.warning(f"Account context method failed: {e}")
            
            # Method 4: Try token introspection (last resort)
            try:
                # Get management token and try to decode it
                mgmt_token = self.credential.get_token("https://management.azure.com/.default")
                
                # This is a basic approach - in production you'd want proper JWT parsing
                import base64
                
                # Split the JWT token
                parts = mgmt_token.token.split('.')
                if len(parts) >= 2:
                    # Decode the payload (add padding if needed)
                    payload = parts[1]
                    payload += '=' * (4 - len(payload) % 4)  # Add padding
                    
                    try:
                        decoded = base64.b64decode(payload)
                        token_data = json.loads(decoded)
                        
                        # Try different claim names for user ID
                        for claim in ['oid', 'sub', 'appid', 'upn']:
                            if claim in token_data:
                                principal_id = token_data[claim]
                                if principal_id and claim in ['oid', 'sub']:  # Prefer object ID or subject
                                    logger.info(f"Successfully obtained user principal ID from token ({claim})")
                                    return principal_id
                    except Exception as decode_error:
                        logger.warning(f"Token decode failed: {decode_error}")
            except Exception as e:
                logger.warning(f"Token introspection method failed: {e}")
            
            logger.error("All methods to obtain user principal ID failed")
            return None
                
        except Exception as e:
            logger.error(f"Error getting current user principal ID: {e}")
            return None
    
    def assign_role(self, user_principal_id: str, resource_scope: str, role_name: str) -> Dict[str, Any]:
        """Assign a role to a user on a specific resource."""
        if not self._auth_client or not self._subscription_id:
            return {'error': 'Authorization client or subscription not initialized'}
        
        if role_name not in self.ROLE_DEFINITIONS:
            return {'error': f'Unknown role: {role_name}'}
        
        try:
            # Get the role definition ID
            role_definition_id = self.ROLE_DEFINITIONS[role_name].format(
                subscription_id=self._subscription_id
            )
            
            # Create role assignment
            assignment_name = str(uuid.uuid4())
            
            assignment_params = RoleAssignmentCreateParameters(
                role_definition_id=role_definition_id,
                principal_id=user_principal_id
            )
            
            assignment = self._auth_client.role_assignments.create(
                scope=resource_scope,
                role_assignment_name=assignment_name,
                parameters=assignment_params
            )
            
            return {
                'success': True,
                'assignment_id': assignment.id,
                'role_name': role_name,
                'user_principal_id': user_principal_id,
                'resource_scope': resource_scope
            }
            
        except Exception as e:
            logger.error(f"Error assigning role {role_name} to user {user_principal_id}: {e}")
            return {'error': str(e)}
    
    def get_role_assignment_instructions(self, operation: str, resource_type: str) -> Dict[str, Any]:
        """Get instructions for assigning the required roles for an operation."""
        if operation not in self.REQUIRED_PERMISSIONS:
            return {'error': f'Unknown operation: {operation}'}
        
        required_roles = self.REQUIRED_PERMISSIONS[operation]
        
        instructions = {
            'operation': operation,
            'resource_type': resource_type,
            'required_roles': required_roles,
            'instructions': []
        }
        
        for role in required_roles:
            if resource_type == 'ai_foundry_account':
                scope_example = "/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices/accounts/{account_name}"
            elif resource_type == 'ai_foundry_hub':
                scope_example = "/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{hub_name}"
            elif resource_type == 'subscription':
                scope_example = "/subscriptions/{subscription_id}"
            else:
                scope_example = "{resource_scope}"
            
            instructions['instructions'].append({
                'role': role,
                'scope_example': scope_example,
                'azure_cli_command': f"az role assignment create --assignee {{user_email}} --role '{role}' --scope '{scope_example}'",
                'description': self._get_role_description(role)
            })
        
        return instructions
    
    def _get_role_description(self, role_name: str) -> str:
        """Get a description of what a role allows."""
        descriptions = {
            'Azure AI User': 'Allows access to AI Foundry accounts and basic operations',
            'Azure AI Administrator': 'Full administrative access to AI Foundry resources',
            'Azure AI Developer': 'Development access to AI Foundry resources',
            'Cognitive Services OpenAI User': 'Access to OpenAI services for inference',
            'Cognitive Services OpenAI Contributor': 'Full access to OpenAI services including management',
            'Search Index Data Contributor': 'Read and write access to search indexes',
            'Search Service Contributor': 'Management access to search services',
            'Owner': 'Full access to all resources and ability to assign roles',
            'Contributor': 'Full access to all resources except role assignment',
            'Reader': 'Read-only access to resources'
        }
        
        return descriptions.get(role_name, 'Standard Azure role')
    
    def validate_rbac_setup(self, user_principal_id: str, ai_foundry_resources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate RBAC setup for AI Foundry resources."""
        validation_results = {
            'user_principal_id': user_principal_id,
            'overall_status': 'checking',
            'resource_permissions': [],
            'missing_permissions': [],
            'recommendations': []
        }
        
        has_any_issues = False
        
        for resource in ai_foundry_resources:
            resource_scope = resource.get('id', '')
            resource_type = resource.get('type', 'unknown')
            
            # Check different operations based on resource type
            operations_to_check = ['ai_foundry_account_access']
            if resource_type == 'ai_foundry_account':
                operations_to_check.extend(['agent_deployment', 'search_integration'])
            elif resource_type == 'ai_foundry_hub':
                operations_to_check.append('project_creation')
            
            resource_result = {
                'resource': resource,
                'scope': resource_scope,
                'operations': {}
            }
            
            for operation in operations_to_check:
                perm_check = self.check_required_permissions(
                    user_principal_id, resource_scope, operation
                )
                
                resource_result['operations'][operation] = perm_check
                
                if not perm_check.get('has_permission', False):
                    has_any_issues = True
                    validation_results['missing_permissions'].extend(
                        perm_check.get('missing_roles', [])
                    )
            
            validation_results['resource_permissions'].append(resource_result)
        
        # Generate recommendations
        if has_any_issues:
            validation_results['overall_status'] = 'issues_found'
            validation_results['recommendations'] = self._generate_rbac_recommendations(
                validation_results['missing_permissions']
            )
        else:
            validation_results['overall_status'] = 'all_good'
        
        return validation_results
    
    def _generate_rbac_recommendations(self, missing_roles: List[str]) -> List[Dict[str, str]]:
        """Generate recommendations for fixing RBAC issues."""
        unique_missing = list(set(missing_roles))
        recommendations = []
        
        for role in unique_missing:
            recommendations.append({
                'role': role,
                'action': f'Assign {role} role to user',
                'priority': 'high' if role in ['Azure AI User', 'Cognitive Services OpenAI User'] else 'medium',
                'description': self._get_role_description(role)
            })
        
        return recommendations
    
    def check_resource_permissions(self, resource_id: str, resource_type: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Check permissions for a specific resource.
        Returns (permissions_list, errors_list) to match UI expectations.
        """
        errors = []
        permissions_list = []
        
        try:
            # Extract subscription ID from resource ID and initialize auth client
            subscription_id = self._extract_subscription_id(resource_id)
            if not subscription_id:
                errors.append("Could not extract subscription ID from resource ID")
                return permissions_list, errors
            
            # Ensure authorization client is initialized
            if not self._auth_client or self._subscription_id != subscription_id:
                self.set_subscription(subscription_id)
            
            # Get current user's principal ID
            user_principal_id = self.get_current_user_principal_id()
            if not user_principal_id:
                errors.append("Could not determine current user principal ID")
                return permissions_list, errors
            
            # Determine operation type based on resource type
            if 'CognitiveServices' in resource_type:
                operation = 'ai_foundry_account_access'
            elif 'MachineLearningServices' in resource_type:
                operation = 'ai_foundry_account_access'  # Treat ML workspaces similar to accounts
            else:
                operation = 'ai_foundry_account_access'  # Default operation
            
            # Check user permissions for the resource
            user_perms = self.check_user_permissions(user_principal_id, resource_id)
            if 'error' in user_perms:
                errors.append(f"Permission check failed: {user_perms['error']}")
                return permissions_list, errors
            
            user_role_names = [role['role_name'] for role in user_perms.get('roles', [])]
            
            # Check required permissions for the operation
            required_perms = self.check_required_permissions(user_principal_id, resource_id, operation)
            if 'error' in required_perms:
                errors.append(f"Required permission check failed: {required_perms['error']}")
                return permissions_list, errors
            
            # Get required roles for this operation
            required_roles = self.REQUIRED_PERMISSIONS.get(operation, [])
            
            # Build permissions list in the format expected by UI
            for role in required_roles:
                has_role = role in user_role_names
                permissions_list.append({
                    'role_name': role,
                    'status': 'granted' if has_role else 'missing',
                    'required': True,
                    'description': self._get_role_description(role)
                })
            
            # Add any additional roles the user has that aren't required
            for role in user_role_names:
                if role not in required_roles:
                    permissions_list.append({
                        'role_name': role,
                        'status': 'granted',
                        'required': False,
                        'description': self._get_role_description(role)
                    })
            
        except Exception as e:
            logger.error(f"Error checking resource permissions: {e}")
            errors.append(f"Unexpected error: {str(e)}")
        
        return permissions_list, errors

    def validate_cli_setup(self) -> Tuple[bool, List[str]]:
        """
        Validate Azure CLI setup for RBAC operations.
        Returns (is_valid, status_messages) to match UI expectations.
        """
        status_messages = []
        is_valid = True
        
        try:
            # Check if user can be identified
            user_principal_id = self.get_current_user_principal_id()
            if user_principal_id:
                status_messages.append("✅ User identity successfully obtained")
            else:
                status_messages.append("❌ Could not obtain user identity")
                is_valid = False
            
            # Check if Azure CLI is authenticated
            try:
                # Try to make a simple Azure API call
                token = self.credential.get_token("https://management.azure.com/.default")
                if token:
                    status_messages.append("✅ Azure CLI authentication verified")
                else:
                    status_messages.append("❌ Azure CLI authentication failed")
                    is_valid = False
            except Exception as e:
                status_messages.append(f"❌ Azure CLI auth error: {str(e)}")
                is_valid = False
            
            # Check if subscription is set
            if hasattr(self, '_subscription_id') and self._subscription_id:
                status_messages.append(f"✅ Subscription set: {self._subscription_id[:8]}...")
            else:
                status_messages.append("⚠️ No subscription configured")
                # This is a warning, not necessarily a failure
                
        except Exception as e:
            logger.error(f"CLI setup validation error: {e}")
            status_messages.append(f"❌ Setup validation error: {str(e)}")
            is_valid = False
        
        return is_valid, status_messages

    def generate_rbac_assignment_commands(self, resource_id: str, resource_type: str, 
                                          permissions: Dict[str, Any]) -> List[str]:
        """
        Generate Azure CLI commands to assign missing RBAC permissions.
        """
        commands = []
        
        try:
            logger.info(f"Generating RBAC commands for resource: {resource_id}")
            logger.info(f"Permissions type: {type(permissions)}, content: {permissions}")
            
            # Get current user's principal ID
            user_principal_id = self.get_current_user_principal_id()
            if not user_principal_id:
                return ["# Error: Could not determine user principal ID"]
            
            # Handle both dict and list formats for permissions
            if isinstance(permissions, dict):
                missing_roles = permissions.get('missing_required', [])
                logger.info(f"Extracted missing roles from dict: {missing_roles}")
            elif isinstance(permissions, list):
                # If it's a list, treat it as the missing roles directly
                missing_roles = permissions
                logger.info(f"Using permissions list directly: {missing_roles}")
            else:
                logger.error(f"Invalid permissions format: {type(permissions)}")
                return ["# Error: Invalid permissions format"]
            
            if not missing_roles:
                return ["# No missing required permissions found."]
            
            # Generate assignment commands for each missing role
            for role_name in missing_roles:
                try:
                    # Ensure role_name is a string
                    if isinstance(role_name, dict):
                        # If it's a dict, try to extract the role name
                        if 'role_name' in role_name:
                            actual_role_name = role_name['role_name']
                        else:
                            logger.warning(f"Role dict missing 'role_name' key: {role_name}")
                            commands.append(f"# Error: Invalid role format - {role_name}")
                            continue
                    else:
                        actual_role_name = str(role_name)
                    
                    # Get the role definition ID
                    if actual_role_name in self.ROLE_DEFINITIONS:
                        role_def_id = self.ROLE_DEFINITIONS[actual_role_name].format(
                            subscription_id=self._subscription_id
                        )
                        
                        command = (
                            f"az role assignment create "
                            f"--assignee {user_principal_id} "
                            f"--role \"{role_def_id}\" "
                            f"--scope \"{resource_id}\""
                        )
                        commands.append(command)
                    else:
                        commands.append(f"# Unknown role: {actual_role_name}")
                except Exception as role_error:
                    logger.error(f"Error processing role {role_name}: {role_error}")
                    commands.append(f"# Error processing role {role_name}: {str(role_error)}")
            
        except Exception as e:
            logger.error(f"Error generating RBAC commands: {e}")
            commands.append(f"# Error generating commands: {str(e)}")
        
        return commands

    def get_rbac_setup_guide(self, resource_type: str) -> Dict[str, Any]:
        """
        Get a setup guide for RBAC configuration for a specific resource type.
        """
        if 'CognitiveServices' in resource_type:
            return {
                'resource_type': 'AI Foundry Account',
                'required_roles': [
                    'Azure AI User',
                    'Cognitive Services OpenAI User'
                ],
                'manual_steps': [
                    "Go to Azure Portal → Your AI Foundry Account → Access Control (IAM)",
                    "Click 'Add role assignment'",
                    "Select 'Azure AI User' role and assign to your user",
                    "Add another assignment for 'Cognitive Services OpenAI User' role",
                    "Save and wait for propagation (may take 5-10 minutes)"
                ],
                'documentation': "https://docs.microsoft.com/azure/cognitive-services/openai/how-to/role-based-access-control"
            }
        elif 'MachineLearningServices' in resource_type:
            return {
                'resource_type': 'AI Foundry Hub',
                'required_roles': [
                    'Azure AI User',
                    'AzureML Data Scientist'
                ],
                'manual_steps': [
                    "Go to Azure Portal → Your AI Foundry Hub → Access Control (IAM)",
                    "Click 'Add role assignment'",
                    "Select 'Azure AI User' role and assign to your user",
                    "Add another assignment for 'AzureML Data Scientist' role",
                    "Save and wait for propagation (may take 5-10 minutes)"
                ],
                'documentation': "https://docs.microsoft.com/azure/machine-learning/how-to-assign-roles"
            }
        else:
            return {
                'resource_type': 'Unknown',
                'required_roles': ['Azure AI User'],
                'manual_steps': [
                    "Refer to Azure documentation for specific RBAC requirements"
                ],
                'documentation': "https://docs.microsoft.com/azure/role-based-access-control/"
            }
    
    def _extract_subscription_id(self, resource_id: str) -> Optional[str]:
        """Extract subscription ID from an Azure resource ID."""
        try:
            # Azure resource IDs have the format:
            # /subscriptions/{subscription_id}/resourceGroups/{rg}/providers/{provider}/{resource_type}/{resource_name}
            parts = resource_id.split('/')
            if len(parts) >= 3 and parts[1] == 'subscriptions':
                return parts[2]
            else:
                logger.warning(f"Could not extract subscription ID from resource ID: {resource_id}")
                return None
        except Exception as e:
            logger.error(f"Error extracting subscription ID from {resource_id}: {e}")
            return None

# Global instance
ai_foundry_rbac = AIFoundryRBACService()
