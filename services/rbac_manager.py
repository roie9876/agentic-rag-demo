"""
RBAC Management Module
---------------------
Handles RBAC permission checking and assignment for AI Foundry resources.
"""

import json
import subprocess
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class RBACAssignment:
    """Represents an RBAC role assignment."""
    role_name: str
    scope: str
    principal_id: str
    assignment_id: Optional[str] = None

class RBACManager:
    """Manages RBAC permissions for AI Foundry resources."""
    
    # Role definitions for different resource types
    AI_FOUNDRY_ACCOUNT_ROLES = {
        "Azure AI User": {
            "id": "64702f94-c441-49e6-a78b-ef80e0188fee",
            "description": "Required for AI Foundry account operations",
            "required": True
        },
        "Cognitive Services User": {
            "id": "a97b65f3-24c7-4388-baec-2e87135dc908", 
            "description": "Required for accessing AI services",
            "required": True
        },
        "Contributor": {
            "id": "b24988ac-6180-42a0-ab88-20f7382dd24c",
            "description": "Required for creating and managing resources",
            "required": False
        }
    }
    
    AI_FOUNDRY_HUB_ROLES = {
        "Azure AI User": {
            "id": "64702f94-c441-49e6-a78b-ef80e0188fee",
            "description": "Required for AI Foundry hub operations",
            "required": True
        },
        "AzureML Data Scientist": {
            "id": "f6c7c914-8db3-469d-8ca1-694a8f32e121",
            "description": "Required for ML workspace access",
            "required": True
        },
        "Machine Learning Workspace Contributor": {
            "id": "e504eca8-c7bb-4b4a-8c47-63c7c5f9b5f7",
            "description": "Required for managing ML workspace resources",
            "required": False
        }
    }
    
    def __init__(self):
        """Initialize the RBAC manager."""
        self.current_user_info = None
        self._load_current_user_info()
    
    def _load_current_user_info(self) -> None:
        """Load current user information from Azure CLI."""
        try:
            result = subprocess.run(
                ["az", "account", "show", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                account_info = json.loads(result.stdout)
                self.current_user_info = {
                    'user_id': account_info.get('user', {}).get('name', 'Unknown'),
                    'tenant_id': account_info.get('tenantId', ''),
                    'subscription_id': account_info.get('id', '')
                }
        except Exception as e:
            logger.error(f"Failed to load user info: {e}")
    
    def check_resource_permissions(self, resource_id: str, resource_type: str) -> Tuple[List[Dict], List[str]]:
        """
        Check current user's permissions on a resource.
        Returns (permissions_status, errors).
        """
        permissions = []
        errors = []
        
        # Get role definitions for resource type
        if resource_type == "account":
            role_defs = self.AI_FOUNDRY_ACCOUNT_ROLES
        elif resource_type == "hub":
            role_defs = self.AI_FOUNDRY_HUB_ROLES
        else:
            errors.append(f"Unknown resource type: {resource_type}")
            return permissions, errors
        
        try:
            # Get current role assignments
            current_assignments = self._get_current_role_assignments(resource_id)
            assigned_roles = {assignment['role_name'] for assignment in current_assignments}
            
            # Check each required role
            for role_name, role_info in role_defs.items():
                status = "granted" if role_name in assigned_roles else "missing"
                
                permissions.append({
                    'role_name': role_name,
                    'role_id': role_info['id'],
                    'description': role_info['description'],
                    'required': role_info['required'],
                    'status': status,
                    'scope': resource_id
                })
        
        except Exception as e:
            error_msg = f"Failed to check permissions: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        return permissions, errors
    
    def _get_current_role_assignments(self, resource_id: str) -> List[Dict]:
        """Get current user's role assignments on a resource."""
        assignments = []
        
        try:
            result = subprocess.run([
                "az", "role", "assignment", "list",
                "--scope", resource_id,
                "--assignee", self.current_user_info.get('user_id', ''),
                "--output", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                role_assignments = json.loads(result.stdout)
                
                for assignment in role_assignments:
                    assignments.append({
                        'role_name': assignment.get('roleDefinitionName', 'Unknown'),
                        'role_id': assignment.get('roleDefinitionId', ''),
                        'scope': assignment.get('scope', ''),
                        'principal_id': assignment.get('principalId', '')
                    })
        
        except Exception as e:
            logger.error(f"Failed to get role assignments: {e}")
        
        return assignments
    
    def generate_rbac_assignment_commands(self, resource_id: str, resource_type: str, missing_permissions) -> List[str]:
        """Generate Azure CLI commands to assign missing roles."""
        commands = []
        
        if not self.current_user_info:
            return ["# Error: Could not determine current user. Please run 'az login' first."]
        
        user_id = self.current_user_info.get('user_id', '')
        
        # Handle different input formats
        if isinstance(missing_permissions, dict) and 'missing_required' in missing_permissions:
            # Legacy format: {'missing_required': ['role1', 'role2']}
            role_names = missing_permissions['missing_required']
            for role_name in role_names:
                command = f"""az role assignment create \\
  --assignee "{user_id}" \\
  --role "{role_name}" \\
  --scope "{resource_id}" \\
  --description "AI Foundry access for {resource_type}"""
                commands.append(command)
        elif isinstance(missing_permissions, list):
            # New format: [{'role_name': 'role1', 'status': 'missing', 'required': True}, ...]
            for permission in missing_permissions:
                if isinstance(permission, dict):
                    if permission.get('status') == 'missing' and permission.get('required', False):
                        role_name = permission.get('role_name', '')
                        if role_name:
                            command = f"""az role assignment create \\
  --assignee "{user_id}" \\
  --role "{role_name}" \\
  --scope "{resource_id}" \\
  --description "AI Foundry access for {resource_type}"""
                            commands.append(command)
                else:
                    # Handle simple permission objects that just have role_name
                    if hasattr(permission, 'role_name'):
                        role_name = permission.role_name
                    elif isinstance(permission, str):
                        role_name = permission
                    else:
                        continue
                    
                    command = f"""az role assignment create \\
  --assignee "{user_id}" \\
  --role "{role_name}" \\
  --scope "{resource_id}" \\
  --description "AI Foundry access for {resource_type}"""
                    commands.append(command)
        
        if not commands:
            commands.append("# No missing required permissions found.")
        
        return commands
    
    def assign_role(self, resource_id: str, role_name: str, assignee: Optional[str] = None) -> Tuple[bool, str]:
        """Assign a role to a user on a resource."""
        try:
            if not assignee:
                assignee = self.current_user_info.get('user_id', '')
            
            if not assignee:
                return False, "Could not determine assignee. Please run 'az login' first."
            
            result = subprocess.run([
                "az", "role", "assignment", "create",
                "--assignee", assignee,
                "--role", role_name,
                "--scope", resource_id,
                "--output", "json"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                assignment_result = json.loads(result.stdout)
                return True, f"Successfully assigned role '{role_name}'"
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                return False, f"Failed to assign role: {error_msg}"
        
        except Exception as e:
            return False, f"Error assigning role: {str(e)}"
    
    def assign_multiple_roles(self, resource_id: str, role_names: List[str], assignee: Optional[str] = None) -> List[Tuple[str, bool, str]]:
        """
        Assign multiple roles to a user on a resource.
        Returns a list of (role_name, success, message) tuples.
        """
        results = []
        
        for role_name in role_names:
            try:
                success, message = self.assign_role(resource_id, role_name, assignee)
                results.append((role_name, success, message))
            except Exception as e:
                results.append((role_name, False, f"Error assigning role: {str(e)}"))
        
        return results
    
    def check_subscription_permissions(self, subscription_id: str) -> Tuple[bool, List[str]]:
        """Check if user has necessary permissions at subscription level."""
        required_permissions = []
        errors = []
        
        try:
            # Check if user can list resources
            result = subprocess.run([
                "az", "resource", "list",
                "--subscription", subscription_id,
                "--output", "json",
                "--query", "[0]"  # Just get first resource to test access
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                required_permissions.append("✅ Can list resources in subscription")
            else:
                required_permissions.append("❌ Cannot list resources in subscription")
                errors.append("Missing permissions to list subscription resources")
            
            # Check if user can list role assignments
            result = subprocess.run([
                "az", "role", "assignment", "list",
                "--subscription", subscription_id,
                "--output", "json",
                "--query", "[0]"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                required_permissions.append("✅ Can list role assignments")
            else:
                required_permissions.append("❌ Cannot list role assignments")
                errors.append("Missing permissions to list role assignments")
        
        except Exception as e:
            errors.append(f"Error checking subscription permissions: {str(e)}")
        
        return len(errors) == 0, required_permissions
    
    def get_rbac_setup_guide(self, resource_type: str) -> Dict[str, List[str]]:
        """Get setup guide for RBAC permissions."""
        if resource_type == "account":
            roles = self.AI_FOUNDRY_ACCOUNT_ROLES
        elif resource_type == "hub":
            roles = self.AI_FOUNDRY_HUB_ROLES
        else:
            return {"error": ["Unknown resource type"]}
        
        guide = {
            "required_roles": [],
            "optional_roles": [],
            "commands": [],
            "manual_steps": []
        }
        
        for role_name, role_info in roles.items():
            if role_info['required']:
                guide['required_roles'].append(f"• {role_name}: {role_info['description']}")
            else:
                guide['optional_roles'].append(f"• {role_name}: {role_info['description']}")
        
        guide['manual_steps'] = [
            "1. Go to Azure Portal",
            "2. Navigate to your AI Foundry resource",
            "3. Click on 'Access control (IAM)'",
            "4. Click '+ Add' -> 'Add role assignment'",
            "5. Select the required role",
            "6. Search for and select your user account",
            "7. Click 'Review + assign'"
        ]
        
        return guide
    
    def validate_cli_setup(self) -> Tuple[bool, List[str]]:
        """Validate Azure CLI setup for RBAC operations."""
        checks = []
        all_passed = True
        
        try:
            # Check if az CLI is installed
            result = subprocess.run(["az", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                checks.append("✅ Azure CLI is installed")
            else:
                checks.append("❌ Azure CLI is not installed")
                all_passed = False
        except FileNotFoundError:
            checks.append("❌ Azure CLI is not installed")
            all_passed = False
        except Exception as e:
            checks.append(f"❌ Error checking Azure CLI: {e}")
            all_passed = False
        
        try:
            # Check if user is logged in
            result = subprocess.run(["az", "account", "show"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                checks.append("✅ Logged in to Azure CLI")
            else:
                checks.append("❌ Not logged in to Azure CLI (run 'az login')")
                all_passed = False
        except Exception as e:
            checks.append(f"❌ Error checking Azure CLI login: {e}")
            all_passed = False
        
        try:
            # Check if user has necessary CLI extensions
            result = subprocess.run(["az", "extension", "list", "--output", "json"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                extensions = json.loads(result.stdout)
                extension_names = {ext['name'] for ext in extensions}
                
                if 'ai' in extension_names:
                    checks.append("✅ Azure AI CLI extension is installed")
                else:
                    checks.append("⚠️ Azure AI CLI extension not installed (optional)")
                
                if 'ml' in extension_names:
                    checks.append("✅ Azure ML CLI extension is installed")
                else:
                    checks.append("⚠️ Azure ML CLI extension not installed (optional)")
            
        except Exception as e:
            checks.append(f"⚠️ Could not check CLI extensions: {e}")
        
        return all_passed, checks
    
    def validate_user_permissions(self, resource_id: str, resource_type: str) -> Dict[str, Any]:
        """
        Validate if the current user has sufficient permissions to assign roles.
        Returns a dictionary with validation results.
        """
        validation_result = {
            "can_assign_roles": False,
            "missing_permissions": [],
            "recommendations": []
        }
        
        try:
            # Check if user can list role assignments (indicates some level of access)
            result = subprocess.run([
                "az", "role", "assignment", "list",
                "--scope", resource_id,
                "--output", "json",
                "--query", "[0]"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                validation_result["can_assign_roles"] = True
                validation_result["recommendations"].append("✅ User has sufficient permissions to manage roles")
            else:
                validation_result["missing_permissions"].append("Cannot list role assignments")
                validation_result["recommendations"].append("❌ User may not have sufficient permissions to assign roles")
                validation_result["recommendations"].append("💡 Try running: az role assignment create --help")
        
        except Exception as e:
            validation_result["missing_permissions"].append(f"Error checking permissions: {str(e)}")
        
        return validation_result
    
    def get_role_assignment_status(self, resource_id: str, role_names: List[str]) -> Dict[str, bool]:
        """
        Check the current assignment status of multiple roles.
        Returns a dictionary mapping role names to their assignment status.
        """
        status_map = {}
        
        if not self.current_user_info:
            return {role: False for role in role_names}
        
        user_id = self.current_user_info.get('user_id', '')
        
        for role_name in role_names:
            try:
                result = subprocess.run([
                    "az", "role", "assignment", "list",
                    "--scope", resource_id,
                    "--assignee", user_id,
                    "--role", role_name,
                    "--output", "json"
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    assignments = json.loads(result.stdout)
                    status_map[role_name] = len(assignments) > 0
                else:
                    status_map[role_name] = False
                    
            except Exception as e:
                logger.error(f"Error checking role assignment for {role_name}: {e}")
                status_map[role_name] = False
        
        return status_map
