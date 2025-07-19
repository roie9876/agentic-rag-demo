#!/usr/bin/env python3
"""
Comprehensive Managed Identity and RBAC Health Checker
=====================================================
This module provides comprehensive managed identity authentication and RBAC permissions testing
for all Azure services used by the Agentic RAG Demo application.

Services tested:
- Azure Blob Storage
- Azure OpenAI
- Azure AI Search 
- Azure Document Intelligence

RBAC roles tested:
- Storage Blob Data Contributor/Reader (Blob Storage)
- Cognitive Services OpenAI User (OpenAI)
- Search Index Data Contributor/Reader (AI Search)
- Cognitive Services User (Document Intelligence)
"""

import os
import sys
import json
import logging
import asyncio
import subprocess
from typing import Dict, List, Optional, Tuple, Any, Union
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
    from azure.storage.blob import BlobServiceClient
    from azure.search.documents.indexes import SearchIndexClient
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from openai import AzureOpenAI
    from azure.identity import get_bearer_token_provider
    
except ImportError as e:
    print(f"❌ Missing required dependencies: {e}")
    print("Run: pip install azure-identity azure-storage-blob azure-search-documents azure-ai-documentintelligence openai")
    sys.exit(1)

from enum import Enum

class RBACTestStatus(Enum):
    """RBAC test status enumeration."""
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    WARNING = "⚠️ WARNING"
    SKIP = "⏭️ SKIP"
    ERROR = "🚨 ERROR"

@dataclass
class RBACTestResult:
    """Result of an RBAC test."""
    service: str
    role: str
    status: RBACTestStatus
    message: str
    details: Dict[str, Any] = None
    fix_command: Optional[str] = None
    azure_portal_link: Optional[str] = None

@dataclass
class ManagedIdentityInfo:
    """Information about the current managed identity."""
    type: str  # "SystemAssigned", "UserAssigned", "None"
    principal_id: Optional[str] = None
    client_id: Optional[str] = None
    vm_resource_id: Optional[str] = None
    tenant_id: Optional[str] = None

@dataclass
class ServiceConfig:
    """Configuration for an Azure service RBAC test."""
    name: str
    endpoint: str
    required_roles: List[str]
    test_operations: List[str]
    scope_type: str  # "resource" or "subscription"
    
class ManagedIdentityRBACChecker:
    """Comprehensive checker for managed identity and RBAC permissions."""
    
    def __init__(self):
        """Initialize the RBAC checker."""
        self.load_environment()
        self.credential = None  # Lazy-loaded
        self.managed_identity_info = None
        self.subscription_id = None
        
        # Service configurations
        self.service_configs = self._initialize_service_configs()
    
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
    
    def _initialize_service_configs(self) -> Dict[str, ServiceConfig]:
        """Initialize service configurations for RBAC testing."""
        return {
            'blob_storage': ServiceConfig(
                name="Azure Blob Storage",
                endpoint=os.getenv('AZURE_STORAGE_ACCOUNT_URL', '') or 
                         f"https://{os.getenv('AZURE_STORAGE_ACCOUNT_NAME', '')}.blob.core.windows.net" if os.getenv('AZURE_STORAGE_ACCOUNT_NAME') else '',
                required_roles=[
                    "Storage Blob Data Contributor",
                    "Storage Blob Data Reader"
                ],
                test_operations=["list_containers", "create_test_blob", "read_test_blob"],
                scope_type="resource"
            ),
            'openai': ServiceConfig(
                name="Azure OpenAI",
                endpoint=os.getenv('AZURE_OPENAI_ENDPOINT') or os.getenv('AZURE_OPENAI_ENDPOINT_41', ''),
                required_roles=[
                    "Cognitive Services OpenAI User",
                    "Cognitive Services User"
                ],
                test_operations=["list_models", "create_completion"],
                scope_type="resource"
            ),
            'ai_search': ServiceConfig(
                name="Azure AI Search",
                endpoint=os.getenv('AZURE_SEARCH_ENDPOINT', ''),
                required_roles=[
                    "Search Index Data Contributor", 
                    "Search Index Data Reader",
                    "Search Service Contributor"
                ],
                test_operations=["list_indexes", "query_index"],
                scope_type="resource"
            ),
            'document_intelligence': ServiceConfig(
                name="Azure Document Intelligence",
                endpoint=os.getenv('DOCUMENT_INTEL_ENDPOINT') or os.getenv('AZURE_FORMREC_ENDPOINT', ''),
                required_roles=[
                    "Cognitive Services User"
                ],
                test_operations=["analyze_document"],
                scope_type="resource"
            )
        }
    
    async def get_credential(self) -> DefaultAzureCredential:
        """Get Azure credential (lazy-loaded)."""
        if self.credential is None:
            self.credential = DefaultAzureCredential()
        return self.credential
    
    async def get_managed_identity_info(self) -> ManagedIdentityInfo:
        """Get information about the current managed identity."""
        if self.managed_identity_info is not None:
            return self.managed_identity_info
            
        identity_info = ManagedIdentityInfo(type="None")
        
        try:
            # First, try to get VM metadata (for system-assigned managed identity)
            import requests
            response = requests.get(
                'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/',
                headers={'Metadata': 'true'},
                timeout=5
            )
            
            if response.status_code == 200:
                token_info = response.json()
                identity_info.type = "SystemAssigned"
                identity_info.client_id = token_info.get('client_id')
                
                # Try to get more detailed info from IMDS
                vm_info_response = requests.get(
                    'http://169.254.169.254/metadata/instance?api-version=2021-02-01',
                    headers={'Metadata': 'true'},
                    timeout=5
                )
                
                if vm_info_response.status_code == 200:
                    vm_info = vm_info_response.json()
                    identity_info.vm_resource_id = vm_info.get('compute', {}).get('resourceId')
                    
        except Exception as e:
            logging.debug(f"Could not get managed identity info from IMDS: {e}")
        
        # Try Azure CLI to get more information
        try:
            result = subprocess.run(
                ["az", "account", "show", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                account_info = json.loads(result.stdout)
                identity_info.tenant_id = account_info.get("tenantId")
                
                # Get subscription ID
                self.subscription_id = account_info.get("id")
                
                # Check if we're using managed identity
                user_type = account_info.get("user", {}).get("type")
                if user_type == "managedIdentity":
                    if identity_info.type == "None":
                        identity_info.type = "SystemAssigned"
                        
        except Exception as e:
            logging.debug(f"Could not get Azure CLI account info: {e}")
            
        self.managed_identity_info = identity_info
        return identity_info
    
    async def test_blob_storage_rbac(self, config: ServiceConfig) -> List[RBACTestResult]:
        """Test Blob Storage RBAC permissions."""
        results = []
        
        if not config.endpoint:
            return [RBACTestResult(
                service="Azure Blob Storage",
                role="Configuration",
                status=RBACTestStatus.SKIP,
                message="No blob storage endpoint configured (AZURE_STORAGE_ACCOUNT_URL or AZURE_STORAGE_ACCOUNT_NAME)"
            )]
        
        try:
            credential = await self.get_credential()
            blob_service_client = BlobServiceClient(
                account_url=config.endpoint,
                credential=credential
            )
            
            # Test: List containers (requires Storage Blob Data Reader or higher)
            try:
                containers = list(blob_service_client.list_containers())
                results.append(RBACTestResult(
                    service="Azure Blob Storage",
                    role="Storage Blob Data Reader", 
                    status=RBACTestStatus.PASS,
                    message=f"✅ Successfully listed {len(containers)} containers",
                    details={"containers_count": len(containers)}
                ))
            except HttpResponseError as e:
                if e.status_code == 403:
                    results.append(RBACTestResult(
                        service="Azure Blob Storage",
                        role="Storage Blob Data Reader",
                        status=RBACTestStatus.FAIL,
                        message="❌ Cannot list containers - missing 'Storage Blob Data Reader' role",
                        fix_command=await self._generate_role_assignment_command("Storage Blob Data Reader", config.endpoint),
                        azure_portal_link=self._generate_portal_link("storage", config.endpoint)
                    ))
                else:
                    results.append(RBACTestResult(
                        service="Azure Blob Storage", 
                        role="Storage Blob Data Reader",
                        status=RBACTestStatus.ERROR,
                        message=f"🚨 Error listing containers: {e}"
                    ))
            
            # Test: Create blob (requires Storage Blob Data Contributor)
            try:
                # Get or create a test container
                container_name = "rbac-test-container"
                container_client = blob_service_client.get_container_client(container_name)
                
                # Try to create container if it doesn't exist
                try:
                    container_client.create_container()
                except Exception:
                    pass  # Container might already exist
                
                # Try to upload a test blob
                blob_name = f"rbac-test-{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
                blob_client = container_client.get_blob_client(blob_name)
                
                test_content = "RBAC test content"
                blob_client.upload_blob(test_content, overwrite=True)
                
                # Clean up test blob
                blob_client.delete_blob()
                
                results.append(RBACTestResult(
                    service="Azure Blob Storage",
                    role="Storage Blob Data Contributor",
                    status=RBACTestStatus.PASS,
                    message="✅ Successfully created and deleted test blob",
                    details={"test_blob": blob_name}
                ))
                
            except HttpResponseError as e:
                if e.status_code == 403:
                    results.append(RBACTestResult(
                        service="Azure Blob Storage",
                        role="Storage Blob Data Contributor", 
                        status=RBACTestStatus.FAIL,
                        message="❌ Cannot create/delete blobs - missing 'Storage Blob Data Contributor' role",
                        fix_command=await self._generate_role_assignment_command("Storage Blob Data Contributor", config.endpoint),
                        azure_portal_link=self._generate_portal_link("storage", config.endpoint)
                    ))
                else:
                    results.append(RBACTestResult(
                        service="Azure Blob Storage",
                        role="Storage Blob Data Contributor",
                        status=RBACTestStatus.ERROR,
                        message=f"🚨 Error creating test blob: {e}"
                    ))
                    
        except Exception as e:
            results.append(RBACTestResult(
                service="Azure Blob Storage",
                role="General",
                status=RBACTestStatus.ERROR,
                message=f"🚨 Failed to initialize blob storage client: {e}"
            ))
        
        return results
    
    async def test_openai_rbac(self, config: ServiceConfig) -> List[RBACTestResult]:
        """Test OpenAI RBAC permissions."""
        results = []
        
        if not config.endpoint:
            return [RBACTestResult(
                service="Azure OpenAI",
                role="Configuration",
                status=RBACTestStatus.SKIP,
                message="No OpenAI endpoint configured (AZURE_OPENAI_ENDPOINT)"
            )]
        
        try:
            credential = await self.get_credential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
            
            client = AzureOpenAI(
                azure_endpoint=config.endpoint,
                azure_ad_token_provider=token_provider,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
            )
            
            # Test: List models (requires Cognitive Services User or higher)
            try:
                models = list(client.models.list())
                results.append(RBACTestResult(
                    service="Azure OpenAI",
                    role="Cognitive Services User",
                    status=RBACTestStatus.PASS,
                    message=f"✅ Successfully listed {len(models)} models",
                    details={"models_count": len(models), "models": [m.id for m in models[:5]]}
                ))
            except Exception as e:
                if "403" in str(e) or "Forbidden" in str(e):
                    results.append(RBACTestResult(
                        service="Azure OpenAI",
                        role="Cognitive Services User",
                        status=RBACTestStatus.FAIL,
                        message="❌ Cannot list models - missing 'Cognitive Services User' role",
                        fix_command=await self._generate_role_assignment_command("Cognitive Services User", config.endpoint),
                        azure_portal_link=self._generate_portal_link("cognitiveservices", config.endpoint)
                    ))
                else:
                    results.append(RBACTestResult(
                        service="Azure OpenAI",
                        role="Cognitive Services User", 
                        status=RBACTestStatus.ERROR,
                        message=f"🚨 Error listing models: {e}"
                    ))
            
            # Test: Create completion (requires Cognitive Services OpenAI User)
            try:
                deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT_41", "")
                if deployment:
                    response = client.completions.create(
                        model=deployment,
                        prompt="Test prompt for RBAC validation",
                        max_tokens=5
                    )
                    
                    results.append(RBACTestResult(
                        service="Azure OpenAI", 
                        role="Cognitive Services OpenAI User",
                        status=RBACTestStatus.PASS,
                        message="✅ Successfully created completion",
                        details={"deployment": deployment, "response_id": response.id}
                    ))
                else:
                    results.append(RBACTestResult(
                        service="Azure OpenAI",
                        role="Cognitive Services OpenAI User",
                        status=RBACTestStatus.SKIP,
                        message="⏭️ No deployment configured for completion test (AZURE_OPENAI_DEPLOYMENT)"
                    ))
                    
            except Exception as e:
                if "403" in str(e) or "Forbidden" in str(e):
                    results.append(RBACTestResult(
                        service="Azure OpenAI",
                        role="Cognitive Services OpenAI User",
                        status=RBACTestStatus.FAIL,
                        message="❌ Cannot create completions - missing 'Cognitive Services OpenAI User' role",
                        fix_command=await self._generate_role_assignment_command("Cognitive Services OpenAI User", config.endpoint),
                        azure_portal_link=self._generate_portal_link("cognitiveservices", config.endpoint)
                    ))
                else:
                    results.append(RBACTestResult(
                        service="Azure OpenAI",
                        role="Cognitive Services OpenAI User",
                        status=RBACTestStatus.ERROR,
                        message=f"🚨 Error creating completion: {e}"
                    ))
                    
        except Exception as e:
            results.append(RBACTestResult(
                service="Azure OpenAI",
                role="General",
                status=RBACTestStatus.ERROR,
                message=f"🚨 Failed to initialize OpenAI client: {e}"
            ))
        
        return results
    
    async def test_ai_search_rbac(self, config: ServiceConfig) -> List[RBACTestResult]:
        """Test AI Search RBAC permissions."""
        results = []
        
        if not config.endpoint:
            return [RBACTestResult(
                service="Azure AI Search",
                role="Configuration", 
                status=RBACTestStatus.SKIP,
                message="No AI Search endpoint configured (AZURE_SEARCH_ENDPOINT)"
            )]
        
        try:
            credential = await self.get_credential()
            search_client = SearchIndexClient(endpoint=config.endpoint, credential=credential)
            
            # Test: List indexes (requires Search Index Data Reader or higher)
            try:
                indexes = list(search_client.list_indexes())
                results.append(RBACTestResult(
                    service="Azure AI Search",
                    role="Search Index Data Reader",
                    status=RBACTestStatus.PASS,
                    message=f"✅ Successfully listed {len(indexes)} indexes",
                    details={"indexes_count": len(indexes), "indexes": [idx.name for idx in indexes[:5]]}
                ))
            except HttpResponseError as e:
                if e.status_code == 403:
                    results.append(RBACTestResult(
                        service="Azure AI Search",
                        role="Search Index Data Reader",
                        status=RBACTestStatus.FAIL,
                        message="❌ Cannot list indexes - missing 'Search Index Data Reader' role",
                        fix_command=await self._generate_role_assignment_command("Search Index Data Reader", config.endpoint),
                        azure_portal_link=self._generate_portal_link("search", config.endpoint)
                    ))
                else:
                    results.append(RBACTestResult(
                        service="Azure AI Search",
                        role="Search Index Data Reader",
                        status=RBACTestStatus.ERROR,
                        message=f"🚨 Error listing indexes: {e}"
                    ))
            
            # Test: Get service statistics (requires Search Service Contributor)
            try:
                stats = search_client.get_service_statistics()
                results.append(RBACTestResult(
                    service="Azure AI Search",
                    role="Search Service Contributor",
                    status=RBACTestStatus.PASS,
                    message="✅ Successfully retrieved service statistics",
                    details={"document_count": stats.counters.document_count, 
                            "index_count": stats.counters.index_count}
                ))
            except HttpResponseError as e:
                if e.status_code == 403:
                    results.append(RBACTestResult(
                        service="Azure AI Search",
                        role="Search Service Contributor",
                        status=RBACTestStatus.FAIL,
                        message="❌ Cannot get service statistics - missing 'Search Service Contributor' role",
                        fix_command=await self._generate_role_assignment_command("Search Service Contributor", config.endpoint),
                        azure_portal_link=self._generate_portal_link("search", config.endpoint)
                    ))
                else:
                    results.append(RBACTestResult(
                        service="Azure AI Search",
                        role="Search Service Contributor", 
                        status=RBACTestStatus.ERROR,
                        message=f"🚨 Error getting service statistics: {e}"
                    ))
                    
        except Exception as e:
            results.append(RBACTestResult(
                service="Azure AI Search",
                role="General",
                status=RBACTestStatus.ERROR,
                message=f"🚨 Failed to initialize AI Search client: {e}"
            ))
        
        return results
    
    async def test_document_intelligence_rbac(self, config: ServiceConfig) -> List[RBACTestResult]:
        """Test Document Intelligence RBAC permissions."""
        results = []
        
        if not config.endpoint:
            return [RBACTestResult(
                service="Azure Document Intelligence",
                role="Configuration",
                status=RBACTestStatus.SKIP,
                message="No Document Intelligence endpoint configured (DOCUMENT_INTEL_ENDPOINT)"
            )]
        
        try:
            credential = await self.get_credential()
            doc_client = DocumentIntelligenceClient(
                endpoint=config.endpoint,
                credential=credential
            )
            
            # Test: Get document models (requires Cognitive Services User)
            try:
                models = doc_client.list_document_models()
                model_list = list(models)
                results.append(RBACTestResult(
                    service="Azure Document Intelligence",
                    role="Cognitive Services User",
                    status=RBACTestStatus.PASS,
                    message=f"✅ Successfully listed {len(model_list)} document models",
                    details={"models_count": len(model_list), "models": [m.model_id for m in model_list[:5]]}
                ))
            except HttpResponseError as e:
                if e.status_code == 403:
                    results.append(RBACTestResult(
                        service="Azure Document Intelligence",
                        role="Cognitive Services User",
                        status=RBACTestStatus.FAIL,
                        message="❌ Cannot list document models - missing 'Cognitive Services User' role",
                        fix_command=await self._generate_role_assignment_command("Cognitive Services User", config.endpoint),
                        azure_portal_link=self._generate_portal_link("cognitiveservices", config.endpoint)
                    ))
                else:
                    results.append(RBACTestResult(
                        service="Azure Document Intelligence",
                        role="Cognitive Services User",
                        status=RBACTestStatus.ERROR,
                        message=f"🚨 Error listing models: {e}"
                    ))
                    
        except Exception as e:
            results.append(RBACTestResult(
                service="Azure Document Intelligence",
                role="General",
                status=RBACTestStatus.ERROR,
                message=f"🚨 Failed to initialize Document Intelligence client: {e}"
            ))
        
        return results
    
    async def test_all_rbac_permissions(self) -> Dict[str, List[RBACTestResult]]:
        """Test RBAC permissions for all services."""
        results = {}
        
        # Get managed identity info first
        identity_info = await self.get_managed_identity_info()
        
        # Test each service
        results["blob_storage"] = await self.test_blob_storage_rbac(self.service_configs["blob_storage"])
        results["openai"] = await self.test_openai_rbac(self.service_configs["openai"])
        results["ai_search"] = await self.test_ai_search_rbac(self.service_configs["ai_search"])
        results["document_intelligence"] = await self.test_document_intelligence_rbac(self.service_configs["document_intelligence"])
        
        return results
    
    async def _generate_role_assignment_command(self, role_name: str, endpoint: str) -> str:
        """Generate Azure CLI command to assign a role."""
        identity_info = await self.get_managed_identity_info()
        
        if identity_info.type == "SystemAssigned" and identity_info.vm_resource_id:
            # For system-assigned managed identity
            vm_id = identity_info.vm_resource_id
            resource_info = self._parse_resource_info_from_endpoint(endpoint)
            
            if resource_info:
                return (
                    f"# Get VM's managed identity principal ID\n"
                    f"PRINCIPAL_ID=$(az vm identity show --ids {vm_id} --query principalId -o tsv)\n"
                    f"# Assign role\n"
                    f"az role assignment create --assignee $PRINCIPAL_ID --role '{role_name}' "
                    f"--scope '/subscriptions/{self.subscription_id}/resourceGroups/{resource_info['rg']}/providers/{resource_info['provider']}/{resource_info['name']}'"
                )
        
        return f"az role assignment create --assignee <PRINCIPAL_ID> --role '{role_name}' --scope <RESOURCE_SCOPE>"
    
    def _parse_resource_info_from_endpoint(self, endpoint: str) -> Optional[Dict[str, str]]:
        """Parse resource information from an endpoint URL."""
        try:
            if "blob.core.windows.net" in endpoint:
                # Storage account
                account_name = endpoint.split("://")[1].split(".")[0]
                return {
                    "name": account_name,
                    "provider": "Microsoft.Storage/storageAccounts",
                    "rg": "<RESOURCE_GROUP>"  # Would need to be discovered
                }
            elif "openai.azure.com" in endpoint:
                # OpenAI account
                account_name = endpoint.split("://")[1].split(".")[0]
                return {
                    "name": account_name,
                    "provider": "Microsoft.CognitiveServices/accounts",
                    "rg": "<RESOURCE_GROUP>"
                }
            elif "search.windows.net" in endpoint:
                # Search service
                service_name = endpoint.split("://")[1].split(".")[0]
                return {
                    "name": service_name,
                    "provider": "Microsoft.Search/searchServices",
                    "rg": "<RESOURCE_GROUP>"
                }
            elif "cognitiveservices.azure.com" in endpoint:
                # Cognitive services account
                account_name = endpoint.split("://")[1].split(".")[0]
                return {
                    "name": account_name,
                    "provider": "Microsoft.CognitiveServices/accounts",
                    "rg": "<RESOURCE_GROUP>"
                }
        except Exception:
            pass
            
        return None
    
    def _generate_portal_link(self, service_type: str, endpoint: str) -> str:
        """Generate Azure Portal link for RBAC configuration."""
        base_url = "https://portal.azure.com/#@/resource"
        
        resource_info = self._parse_resource_info_from_endpoint(endpoint)
        if resource_info and self.subscription_id:
            resource_id = f"/subscriptions/{self.subscription_id}/resourceGroups/{resource_info['rg']}/providers/{resource_info['provider']}/{resource_info['name']}"
            return f"{base_url}{resource_id}/users"
        
        return "https://portal.azure.com"
    
    def generate_rbac_fix_summary(self, all_results: Dict[str, List[RBACTestResult]]) -> Dict[str, Any]:
        """Generate a summary of RBAC issues and fixes."""
        summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "skipped": 0,
            "errors": 0,
            "failed_roles": [],
            "fix_commands": [],
            "portal_links": []
        }
        
        for service_name, results in all_results.items():
            for result in results:
                summary["total_tests"] += 1
                
                if result.status == RBACTestStatus.PASS:
                    summary["passed"] += 1
                elif result.status == RBACTestStatus.FAIL:
                    summary["failed"] += 1
                    summary["failed_roles"].append(f"{result.service}: {result.role}")
                    if result.fix_command:
                        summary["fix_commands"].append(result.fix_command)
                    if result.azure_portal_link:
                        summary["portal_links"].append({
                            "service": result.service,
                            "url": result.azure_portal_link
                        })
                elif result.status == RBACTestStatus.WARNING:
                    summary["warnings"] += 1
                elif result.status == RBACTestStatus.SKIP:
                    summary["skipped"] += 1
                elif result.status == RBACTestStatus.ERROR:
                    summary["errors"] += 1
        
        return summary
