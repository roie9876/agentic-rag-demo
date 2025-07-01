"""
Automated RBAC Management for Private Azure Resources

This module provides automated RBAC role assignment for Azure AI Search
managed identity to access other Azure services like OpenAI and Document Intelligence.
"""

import os
import subprocess
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

@dataclass
class AzureResourceInfo:
    """Information about an Azure resource."""
    name: str
    resource_group: str
    resource_type: str
    principal_id: Optional[str] = None
    subscription_id: Optional[str] = None

class AzureRBACManager:
    """Manages RBAC role assignments for Azure services."""
    
    def __init__(self):
        self.subscription_id = self._get_subscription_id()
        
    def _get_subscription_id(self) -> Optional[str]:
        """Get the current Azure subscription ID."""
        try:
            result = subprocess.run(
                ["az", "account", "show", "--query", "id", "-o", "tsv"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logging.error(f"Failed to get subscription ID: {e}")
        return None
    
    def _run_az_command(self, command: List[str], timeout: int = 30) -> Tuple[bool, str]:
        """Run an Azure CLI command and return success status and output."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            logging.error(f"Command timed out: {' '.join(command)}")
            return False, "Command timed out"
        except Exception as e:
            logging.error(f"Command failed: {' '.join(command)}, Error: {e}")
            return False, str(e)
    
    def discover_azure_resources_from_env(self) -> Dict[str, AzureResourceInfo]:
        """Discover Azure resources from environment variables."""
        resources = {}
        
        # Azure AI Search
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
        if search_endpoint:
            # Extract service name from endpoint: https://service-name.search.windows.net
            if "://" in search_endpoint:
                service_name = search_endpoint.split("://")[1].split(".")[0]
                resources["search"] = AzureResourceInfo(
                    name=service_name,
                    resource_group="",  # Will be discovered
                    resource_type="Microsoft.Search/searchServices"
                )
        
        # Azure OpenAI
        openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT_41", "")
        if openai_endpoint:
            # Extract service name from endpoint: https://service-name.openai.azure.com/
            if "://" in openai_endpoint:
                service_name = openai_endpoint.split("://")[1].split(".")[0]
                resources["openai"] = AzureResourceInfo(
                    name=service_name,
                    resource_group="",  # Will be discovered
                    resource_type="Microsoft.CognitiveServices/accounts"
                )
        
        # Document Intelligence
        doc_intel_endpoint = os.getenv("DOCUMENT_INTEL_ENDPOINT") or os.getenv("AZURE_FORMREC_ENDPOINT", "")
        if doc_intel_endpoint:
            # Extract service name from endpoint: https://service-name.cognitiveservices.azure.com/
            if "://" in doc_intel_endpoint:
                service_name = doc_intel_endpoint.split("://")[1].split(".")[0]
                resources["document_intelligence"] = AzureResourceInfo(
                    name=service_name,
                    resource_group="",  # Will be discovered
                    resource_type="Microsoft.CognitiveServices/accounts"
                )
        
        return resources
    
    def find_resource_group(self, service_name: str, service_type: str) -> Optional[str]:
        """Find the resource group for a given service."""
        try:
            if service_type == "Microsoft.Search/searchServices":
                # Search for AI Search service
                success, output = self._run_az_command([
                    "az", "resource", "list",
                    "--resource-type", "Microsoft.Search/searchServices",
                    "--query", f"[?name=='{service_name}'].resourceGroup",
                    "-o", "tsv"
                ])
            else:
                # Search for Cognitive Services
                success, output = self._run_az_command([
                    "az", "resource", "list",
                    "--resource-type", "Microsoft.CognitiveServices/accounts",
                    "--query", f"[?name=='{service_name}'].resourceGroup",
                    "-o", "tsv"
                ])
            
            if success and output.strip():
                return output.strip()
                
        except Exception as e:
            logging.error(f"Failed to find resource group for {service_name}: {e}")
        
        return None
    
    def get_managed_identity_principal_id(self, service_name: str, resource_group: str, service_type: str) -> Optional[str]:
        """Get the managed identity principal ID for a service."""
        try:
            if service_type == "Microsoft.Search/searchServices":
                success, output = self._run_az_command([
                    "az", "search", "service", "show",
                    "--name", service_name,
                    "--resource-group", resource_group,
                    "--query", "identity.principalId",
                    "-o", "tsv"
                ])
            else:
                success, output = self._run_az_command([
                    "az", "cognitiveservices", "account", "show",
                    "--name", service_name,
                    "--resource-group", resource_group,
                    "--query", "identity.principalId",
                    "-o", "tsv"
                ])
            
            if success and output.strip() and output.strip() != "None":
                return output.strip()
                
        except Exception as e:
            logging.error(f"Failed to get principal ID for {service_name}: {e}")
        
        return None
    
    def check_role_assignment(self, principal_id: str, role: str, scope: str) -> bool:
        """Check if a role assignment already exists."""
        try:
            success, output = self._run_az_command([
                "az", "role", "assignment", "list",
                "--assignee", principal_id,
                "--role", role,
                "--scope", scope,
                "--query", "[].principalId",
                "-o", "tsv"
            ])
            
            return success and principal_id in output
            
        except Exception as e:
            logging.error(f"Failed to check role assignment: {e}")
            return False
    
    def assign_role(self, principal_id: str, role: str, scope: str) -> bool:
        """Assign a role to a principal."""
        try:
            # Check if assignment already exists
            if self.check_role_assignment(principal_id, role, scope):
                logging.info(f"Role assignment already exists: {role} for {principal_id}")
                return True
            
            success, output = self._run_az_command([
                "az", "role", "assignment", "create",
                "--role", role,
                "--assignee", principal_id,
                "--scope", scope
            ])
            
            if success:
                logging.info(f"Successfully assigned role {role} to {principal_id}")
                return True
            else:
                logging.error(f"Failed to assign role {role}: {output}")
                return False
                
        except Exception as e:
            logging.error(f"Failed to assign role {role}: {e}")
            return False
    
    def check_rbac_status(self) -> Dict[str, Any]:
        """Check the current RBAC status for Azure AI Search to OpenAI access."""
        try:
            # Discover resources
            resources = self.discover_azure_resources_from_env()
            
            if "search" not in resources:
                return {
                    "rbac_configured": False,
                    "message": "Azure AI Search endpoint not found in environment variables",
                    "can_fix": False,
                    "details": {}
                }
            
            if "openai" not in resources:
                return {
                    "rbac_configured": False,
                    "message": "Azure OpenAI endpoint not found in environment variables",
                    "can_fix": False,
                    "details": {}
                }
            
            # Find resource groups
            search_rg = self.find_resource_group(resources["search"].name, resources["search"].resource_type)
            if not search_rg:
                return {
                    "rbac_configured": False,
                    "message": f"Could not find resource group for Azure AI Search service: {resources['search'].name}",
                    "can_fix": False,
                    "details": {}
                }
            
            openai_rg = self.find_resource_group(resources["openai"].name, resources["openai"].resource_type)
            if not openai_rg:
                return {
                    "rbac_configured": False,
                    "message": f"Could not find resource group for Azure OpenAI service: {resources['openai'].name}",
                    "can_fix": False,
                    "details": {}
                }
            
            # Get Search service managed identity
            search_principal_id = self.get_managed_identity_principal_id(
                resources["search"].name,
                search_rg,
                resources["search"].resource_type
            )
            
            if not search_principal_id:
                return {
                    "rbac_configured": False,
                    "message": f"Azure AI Search service {resources['search'].name} does not have managed identity enabled",
                    "can_fix": False,
                    "details": {}
                }
            
            # Create scope for OpenAI service
            openai_scope = (
                f"/subscriptions/{self.subscription_id}"
                f"/resourceGroups/{openai_rg}"
                f"/providers/Microsoft.CognitiveServices/accounts/{resources['openai'].name}"
            )
            
            # Check all required roles
            required_roles = [
                "Cognitive Services OpenAI User",
                "Azure AI Developer", 
                "Reader"
            ]
            
            role_status = {}
            all_configured = True
            
            for role in required_roles:
                is_assigned = self.check_role_assignment(search_principal_id, role, openai_scope)
                role_status[role] = is_assigned
                if not is_assigned:
                    all_configured = False
            
            # Prepare details
            details = {
                "search_service": resources["search"].name,
                "search_resource_group": search_rg,
                "openai_service": resources["openai"].name,
                "openai_resource_group": openai_rg,
                "search_principal_id": search_principal_id,
                "role_assignments": role_status,
                "required_roles": required_roles
            }
            
            if all_configured:
                return {
                    "rbac_configured": True,
                    "message": f"All required RBAC roles are assigned for {resources['search'].name} → {resources['openai'].name}",
                    "can_fix": True,
                    "details": details
                }
            else:
                missing_roles = [role for role, assigned in role_status.items() if not assigned]
                return {
                    "rbac_configured": False,
                    "message": f"Missing RBAC roles: {', '.join(missing_roles)}",
                    "can_fix": True,
                    "details": details
                }
                
        except Exception as e:
            logging.error(f"Failed to check RBAC status: {e}")
            return {
                "rbac_configured": False,
                "message": f"Error checking RBAC status: {str(e)}",
                "can_fix": False,
                "details": {}
            }

    def setup_search_to_openai_rbac(self) -> Tuple[bool, str]:
        """Set up RBAC for Azure AI Search to access Azure OpenAI with all required roles."""
        try:
            # Discover resources
            resources = self.discover_azure_resources_from_env()
            
            if "search" not in resources:
                return False, "Azure AI Search endpoint not found in environment variables"
            
            if "openai" not in resources:
                return False, "Azure OpenAI endpoint not found in environment variables"
            
            # Find resource groups
            search_rg = self.find_resource_group(resources["search"].name, resources["search"].resource_type)
            if not search_rg:
                return False, f"Could not find resource group for Azure AI Search service: {resources['search'].name}"
            
            openai_rg = self.find_resource_group(resources["openai"].name, resources["openai"].resource_type)
            if not openai_rg:
                return False, f"Could not find resource group for Azure OpenAI service: {resources['openai'].name}"
            
            # Get Search service managed identity
            search_principal_id = self.get_managed_identity_principal_id(
                resources["search"].name,
                search_rg,
                resources["search"].resource_type
            )
            
            if not search_principal_id:
                return False, f"Azure AI Search service {resources['search'].name} does not have managed identity enabled"
            
            # Create scope for OpenAI service
            openai_scope = (
                f"/subscriptions/{self.subscription_id}"
                f"/resourceGroups/{openai_rg}"
                f"/providers/Microsoft.CognitiveServices/accounts/{resources['openai'].name}"
            )
            
            # All required roles for Azure AI Search to access OpenAI in private mode
            required_roles = [
                "Cognitive Services OpenAI User",
                "Azure AI Developer", 
                "Reader"
            ]
            
            success_count = 0
            failed_roles = []
            
            # Assign all required roles
            for role in required_roles:
                if self.assign_role(search_principal_id, role, openai_scope):
                    success_count += 1
                    logging.info(f"✅ Assigned role: {role}")
                else:
                    failed_roles.append(role)
                    logging.error(f"❌ Failed to assign role: {role}")
            
            if success_count == len(required_roles):
                return True, (
                    f"Successfully configured all RBAC roles for Azure AI Search ({resources['search'].name}) "
                    f"to access Azure OpenAI ({resources['openai'].name}). "
                    f"Assigned roles: {', '.join(required_roles)}"
                )
            elif success_count > 0:
                return False, (
                    f"Partially configured RBAC for Azure AI Search ({resources['search'].name}) "
                    f"to access Azure OpenAI ({resources['openai'].name}). "
                    f"Successfully assigned: {success_count}/{len(required_roles)} roles. "
                    f"Failed roles: {', '.join(failed_roles)}"
                )
            else:
                return False, f"Failed to assign any RBAC roles. Failed roles: {', '.join(failed_roles)}"
                
        except Exception as e:
            logging.error(f"Failed to setup Search to OpenAI RBAC: {e}")
            return False, f"Error setting up RBAC: {str(e)}"
    
    def setup_all_required_rbac(self) -> Dict[str, Tuple[bool, str]]:
        """Set up all required RBAC assignments for the application."""
        results = {}
        
        # Setup Search to OpenAI RBAC
        results["search_to_openai"] = self.setup_search_to_openai_rbac()
        
        # TODO: Add more RBAC setups as needed
        # results["app_to_search"] = self.setup_app_to_search_rbac()
        # results["app_to_document_intelligence"] = self.setup_app_to_document_intelligence_rbac()
        
        return results

# Convenience function for use in health checks
def check_and_fix_rbac() -> Dict[str, Tuple[bool, str]]:
    """Check and automatically fix RBAC issues."""
    manager = AzureRBACManager()
    return manager.setup_all_required_rbac()

# CLI interface for manual execution
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage Azure RBAC for Agentic RAG Demo")
    parser.add_argument("--setup-search-openai", action="store_true", 
                       help="Setup RBAC for Azure AI Search to access Azure OpenAI")
    parser.add_argument("--setup-all", action="store_true",
                       help="Setup all required RBAC assignments")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    manager = AzureRBACManager()
    
    if args.setup_search_openai:
        success, message = manager.setup_search_to_openai_rbac()
        print(f"{'✅' if success else '❌'} {message}")
    elif args.setup_all:
        results = manager.setup_all_required_rbac()
        for operation, (success, message) in results.items():
            print(f"{'✅' if success else '❌'} {operation}: {message}")
    else:
        print("Use --setup-search-openai or --setup-all to configure RBAC")
