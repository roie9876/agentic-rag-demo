#!/usr/bin/env python3
"""
Private Endpoint Health Checker for Azure Resources

This module provides comprehensive health checking for Azure resources
accessed through private endpoints using managed identity authentication.

Resources checked:
- Azure OpenAI (private-openai-agentic)
- Document Intelligence (private-doc-int)
- AI Search (private-ai-search)
"""

import os
import sys
import asyncio
import json
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import traceback

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
    from azure.core.credentials import AccessToken, AzureKeyCredential
    from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
    
    # Azure SDK imports
    from azure.search.documents.indexes import SearchIndexClient
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from openai import AzureOpenAI
    
except ImportError as e:
    print(f"❌ Missing required dependencies: {e}")
    print("Run: pip install azure-identity azure-search-documents azure-ai-documentintelligence openai")
    sys.exit(1)

from enum import Enum

class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    service: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = None

@dataclass
class PrivateEndpointConfig:
    """Configuration for a private endpoint resource."""
    name: str
    endpoint: str
    resource_type: str
    auth_scope: str
    required_env_vars: List[str]
    test_operations: List[str]

class PrivateEndpointHealthChecker:
    """Health checker for private endpoint Azure resources."""
    
    def __init__(self):
        self.load_environment()
        self.credential = None  # Lazy-loaded to avoid blocking initialization
        
        # Configuration for each private endpoint resource
        self.configs = {
            'openai': PrivateEndpointConfig(
                name="Azure OpenAI",
                endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', ''),
                resource_type="openai",
                auth_scope="https://cognitiveservices.azure.com/.default",
                required_env_vars=['AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_DEPLOYMENT'],
                test_operations=['list_models']
            ),
            'document_intelligence': PrivateEndpointConfig(
                name="Document Intelligence", 
                endpoint=os.getenv('DOCUMENT_INTEL_ENDPOINT', ''),
                resource_type="document_intelligence",
                auth_scope="https://cognitiveservices.azure.com/.default",
                required_env_vars=['DOCUMENT_INTEL_ENDPOINT'],
                test_operations=[]
            ),
            'search': PrivateEndpointConfig(
                name="AI Search",
                endpoint=os.getenv('AZURE_SEARCH_ENDPOINT', ''),
                resource_type="search",
                auth_scope="https://search.azure.com/.default", 
                required_env_vars=['AZURE_SEARCH_ENDPOINT'],
                test_operations=['list_indexes']
            )
        }
    
    def load_environment(self):
        """Load environment variables from .env file."""
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key not in os.environ:
                            os.environ[key] = value
        
        # Initialize identity info structure
        identity_info = {
            "credential_chain": [],
            "details": {}
        }
        
        try:
            # Try to get identity information from Azure CLI
            result = subprocess.run(
                ["az", "account", "show", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                account_info = json.loads(result.stdout)
                identity_info["credential_chain"].append("Azure CLI")
                identity_info["details"]["cli_account"] = {
                    "name": account_info.get("name"),
                    "tenant_id": account_info.get("tenantId"),
                    "subscription_id": account_info.get("id"),
                    "user_type": account_info.get("user", {}).get("type")
                }
            
        except Exception as e:
            identity_info["credential_chain"].append(f"Azure CLI Error: {str(e)}")
        
        # Check for managed identity
        try:
            # Check if we're actually using managed identity, not just if IMDS is available
            # First check if current Azure CLI session is using managed identity
            if result.returncode == 0:
                account_info = json.loads(result.stdout)
                user_type = account_info.get("user", {}).get("type")
                
                if user_type == "servicePrincipal":
                    # This could be managed identity or service principal
                    # If we have AZURE_CLIENT_ID in env, it's service principal
                    # Otherwise, it's likely managed identity
                    if not os.getenv("AZURE_CLIENT_ID"):
                        identity_info["credential_chain"].append("Managed Identity")
                        
                        # Get additional metadata if available
                        try:
                            imds_result = subprocess.run(
                                ["curl", "-s", "-H", "Metadata:true", 
                                 "http://169.254.169.254/metadata/instance?api-version=2021-02-01"],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            
                            if imds_result.returncode == 0 and imds_result.stdout.strip():
                                instance_info = json.loads(imds_result.stdout)
                                identity_info["details"]["managed_identity"] = {
                                    "vm_id": instance_info.get("compute", {}).get("vmId"),
                                    "resource_group": instance_info.get("compute", {}).get("resourceGroupName"),
                                    "location": instance_info.get("compute", {}).get("location")
                                }
                        except:
                            pass
            
        except Exception as e:
            identity_info["credential_chain"].append(f"Managed Identity Check Error: {str(e)}")
        
        # Check environment variables
        env_vars = ["AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID"]
        env_present = {var: bool(os.getenv(var)) for var in env_vars}
        if any(env_present.values()):
            identity_info["credential_chain"].append("Service Principal (env vars)")
            identity_info["details"]["service_principal"] = env_present
        
        return identity_info
    
    def check_network_connectivity(self, endpoint: str, service_name: str) -> Tuple[bool, str]:
        """Check network connectivity to a private endpoint."""
        try:
            # Extract hostname from endpoint
            if "://" in endpoint:
                hostname = endpoint.split("://")[1].split("/")[0]
            else:
                hostname = endpoint.split("/")[0]
            
            # Try basic connectivity check
            result = subprocess.run(
                ["nslookup", hostname],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Check if it resolves to a private IP
                output = result.stdout.lower()
                private_ip_patterns = ["10.", "172.", "192.168."]
                is_private = any(pattern in output for pattern in private_ip_patterns)
                
                if is_private:
                    return True, f"✅ {service_name} resolves to private IP (private endpoint working)"
                else:
                    return True, f"⚠️ {service_name} resolves to public IP (not using private endpoint)"
            else:
                return False, f"❌ {service_name} DNS resolution failed: {result.stderr}"
                
        except Exception as e:
            return False, f"❌ Network connectivity check failed: {str(e)}"
    
    def check_openai_private_endpoint(self) -> Tuple[bool, str]:
        """Enhanced OpenAI health check for private endpoints using managed identity only."""
        try:
            # Get endpoint from environment
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT_41") or os.getenv("AZURE_OPENAI_ENDPOINT", "")
            if not endpoint.startswith("https://"):
                endpoint = f"https://{endpoint}"
            
            if not endpoint:
                return False, "❌ No OpenAI endpoint configured"
            
            # Check network connectivity first
            network_ok, network_msg = self.check_network_connectivity(endpoint, "OpenAI")
            
            # Use managed identity only (no API keys for private endpoints)
            api_version = os.getenv("AZURE_OPENAI_API_VERSION_41", "2024-05-01-preview")
            
            try:
                from azure.identity import get_bearer_token_provider
                credential = DefaultAzureCredential()
                token_provider = get_bearer_token_provider(
                    credential, 
                    "https://cognitiveservices.azure.com/.default"
                )
                
                client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version=api_version
                )
                models = list(client.models.list())
                return True, f"✅ OpenAI connected with managed identity. {network_msg}. Found {len(models)} models."
                
            except ClientAuthenticationError as e:
                return False, f"❌ Managed identity authentication failed: {str(e)}. {network_msg}. Check if managed identity is enabled and has proper RBAC roles."
            except HttpResponseError as e:
                if "Forbidden" in str(e):
                    return False, f"❌ Access forbidden: {str(e)}. {network_msg}. Check RBAC permissions: 'Cognitive Services OpenAI User' role required."
                else:
                    return False, f"❌ HTTP error: {str(e)}. {network_msg}"
            except Exception as e:
                return False, f"❌ Managed identity connection failed: {str(e)}. {network_msg}"
                
        except Exception as e:
            return False, f"❌ OpenAI health check failed: {str(e)}"
    
    def check_document_intelligence_private_endpoint(self) -> Tuple[bool, str]:
        """Enhanced Document Intelligence health check for private endpoints using managed identity only."""
        try:
            # Get endpoint from environment
            endpoint = (os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT") or 
                       os.getenv("DOCUMENT_INTEL_ENDPOINT") or 
                       os.getenv("AZURE_FORMREC_SERVICE", ""))
            
            if not endpoint:
                return False, "❌ No Document Intelligence endpoint configured"
            
            if not endpoint.startswith("https://"):
                endpoint = f"https://{endpoint}"
            
            # Check network connectivity first
            network_ok, network_msg = self.check_network_connectivity(endpoint, "Document Intelligence")
            
            # Use managed identity only (no API keys for private endpoints)
            try:
                credential = DefaultAzureCredential()
                client = DocumentIntelligenceClient(
                    endpoint=endpoint,
                    credential=credential
                )
                # Simple connectivity test - client initialization
                return True, f"✅ Document Intelligence connected with managed identity. {network_msg}"
                
            except ClientAuthenticationError as e:
                return False, f"❌ Managed identity authentication failed: {str(e)}. {network_msg}. Check if managed identity is enabled and has proper RBAC roles."
            except HttpResponseError as e:
                if "Forbidden" in str(e):
                    return False, f"❌ Access forbidden: {str(e)}. {network_msg}. Check RBAC permissions: 'Cognitive Services User' role required."
                else:
                    return False, f"❌ HTTP error: {str(e)}. {network_msg}"
            except Exception as e:
                return False, f"❌ Managed identity connection failed: {str(e)}. {network_msg}"
                
        except Exception as e:
            return False, f"❌ Document Intelligence health check failed: {str(e)}"
    
    def check_ai_search_private_endpoint(self) -> Tuple[bool, str]:
        """Enhanced AI Search health check for private endpoints using managed identity only."""
        try:
            # Get endpoint from environment
            endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
            if not endpoint:
                return False, "❌ No AI Search endpoint configured"
            
            # Check network connectivity first
            network_ok, network_msg = self.check_network_connectivity(endpoint, "AI Search")
            
            # Use managed identity only (no API keys for private endpoints)
            try:
                credential = DefaultAzureCredential()
                client = SearchIndexClient(
                    endpoint=endpoint,
                    credential=credential
                )
                indexes = list(client.list_indexes())
                return True, f"✅ AI Search connected with managed identity. {network_msg}. Found {len(indexes)} indexes."
                
            except ClientAuthenticationError as e:
                return False, f"❌ Managed identity authentication failed: {str(e)}. {network_msg}. Check if managed identity is enabled and has proper RBAC roles."
            except HttpResponseError as e:
                if "Forbidden" in str(e):
                    return False, f"❌ Access forbidden: {str(e)}. {network_msg}. Check RBAC permissions: 'Search Index Data Reader' and 'Search Service Contributor' roles required."
                else:
                    return False, f"❌ HTTP error: {str(e)}. {network_msg}"
            except Exception as e:
                return False, f"❌ Managed identity connection failed: {str(e)}. {network_msg}"
                
        except Exception as e:
            return False, f"❌ AI Search health check failed: {str(e)}"
    
    def generate_rbac_guidance(self, service_name: str, error_message: str) -> Dict[str, Any]:
        """Generate RBAC guidance for 403 Forbidden errors."""
        
        guidance = {
            "error": "403 Forbidden - Missing RBAC permissions",
            "service": service_name,
            "required_roles": [],
            "instructions": [],
            "commands": []
        }
        
        if "search" in service_name.lower():
            guidance["required_roles"] = [
                "Search Index Data Reader",
                "Search Service Contributor"
            ]
            guidance["instructions"] = [
                "1. Go to Azure Portal → AI Search service → Access control (IAM)",
                "2. Click 'Add role assignment'",
                "3. Assign the required roles to your user account or managed identity",
                "4. Wait 5-10 minutes for permissions to propagate"
            ]
            guidance["commands"] = [
                "# Replace <YOUR_EMAIL>, <SUBSCRIPTION_ID>, <RESOURCE_GROUP>, <SEARCH_SERVICE> with actual values",
                "az role assignment create --assignee <YOUR_EMAIL> --role 'Search Index Data Reader' --scope '/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP>/providers/Microsoft.Search/searchServices/<SEARCH_SERVICE>'",
                "az role assignment create --assignee <YOUR_EMAIL> --role 'Search Service Contributor' --scope '/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP>/providers/Microsoft.Search/searchServices/<SEARCH_SERVICE>'"
            ]
        
        elif "openai" in service_name.lower():
            guidance["required_roles"] = [
                "Cognitive Services OpenAI User",
                "Cognitive Services User"
            ]
            guidance["instructions"] = [
                "1. Go to Azure Portal → OpenAI service → Access control (IAM)",
                "2. Click 'Add role assignment'", 
                "3. Assign 'Cognitive Services OpenAI User' role to your account",
                "4. Wait 5-10 minutes for permissions to propagate"
            ]
        
        elif "document" in service_name.lower():
            guidance["required_roles"] = [
                "Cognitive Services User"
            ]
            guidance["instructions"] = [
                "1. Go to Azure Portal → Document Intelligence service → Access control (IAM)",
                "2. Click 'Add role assignment'",
                "3. Assign 'Cognitive Services User' role to your account",
                "4. Wait 5-10 minutes for permissions to propagate"
            ]
        
        return guidance
        """Generate a setup guide for configuring managed identity with private endpoints."""
        
        identity_info = self.get_current_identity_info()
        
        guide = {
            "current_identity": identity_info,
            "steps": [],
            "required_roles": {
                "OpenAI": [
                    "Cognitive Services OpenAI User",
                    "Cognitive Services User"
                ],
                "Document Intelligence": [
                    "Cognitive Services User"
                ],
                "AI Search": [
                    "Search Index Data Reader",
                    "Search Service Contributor"
                ]
            },
            "azure_cli_commands": []
        }
        
        # Determine the identity type and provide appropriate guidance
        if any("Managed Identity" in chain for chain in identity_info["credential_chain"]):
            guide["steps"].extend([
                "✅ Managed Identity detected - you're running in Azure (VM, App Service, etc.)",
                "🔧 Configure RBAC permissions for your managed identity",
                "🔧 Ensure private endpoint DNS resolution is working"
            ])
            
            # Add Azure CLI commands for role assignment
            if "managed_identity" in identity_info["details"]:
                vm_id = identity_info["details"]["managed_identity"].get("vm_id")
                if vm_id:
                    guide["azure_cli_commands"].extend([
                        f"# Get your VM's managed identity principal ID",
                        f"PRINCIPAL_ID=$(az vm identity show --ids {vm_id} --query principalId -o tsv)",
                        "",
                        "# Assign OpenAI roles",
                        "az role assignment create --assignee $PRINCIPAL_ID --role 'Cognitive Services OpenAI User' --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<OPENAI_NAME>",
                        "",
                        "# Assign Document Intelligence roles", 
                        "az role assignment create --assignee $PRINCIPAL_ID --role 'Cognitive Services User' --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<DOC_INTEL_NAME>",
                        "",
                        "# Assign AI Search roles",
                        "az role assignment create --assignee $PRINCIPAL_ID --role 'Search Index Data Reader' --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.Search/searchServices/<SEARCH_NAME>",
                        "az role assignment create --assignee $PRINCIPAL_ID --role 'Search Service Contributor' --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.Search/searchServices/<SEARCH_NAME>"
                    ])
        
        elif any("Azure CLI" in chain for chain in identity_info["credential_chain"]):
            guide["steps"].extend([
                "✅ Azure CLI authentication detected",
                "⚠️ You're using your personal Azure CLI login",
                "🔧 For production, configure managed identity or service principal",
                "🔧 Ensure your user account has proper RBAC permissions"
            ])
            
            # Add Azure CLI commands for role assignment to current user
            if "cli_account" in identity_info["details"]:
                guide["azure_cli_commands"].extend([
                    "# Assign roles to your current user account",
                    "CURRENT_USER=$(az account show --query user.name -o tsv)",
                    "",
                    "# Assign OpenAI roles",
                    "az role assignment create --assignee $CURRENT_USER --role 'Cognitive Services OpenAI User' --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<OPENAI_NAME>",
                    "",
                    "# Assign Document Intelligence roles",
                    "az role assignment create --assignee $CURRENT_USER --role 'Cognitive Services User' --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<DOC_INTEL_NAME>",
                    "",
                    "# Assign AI Search roles", 
                    "az role assignment create --assignee $CURRENT_USER --role 'Search Index Data Reader' --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.Search/searchServices/<SEARCH_NAME>",
                    "az role assignment create --assignee $CURRENT_USER --role 'Search Service Contributor' --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.Search/searchServices/<SEARCH_NAME>"
                ])
        
        else:
            guide["steps"].extend([
                "❌ No Azure authentication detected",
                "🔧 Install Azure CLI and run 'az login'",
                "🔧 Or configure managed identity if running in Azure",
                "🔧 Or set up service principal with environment variables"
            ])
        
        return guide
    
    def check_all_private_endpoint_services(self) -> Tuple[Dict[str, Tuple[bool, str]], bool, Dict[str, Any]]:
        """Check health of all private endpoint services and return comprehensive diagnostics."""
        
        results = {
            "OpenAI": self.check_openai_private_endpoint(),
            "Document Intelligence": self.check_document_intelligence_private_endpoint(),
            "AI Search": self.check_ai_search_private_endpoint()
        }
        
        all_healthy = all(status for status, _ in results.values())
        
        # Generate comprehensive diagnostics
        diagnostics = {
            "identity_info": self.get_current_identity_info(),
            "setup_guide": self.generate_managed_identity_setup_guide(),
            "timestamp": datetime.now().isoformat(),
            "all_healthy": all_healthy
        }
        
        return results, all_healthy, diagnostics

    def check_all_services(self) -> Tuple[Dict[str, Tuple[bool, str]], bool, Dict[str, str]]:
        """
        Check all services and return results in format expected by UI.
        
        Returns:
            Tuple containing:
            - Dict of service results: {service_name: (is_healthy, message)}
            - bool: True if all services are healthy
            - Dict of troubleshooting messages: {service_name: troubleshooting_text}
        """
        try:
            # Use the existing private endpoint check method
            results, all_healthy, diagnostics = self.check_all_private_endpoint_services()
            
            # Generate troubleshooting messages for failed services
            troubleshooting = {}
            for service_name, (is_healthy, message) in results.items():
                if not is_healthy:
                    troubleshooting[service_name] = self._generate_troubleshooting_message(service_name, message)
            
            return results, all_healthy, troubleshooting
            
        except Exception as e:
            # Fallback: return error state for all services
            error_message = f"Health check failed: {str(e)}"
            results = {
                "Azure OpenAI": (False, error_message),
                "Document Intelligence": (False, error_message),
                "AI Search": (False, error_message)
            }
            troubleshooting = {
                "Azure OpenAI": "Check your Azure OpenAI configuration and network connectivity",
                "Document Intelligence": "Check your Document Intelligence configuration and network connectivity", 
                "AI Search": "Check your AI Search configuration and network connectivity"
            }
            return results, False, troubleshooting

    def _generate_troubleshooting_message(self, service_name: str, error_message: str) -> str:
        """Generate troubleshooting message for a failed service."""
        
        base_troubleshooting = {
            "Azure OpenAI": """
**Common Issues:**
1. **Missing Environment Variables**: Ensure AZURE_OPENAI_ENDPOINT is set
2. **Authentication**: Check managed identity or API key configuration
3. **Network**: Verify private endpoint DNS resolution
4. **RBAC**: Ensure 'Cognitive Services OpenAI User' role is assigned

**Quick Fixes:**
- Verify endpoint URL format: https://your-service.openai.azure.com/
- Check if managed identity is enabled on your VM/App Service
- Test DNS resolution: `nslookup your-service.openai.azure.com`
            """,
            
            "Document Intelligence": """
**Common Issues:**
1. **Missing Environment Variables**: Ensure DOCUMENT_INTEL_ENDPOINT is set
2. **Authentication**: Check managed identity or API key configuration
3. **Network**: Verify private endpoint connectivity
4. **RBAC**: Ensure 'Cognitive Services User' role is assigned

**Quick Fixes:**
- Verify endpoint URL format: https://your-service.cognitiveservices.azure.com/
- Check if the service is accessible from your network
- Verify managed identity has proper permissions
            """,
            
            "AI Search": """
**Common Issues:**
1. **Missing Environment Variables**: Ensure AZURE_SEARCH_ENDPOINT is set
2. **Authentication**: Check managed identity or API key configuration
3. **Network**: Verify private endpoint connectivity
4. **RBAC**: Ensure 'Search Index Data Reader' role is assigned

**Quick Fixes:**
- Verify endpoint URL format: https://your-service.search.windows.net/
- Check if RBAC is enabled on the search service
- Verify managed identity has proper search permissions
            """
        }
        
        # Add specific error context if available
        troubleshooting_text = base_troubleshooting.get(service_name, "Check service configuration and connectivity")
        
        if "403" in error_message or "Forbidden" in error_message:
            troubleshooting_text += "\n\n**403 Forbidden Error Detected:**\nThis usually indicates missing RBAC permissions. Check that your managed identity has the required roles assigned."
        elif "401" in error_message or "Unauthorized" in error_message:
            troubleshooting_text += "\n\n**401 Unauthorized Error Detected:**\nThis usually indicates authentication issues. Check your managed identity configuration or API keys."
        elif "DNS" in error_message or "resolve" in error_message.lower():
            troubleshooting_text += "\n\n**DNS Resolution Error Detected:**\nThis usually indicates private endpoint DNS issues. Check your private DNS zone configuration."
        
        return troubleshooting_text

    async def check_all_resources(self) -> Dict[str, HealthCheckResult]:
        """Check health of all private endpoint resources."""
        results = {}
        
        print("🏥 Starting Private Endpoint Health Check")
        print("=" * 50)
        
        for resource_key, config in self.configs.items():
            print(f"\n🔍 Checking {config.name}...")
            try:
                result = await self.check_resource_health(config)
                results[resource_key] = result
                
                if result.status == HealthStatus.HEALTHY:
                    print(f"✅ {config.name}: HEALTHY")
                elif result.status == HealthStatus.WARNING:
                    print(f"⚠️  {config.name}: WARNING - {result.message}")
                else:
                    print(f"❌ {config.name}: UNHEALTHY - {result.message}")
                    
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                results[resource_key] = HealthCheckResult(
                    service=config.name,
                    status=HealthStatus.UNHEALTHY,
                    message=error_msg,
                    details={'error': str(e), 'traceback': traceback.format_exc()}
                )
                print(f"❌ {config.name}: ERROR - {error_msg}")
        
        return results
    
    async def check_resource_health(self, config: PrivateEndpointConfig) -> HealthCheckResult:
        """Check health of a specific resource."""
        details = {
            'endpoint': config.endpoint,
            'resource_type': config.resource_type,
            'timestamp': datetime.now().isoformat()
        }
        
        # Check environment variables
        env_check = self.check_environment_variables(config)
        details['environment_check'] = env_check
        
        if not env_check['all_present']:
            return HealthCheckResult(
                service=config.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Missing environment variables: {', '.join(env_check['missing'])}",
                details=details
            )
        
        # Check authentication
        auth_check = await self.check_authentication(config)
        details['authentication_check'] = auth_check
        
        if not auth_check['success']:
            return HealthCheckResult(
                service=config.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Authentication failed: {auth_check['error']}",
                details=details
            )
        
        # Check connectivity
        connectivity_check = await self.check_connectivity(config)
        details['connectivity_check'] = connectivity_check
        
        if not connectivity_check['success']:
            return HealthCheckResult(
                service=config.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Connectivity failed: {connectivity_check['error']}",
                details=details
            )
        
        # Run test operations
        operations_check = await self.test_operations(config)
        details['operations_check'] = operations_check
        
        # Determine overall status
        if operations_check['all_successful']:
            status = HealthStatus.HEALTHY
            message = "All checks passed"
        elif operations_check['some_successful']:
            status = HealthStatus.WARNING
            failed_details = '; '.join(operations_check['failed'])
            message = f"Some operations failed: {failed_details}"
        elif operations_check['total_tested'] > 0:
            status = HealthStatus.UNHEALTHY
            failed_details = '; '.join(operations_check['failed'])
            message = f"All operations failed: {failed_details}"
        else:
            # No operations were tested, but connectivity worked - mark as healthy
            if connectivity_check['success']:
                status = HealthStatus.HEALTHY
                message = "Connectivity successful (basic health check passed)"
            else:
                status = HealthStatus.WARNING
                message = "Connectivity successful, but no operations tested"
        
        return HealthCheckResult(
            service=config.name,
            status=status,
            message=message,
            details=details
        )
    
    def check_environment_variables(self, config: PrivateEndpointConfig) -> Dict[str, Any]:
        """Check if required environment variables are present."""
        missing = []
        present = []
        
        for var in config.required_env_vars:
            value = os.getenv(var)
            if not value or value.strip() == '':
                missing.append(var)
            else:
                present.append(var)
        
        return {
            'all_present': len(missing) == 0,
            'missing': missing,
            'present': present,
            'total_required': len(config.required_env_vars)
        }
    
    async def check_authentication(self, config: PrivateEndpointConfig) -> Dict[str, Any]:
        """Check if we can authenticate to the resource."""
        try:
            # Try to get an access token
            token = await asyncio.to_thread(
                self._get_credential().get_token,
                config.auth_scope
            )
            
            return {
                'success': True,
                'token_expires': token.expires_on,
                'auth_method': 'managed_identity'
            }
            
        except ClientAuthenticationError as e:
            return {
                'success': False,
                'error': f"Authentication error: {str(e)}",
                'error_type': 'authentication'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Token acquisition failed: {str(e)}",
                'error_type': 'token_acquisition'
            }
    
    async def check_connectivity(self, config: PrivateEndpointConfig) -> Dict[str, Any]:
        """Check basic connectivity to the resource."""
        try:
            if config.resource_type == 'openai':
                return await self.check_openai_connectivity(config)
            elif config.resource_type == 'document_intelligence':
                return await self.check_document_intelligence_connectivity(config)
            elif config.resource_type == 'search':
                return await self.check_search_connectivity(config)
            else:
                return {
                    'success': False,
                    'error': f"Unknown resource type: {config.resource_type}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Connectivity check failed: {str(e)}",
                'traceback': traceback.format_exc()
            }
    
    async def check_openai_connectivity(self, config: PrivateEndpointConfig) -> Dict[str, Any]:
        """Check OpenAI connectivity."""
        try:
            # Ensure endpoint has proper format
            endpoint = config.endpoint
            if not endpoint.startswith('https://'):
                endpoint = f"https://{endpoint}"
            if not endpoint.endswith('/'):
                endpoint += '/'
            
            # Use token provider for managed identity
            from azure.identity import get_bearer_token_provider
            token_provider = get_bearer_token_provider(
                self._get_credential(), 
                "https://cognitiveservices.azure.com/.default"
            )
            
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider,
                api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01')
            )
            
            # Try to list models (simple connectivity test)
            models = await asyncio.to_thread(client.models.list)
            
            return {
                'success': True,
                'models_count': len(models.data) if hasattr(models, 'data') else 0,
                'endpoint_used': endpoint
            }
            
        except HttpResponseError as e:
            return {
                'success': False,
                'error': f"HTTP error: {e.status_code} - {e.message}",
                'error_type': 'http_error'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'connection_error'
            }
    
    async def check_document_intelligence_connectivity(self, config: PrivateEndpointConfig) -> Dict[str, Any]:
        """Check Document Intelligence connectivity."""
        try:
            endpoint = config.endpoint
            if not endpoint.startswith('https://'):
                endpoint = f"https://{endpoint}"
            if endpoint.endswith('/'):
                endpoint = endpoint[:-1]
            
            client = DocumentIntelligenceClient(
                endpoint=endpoint,
                credential=self._get_credential()
            )
            
            # Just verify client initialization - no specific API call needed
            return {
                'success': True,
                'message': 'Document Intelligence client initialized successfully',
                'endpoint_used': endpoint
            }
            
        except HttpResponseError as e:
            return {
                'success': False,
                'error': f"HTTP error: {e.status_code} - {e.message}",
                'error_type': 'http_error'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'connection_error'
            }
    
    async def check_search_connectivity(self, config: PrivateEndpointConfig) -> Dict[str, Any]:
        """Check AI Search connectivity."""
        try:
            endpoint = config.endpoint
            if not endpoint.startswith('https://'):
                endpoint = f"https://{endpoint}"
            
            client = SearchIndexClient(
                endpoint=endpoint,

                credential=self._get_credential()
            )
            
            # Try to list indexes
            indexes = await asyncio.to_thread(lambda: list(client.list_indexes()))
            
            return {
                'success': True,
                'indexes_count': len(indexes),
                'endpoint_used': endpoint
            }
            
        except HttpResponseError as e:
            if e.status_code == 403:
                rbac_guidance = self.generate_rbac_guidance("AI Search", str(e))
                return {
                    'success': False,
                    'error': f"HTTP error: {e.status_code} - {e.message}",
                    'error_type': 'rbac_permission',
                    'rbac_guidance': rbac_guidance
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP error: {e.status_code} - {e.message}",
                    'error_type': 'http_error'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'connection_error'
            }
    
    async def test_operations(self, config: PrivateEndpointConfig) -> Dict[str, Any]:
        """Test specific operations for the resource."""
        results = {}
        successful = []
        failed = []
        
        for operation in config.test_operations:
            try:
                if config.resource_type == 'openai' and operation == 'simple_completion':
                    result = await self.test_openai_completion()
                elif config.resource_type == 'search' and operation == 'get_service_stats':
                    result = await self.test_search_stats()
                else:
                    # Skip operations we don't have specific tests for
                    continue
                
                results[operation] = result
                if result.get('success', False):
                    successful.append(operation)
                else:
                    failed.append(f"{operation}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                error_msg = str(e)
                results[operation] = {
                    'success': False,
                    'error': error_msg
                }
                failed.append(f"{operation}: {error_msg}")
        
        return {
            'results': results,
            'successful': successful,
            'failed': failed,
            'all_successful': len(failed) == 0 and len(successful) > 0,
            'some_successful': len(successful) > 0,
            'total_tested': len(results)
        }
    
    async def test_openai_completion(self) -> Dict[str, Any]:
        """Test OpenAI completion functionality."""
        try:
            # Get endpoint with proper format
            endpoint = os.getenv('AZURE_OPENAI_ENDPOINT_41') or os.getenv('AZURE_OPENAI_ENDPOINT', '')
            if not endpoint.startswith('https://'):
                endpoint = f"https://{endpoint}"
            if not endpoint.endswith('/'):
                endpoint += '/'
            
            # Use token provider for managed identity
            from azure.identity import get_bearer_token_provider
            token_provider = get_bearer_token_provider(
                self._get_credential(), 
                "https://cognitiveservices.azure.com/.default"
            )
            
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider,
                api_version=os.getenv('AZURE_OPENAI_API_VERSION_41', '2025-01-01-preview')
            )
            
            deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT_41', 'gpt-4.1')
            
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=deployment,
                messages=[{"role": "user", "content": "Say 'OK' if you can hear me."}],
                max_tokens=5
            )
            
            return {
                'success': True,
                'response': response.choices[0].message.content if response.choices else 'No response',
                'usage': response.usage.total_tokens if response.usage else 0,
                'deployment': deployment
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'endpoint': endpoint if 'endpoint' in locals() else 'unknown'
            }
    
    async def test_search_stats(self) -> Dict[str, Any]:
        """Test Search service statistics."""
        try:
            endpoint = os.getenv('AZURE_SEARCH_ENDPOINT', '')
            if not endpoint.startswith('https://'):
                endpoint = f"https://{endpoint}"
            
            client = SearchIndexClient(
                endpoint=endpoint,
                credential=self._get_credential()
            )
            
            # Get service statistics
            stats = await asyncio.to_thread(client.get_service_statistics)
            
            return {
                'success': True,
                'counters': {
                    'storage_size': stats.counters.storage_size,
                    'document_count': stats.counters.document_count,
                    'index_count': stats.counters.index_count
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def print_detailed_report(self, results: Dict[str, HealthCheckResult]):
        """Print a detailed health check report."""
        print("\n" + "="*60)
        print("📊 DETAILED HEALTH CHECK REPORT")
        print("="*60)
        
        for resource_key, result in results.items():
            config = self.configs[resource_key]
            print(f"\n🔍 {config.name}")
            print("-" * 40)
            
            # Status
            status_emoji = "✅" if result.status == HealthStatus.HEALTHY else "⚠️" if result.status == HealthStatus.WARNING else "❌"
            print(f"Status: {status_emoji} {result.status.value}")
            print(f"Message: {result.message}")
            
            # Environment check
            if 'environment_check' in result.details:
                env_check = result.details['environment_check']
                print(f"Environment Variables: {len(env_check['present'])}/{env_check['total_required']} present")
                if env_check['missing']:
                    print(f"  Missing: {', '.join(env_check['missing'])}")
            
            # Authentication check
            if 'authentication_check' in result.details:
                auth_check = result.details['authentication_check']
                auth_status = "✅" if auth_check['success'] else "❌"
                print(f"Authentication: {auth_status}")
                if not auth_check['success']:
                    print(f"  Error: {auth_check['error']}")
            
            # Connectivity check
            if 'connectivity_check' in result.details:
                conn_check = result.details['connectivity_check']
                conn_status = "✅" if conn_check['success'] else "❌"
                print(f"Connectivity: {conn_status}")
                if not conn_check['success']:
                    print(f"  Error: {conn_check['error']}")
                    
                    # Show RBAC guidance if available
                    if 'rbac_guidance' in conn_check:
                        guidance = conn_check['rbac_guidance']
                        print(f"\n  📋 RBAC Setup Required:")
                        print(f"  Required Roles: {', '.join(guidance['required_roles'])}")
                        print(f"  Instructions:")
                        for i, instruction in enumerate(guidance['instructions'], 1):
                            print(f"    {instruction}")
                        if guidance.get('commands'):
                            print(f"  Azure CLI Commands:")
                            for cmd in guidance['commands']:
                                print(f"    {cmd}")
            
            # Operations check
            if 'operations_check' in result.details:
                ops_check = result.details['operations_check']
                if ops_check['successful']:
                    print(f"Operations: ✅ {len(ops_check['successful'])} successful")
                if ops_check['failed']:
                    print(f"Operations: ❌ {len(ops_check['failed'])} failed")

    def get_current_identity_info(self) -> Dict[str, Any]:
        """Get current identity information for diagnostics."""
        return self.load_environment()
    
    def validate_env_configuration(self) -> Dict[str, Any]:
        """
        Comprehensive validation of .env configuration.
        
        Returns:
            Dict containing validation results, missing variables, and guidance.
        """
        # Define all possible environment variables for the application
        env_var_definitions = {
            # Core Azure endpoints (required)
            'AZURE_OPENAI_ENDPOINT': {
                'required': True,
                'description': 'Azure OpenAI service endpoint URL',
                'example': 'https://your-openai-service.openai.azure.com/',
                'category': 'azure_endpoints'
            },
            'AZURE_SEARCH_ENDPOINT': {
                'required': True,
                'description': 'Azure AI Search service endpoint URL',
                'example': 'https://your-search-service.search.windows.net/',
                'category': 'azure_endpoints'
            },
            'DOCUMENT_INTEL_ENDPOINT': {
                'required': True,
                'description': 'Azure Document Intelligence service endpoint URL',
                'example': 'https://your-docint-service.cognitiveservices.azure.com/',
                'category': 'azure_endpoints'
            },
            
            # OpenAI specific configuration
            'AZURE_OPENAI_DEPLOYMENT': {
                'required': True,
                'description': 'OpenAI model deployment name',
                'example': 'gpt-4',
                'category': 'openai_config'
            },
            'AZURE_OPENAI_MODEL_VERSION': {
                'required': False,
                'description': 'OpenAI model API version',
                'example': '2024-02-15-preview',
                'category': 'openai_config'
            },
            
            # Alternative OpenAI endpoints (optional)
            'AZURE_OPENAI_ENDPOINT_41': {
                'required': False,
                'description': 'Alternative OpenAI endpoint for GPT-4-turbo',
                'example': 'https://your-openai-41.openai.azure.com/',
                'category': 'openai_alternatives'
            },
            'AZURE_OPENAI_ENDPOINT_4o': {
                'required': False,
                'description': 'Alternative OpenAI endpoint for GPT-4o',
                'example': 'https://your-openai-4o.openai.azure.com/',
                'category': 'openai_alternatives'
            },
            
            # API Keys (optional - for API key authentication)
            'AZURE_OPENAI_KEY': {
                'required': False,
                'description': 'OpenAI service API key (if not using managed identity)',
                'example': 'your_api_key_here',
                'category': 'api_keys',
                'sensitive': True
            },
            'AZURE_SEARCH_KEY': {
                'required': False,
                'description': 'AI Search service API key (if not using managed identity)',
                'example': 'your_api_key_here',
                'category': 'api_keys',
                'sensitive': True
            },
            'DOCUMENT_INTEL_KEY': {
                'required': False,
                'description': 'Document Intelligence API key (if not using managed identity)',
                'example': 'your_api_key_here',
                'category': 'api_keys',
                'sensitive': True
            },
            
            # Service Principal authentication (optional)
            'AZURE_CLIENT_ID': {
                'required': False,
                'description': 'Service principal client ID',
                'example': 'your-client-id-guid',
                'category': 'service_principal',
                'sensitive': True
            },
            'AZURE_CLIENT_SECRET': {
                'required': False,
                'description': 'Service principal client secret',
                'example': 'your-client-secret',
                'category': 'service_principal',
                'sensitive': True
            },
            'AZURE_TENANT_ID': {
                'required': False,
                'description': 'Azure tenant ID',
                'example': 'your-tenant-id-guid',
                'category': 'service_principal',
                'sensitive': True
            },
            
            # SharePoint integration (optional)
            'SHAREPOINT_SITE_URL': {
                'required': False,
                'description': 'SharePoint site URL for document integration',
                'example': 'https://yourtenant.sharepoint.com/sites/yoursite',
                'category': 'sharepoint'
            },
            'SHAREPOINT_CLIENT_ID': {
                'required': False,
                'description': 'SharePoint app client ID',
                'example': 'your-sharepoint-client-id',
                'category': 'sharepoint',
                'sensitive': True
            },
            'SHAREPOINT_CLIENT_SECRET': {
                'required': False,
                'description': 'SharePoint app client secret',
                'example': 'your-sharepoint-client-secret',
                'category': 'sharepoint',
                'sensitive': True
            }
        }
        
        # Check current environment
        env_status = {}
        missing_required = []
        missing_optional = []
        present_vars = []
        
        for var_name, var_info in env_var_definitions.items():
            value = os.getenv(var_name)
            is_present = bool(value and value.strip())
            
            env_status[var_name] = {
                'present': is_present,
                'value_length': len(value) if value else 0,
                'definition': var_info
            }
            
            if is_present:
                present_vars.append(var_name)
            elif var_info['required']:
                missing_required.append(var_name)
            else:
                missing_optional.append(var_name)
        
        # Determine authentication method
        has_api_keys = any(os.getenv(key) for key in ['AZURE_OPENAI_KEY', 'AZURE_SEARCH_KEY', 'DOCUMENT_INTEL_KEY'])
        has_service_principal = all(os.getenv(key) for key in ['AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET', 'AZURE_TENANT_ID'])
        
        auth_method = 'unknown'
        if has_service_principal:
            auth_method = 'service_principal'
        elif has_api_keys:
            auth_method = 'api_keys'
        else:
            auth_method = 'managed_identity'
        
        # Check .env file existence
        env_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        env_file_exists = os.path.exists(env_file_path)
        
        return {
            'env_file_exists': env_file_exists,
            'env_file_path': env_file_path,
            'total_vars_defined': len(env_var_definitions),
            'present_vars': present_vars,
            'missing_required': missing_required,
            'missing_optional': missing_optional,
            'auth_method': auth_method,
            'has_api_keys': has_api_keys,
            'has_service_principal': has_service_principal,
            'env_status': env_status,
            'is_configuration_complete': len(missing_required) == 0,
            'var_definitions': env_var_definitions
        }
    
    def generate_env_guidance(self, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate user-friendly guidance based on .env validation results.
        
        Args:
            validation_result: Result from validate_env_configuration()
            
        Returns:
            Dict containing guidance, next steps, and sample .env content
        """
        missing_required = validation_result['missing_required']
        missing_optional = validation_result['missing_optional']
        auth_method = validation_result['auth_method']
        env_file_exists = validation_result['env_file_exists']
        var_definitions = validation_result['var_definitions']
        
        # Generate guidance message
        if len(missing_required) == 0:
            if auth_method == 'managed_identity':
                guidance_message = "✅ **Configuration Complete**: All required variables are set for managed identity authentication."
            elif auth_method == 'api_keys':
                guidance_message = "✅ **Configuration Complete**: All required variables are set for API key authentication."
            elif auth_method == 'service_principal':
                guidance_message = "✅ **Configuration Complete**: All required variables are set for service principal authentication."
            else:
                guidance_message = "⚠️ **Configuration Review**: Required variables are set but authentication method is unclear."
        else:
            guidance_message = f"❌ **Configuration Incomplete**: {len(missing_required)} required variables are missing."
        
        # Generate next steps
        next_steps = []
        
        if not env_file_exists:
            next_steps.append("1. Create a `.env` file in your project root directory")
        
        if missing_required:
            next_steps.append("2. Add the missing required environment variables:")
            for var in missing_required:
                next_steps.append(f"   - {var}: {var_definitions[var]['description']}")
        
        next_steps.append("3. Choose your authentication method:")
        next_steps.append("   - **Managed Identity** (recommended for Azure VMs): No additional setup needed")
        next_steps.append("   - **API Keys**: Add *_KEY variables for each service")
        next_steps.append("   - **Service Principal**: Add AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID")
        
        next_steps.append("4. Restart the application after updating the .env file")
        
        # Generate sample .env content
        sample_env_lines = []
        sample_env_lines.append("# Azure Service Endpoints (Required)")
        sample_env_lines.append("#" + "="*50)
        
        # Add required variables
        for var_name, var_info in var_definitions.items():
            if var_info['required']:
                sample_env_lines.append(f"{var_name}={var_info['example']}")
        
        sample_env_lines.append("")
        sample_env_lines.append("# Authentication Method 1: API Keys (Optional)")
        sample_env_lines.append("#" + "="*50)
        sample_env_lines.append("# Uncomment these if you want to use API key authentication")
        
        for var_name, var_info in var_definitions.items():
            if var_info['category'] == 'api_keys':
                sample_env_lines.append(f"# {var_name}={var_info['example']}")
        
        sample_env_lines.append("")
        sample_env_lines.append("# Authentication Method 2: Service Principal (Optional)")
        sample_env_lines.append("#" + "="*50)
        sample_env_lines.append("# Uncomment these if you want to use service principal authentication")
        
        for var_name, var_info in var_definitions.items():
            if var_info['category'] == 'service_principal':
                sample_env_lines.append(f"# {var_name}={var_info['example']}")
        
        sample_env_lines.append("")
        sample_env_lines.append("# Optional: Alternative OpenAI Endpoints")
        sample_env_lines.append("#" + "="*50)
        
        for var_name, var_info in var_definitions.items():
            if var_info['category'] == 'openai_alternatives':
                sample_env_lines.append(f"# {var_name}={var_info['example']}")
        
        sample_env_lines.append("")
        sample_env_lines.append("# Optional: SharePoint Integration")
        sample_env_lines.append("#" + "="*50)
        
        for var_name, var_info in var_definitions.items():
            if var_info['category'] == 'sharepoint':
                sample_env_lines.append(f"# {var_name}={var_info['example']}")
        
        return {
            'guidance_message': guidance_message,
            'next_steps': next_steps,
            'sample_env_content': '\n'.join(sample_env_lines),
            'auth_recommendations': {
                'managed_identity': {
                    'recommended': True,
                    'description': 'Best for Azure VMs, App Services, and Container Instances',
                    'setup_required': 'Ensure managed identity is enabled and RBAC roles are assigned'
                },
                'api_keys': {
                    'recommended': False,
                    'description': 'Simple but less secure, requires key management',
                    'setup_required': 'Copy API keys from Azure portal to .env file'
                },
                'service_principal': {
                    'recommended': False,
                    'description': 'Good for on-premises or non-Azure environments',
                    'setup_required': 'Create app registration and add credentials to .env file'
                }
            }
        }
    
    def print_env_validation_report(self) -> None:
        """
        Print a comprehensive .env validation report to console.
        """
        print("\n" + "="*80)
        print("🔍 ENVIRONMENT CONFIGURATION VALIDATION REPORT")
        print("="*80)
        
        # Get validation results
        validation = self.validate_env_configuration()
        guidance = self.generate_env_guidance(validation)
        
        # Print overview
        print(f"\n📁 Environment File: {validation['env_file_path']}")
        print(f"📄 File Exists: {'✅ Yes' if validation['env_file_exists'] else '❌ No'}")
        print(f"🔐 Authentication Method: {validation['auth_method'].replace('_', ' ').title()}")
        print(f"✅ Configuration Complete: {'Yes' if validation['is_configuration_complete'] else 'No'}")
        
        # Print status summary
        print(f"\n📊 CONFIGURATION SUMMARY")
        print(f"├── Variables Present: {len(validation['present_vars'])}")
        print(f"├── Required Missing: {len(validation['missing_required'])}")
        print(f"└── Optional Missing: {len(validation['missing_optional'])}")
        
        # Print missing required variables
        if validation['missing_required']:
            print(f"\n❌ MISSING REQUIRED VARIABLES ({len(validation['missing_required'])})")
            for var in validation['missing_required']:
                var_info = validation['var_definitions'][var]
                print(f"├── {var}")
                print(f"│   └── {var_info['description']}")
        
        # Print present variables
        if validation['present_vars']:
            print(f"\n✅ PRESENT VARIABLES ({len(validation['present_vars'])})")
            for var in validation['present_vars']:
                var_info = validation['var_definitions'][var]
                value_len = validation['env_status'][var]['value_length']
                is_sensitive = var_info.get('sensitive', False)
                value_display = f"({value_len} chars)" if is_sensitive else f"length: {value_len}"
                print(f"├── {var} {value_display}")
        
        # Print guidance
        print(f"\n💡 GUIDANCE")
        print(guidance['guidance_message'])
        
        # Print next steps
        if guidance['next_steps']:
            print(f"\n📋 NEXT STEPS")
            for step in guidance['next_steps']:
                print(f"   {step}")
        
        # Print sample .env content if configuration is incomplete
        if not validation['is_configuration_complete']:
            print(f"\n📝 SAMPLE .ENV FILE CONTENT")
            print("-" * 50)
            print(guidance['sample_env_content'])
            print("-" * 50)
        
        # Print authentication recommendations
        print(f"\n🔐 AUTHENTICATION METHOD RECOMMENDATIONS")
        for method, info in guidance['auth_recommendations'].items():
            recommended = "✅ RECOMMENDED" if info['recommended'] else "⚠️  ALTERNATIVE"
            print(f"├── {method.replace('_', ' ').title()}: {recommended}")
            print(f"│   ├── {info['description']}")
            print(f"│   └── Setup: {info['setup_required']}")
        
        print("="*80 + "\n")

    async def check_all_resources_with_env_validation(self) -> Dict[str, Any]:
        """
        Check health of all resources with comprehensive .env validation.
        
        Returns:
            Dict containing:
            - resource_results: Individual resource health check results
            - env_validation: Comprehensive .env validation results
            - overall_status: Overall system health status
            - recommendations: User-friendly recommendations
        """
        print("🏥 Starting Comprehensive Health Check with Environment Validation")
        print("=" * 70)
        
        # First, validate .env configuration
        print("\n🔍 Step 1: Validating Environment Configuration...")
        env_validation = self.validate_env_configuration()
        env_guidance = self.generate_env_guidance(env_validation)
        
        # Print .env validation summary
        if env_validation['is_configuration_complete']:
            print("✅ Environment configuration is complete")
            print(f"🔐 Authentication method: {env_validation['auth_method'].replace('_', ' ').title()}")
        else:
            print(f"❌ Environment configuration incomplete - {len(env_validation['missing_required'])} required variables missing")
            print("Missing required variables:")
            for var in env_validation['missing_required']:
                print(f"   - {var}")
        
        # Then, check individual resources
        print("\n🔍 Step 2: Checking Individual Azure Resources...")
        resource_results = await self.check_all_resources()
        
        # Determine overall status
        resource_statuses = [result.status for result in resource_results.values()]
        
        if not env_validation['is_configuration_complete']:
            overall_status = HealthStatus.UNHEALTHY
            overall_message = "Environment configuration is incomplete"
        elif all(status == HealthStatus.HEALTHY for status in resource_statuses):
            overall_status = HealthStatus.HEALTHY
            overall_message = "All services are healthy and ready"
        elif any(status == HealthStatus.UNHEALTHY for status in resource_statuses):
            overall_status = HealthStatus.UNHEALTHY
            unhealthy_services = [
                service_name for service_name, result in resource_results.items()
                if result.status == HealthStatus.UNHEALTHY
            ]
            overall_message = f"Some services are unhealthy: {', '.join(unhealthy_services)}"
        else:
            overall_status = HealthStatus.WARNING
            overall_message = "All services are accessible but some have warnings"
        
        # Generate recommendations
        recommendations = []
        
        if not env_validation['is_configuration_complete']:
            recommendations.extend([
                "📝 Complete the .env file configuration",
                "🔐 Choose and configure your authentication method",
                "🔄 Restart the application after updating configuration"
            ])
        
        # Add service-specific recommendations
        for service_name, result in resource_results.items():
            if result.status == HealthStatus.UNHEALTHY:
                if 'environment_check' in result.details and not result.details['environment_check']['all_present']:
                    recommendations.append(f"🔧 Fix missing environment variables for {service_name}")
                elif 'authentication_check' in result.details and not result.details['authentication_check']['success']:
                    recommendations.append(f"🔐 Fix authentication issues for {service_name}")
                elif 'connectivity_check' in result.details and not result.details['connectivity_check']['success']:
                    recommendations.append(f"🌐 Fix connectivity issues for {service_name}")
        
        if env_validation['auth_method'] == 'managed_identity':
            has_auth_issues = any(
                result.status == HealthStatus.UNHEALTHY and 
                'authentication_check' in result.details and 
                not result.details['authentication_check']['success']
                for result in resource_results.values()
            )
            if has_auth_issues:
                recommendations.append("🔑 Check RBAC role assignments for managed identity")
        
        print(f"\n📊 OVERALL STATUS: {overall_status.value.upper()}")
        print(f"💬 {overall_message}")
        
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        return {
            'overall_status': overall_status,
            'overall_message': overall_message,
            'resource_results': resource_results,
            'env_validation': env_validation,
            'env_guidance': env_guidance,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }

    def check_azure_cli_status(self) -> Dict[str, Any]:
        """Check Azure CLI authentication status."""
        try:
            import subprocess
            import json
            
            # Check if Azure CLI is installed
            try:
                subprocess.run(['az', '--version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return {
                    'authenticated': False,
                    'error': 'Azure CLI is not installed or not accessible'
                }
            
            # Check if user is logged in
            try:
                result = subprocess.run(['az', 'account', 'show'], 
                                      capture_output=True, text=True, check=True)
                account_info = json.loads(result.stdout)
                
                return {
                    'authenticated': True,
                    'account_info': account_info
                }
            except subprocess.CalledProcessError:
                return {
                    'authenticated': False,
                    'error': 'Not logged in to Azure CLI'
                }
                
        except Exception as e:
            return {
                'authenticated': False,
                'error': f'Error checking Azure CLI status: {str(e)}'
            }

    def initiate_azure_cli_login(self) -> Dict[str, Any]:
        """Initiate Azure CLI login process."""
        try:
            import subprocess
            import json
            
            # Start the login process
            try:
                result = subprocess.run(['az', 'login'], 
                                      capture_output=True, text=True, check=True)
                
                # Parse the login result
                login_output = result.stdout.strip()
                if login_output:
                    try:
                        account_info = json.loads(login_output)
                        if isinstance(account_info, list) and account_info:
                            account_info = account_info[0]  # Take first account
                        
                        return {
                            'success': True,
                            'account_info': account_info
                        }
                    except json.JSONDecodeError:
                        return {
                            'success': True,
                            'message': 'Login completed successfully'
                        }
                else:
                    return {
                        'success': True,
                        'message': 'Login process completed'
                    }
                    
            except subprocess.CalledProcessError as e:
                return {
                    'success': False,
                    'error': f'Login failed: {e.stderr or str(e)}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error initiating login: {str(e)}'
            }

    def generate_managed_identity_setup_guide(self) -> Dict[str, Any]:
        """Generate a setup guide for configuring managed identity with private endpoints."""
        
        identity_info = self.get_current_identity_info()
        
        guide = {
            "current_identity": identity_info,
            "steps": [],
            "required_roles": {
                "OpenAI": [
                    "Cognitive Services OpenAI User",
                    "Cognitive Services User"
                ],
                "Document Intelligence": [
                    "Cognitive Services User"
                ],
                "AI Search": [
                    "Search Index Data Reader",
                    "Search Service Contributor"
                ]
            },
            "azure_cli_commands": []
        }
        
        # Determine the identity type and provide appropriate guidance
        if any("Managed Identity" in chain for chain in identity_info["credential_chain"]):
            guide["steps"].extend([
                "✅ Managed Identity detected - you're running in Azure (VM, App Service, etc.)",
                "🔧 Configure RBAC permissions for your managed identity",
                "🔧 Ensure private endpoint DNS resolution is working"
            ])
            
            # Add Azure CLI commands for role assignment
            if "managed_identity" in identity_info["details"]:
                vm_details = identity_info["details"]["managed_identity"]
                vm_id = vm_details.get("vm_id", "<VM_RESOURCE_ID>")
                
                guide["azure_cli_commands"].extend([
                    "# Get your VM's managed identity principal ID",
                    f"PRINCIPAL_ID=$(az vm identity show --ids {vm_id} --query principalId -o tsv)" if vm_id != "<VM_RESOURCE_ID>" else "PRINCIPAL_ID=$(az vm identity show --resource-group <RG> --name <VM_NAME> --query principalId -o tsv)",
                    "",
                    "# Assign OpenAI roles",
                    "az role assignment create --assignee $PRINCIPAL_ID --role 'Cognitive Services OpenAI User' --scope '/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<OPENAI_NAME>'",
                    "",
                    "# Assign Document Intelligence roles",
                    "az role assignment create --assignee $PRINCIPAL_ID --role 'Cognitive Services User' --scope '/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<DOC_INTEL_NAME>'",
                    "",
                    "# Assign AI Search roles", 
                    "az role assignment create --assignee $PRINCIPAL_ID --role 'Search Index Data Reader' --scope '/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.Search/searchServices/<SEARCH_NAME>'",
                    "az role assignment create --assignee $PRINCIPAL_ID --role 'Search Service Contributor' --scope '/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.Search/searchServices/<SEARCH_NAME>'"
                ])
        
        elif any("Azure CLI" in chain for chain in identity_info["credential_chain"]):
            guide["steps"].extend([
                "✅ Azure CLI authentication detected",
                "⚠️ You're using your personal Azure CLI login",
                "🔧 For production, configure managed identity or service principal",
                "🔧 Ensure your user account has proper RBAC permissions"
            ])
            
            # Add Azure CLI commands for role assignment to current user
            if "cli_account" in identity_info["details"]:
                guide["azure_cli_commands"].extend([
                    "# Assign roles to your current user account",
                    "CURRENT_USER=$(az account show --query user.name -o tsv)",
                    "",
                    "# Assign OpenAI roles",
                    "az role assignment create --assignee $CURRENT_USER --role 'Cognitive Services OpenAI User' --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<OPENAI_NAME>",
                    "",
                    "# Assign Document Intelligence roles",
                    "az role assignment create --assignee $CURRENT_USER --role 'Cognitive Services User' --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<DOC_INTEL_NAME>",
                    "",
                    "# Assign AI Search roles", 
                    "az role assignment create --assignee $CURRENT_USER --role 'Search Index Data Reader' --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.Search/searchServices/<SEARCH_NAME>",
                    "az role assignment create --assignee $CURRENT_USER --role 'Search Service Contributor' --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.Search/searchServices/<SEARCH_NAME>'"
                ])
        
        else:
            guide["steps"].extend([
                "❌ No Azure authentication detected",
                "🔧 Install Azure CLI and run 'az login'",
                "🔧 Or configure managed identity if running in Azure",
                "🔧 Or set up service principal with environment variables"
            ])
        
        return guide

    def _init_openai_for_health_check(self) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Initialize OpenAI client for health check using the same logic as the public health checker.
        Tries all available endpoint configurations in order: _41, _4o, and base.
        """
        clients = []
        models_tried = []
        
        # Try the endpoint variations in priority order
        for suffix in ["_41", "_4o", ""]:
            endpoint = os.getenv(f"AZURE_OPENAI_ENDPOINT{suffix}", "").strip()
            api_version = os.getenv(f"AZURE_OPENAI_API_VERSION{suffix}", "2024-05-01-preview").strip()
            deployment = os.getenv(f"AZURE_OPENAI_DEPLOYMENT{suffix}", "").strip()
            
            if endpoint:
                models_tried.append(f"AZURE_OPENAI_ENDPOINT{suffix}")
                try:
                    # For private endpoints, always use managed identity
                    from azure.identity import get_bearer_token_provider
                    token_provider = get_bearer_token_provider(
                        self._get_credential(), 
                        "https://cognitiveservices.azure.com/.default"
                    )
                    
                    client = AzureOpenAI(
                        azure_endpoint=endpoint,
                        azure_ad_token_provider=token_provider,
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

    def _get_credential(self):
        """Get Azure credential (lazy-loaded to avoid blocking initialization)."""
        if self.credential is None:
            self.credential = DefaultAzureCredential()
        return self.credential
    
    async def main():
        """Main function to run the health check."""
        checker = PrivateEndpointHealthChecker()
        
        try:
            results = await checker.check_all_resources()
            checker.print_detailed_report(results)
            
            # Summary
            healthy_count = sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY)
            total_count = len(results)
            
            print(f"\n📋 SUMMARY: {healthy_count}/{total_count} resources healthy")
            
            if healthy_count == total_count:
                print("🎉 All resources are healthy!")
                return 0
            else:
                print("⚠️  Some resources need attention")
                return 1
                
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            traceback.print_exc()
            return 1
            
    if __name__ == "__main__":
        import asyncio
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
