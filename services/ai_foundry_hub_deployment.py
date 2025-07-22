"""
AI Foundry Hub Deployment Service
--------------------------------
Service for deploying new AI Foundry Hubs using the bicep template from
15-private-network-standard-agent-setup directory.

This service handles:
- Parameter collection for bicep template
- Resource selection (new vs existing)
- Private endpoint configuration
- DNS configuration
- Bicep template deployment
"""

import os
import json
import logging
import subprocess
import traceback
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from azure.identity import DefaultAzureCredential, AzureCliCredential
from utils.azure_helpers import check_azure_cli_login

logger = logging.getLogger(__name__)

@dataclass
class DeploymentResource:
    """Represents a resource that can be deployed or used as existing."""
    name: str
    resource_type: str
    create_new: bool = True
    skip_deployment: bool = False  # Option to skip deployment entirely
    existing_resource_id: str = ""
    use_private_endpoint: bool = False
    use_dns: bool = False
    # For existing resources with custom DNS
    custom_dns_records: Dict[str, str] = None
    create_private_endpoint: bool = False  # For existing resources
    create_dns_records: bool = False  # For existing resources
    existing_private_endpoint_name: str = ""  # Name of existing private endpoint to use
    
    def __post_init__(self):
        """Initialize default values."""
        if self.custom_dns_records is None:
            self.custom_dns_records = {}

@dataclass
class NetworkConfig:
    """Network configuration for the deployment."""
    create_new_vnet: bool = True
    existing_vnet_resource_id: str = ""
    vnet_name: str = "agent-vnet-test"
    vnet_address_prefix: str = "192.168.0.0/16"
    agent_subnet_name: str = "agent-subnet"
    agent_subnet_prefix: str = "192.168.0.0/24"
    pe_subnet_name: str = "pe-subnet"
    pe_subnet_prefix: str = "192.168.1.0/24"
    # For existing VNet subnet selection
    existing_agent_subnet_id: str = ""
    existing_pe_subnet_id: str = ""

@dataclass
class AIFoundryHubDeploymentConfig:
    """Configuration for AI Foundry Hub deployment."""
    # Basic settings
    location: str = "eastus2"
    ai_services_name: str = "aiservices"
    project_name: str = "project"
    project_description: str = "A project for the AI Foundry account with network secured deployed Agent"
    display_name: str = "network secured agent project"
    
    # Model settings (OpenAI deployment) - Fixed configuration
    model_name: str = "gpt-4.1"
    model_format: str = "OpenAI"
    model_version: str = "2025-04-14"
    model_sku_name: str = "GlobalStandard"
    model_capacity: int = 30
    skip_openai_deployment: bool = False  # Default to deploy OpenAI model
    
    # DNS Zone Configuration
    dns_zone_subscription_id: str = ""  # Default to current subscription
    dns_zone_resource_group_name: str = ""  # Default to current resource group
    create_dns_zones_if_not_exist: bool = False  # Default to use existing DNS zones
    
    # Network configuration
    network_config: NetworkConfig = None
    
    # Resources
    cosmos_db: DeploymentResource = None
    ai_search: DeploymentResource = None
    storage_account: DeploymentResource = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.network_config is None:
            self.network_config = NetworkConfig()
        if self.cosmos_db is None:
            self.cosmos_db = DeploymentResource("cosmos-db", "Microsoft.DocumentDB/databaseAccounts")
        if self.ai_search is None:
            self.ai_search = DeploymentResource("ai-search", "Microsoft.Search/searchServices")
        if self.storage_account is None:
            self.storage_account = DeploymentResource("storage-account", "Microsoft.Storage/storageAccounts")

class AIFoundryHubDeploymentService:
    """Service for deploying AI Foundry Hubs with bicep templates."""
    
    def __init__(self):
        """Initialize the deployment service."""
        self.credential = None
        self.cli_credential = None
        # Dynamic path detection - works on any machine with any user
        self.template_path = self._get_template_path()
        # Lazy credential initialization - only when needed
    
    def _get_template_path(self) -> str:
        """Get the template path dynamically, works on any machine."""
        import os
        
        # Try to find project root by looking for agentic-rag-demo.py
        current_file = os.path.abspath(__file__)
        current_dir = os.path.dirname(current_file)
        
        # Go up directories until we find the project root
        search_dir = current_dir
        max_levels = 10  # Prevent infinite loops
        
        for _ in range(max_levels):
            # Check if this is the project root
            if os.path.exists(os.path.join(search_dir, "agentic-rag-demo.py")):
                template_path = os.path.join(search_dir, "15-private-network-standard-agent-setup")
                logger.info(f"Found template path: {template_path}")
                return template_path
            
            parent_dir = os.path.dirname(search_dir)
            if parent_dir == search_dir:  # Reached filesystem root
                break
            search_dir = parent_dir
        
        # Fallback: try relative path from current working directory
        cwd_template_path = os.path.join(os.getcwd(), "15-private-network-standard-agent-setup")
        if os.path.exists(cwd_template_path):
            logger.info(f"Using fallback template path: {cwd_template_path}")
            return cwd_template_path
        
        # Last resort: use original path (will fail on different machines but maintains backward compatibility)
        fallback_path = "/home/azureuser/agentic-rag-demo/15-private-network-standard-agent-setup"
        logger.warning(f"Could not find template path dynamically, using fallback: {fallback_path}")
        return fallback_path
    
    def _initialize_credentials(self):
        """Initialize Azure credentials lazily."""
        if self.credential is None:
            try:
                # Try managed identity first
                self.credential = DefaultAzureCredential()
                self.cli_credential = AzureCliCredential()
                logger.info("AI Foundry Hub deployment service credentials initialized")
            except Exception as e:
                logger.error(f"Failed to initialize credentials: {e}")
    
    def get_available_subscriptions(self) -> List[Dict[str, str]]:
        """Get list of available Azure subscriptions using Azure CLI."""
        try:
            import subprocess
            import json
            
            logger.info("Getting available subscriptions using Azure CLI...")
            
            # Use Azure CLI to get all accessible subscriptions
            result = subprocess.run([
                "az", "account", "list", 
                "--all", 
                "--output", "json"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"Azure CLI command failed: {result.stderr}")
                return []
            
            try:
                subscriptions_data = json.loads(result.stdout)
                logger.info(f"Found {len(subscriptions_data)} subscriptions via Azure CLI")
                
                subscriptions = []
                for sub in subscriptions_data:
                    subscription_info = {
                        "subscription_id": sub.get("id", ""),
                        "subscription_name": sub.get("name", "Unknown"),  # Use subscription_name for consistency
                        "display_name": sub.get("name", "Unknown"),  # Keep for backward compatibility
                        "state": sub.get("state", "Unknown"),
                        "tenantId": sub.get("tenantId", ""),
                        "isDefault": sub.get("isDefault", False),
                        "user": sub.get("user", {})
                    }
                    subscriptions.append(subscription_info)
                    logger.debug(f"Subscription: {subscription_info['subscription_name']} ({subscription_info['subscription_id']})")
                
                # Sort subscriptions: default first, then alphabetically
                subscriptions.sort(key=lambda x: (not x.get("isDefault", False), x.get("subscription_name", "")))
                
                return subscriptions
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Azure CLI output: {e}")
                logger.error(f"Raw output: {result.stdout}")
                return []
            
        except subprocess.TimeoutExpired:
            logger.error("Azure CLI command timed out")
            return []
        except Exception as e:
            logger.error(f"Failed to get subscriptions via Azure CLI: {e}")
            # Fallback to Azure SDK method
            return self._get_subscriptions_via_sdk()
    
    def get_current_subscription_info(self) -> Optional[Dict[str, str]]:
        """Get information about the current default subscription."""
        try:
            # Use the comprehensive context method for consistency
            context_info = self.get_subscription_context_info()
            
            if context_info and context_info.get('subscription_id') not in ['Not logged in', 'Error']:
                return {
                    "subscription_id": context_info.get('subscription_id'),
                    "subscription_name": context_info.get('subscription_name'),
                    "display_name": context_info.get('subscription_name'),  # For backward compatibility
                    "state": context_info.get('state'),
                    "tenant_id": context_info.get('tenant_id'),
                    "user_name": context_info.get('user_name')
                }
            
            return None
        except Exception as e:
            logger.error(f"Failed to get current subscription info: {e}")
            return None
    
    def get_prioritized_subscriptions(self) -> List[Dict[str, str]]:
        """Get subscriptions with current subscription prioritized at the top."""
        try:
            all_subs = self.get_available_subscriptions()
            current_sub = self.get_current_subscription_info()
            
            if not current_sub:
                return all_subs
            
            # Remove current subscription from list and add it at the top
            other_subs = [sub for sub in all_subs if sub['subscription_id'] != current_sub['subscription_id']]
            return [current_sub] + other_subs
            
        except Exception as e:
            logger.error(f"Failed to get prioritized subscriptions: {e}")
            return self.get_available_subscriptions()
    
    def get_resource_groups_for_subscription(self, subscription_id: str) -> List[str]:
        """Get list of resource groups for a specific subscription using Azure CLI."""
        try:
            # Check if Azure CLI is logged in
            logged_in, error = check_azure_cli_login()
            if not logged_in:
                logger.error(f"Azure CLI not logged in: {error}")
                return []

            # Use Azure CLI which is more reliable than SDK for cross-subscription queries
            cmd = ["az", "group", "list", "--subscription", subscription_id, "--query", "[].name", "--output", "json"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                resource_groups = json.loads(result.stdout)
                return sorted(resource_groups)
            else:
                logger.error(f"Failed to get resource groups for subscription {subscription_id}: {result.stderr}")
                return []
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout getting resource groups for subscription {subscription_id}")
            return []
        except Exception as e:
            logger.error(f"Failed to get resource groups for subscription {subscription_id}: {e}")
            return []
    
    def suggest_dns_zone_resource_groups(self, subscription_id: str) -> List[str]:
        """Get resource groups with common DNS zone naming patterns prioritized."""
        try:
            logger.info(f"Getting resource groups for DNS zone subscription: {subscription_id}")
            all_rgs = self.get_resource_groups_for_subscription(subscription_id)
            logger.info(f"Found {len(all_rgs)} resource groups in subscription {subscription_id}")
            
            if not all_rgs:
                logger.warning(f"No resource groups found in subscription {subscription_id}")
                return []
            
            # Common patterns for DNS zone resource groups
            dns_patterns = [
                'private-rg', 'network-rg', 'dns-zones-rg', 'shared-network-rg',
                'hub-network-rg', 'connectivity-rg', 'network-hub-rg'
            ]
            
            prioritized_rgs = []
            remaining_rgs = []
            
            for rg in all_rgs:
                rg_lower = rg.lower()
                if any(pattern in rg_lower for pattern in ['private', 'dns', 'network', 'hub', 'connectivity']):
                    prioritized_rgs.append(rg)
                else:
                    remaining_rgs.append(rg)
            
            # Sort prioritized by common patterns
            def sort_key(rg):
                rg_lower = rg.lower()
                for i, pattern in enumerate(dns_patterns):
                    if pattern in rg_lower:
                        return i
                return len(dns_patterns)
            
            prioritized_rgs.sort(key=sort_key)
            
            result = prioritized_rgs + remaining_rgs
            logger.info(f"Returning {len(result)} resource groups, {len(prioritized_rgs)} prioritized")
            return result
            
        except Exception as e:
            logger.error(f"Failed to suggest DNS zone resource groups: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fallback to basic resource group listing
            fallback_rgs = self.get_resource_groups_for_subscription(subscription_id)
            logger.info(f"Fallback returned {len(fallback_rgs)} resource groups")
            return fallback_rgs

    def validate_dns_zones_exist(self, subscription_id: str, resource_group_name: str) -> Dict[str, bool]:
        """Validate that required private DNS zones exist in the specified location using Azure CLI."""
        try:
            required_zones = [
                "privatelink.services.ai.azure.com",
                "privatelink.openai.azure.com",
                "privatelink.cognitiveservices.azure.com",
                "privatelink.search.windows.net",
                "privatelink.blob.core.windows.net",
                "privatelink.documents.azure.com"
            ]
            
            logger.info(f"🔍 Validating DNS zones in subscription {subscription_id[:8]}..., resource group: {resource_group_name}")
            
            # Use Azure CLI to list private DNS zones in the resource group
            cmd = [
                "az", "network", "private-dns", "zone", "list",
                "--subscription", subscription_id,
                "--resource-group", resource_group_name
            ]
            
            logger.debug(f"Running DNS zone discovery command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"❌ Failed to list private DNS zones: {result.stderr}")
                logger.error(f"Command: {' '.join(cmd)}")
                return {}
            
            # Parse the JSON response
            try:
                zones_data = json.loads(result.stdout)
                existing_zones = [zone.get('name', '') for zone in zones_data if zone.get('name')]
                
                logger.info(f"📍 Found {len(existing_zones)} private DNS zones in {resource_group_name}")
                logger.debug(f"Existing zones: {existing_zones}")
                
                # Check each required zone
                zone_status = {}
                for zone_name in required_zones:
                    exists = zone_name in existing_zones
                    zone_status[zone_name] = exists
                    status_emoji = "✅" if exists else "❌"
                    logger.debug(f"{status_emoji} {zone_name}: {'Found' if exists else 'Not found'}")
                
                found_count = sum(zone_status.values())
                logger.info(f"🎯 DNS Zone validation complete: {found_count}/{len(required_zones)} required zones found")
                
                return zone_status
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse DNS zones JSON response: {e}")
                logger.debug(f"Raw output: {result.stdout[:500]}...")
                return {}
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Timeout validating DNS zones in {resource_group_name}")
            return {}
        except Exception as e:
            logger.error(f"❌ Unexpected error validating DNS zones: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {}

    def validate_template_path(self) -> Tuple[bool, str]:
        """Validate that either ARM or Bicep template exists."""
        try:
            main_json = os.path.join(self.template_path, "main.json")
            main_bicep = os.path.join(self.template_path, "main.bicep")
            
            # Check for ARM template first (preferred to avoid BCP177)
            if os.path.exists(main_json):
                print(f"✅ DEBUG: ARM template found: {main_json}")
                
                # Check for modules directory
                modules_dir = os.path.join(self.template_path, "modules-network-secured")
                if not os.path.exists(modules_dir):
                    return False, f"Modules directory not found: {modules_dir}"
                
                return True, f"ARM template validation successful: {main_json}"
            
            # Fallback to Bicep template
            elif os.path.exists(main_bicep):
                print(f"⚠️ DEBUG: Bicep template found: {main_bicep}")
                print(f"💡 DEBUG: Note: ARM template (main.json) is preferred to avoid Bicep compilation issues")
                
                # Check for modules directory
                modules_dir = os.path.join(self.template_path, "modules-network-secured")
                if not os.path.exists(modules_dir):
                    return False, f"Modules directory not found: {modules_dir}"
                
                return True, f"Bicep template validation successful: {main_bicep}"
            
            else:
                return False, f"Neither main.json nor main.bicep template found in: {self.template_path}"
            
        except Exception as e:
            return False, f"Template validation failed: {str(e)}"
    
    def get_available_locations(self) -> List[str]:
        """Get available locations for AI Foundry Hub deployment."""
        return [
            'australiaeast',
            'eastus',
            'eastus2',
            'francecentral',
            'japaneast',
            'norwayeast',
            'southindia',
            'swedencentral',
            'uaenorth',
            'uksouth',
            'westus',
            'westus3',
            'westus2'
        ]
    
    def get_subscription_resource_groups(self, subscription_id: Optional[str] = None) -> List[str]:
        """Get available resource groups in the subscription.
        
        Args:
            subscription_id: Optional subscription ID. If not provided, uses current subscription.
        """
        try:
            # Check if Azure CLI is logged in
            logged_in, error = check_azure_cli_login()
            if not logged_in:
                logger.error(f"Azure CLI not logged in: {error}")
                return []
            
            # Build command with optional subscription parameter
            cmd = ["az", "group", "list", "--query", "[].name", "--output", "json"]
            if subscription_id:
                cmd.extend(["--subscription", subscription_id])
            
            # Get resource groups using Azure CLI
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                resource_groups = json.loads(result.stdout)
                return sorted(resource_groups)
            else:
                logger.error(f"Failed to get resource groups: {result.stderr}")
                return []
        except Exception as e:
            logger.error(f"Error getting resource groups: {str(e)}")
            return []
    
    def get_subscription_resources(self, resource_type: str) -> List[Dict[str, Any]]:
        """Get available resources of a specific type in the subscription."""
        try:
            # Check if Azure CLI is logged in
            logged_in, error = check_azure_cli_login()
            if not logged_in:
                logger.error(f"Azure CLI not logged in: {error}")
                return []
            
            # Get resources using Azure CLI
            result = subprocess.run([
                "az", "resource", "list",
                "--resource-type", resource_type,
                "--query", "[].{name:name, resourceGroup:resourceGroup, id:id, location:location}",
                "--output", "json"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                resources = json.loads(result.stdout)
                return resources
            else:
                logger.error(f"Failed to get resources of type {resource_type}: {result.stderr}")
                return []
        except Exception as e:
            logger.error(f"Error getting resources of type {resource_type}: {str(e)}")
            return []
    
    def generate_bicep_parameters(self, config: AIFoundryHubDeploymentConfig, resource_group: str = "", subscription_id: str = "") -> Dict[str, Any]:
        """Generate bicep parameters from deployment configuration."""
        
        # Get current subscription ID if not provided
        if not subscription_id:
            try:
                import subprocess
                result = subprocess.run([
                    "az", "account", "show", "--query", "id", "--output", "tsv"
                ], capture_output=True, text=True, timeout=30)
                subscription_id = result.stdout.strip() if result.returncode == 0 else ""
            except Exception:
                subscription_id = ""
        
        params = {
            "location": {"value": config.location},
            "aiServices": {"value": config.ai_services_name},
            "firstProjectName": {"value": config.project_name},
            "projectDescription": {"value": config.project_description},
            "displayName": {"value": config.display_name},
            "modelName": {"value": config.model_name},
            "modelFormat": {"value": config.model_format},
            "modelVersion": {"value": config.model_version},
            "modelSkuName": {"value": config.model_sku_name},
            "modelCapacity": {"value": config.model_capacity},
            "skipOpenAIDeployment": {"value": config.skip_openai_deployment}
        }
        
        # DNS Zone Configuration
        params["dnsZoneSubscriptionId"] = {"value": config.dns_zone_subscription_id or subscription_id}
        params["dnsZoneResourceGroupName"] = {"value": config.dns_zone_resource_group_name or resource_group}
        params["createDnsZonesIfNotExist"] = {"value": config.create_dns_zones_if_not_exist}
        
        # Network configuration
        if config.network_config.create_new_vnet:
            # For new VNet, pass the network configuration
            params["vnetName"] = {"value": config.network_config.vnet_name}
            params["vnetAddressPrefix"] = {"value": config.network_config.vnet_address_prefix}
            params["agentSubnetName"] = {"value": config.network_config.agent_subnet_name}
            params["agentSubnetPrefix"] = {"value": config.network_config.agent_subnet_prefix}
            params["peSubnetName"] = {"value": config.network_config.pe_subnet_name}
            params["peSubnetPrefix"] = {"value": config.network_config.pe_subnet_prefix}
            # Pass empty existingVnetResourceId for new VNet
            params["existingVnetResourceId"] = {"value": ""}
            params["createSubnetsInExistingVnet"] = {"value": False}
        else:
            # For existing VNet, pass the full resource ID and let bicep extract the name
            vnet_resource_id = config.network_config.existing_vnet_resource_id
            
            params["existingVnetResourceId"] = {"value": vnet_resource_id}
            # Pass vnetName for new VNet creation scenarios, bicep will use extracted name for existing VNet
            params["vnetName"] = {"value": config.network_config.vnet_name}
            
            # Check if we're creating new subnets or using existing ones
            has_explicit_subnet_ids = (hasattr(config.network_config, 'existing_agent_subnet_id') and config.network_config.existing_agent_subnet_id) or \
                                     (hasattr(config.network_config, 'existing_pe_subnet_id') and config.network_config.existing_pe_subnet_id)
            
            # Initialize subnet existence flags
            agent_subnet_exists = False
            pe_subnet_exists = False
            
            # If no explicit subnet IDs were provided, try to auto-detect existing subnets by name
            if not has_explicit_subnet_ids and vnet_resource_id:
                try:
                    existing_subnets = self.get_vnet_subnets(vnet_resource_id)
                    subnet_names = [s.get('name', '') for s in existing_subnets]
                    
                    # Check individual subnet existence
                    agent_subnet_exists = config.network_config.agent_subnet_name in subnet_names
                    pe_subnet_exists = config.network_config.pe_subnet_name in subnet_names
                    
                    if agent_subnet_exists and pe_subnet_exists:
                        logger.info(f"Auto-detected existing subnets: {config.network_config.agent_subnet_name}, {config.network_config.pe_subnet_name}")
                    elif agent_subnet_exists or pe_subnet_exists:
                        logger.info(f"Partial subnet overlap detected - agent_exists: {agent_subnet_exists}, pe_exists: {pe_subnet_exists}")
                    else:
                        logger.info(f"No existing subnets found, will create both: {config.network_config.agent_subnet_name}, {config.network_config.pe_subnet_name}")
                except Exception as e:
                    logger.warning(f"Could not auto-detect existing subnets: {e}")
            elif has_explicit_subnet_ids:
                # If explicit subnet IDs are provided, check which ones exist
                agent_subnet_exists = hasattr(config.network_config, 'existing_agent_subnet_id') and config.network_config.existing_agent_subnet_id
                pe_subnet_exists = hasattr(config.network_config, 'existing_pe_subnet_id') and config.network_config.existing_pe_subnet_id
            
            # Determine what needs to be created
            has_all_existing_subnets = agent_subnet_exists and pe_subnet_exists
            needs_subnet_creation = not has_all_existing_subnets
            
            params["createSubnetsInExistingVnet"] = {"value": needs_subnet_creation}
            params["createAgentSubnet"] = {"value": not agent_subnet_exists}
            params["createPeSubnet"] = {"value": not pe_subnet_exists}
            
            # Subnet configuration
            params["agentSubnetName"] = {"value": config.network_config.agent_subnet_name}
            params["peSubnetName"] = {"value": config.network_config.pe_subnet_name}
            
            # Only pass address prefixes when creating new subnets
            if needs_subnet_creation:
                params["agentSubnetPrefix"] = {"value": config.network_config.agent_subnet_prefix}
                params["peSubnetPrefix"] = {"value": config.network_config.pe_subnet_prefix}
        
        # Resource configuration - only pass resource IDs for existing resources
        # The bicep template uses empty string to indicate "create new"
        
        # Cosmos DB
        if config.cosmos_db.skip_deployment:
            # Pass the skip parameter to bicep template
            params["azureCosmosDBAccountResourceId"] = {"value": ""}
            params["skipCosmosDBDeployment"] = {"value": True}
        elif not config.cosmos_db.create_new and config.cosmos_db.existing_resource_id:
            params["azureCosmosDBAccountResourceId"] = {"value": config.cosmos_db.existing_resource_id}
            params["skipCosmosDBDeployment"] = {"value": False}
        else:
            params["azureCosmosDBAccountResourceId"] = {"value": ""}
            params["skipCosmosDBDeployment"] = {"value": False}
        
        # AI Search
        if config.ai_search.skip_deployment:
            # Pass the skip parameter to bicep template
            params["aiSearchResourceId"] = {"value": ""}
            params["skipAiSearchDeployment"] = {"value": True}
        elif not config.ai_search.create_new and config.ai_search.existing_resource_id:
            params["aiSearchResourceId"] = {"value": config.ai_search.existing_resource_id}
            params["skipAiSearchDeployment"] = {"value": False}
        else:
            params["aiSearchResourceId"] = {"value": ""}
            params["skipAiSearchDeployment"] = {"value": False}
        
        # Storage Account
        if config.storage_account.skip_deployment:
            # Pass the skip parameter to bicep template
            params["azureStorageAccountResourceId"] = {"value": ""}
            params["skipStorageAccountDeployment"] = {"value": True}
        elif not config.storage_account.create_new and config.storage_account.existing_resource_id:
            params["azureStorageAccountResourceId"] = {"value": config.storage_account.existing_resource_id}
            params["skipStorageAccountDeployment"] = {"value": False}
        else:
            params["azureStorageAccountResourceId"] = {"value": ""}
            params["skipStorageAccountDeployment"] = {"value": False}
        
        # Existing private endpoint names (to avoid creating duplicates)
        # These parameters tell the bicep template to use existing private endpoints instead of creating new ones
        
        # Auto-detect existing private endpoints for existing resources
        ai_search_pe_name = ""
        storage_pe_name = ""
        cosmos_pe_name = ""
        
        # For existing AI Search service, try to find existing private endpoint
        if not config.ai_search.skip_deployment and not config.ai_search.create_new and config.ai_search.existing_resource_id:
            try:
                ai_search_endpoints = self.get_existing_private_endpoints_for_resource(config.ai_search.existing_resource_id)
                if ai_search_endpoints:
                    ai_search_pe_name = ai_search_endpoints[0]['name']  # Use first found
                    logger.info(f"Auto-detected existing AI Search private endpoint: {ai_search_pe_name}")
            except Exception as e:
                logger.warning(f"Could not auto-detect AI Search private endpoint: {e}")
        
        # For existing Storage Account, try to find existing private endpoint
        if not config.storage_account.skip_deployment and not config.storage_account.create_new and config.storage_account.existing_resource_id:
            try:
                storage_endpoints = self.get_existing_private_endpoints_for_resource(config.storage_account.existing_resource_id)
                if storage_endpoints:
                    storage_pe_name = storage_endpoints[0]['name']  # Use first found
                    logger.info(f"Auto-detected existing Storage Account private endpoint: {storage_pe_name}")
            except Exception as e:
                logger.warning(f"Could not auto-detect Storage Account private endpoint: {e}")
        
        # For existing Cosmos DB, try to find existing private endpoint
        if not config.cosmos_db.skip_deployment and not config.cosmos_db.create_new and config.cosmos_db.existing_resource_id:
            try:
                cosmos_endpoints = self.get_existing_private_endpoints_for_resource(config.cosmos_db.existing_resource_id)
                if cosmos_endpoints:
                    cosmos_pe_name = cosmos_endpoints[0]['name']  # Use first found
                    logger.info(f"Auto-detected existing Cosmos DB private endpoint: {cosmos_pe_name}")
            except Exception as e:
                logger.warning(f"Could not auto-detect Cosmos DB private endpoint: {e}")
        
        # Override with user-specified names if provided
        if hasattr(config.ai_search, 'existing_private_endpoint_name') and config.ai_search.existing_private_endpoint_name:
            ai_search_pe_name = config.ai_search.existing_private_endpoint_name
        
        if hasattr(config.storage_account, 'existing_private_endpoint_name') and config.storage_account.existing_private_endpoint_name:
            storage_pe_name = config.storage_account.existing_private_endpoint_name
            
        if hasattr(config.cosmos_db, 'existing_private_endpoint_name') and config.cosmos_db.existing_private_endpoint_name:
            cosmos_pe_name = config.cosmos_db.existing_private_endpoint_name
        
        params["existingAiSearchPrivateEndpointName"] = {"value": ai_search_pe_name}
        params["existingStoragePrivateEndpointName"] = {"value": storage_pe_name}
        params["existingCosmosDBPrivateEndpointName"] = {"value": cosmos_pe_name}
        params["existingAiServicesPrivateEndpointName"] = {"value": ""} # AI Services always creates new in this template
        
        return params
    
    def create_parameters_file(self, config: AIFoundryHubDeploymentConfig, output_path: str, resource_group: str = "", subscription_id: str = "") -> bool:
        """Create a parameters file for the bicep deployment."""
        try:
            params = self.generate_bicep_parameters(config, resource_group, subscription_id)
            
            # Create parameters file content
            parameters_content = {
                "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
                "contentVersion": "1.0.0.0",
                "parameters": params
            }
            
            with open(output_path, 'w') as f:
                json.dump(parameters_content, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error creating parameters file: {str(e)}")
            return False
    
    def _validate_template(self, template_file: str, params_file: str, resource_group: str, template_type: str, subscription_id: Optional[str] = None) -> Tuple[bool, str]:
        """Validate ARM or Bicep template and parameters before deployment."""
        try:
            print(f"🔍 DEBUG: Validating {template_type} template: {template_file}")
            
            validate_cmd = [
                "az", "deployment", "group", "validate",
                "--resource-group", resource_group,
                "--template-file", template_file,
                "--parameters", f"@{params_file}",
                "--output", "json"
            ]
            
            # Add subscription parameter if specified
            if subscription_id:
                validate_cmd.extend(["--subscription", subscription_id])
                print(f"🎯 DEBUG: Adding subscription to validation: {subscription_id}")
            
            print(f"🔍 DEBUG: Template validation command: {' '.join(validate_cmd)}")
            
            validate_result = subprocess.run(
                validate_cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes for validation
            )
            
            print(f"🔍 DEBUG: Validation return code: {validate_result.returncode}")
            
            # Check if validation succeeded or just had warnings
            if validate_result.returncode == 0:
                print(f"✅ DEBUG: Template validation passed")
                try:
                    validation_info = json.loads(validate_result.stdout)
                    print(f"📋 DEBUG: Validation result: {validation_info.get('properties', {}).get('provisioningState', 'Unknown')}")
                except:
                    print(f"📋 DEBUG: Validation passed but couldn't parse result")
                return True, "Template validation successful"
            else:
                # Non-zero return code - could be warnings or actual errors
                # Check stderr for pattern analysis regardless of stdout content
                stderr_lower = validate_result.stderr.lower()
                stdout_lower = validate_result.stdout.lower() if validate_result.stdout else ""
                
                print(f"🔍 DEBUG: Analyzing non-zero return code validation result")
                print(f"🔍 DEBUG: Stderr starts with: {validate_result.stderr[:100]}...")
                
                # Check for specific issues based on template type
                if template_type == "Bicep" and "bcp177" in stderr_lower:
                    print(f"❌ DEBUG: Detected BCP177 error in Bicep template")
                    print(f"💡 DEBUG: Consider using main.json ARM template instead")
                    return False, f"BCP177 error in Bicep template. Try using the main.json ARM template: {validate_result.stderr}"
                
                # Bicep warnings can appear in different formats:
                # - "Warning BCP036:" (bicep compiler warnings)  
                # - "Warning no-unused-params:" (bicep linter warnings)
                # - "WARNING: /path/to/file.bicep" (prefixed warnings)
                bicep_warning_patterns = [
                    "warning bcp", "warning no-unused-params", "warning prefer-", 
                    "warning use-", "warning outputs-", "warning secure-",
                    "warning:", "warning bcp036", "warning bcp038"
                ]
                
                # Check for actual errors vs warnings
                has_bicep_warnings = any(warning in stderr_lower for warning in bicep_warning_patterns)
                
                # Also check for "WARNING:" prefix which is common in bicep output
                has_warning_prefix = "warning:" in stderr_lower
                
                # Special check: if stderr starts with "WARNING:" it's likely all warnings
                starts_with_warning = validate_result.stderr.strip().upper().startswith("WARNING:")
                
                # Check for actual errors (not warnings) - be more specific to avoid false positives
                # Only check for actual error indicators, not words that might appear in warning messages
                actual_error_patterns = [
                    'deployment failed', 'template is not valid', 'syntax error', 
                    'access denied', 'forbidden', 'authentication failed',
                    'resource not found', 'subscription not found', 'cannot create',
                    'error bcp', 'failed:', 'invalid template'
                ]
                has_actual_errors = any(error_pattern in stdout_lower or error_pattern in stderr_lower 
                                     for error_pattern in actual_error_patterns)
                
                # Check for bicep compilation errors specifically 
                # Exclude Azure CLI response consumption error which is not a template error
                has_bicep_errors = (
                    ("error bcp" in stderr_lower or "error:" in stderr_lower) and
                    "the content for this response was already consumed" not in stderr_lower
                )
                
                # Additional check: look for patterns that indicate this is really just warnings
                warning_only_indicators = [
                    "warning bcp036", "warning no-unused-params", "warning prefer-",
                    "bicep linter", "bicep compiler", "bicep diagnostic"
                ]
                likely_warnings_only = any(indicator in stderr_lower for indicator in warning_only_indicators)
                
                print(f"🔍 DEBUG: Analysis results:")
                print(f"   has_bicep_warnings: {has_bicep_warnings}")
                print(f"   has_warning_prefix: {has_warning_prefix}")
                print(f"   starts_with_warning: {starts_with_warning}")
                print(f"   has_actual_errors: {has_actual_errors}")
                print(f"   has_bicep_errors: {has_bicep_errors}")
                print(f"   likely_warnings_only: {likely_warnings_only}")
                
                # Special handling for Azure CLI response consumption error
                if "the content for this response was already consumed" in stderr_lower:
                    print(f"🔄 DEBUG: Azure CLI response consumption error detected during validation")
                    print(f"✅ DEBUG: This is not a template error - proceeding with deployment anyway")
                    return True, "Template validation successful (Azure CLI response issue ignored)"
                
                # If we have actual bicep errors, fail validation
                if has_bicep_errors:
                    print(f"❌ DEBUG: Template validation failed with bicep errors")
                    print(f"❌ DEBUG: Bicep errors: {validate_result.stderr}")
                    return False, f"Template validation failed with bicep errors: {validate_result.stderr}"
                
                # If we have bicep warnings (or warning prefix) and no actual errors, consider it a pass
                elif (has_bicep_warnings or has_warning_prefix or starts_with_warning or likely_warnings_only) and not has_actual_errors:
                    print(f"⚠️ DEBUG: Template validation passed with bicep warnings")
                    print(f"⚠️ DEBUG: Bicep warnings: {validate_result.stderr}")
                    
                    # Extract and display the specific warnings
                    warning_lines = []
                    for line in validate_result.stderr.split('\n'):
                        if line.strip() and ('Warning' in line or 'WARNING' in line):
                            warning_lines.append(line.strip())
                    
                    if warning_lines:
                        print(f"📋 DEBUG: Specific warnings found:")
                        for warning in warning_lines:
                            print(f"   - {warning}")
                    
                    return True, "Template validation successful (with bicep warnings)"
                
                # Try JSON parsing if we have stdout content
                elif validate_result.stdout:
                    try:
                        validation_info = json.loads(validate_result.stdout)
                        # If we get a successful validation result, it's just warnings
                        if validation_info.get('properties', {}).get('provisioningState') == 'Succeeded':
                            print(f"⚠️ DEBUG: Template validation passed with warnings (JSON)")
                            print(f"⚠️ DEBUG: Validation warnings: {validate_result.stderr}")
                            return True, "Template validation successful (with warnings)"
                        else:
                            print(f"❌ DEBUG: Template validation failed - invalid state")
                            print(f"❌ DEBUG: Validation state: {validation_info.get('properties', {}).get('provisioningState', 'Unknown')}")
                            return False, f"Template validation failed: {validate_result.stderr}"
                    except json.JSONDecodeError:
                        # JSON parsing failed, continue to final error check
                        pass
                
                # Final check - if no actual errors detected, treat as warnings
                if not has_actual_errors:
                    print(f"⚠️ DEBUG: Template validation passed with warnings (no actual errors detected)")
                    print(f"⚠️ DEBUG: Validation warnings: {validate_result.stderr}")
                    return True, "Template validation successful (with warnings)"
                else:
                    print(f"❌ DEBUG: Template validation failed with actual errors")
                    print(f"❌ DEBUG: Validation errors: {validate_result.stderr}")
                    return False, f"Template validation failed: {validate_result.stderr}"
                
        except subprocess.TimeoutExpired:
            print(f"⏱️ DEBUG: Template validation timed out")
            return False, "Template validation timed out"
        except Exception as e:
            print(f"⚠️ DEBUG: Template validation exception: {e}")
            return False, f"Template validation error: {str(e)}"
    
    def deploy_ai_foundry_hub(self, config: AIFoundryHubDeploymentConfig, resource_group: str, deployment_name: str, subscription_id: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Deploy AI Foundry Hub using ARM or Bicep template (prefers ARM to avoid BCP177 issues)."""
        try:
            print(f"🔍 DEBUG: Starting AI Foundry Hub deployment")
            print(f"📋 DEBUG: Deployment Name: {deployment_name}")
            print(f"🏢 DEBUG: Resource Group: {resource_group}")
            print(f"📍 DEBUG: Location: {config.location}")
            if subscription_id:
                print(f"🎯 DEBUG: Target Subscription: {subscription_id}")
            
            # Validate template
            valid, msg = self.validate_template_path()
            if not valid:
                print(f"❌ DEBUG: Template validation failed: {msg}")
                return False, msg, None
            print(f"✅ DEBUG: Template validation successful")
            
            # Check Azure CLI login and get account info
            logged_in, error = check_azure_cli_login()
            if not logged_in:
                print(f"❌ DEBUG: Azure CLI not logged in: {error}")
                return False, f"Azure CLI not logged in: {error}", None
            
            # Get detailed account information for debugging
            try:
                account_result = subprocess.run([
                    "az", "account", "show", "--output", "json"
                ], capture_output=True, text=True, timeout=30)
                
                if account_result.returncode == 0:
                    account_info = json.loads(account_result.stdout)
                    current_subscription = account_info.get('id', 'Unknown')
                    print(f"✅ DEBUG: Azure CLI logged in successfully")
                    print(f"📧 DEBUG: Account: {account_info.get('user', {}).get('name', 'Unknown')}")
                    print(f"🔑 DEBUG: Current Subscription ID: {current_subscription}")
                    print(f"🏠 DEBUG: Tenant ID: {account_info.get('tenantId', 'Unknown')}")
                    print(f"☁️ DEBUG: Cloud: {account_info.get('environmentName', 'Unknown')}")
                    
                    # Handle cross-subscription deployment
                    if subscription_id and subscription_id != current_subscription:
                        print(f"🔄 DEBUG: Cross-subscription deployment detected")
                        print(f"🎯 DEBUG: Switching to target subscription: {subscription_id}")
                        
                        # Switch to target subscription
                        switch_result = subprocess.run([
                            "az", "account", "set", "--subscription", subscription_id
                        ], capture_output=True, text=True, timeout=30)
                        
                        if switch_result.returncode != 0:
                            error_msg = f"Failed to switch to target subscription {subscription_id}: {switch_result.stderr}"
                            print(f"❌ DEBUG: {error_msg}")
                            return False, error_msg, None
                        
                        print(f"✅ DEBUG: Successfully switched to target subscription")
                    elif subscription_id:
                        print(f"✅ DEBUG: Target subscription matches current subscription")
                else:
                    print(f"⚠️ DEBUG: Could not get account info: {account_result.stderr}")
            except Exception as e:
                print(f"⚠️ DEBUG: Account info check failed: {e}")
            
            # Use target subscription ID in resource group check
            target_subscription = subscription_id if subscription_id else "current"
            print(f"🔍 DEBUG: Checking resource group in subscription: {target_subscription}")
            
            # Check if resource group exists (in target subscription)
            try:
                rg_check_cmd = ["az", "group", "show", "--name", resource_group, "--output", "json"]
                if subscription_id:
                    rg_check_cmd.extend(["--subscription", subscription_id])
                
                rg_result = subprocess.run(rg_check_cmd, capture_output=True, text=True, timeout=30)
                
                if rg_result.returncode == 0:
                    rg_info = json.loads(rg_result.stdout)
                    print(f"✅ DEBUG: Resource group exists: {resource_group}")
                    print(f"📍 DEBUG: RG Location: {rg_info.get('location', 'Unknown')}")
                    print(f"🏷️ DEBUG: RG Provisioning State: {rg_info.get('properties', {}).get('provisioningState', 'Unknown')}")
                else:
                    print(f"❌ DEBUG: Resource group not found or access denied: {rg_result.stderr}")
                    return False, f"Resource group '{resource_group}' not found or access denied", None
            except Exception as e:
                print(f"⚠️ DEBUG: Resource group check failed: {e}")
            
            # Refresh access token to prevent expiration during deployment
            try:
                token_result = subprocess.run([
                    "az", "account", "get-access-token", "--query", "accessToken", "--output", "tsv"
                ], capture_output=True, text=True, timeout=30)
                
                if token_result.returncode != 0:
                    print(f"❌ DEBUG: Failed to refresh access token: {token_result.stderr}")
                    return False, "Failed to refresh access token", None
                
                print(f"✅ DEBUG: Access token refreshed successfully")
                # Don't log the actual token for security
                token_length = len(token_result.stdout.strip()) if token_result.stdout else 0
                print(f"🔑 DEBUG: Token length: {token_length} characters")
            except Exception as e:
                print(f"⚠️ DEBUG: Token refresh failed: {e}")
            
            # Generate and validate parameters
            print(f"📝 DEBUG: Generating deployment parameters...")
            params = self.generate_bicep_parameters(config, resource_group, subscription_id or "")
            print(f"📊 DEBUG: Generated {len(params)} parameters")
            
            # Log key parameters (without sensitive info)
            print(f"🔧 DEBUG: Key parameters:")
            safe_params = ["location", "aiServices", "firstProjectName", "modelName", "vnetName"]
            for param in safe_params:
                if param in params:
                    print(f"   {param}: {params[param]['value']}")
            
            # Check network configuration
            if config.network_config.create_new_vnet:
                print(f"🌐 DEBUG: Creating new VNet: {config.network_config.vnet_name}")
                print(f"   Address prefix: {config.network_config.vnet_address_prefix}")
                print(f"   Agent subnet: {config.network_config.agent_subnet_name} ({config.network_config.agent_subnet_prefix})")
                print(f"   PE subnet: {config.network_config.pe_subnet_name} ({config.network_config.pe_subnet_prefix})")
            else:
                print(f"🌐 DEBUG: Using existing VNet: {config.network_config.existing_vnet_resource_id}")
            
            # Create temporary parameters file
            params_file = f"/tmp/ai-foundry-hub-params-{deployment_name}.json"
            print(f"📄 DEBUG: Creating parameters file: {params_file}")
            
            if not self.create_parameters_file(config, params_file, resource_group, subscription_id or ""):
                print(f"❌ DEBUG: Failed to create parameters file")
                return False, "Failed to create parameters file", None
            
            # Verify parameters file was created correctly
            try:
                with open(params_file, 'r') as f:
                    params_content = f.read()
                    print(f"✅ DEBUG: Parameters file created successfully ({len(params_content)} bytes)")
                    # Log first 500 characters for debugging (truncated for safety)
                    print(f"📋 DEBUG: Parameters file content (first 500 chars):")
                    print(params_content[:500] + "..." if len(params_content) > 500 else params_content)
            except Exception as e:
                print(f"⚠️ DEBUG: Could not read parameters file: {e}")
            
            # Choose template file: prefer main.json (ARM) over main.bicep to avoid BCP177 error
            main_json = os.path.join(self.template_path, "main.json")
            main_bicep = os.path.join(self.template_path, "main.bicep")
            
            template_file = None
            template_type = None
            
            if os.path.exists(main_json):
                template_file = main_json
                template_type = "ARM (JSON)"
                print(f"✅ DEBUG: Using ARM template: {main_json}")
                print(f"💡 DEBUG: ARM template avoids Bicep compilation issues (BCP177)")
            elif os.path.exists(main_bicep):
                template_file = main_bicep
                template_type = "Bicep"
                print(f"⚠️ DEBUG: Using Bicep template: {main_bicep}")
                print(f"⚠️ DEBUG: Bicep template may have compilation issues - consider using ARM template")
            else:
                # Clean up parameters file
                try:
                    os.remove(params_file)
                except:
                    pass
                return False, "Neither main.json nor main.bicep template found", None
            
            # Validate template before deployment
            print(f"🔍 DEBUG: Validating {template_type} template...")
            validation_success, validation_message = self._validate_template(template_file, params_file, resource_group, template_type, subscription_id)
            
            if not validation_success:
                # Clean up parameters file
                try:
                    os.remove(params_file)
                except:
                    pass
                return False, validation_message, None
            
            # Prepare deployment command with additional options to prevent response consumption errors
            cmd = [
                "az", "deployment", "group", "create",
                "--resource-group", resource_group,
                "--name", deployment_name,
                "--template-file", template_file,
                "--parameters", f"@{params_file}",
                "--mode", "Incremental",  # Explicit mode
                "--no-wait",  # Don't wait for completion to avoid response consumption
                "--output", "json"  # Structured output
            ]
            
            # Add subscription parameter if specified (for cross-subscription deployments)
            if subscription_id:
                cmd.extend(["--subscription", subscription_id])
                print(f"🎯 DEBUG: Adding subscription parameter: {subscription_id}")
            
            print(f"🚀 DEBUG: Deployment command: {' '.join(cmd)}")
            print(f"📁 DEBUG: Working directory: {os.getcwd()}")
            print(f"🎯 DEBUG: Template file ({template_type}): {template_file}")
            print(f"🎯 DEBUG: Template file exists: {os.path.exists(template_file)}")
            print(f"📄 DEBUG: Parameters file exists: {os.path.exists(params_file)}")
            
            # Execute deployment without waiting
            print(f"⏳ DEBUG: Executing deployment command...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout for submission
            )
            
            print(f"🔄 DEBUG: Deployment command completed")
            print(f"📊 DEBUG: Return code: {result.returncode}")
            print(f"📝 DEBUG: Stdout length: {len(result.stdout) if result.stdout else 0}")
            print(f"📝 DEBUG: Stderr length: {len(result.stderr) if result.stderr else 0}")
            
            if result.stdout:
                print(f"📋 DEBUG: Stdout content:")
                print(result.stdout)
            
            if result.stderr:
                print(f"⚠️ DEBUG: Stderr content:")
                print(result.stderr)
            
            # Clean up parameters file
            try:
                os.remove(params_file)
                print(f"🗑️ DEBUG: Parameters file cleaned up")
            except Exception as e:
                print(f"⚠️ DEBUG: Could not clean up parameters file: {e}")
            
            if result.returncode == 0:
                print(f"✅ DEBUG: Deployment submitted successfully")
                logger.info("AI Foundry Hub deployment submitted successfully")
                
                # Handle empty stdout from --no-wait flag
                if not result.stdout or not result.stdout.strip():
                    print(f"ℹ️ DEBUG: Empty stdout from --no-wait deployment (expected)")
                    
                    # Create success message for async deployment
                    success_msg = f"✅ Deployment SUBMITTED successfully!\n\n"
                    success_msg += f"📋 Deployment Name: {deployment_name}\n"
                    success_msg += f"🏢 Resource Group: {resource_group}\n"
                    success_msg += f"📍 Location: {config.location}\n"
                    success_msg += f"⏱️ Status: Deployment started asynchronously\n\n"
                    success_msg += "🔄 The deployment is now running in Azure. This typically takes 10-15 minutes.\n\n"
                    success_msg += "💡 Next Steps:\n"
                    success_msg += "1. Go to the 'Status' tab to monitor progress\n"
                    success_msg += "2. Click 'Refresh Status' to get real-time updates\n"
                    success_msg += "3. The deployment will show 'Succeeded' when complete\n\n"
                    success_msg += "⚠️ IMPORTANT: Do NOT navigate away from this page until deployment completes!"
                    
                    # Log deployment details for debugging
                    logger.info(f"Async deployment submitted - Name: {deployment_name}, RG: {resource_group}")
                    
                    return True, success_msg, ""
                
                # Parse the deployment info if stdout is not empty
                try:
                    deployment_info = json.loads(result.stdout)
                    deployment_id = deployment_info.get("id", "unknown")
                    provisioning_state = deployment_info.get("properties", {}).get("provisioningState", "unknown")
                    
                    print(f"📋 DEBUG: Deployment ID: {deployment_id}")
                    print(f"📊 DEBUG: Initial provisioning state: {provisioning_state}")
                    
                    success_msg = f"✅ Deployment SUBMITTED successfully!\n\n"
                    success_msg += f"📋 Deployment Name: {deployment_name}\n"
                    success_msg += f"🏢 Resource Group: {resource_group}\n"
                    success_msg += f"⏱️ Initial Status: {provisioning_state}\n\n"
                    success_msg += "🔄 The deployment is now running in Azure. This typically takes 10-15 minutes.\n\n"
                    success_msg += "💡 Next Steps:\n"
                    success_msg += "1. Go to the 'Status' tab to monitor progress\n"
                    success_msg += "2. Click 'Refresh Status' to get real-time updates\n"
                    success_msg += "3. The deployment will show 'Succeeded' when complete\n\n"
                    success_msg += "⚠️ IMPORTANT: Do NOT navigate away from this page until deployment completes!"
                    
                    # Log deployment details for debugging
                    logger.info(f"Deployment submitted - Name: {deployment_name}, RG: {resource_group}, State: {provisioning_state}")
                    
                    return True, success_msg, result.stdout
                except json.JSONDecodeError as e:
                    print(f"⚠️ DEBUG: JSON decode error: {e}")
                    print(f"📋 DEBUG: Raw stdout for JSON parsing: {result.stdout}")
                    
                    fallback_msg = f"✅ Deployment SUBMITTED successfully!\n\n"
                    fallback_msg += f"📋 Deployment Name: {deployment_name}\n"
                    fallback_msg += f"🏢 Resource Group: {resource_group}\n\n"
                    fallback_msg += "🔄 The deployment is now running in Azure.\n\n"
                    fallback_msg += "⚠️ Unable to parse initial response, but deployment has started.\n"
                    fallback_msg += "Please check the Status tab for progress updates."
                    
                    logger.warning("Deployment submitted but unable to parse response JSON")
                    return True, fallback_msg, result.stdout
                
            else:
                print(f"❌ DEBUG: Deployment submission failed with return code {result.returncode}")
                error_msg = f"Deployment submission failed: {result.stderr}"
                logger.error(error_msg)
                
                # Handle specific error patterns
                if "The content for this response was already consumed" in result.stderr:
                    print(f"🔄 DEBUG: Response consumption error detected, retrying with synchronous deployment...")
                    # Try alternative approach with synchronous deployment
                    logger.info("Retrying with synchronous deployment...")
                    return self._deploy_synchronous(config, resource_group, deployment_name)
                
                return False, error_msg, result.stdout
        
        except subprocess.TimeoutExpired:
            print(f"⏱️ DEBUG: Deployment submission timed out after 5 minutes")
            return False, "Deployment submission timed out (5 minutes)", None
        except Exception as e:
            print(f"💥 DEBUG: Deployment exception: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"📋 DEBUG: Full traceback:")
            traceback.print_exc()
            
            error_msg = f"Deployment error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def _deploy_synchronous(self, config: AIFoundryHubDeploymentConfig, resource_group: str, deployment_name: str) -> Tuple[bool, str, Optional[str]]:
        """Fallback synchronous deployment method."""
        try:
            print(f"🔄 DEBUG: Attempting synchronous deployment...")
            
            # Generate parameters
            params_file = f"/tmp/ai-foundry-hub-params-sync-{deployment_name}.json"
            if not self.create_parameters_file(config, params_file, resource_group):
                return False, "Failed to create parameters file for synchronous deployment", None
            
            # Choose template file: prefer main.json (ARM) over main.bicep to avoid BCP177 error
            main_json = os.path.join(self.template_path, "main.json")
            main_bicep = os.path.join(self.template_path, "main.bicep")
            
            template_file = None
            template_type = None
            
            if os.path.exists(main_json):
                template_file = main_json
                template_type = "ARM (JSON)"
                print(f"✅ DEBUG: Using ARM template for sync deployment: {main_json}")
            elif os.path.exists(main_bicep):
                template_file = main_bicep
                template_type = "Bicep"
                print(f"⚠️ DEBUG: Using Bicep template for sync deployment: {main_bicep}")
            else:
                return False, "Neither main.json nor main.bicep template found", None
            
            # Use synchronous deployment command
            cmd = [
                "az", "deployment", "group", "create",
                "--resource-group", resource_group,
                "--name", f"{deployment_name}-sync",
                "--template-file", template_file,
                "--parameters", f"@{params_file}",
                "--mode", "Incremental",
                "--output", "json"
            ]
            
            print(f"🔄 DEBUG: Synchronous deployment command ({template_type}): {' '.join(cmd)}")
            
            # Try to clear Azure CLI session cache before synchronous deployment
            try:
                print(f"🔧 DEBUG: Refreshing Azure CLI session to clear response cache...")
                refresh_cmd = ["az", "account", "show", "--output", "json"]
                refresh_result = subprocess.run(refresh_cmd, capture_output=True, text=True, timeout=30)
                if refresh_result.returncode == 0:
                    print(f"✅ DEBUG: Azure CLI session refreshed successfully")
                else:
                    print(f"⚠️ DEBUG: Azure CLI session refresh failed, proceeding anyway")
            except:
                print(f"⚠️ DEBUG: Azure CLI session refresh failed, proceeding anyway")
            
            # Execute with extended timeout for synchronous deployment
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes for full deployment
            )
            
            # Clean up parameters file
            try:
                os.remove(params_file)
            except:
                pass
            
            print(f"🔄 DEBUG: Synchronous deployment completed with return code: {result.returncode}")
            
            if result.returncode == 0:
                print(f"✅ DEBUG: Synchronous deployment successful")
                success_msg = f"✅ Deployment COMPLETED successfully!\n\n"
                success_msg += f"📋 Deployment Name: {deployment_name}-sync\n"
                success_msg += f"🏢 Resource Group: {resource_group}\n"
                success_msg += f"⏱️ Deployment completed synchronously\n\n"
                success_msg += "🎉 Your AI Foundry Hub is now ready for use!"
                
                logger.info(f"Synchronous deployment successful - {deployment_name}-sync")
                return True, success_msg, result.stdout
            else:
                print(f"❌ DEBUG: Synchronous deployment failed: {result.stderr}")
                
                # If this is also the "content already consumed" error, try one more approach
                if "The content for this response was already consumed" in result.stderr:
                    print(f"🔄 DEBUG: Content consumption error in sync deployment too - trying final fallback...")
                    return self._deploy_with_polling_fallback(config, resource_group, deployment_name)
                
                return False, f"Synchronous deployment failed: {result.stderr}", result.stdout
                
        except subprocess.TimeoutExpired:
            print(f"⏱️ DEBUG: Synchronous deployment timed out after 30 minutes")
            return False, "Synchronous deployment timed out (30 minutes)", None
        except Exception as e:
            print(f"💥 DEBUG: Synchronous deployment exception: {e}")
            return False, f"Synchronous deployment error: {str(e)}", None
    
    def _deploy_with_polling_fallback(self, config: AIFoundryHubDeploymentConfig, resource_group: str, deployment_name: str) -> Tuple[bool, str, Optional[str]]:
        """Final fallback deployment method using separate submission and polling."""
        try:
            print(f"🔄 DEBUG: Attempting polling fallback deployment...")
            
            # Generate parameters for fallback
            params_file = f"/tmp/ai-foundry-hub-params-fallback-{deployment_name}.json"
            if not self.create_parameters_file(config, params_file, resource_group):
                return False, "Failed to create parameters file for fallback deployment", None
            
            # Use ARM template
            template_file = os.path.join(self.template_path, "main.json")
            if not os.path.exists(template_file):
                return False, "ARM template not found for fallback deployment", None
            
            # Try deployment with minimal output and no-wait to avoid response consumption
            cmd = [
                "az", "deployment", "group", "create",
                "--resource-group", resource_group,
                "--name", f"{deployment_name}-fallback",
                "--template-file", template_file,
                "--parameters", f"@{params_file}",
                "--mode", "Incremental",
                "--no-wait",
                "--output", "table"  # Use table output instead of JSON to avoid response consumption
            ]
            
            print(f"🔄 DEBUG: Fallback deployment command: {' '.join(cmd)}")
            
            # Submit deployment with minimal output
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for submission
            )
            
            # Clean up parameters file
            try:
                os.remove(params_file)
            except:
                pass
            
            print(f"🔄 DEBUG: Fallback deployment submission return code: {result.returncode}")
            
            if result.returncode == 0:
                print(f"✅ DEBUG: Fallback deployment submitted successfully")
                success_msg = f"✅ Deployment SUBMITTED successfully!\n\n"
                success_msg += f"📋 Deployment Name: {deployment_name}-fallback\n"
                success_msg += f"🏢 Resource Group: {resource_group}\n"
                success_msg += f"⏱️ Deployment is running in the background\n\n"
                success_msg += "🎉 Check Azure Portal to monitor deployment progress!"
                
                logger.info(f"Fallback deployment submitted successfully - {deployment_name}-fallback")
                return True, success_msg, result.stdout
            else:
                print(f"❌ DEBUG: Fallback deployment submission failed: {result.stderr}")
                
                # If even table output fails, try direct REST API as final resort
                if "The content for this response was already consumed" in result.stderr:
                    print(f"🔄 DEBUG: All Azure CLI methods failed - trying direct REST API...")
                    return self._deploy_with_rest_api(config, resource_group, deployment_name)
                
                return False, f"Fallback deployment submission failed: {result.stderr}", result.stdout
                
        except Exception as e:
            print(f"💥 DEBUG: Fallback deployment exception: {e}")
            return False, f"Fallback deployment error: {str(e)}", None
    
    def _deploy_with_rest_api(self, config: AIFoundryHubDeploymentConfig, resource_group: str, deployment_name: str) -> Tuple[bool, str, Optional[str]]:
        """Final resort: Direct REST API deployment bypassing Azure CLI entirely."""
        try:
            import json
            import requests
            
            print(f"🔄 DEBUG: Attempting direct REST API deployment...")
            
            # Get access token
            token_cmd = ["az", "account", "get-access-token", "--query", "accessToken", "--output", "tsv"]
            token_result = subprocess.run(token_cmd, capture_output=True, text=True, timeout=30)
            
            if token_result.returncode != 0:
                return False, "Failed to get access token for REST API deployment", None
            
            access_token = token_result.stdout.strip()
            
            # Read the ARM template
            template_file = os.path.join(self.template_path, "main.json")
            if not os.path.exists(template_file):
                return False, "ARM template not found for REST API deployment", None
            
            with open(template_file, 'r') as f:
                template_content = json.load(f)
            
            # Generate parameters
            params_file = f"/tmp/ai-foundry-hub-params-restapi-{deployment_name}.json"
            if not self.create_parameters_file(config, params_file, resource_group):
                return False, "Failed to create parameters file for REST API deployment", None
            
            with open(params_file, 'r') as f:
                params_content = json.load(f)
            
            # Clean up parameters file
            try:
                os.remove(params_file)
            except:
                pass
            
            # Prepare REST API request
            subscription_id = "7aa77d2e-cbec-48b4-8518-9802543b25af"
            deployment_url = f"https://management.azure.com/subscriptions/{subscription_id}/resourcegroups/{resource_group}/providers/Microsoft.Resources/deployments/{deployment_name}-restapi"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            deployment_body = {
                "properties": {
                    "template": template_content,
                    "parameters": params_content["parameters"],
                    "mode": "Incremental"
                }
            }
            
            print(f"🔄 DEBUG: REST API deployment URL: {deployment_url}")
            
            # Submit deployment via REST API
            response = requests.put(
                deployment_url + "?api-version=2021-04-01",
                headers=headers,
                json=deployment_body,
                timeout=300
            )
            
            print(f"🔄 DEBUG: REST API response status: {response.status_code}")
            
            if response.status_code in [200, 201, 202]:
                print(f"✅ DEBUG: REST API deployment submitted successfully")
                success_msg = f"✅ Deployment SUBMITTED successfully via REST API!\n\n"
                success_msg += f"📋 Deployment Name: {deployment_name}-restapi\n"
                success_msg += f"🏢 Resource Group: {resource_group}\n"
                success_msg += f"⏱️ Deployment is running in the background\n\n"
                success_msg += "🎉 Check Azure Portal to monitor deployment progress!"
                
                logger.info(f"REST API deployment submitted successfully - {deployment_name}-restapi")
                return True, success_msg, str(response.json() if response.text else "")
            else:
                print(f"❌ DEBUG: REST API deployment failed: {response.status_code} - {response.text}")
                return False, f"REST API deployment failed: {response.status_code} - {response.text}", None
                
        except Exception as e:
            print(f"💥 DEBUG: REST API deployment exception: {e}")
            return False, f"REST API deployment error: {str(e)}", None
    
    def get_deployment_status(self, resource_group: str, deployment_name: str) -> Tuple[str, str, Optional[dict]]:
        """Get the current status of a deployment."""
        try:
            print(f"🔍 DEBUG: Getting deployment status for: {deployment_name}")
            
            # Get deployment status
            cmd = [
                "az", "deployment", "group", "show",
                "--resource-group", resource_group,
                "--name", deployment_name,
                "--output", "json"
            ]
            
            print(f"🔍 DEBUG: Status command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            print(f"🔍 DEBUG: Status return code: {result.returncode}")
            print(f"🔍 DEBUG: Status stderr: {result.stderr}")
            
            if result.returncode != 0:
                print(f"❌ DEBUG: Failed to get deployment status: {result.stderr}")
                
                # Check if deployment doesn't exist
                if "DeploymentNotFound" in result.stderr or "NotFound" in result.stderr:
                    print(f"🔍 DEBUG: Deployment not found, checking for alternative names")
                    # Try with -sync suffix
                    return self.get_deployment_status(resource_group, f"{deployment_name}-sync")
                
                return "Unknown", f"Failed to get deployment status: {result.stderr}", None
            
            try:
                deployment_info = json.loads(result.stdout)
                print(f"🔍 DEBUG: Successfully parsed deployment info")
                
                props = deployment_info.get("properties", {})
                provisioning_state = props.get("provisioningState", "Unknown")
                correlation_id = props.get("correlationId", "Unknown")
                timestamp = props.get("timestamp", "Unknown")
                
                print(f"🔍 DEBUG: Provisioning state: {provisioning_state}")
                print(f"🔍 DEBUG: Correlation ID: {correlation_id}")
                print(f"🔍 DEBUG: Timestamp: {timestamp}")
                
                # Create detailed status message
                status_details = []
                status_details.append(f"📊 **Status**: {provisioning_state}")
                status_details.append(f"🕒 **Last Update**: {timestamp}")
                status_details.append(f"🔗 **Correlation ID**: {correlation_id}")
                
                # Add duration if available
                if "duration" in props:
                    duration = props["duration"]
                    status_details.append(f"⏱️ **Duration**: {duration}")
                
                # Add progress information
                try:
                    operations_info = self._get_operations_summary(resource_group, deployment_name)
                    if operations_info:
                        status_details.append(f"\n📋 **Operations Summary**:")
                        status_details.extend(operations_info)
                except Exception as e:
                    print(f"⚠️ DEBUG: Could not get operations summary: {e}")
                    # Continue without operations summary
                
                # Add specific guidance based on state
                if provisioning_state == "Running":
                    status_details.append(f"\n🔄 **Deployment in Progress**")
                    status_details.append(f"The deployment is currently running. This typically takes 10-15 minutes.")
                    status_details.append(f"Please wait and refresh the status periodically.")
                elif provisioning_state == "Succeeded":
                    status_details.append(f"\n✅ **Deployment Successful**")
                    status_details.append(f"Your AI Foundry Hub has been deployed successfully!")
                    status_details.append(f"You can now access your resources in the Azure portal.")
                elif provisioning_state == "Failed":
                    status_details.append(f"\n❌ **Deployment Failed**")
                    status_details.append(f"The deployment encountered errors. Check the error details below.")
                elif provisioning_state == "Canceled":
                    status_details.append(f"\n🛑 **Deployment Canceled**")
                    status_details.append(f"The deployment was canceled. You can retry the deployment if needed.")
                
                status_message = "\n".join(status_details)
                print(f"🔍 DEBUG: Generated status message ({len(status_message)} characters)")
                
                return provisioning_state, status_message, deployment_info
                
            except json.JSONDecodeError as e:
                print(f"❌ DEBUG: JSON decode error for deployment status: {e}")
                error_msg = f"Failed to parse deployment status: {str(e)}"
                return "Unknown", error_msg, None
            
        except Exception as e:
            print(f"💥 DEBUG: Exception getting deployment status: {e}")
            error_msg = f"Error retrieving deployment status: {str(e)}"
            return "Unknown", error_msg, None
    
    def _get_operations_summary(self, resource_group: str, deployment_name: str) -> List[str]:
        """Get a summary of deployment operations for status display."""
        try:
            print(f"🔍 DEBUG: Getting operations summary for: {deployment_name}")
            
            # Get deployment operations
            cmd = [
                "az", "deployment", "operation", "group", "list",
                "--resource-group", resource_group,
                "--name", deployment_name,
                "--query", "[].{name:properties.targetResource.resourceName, type:properties.targetResource.resourceType, state:properties.provisioningState}",
                "--output", "json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"⚠️ DEBUG: Failed to get operations summary: {result.stderr}")
                return []
            
            try:
                operations = json.loads(result.stdout)
                print(f"🔍 DEBUG: Found {len(operations)} operations for summary")
                
                if not operations:
                    return []
                
                summary_lines = []
                
                # Count operations by state
                state_counts = {}
                for op in operations:
                    state = op.get("state", "Unknown")
                    state_counts[state] = state_counts.get(state, 0) + 1
                
                # Add state summary
                for state, count in state_counts.items():
                    emoji = "✅" if state == "Succeeded" else "🔄" if state == "Running" else "❌" if state == "Failed" else "⏸️"
                    summary_lines.append(f"{emoji} {state}: {count} operations")
                
                # Add details for non-succeeded operations
                non_succeeded = [op for op in operations if op.get("state") not in ["Succeeded"]]
                if non_succeeded:
                    summary_lines.append("")
                    summary_lines.append("📋 **Active Operations:**")
                    for op in non_succeeded[:5]:  # Limit to first 5 for brevity
                        resource_name = op.get("name", "Unknown")
                        resource_type = op.get("type", "Unknown").split("/")[-1] if op.get("type") else "Unknown"
                        state = op.get("state", "Unknown")
                        emoji = "🔄" if state == "Running" else "❌" if state == "Failed" else "⏸️"
                        summary_lines.append(f"  {emoji} {resource_type}: {resource_name} ({state})")
                    
                    if len(non_succeeded) > 5:
                        summary_lines.append(f"  ... and {len(non_succeeded) - 5} more operations")
                
                print(f"🔍 DEBUG: Generated {len(summary_lines)} summary lines")
                return summary_lines
                
            except json.JSONDecodeError as e:
                print(f"❌ DEBUG: JSON decode error for operations summary: {e}")
                return []
            
        except Exception as e:
            print(f"⚠️ DEBUG: Exception getting operations summary: {e}")
            return []

    def get_deployment_outputs(self, resource_group: str, deployment_name: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Get the outputs of a completed deployment."""
        try:
            success, msg, deployment_info = self.get_deployment_status(resource_group, deployment_name)
            if not success:
                return False, msg, None
            
            if deployment_info and "properties" in deployment_info:
                outputs = deployment_info["properties"].get("outputs", {})
                return True, "Deployment outputs retrieved", outputs
            else:
                return False, "No deployment outputs found", None
        
        except Exception as e:
            return False, f"Error getting deployment outputs: {str(e)}", None
    
    def validate_deployment_config(self, config: AIFoundryHubDeploymentConfig) -> List[str]:
        """Validate deployment configuration and return list of issues."""
        issues = []
        
        # Validate basic settings
        if not config.ai_services_name.strip():
            issues.append("AI Services name is required")
        
        if not config.project_name.strip():
            issues.append("Project name is required")
        
        if config.location not in self.get_available_locations():
            issues.append(f"Location '{config.location}' is not available")
        
        # Validate network configuration
        if not config.network_config.create_new_vnet:
            if not config.network_config.existing_vnet_resource_id.strip():
                issues.append("Existing VNet resource ID is required when not creating new VNet")
        
        # Validate existing resources (skip validation if resource is not being deployed)
        if not config.cosmos_db.skip_deployment and not config.cosmos_db.create_new:
            if not config.cosmos_db.existing_resource_id.strip():
                issues.append("Existing Cosmos DB resource ID is required when not creating new Cosmos DB")
        
        if not config.ai_search.skip_deployment and not config.ai_search.create_new:
            if not config.ai_search.existing_resource_id.strip():
                issues.append("Existing AI Search resource ID is required when not creating new AI Search")
        
        if not config.storage_account.skip_deployment and not config.storage_account.create_new:
            if not config.storage_account.existing_resource_id.strip():
                issues.append("Existing Storage Account resource ID is required when not creating new Storage Account")
        
        return issues
    
    def get_vnet_subnets(self, vnet_resource_id: str) -> List[Dict[str, Any]]:
        """Get subnets for a specific VNet."""
        try:
            # Check if Azure CLI is logged in
            logged_in, error = check_azure_cli_login()
            if not logged_in:
                logger.error(f"Azure CLI not logged in: {error}")
                return []
            
            # Extract resource group and VNet name from resource ID
            # Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}
            parts = vnet_resource_id.split('/')
            if len(parts) < 8:
                logger.error(f"Invalid VNet resource ID format: {vnet_resource_id}")
                return []
            
            resource_group = parts[4]
            vnet_name = parts[8]
            
            # Get subnets using Azure CLI
            result = subprocess.run([
                "az", "network", "vnet", "subnet", "list",
                "--resource-group", resource_group,
                "--vnet-name", vnet_name,
                "--query", "[].{name:name, id:id, addressPrefix:addressPrefix, privateEndpointNetworkPolicies:privateEndpointNetworkPolicies}",
                "--output", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                subnets = json.loads(result.stdout)
                return subnets
            else:
                logger.error(f"Failed to get subnets for VNet {vnet_name}: {result.stderr}")
                return []
        except Exception as e:
            logger.error(f"Error getting subnets for VNet {vnet_resource_id}: {str(e)}")
            return []
    
    def save_deployment_config(self, config: AIFoundryHubDeploymentConfig, config_name: str = "last_deployment") -> bool:
        """Save deployment configuration to a file (all parameters)."""
        try:
            config_dir = "/tmp/ai_foundry_configs"
            os.makedirs(config_dir, exist_ok=True)
            # Use asdict to ensure all dataclass fields are saved
            from dataclasses import asdict
            config_dict = asdict(config)
            # Save to file
            config_file = os.path.join(config_dir, f"{config_name}.json")
            with open(config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            logger.info(f"Configuration saved to {config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {str(e)}")
            return False

    def load_deployment_config(self, config_name: str = "last_deployment") -> Optional[AIFoundryHubDeploymentConfig]:
        """Load deployment configuration from a file (all parameters)."""
        try:
            config_dir = "/tmp/ai_foundry_configs"
            config_file = os.path.join(config_dir, f"{config_name}.json")
            if not os.path.exists(config_file):
                logger.info(f"No saved configuration found: {config_file}")
                return None
            with open(config_file, 'r') as f:
                config_dict = json.load(f)
            # Reconstruct dataclasses
            network_config = NetworkConfig(**config_dict["network_config"])
            cosmos_db = DeploymentResource(**config_dict["cosmos_db"])
            ai_search = DeploymentResource(**config_dict["ai_search"])
            storage_account = DeploymentResource(**config_dict["storage_account"])
            config = AIFoundryHubDeploymentConfig(
                location=config_dict["location"],
                ai_services_name=config_dict["ai_services_name"],
                project_name=config_dict["project_name"],
                project_description=config_dict["project_description"],
                display_name=config_dict["display_name"],
                model_name=config_dict["model_name"],
                model_format=config_dict["model_format"],
                model_version=config_dict["model_version"],
                model_sku_name=config_dict["model_sku_name"],
                model_capacity=config_dict["model_capacity"],
                network_config=network_config,
                cosmos_db=cosmos_db,
                ai_search=ai_search,
                storage_account=storage_account
            )
            logger.info(f"Configuration loaded from {config_file}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            return None
    
    def list_saved_configs(self) -> List[str]:
        """List all saved configuration names."""
        try:
            config_dir = "/tmp/ai_foundry_configs"
            if not os.path.exists(config_dir):
                return []
            
            configs = []
            for file in os.listdir(config_dir):
                if file.endswith('.json'):
                    configs.append(file[:-5])  # Remove .json extension
            
            return sorted(configs)
            
        except Exception as e:
            logger.error(f"Failed to list saved configurations: {str(e)}")
            return []
    
    def monitor_deployment_progress(self, resource_group: str, deployment_name: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Monitor deployment progress with better error handling."""
        try:
            # Check Azure CLI login
            logged_in, error = check_azure_cli_login()
            if not logged_in:
                return False, f"Azure CLI not logged in: {error}", None
            
            # Get deployment status with retry logic
            for attempt in range(3):
                try:
                    result = subprocess.run([
                        "az", "deployment", "group", "show",
                        "--resource-group", resource_group,
                        "--name", deployment_name,
                        "--output", "json"
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        deployment_info = json.loads(result.stdout)
                        
                        # Extract key information
                        properties = deployment_info.get("properties", {})
                        provisioning_state = properties.get("provisioningState", "Unknown")
                        
                        # Format response
                        status_info = {
                            "provisioningState": provisioning_state,
                            "timestamp": properties.get("timestamp"),
                            "duration": properties.get("duration"),
                            "correlationId": properties.get("correlationId"),
                            "error": properties.get("error")
                        }
                        
                        return True, f"Deployment status: {provisioning_state}", status_info
                    
                    elif "DeploymentNotFound" in result.stderr or "ResourceNotFound" in result.stderr:
                        return False, f"Deployment '{deployment_name}' not found in resource group '{resource_group}'", None
                    
                    else:
                        if attempt < 2:  # Retry on failure
                            logger.warning(f"Deployment status check failed (attempt {attempt + 1}): {result.stderr}")
                            continue
                        else:
                            return False, f"Failed to get deployment status: {result.stderr}", None
                
                except subprocess.TimeoutExpired:
                    if attempt < 2:
                        logger.warning(f"Deployment status check timed out (attempt {attempt + 1})")
                        continue
                    else:
                        return False, "Deployment status check timed out", None
                
                except json.JSONDecodeError as e:
                    if attempt < 2:
                        logger.warning(f"Failed to parse deployment status JSON (attempt {attempt + 1}): {e}")
                        continue
                    else:
                        return False, f"Failed to parse deployment status: {e}", None
            
            return False, "All deployment status check attempts failed", None
        
        except Exception as e:
            return False, f"Error monitoring deployment progress: {str(e)}", None
    
    def get_deployment_error_details(self, resource_group: str, deployment_name: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Get detailed error information for a failed deployment."""
        try:
            print(f"🔍 DEBUG: Getting error details for deployment: {deployment_name}")
            
            # Get deployment operation details
            cmd = [
                "az", "deployment", "operation", "group", "list",
                "--resource-group", resource_group,
                "--name", deployment_name,
                "--output", "json"
            ]
            
            print(f"🔍 DEBUG: Error details command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            print(f"🔍 DEBUG: Error details return code: {result.returncode}")
            
            if result.returncode != 0:
                print(f"❌ DEBUG: Failed to get error details: {result.stderr}")
                return False, f"❌ Failed to retrieve error details: {result.stderr}", None
            
            try:
                operations = json.loads(result.stdout)
                print(f"🔍 DEBUG: Found {len(operations)} operations")
                
                error_details = []
                error_details.append("🔍 **DEPLOYMENT ERROR ANALYSIS**\n")
                
                # Look for failed operations
                failed_ops = [op for op in operations if op.get("properties", {}).get("provisioningState") == "Failed"]
                print(f"🔍 DEBUG: Found {len(failed_ops)} failed operations")
                
                if not failed_ops:
                    error_details.append("⚠️ No failed operations found. The deployment may still be in progress.")
                    # Check for running operations
                    running_ops = [op for op in operations if op.get("properties", {}).get("provisioningState") in ["Running", "Accepted"]]
                    if running_ops:
                        error_details.append(f"🔄 Found {len(running_ops)} operations still running.")
                else:
                    for i, op in enumerate(failed_ops, 1):
                        try:
                            props = op.get("properties", {})
                            resource_name = props.get("targetResource", {}).get("resourceName", "Unknown")
                            resource_type = props.get("targetResource", {}).get("resourceType", "Unknown")
                            
                            error_details.append(f"\n**❌ Failed Operation {i}:**")
                            error_details.append(f"📋 Resource: {resource_name}")
                            error_details.append(f"🏷️ Type: {resource_type}")
                            error_details.append(f"📊 Status: {props.get('provisioningState', 'Unknown')}")
                            
                            # Get status message
                            status_msg = props.get("statusMessage", {})
                            if status_msg:
                                if isinstance(status_msg, dict):
                                    error_code = status_msg.get("error", {}).get("code", "Unknown")
                                    error_msg = status_msg.get("error", {}).get("message", "No message")
                                    error_details.append(f"🔴 Error Code: {error_code}")
                                    error_details.append(f"📝 Error Message: {error_msg}")
                                    
                                    # Check for detailed error information
                                    error_details_nested = status_msg.get("error", {}).get("details", [])
                                    if error_details_nested:
                                        error_details.append(f"📋 **Additional Details:**")
                                        for detail in error_details_nested:
                                            if isinstance(detail, dict):
                                                detail_code = detail.get("code", "Unknown")
                                                detail_msg = detail.get("message", "No message")
                                                error_details.append(f"  - {detail_code}: {detail_msg}")
                                            if isinstance(detail, dict):
                                                detail_code = detail.get("code", "Unknown")
                                                detail_msg = detail.get("message", "No message")
                                                error_details.append(f"  - {detail_code}: {detail_msg}")
                                else:
                                    error_details.append(f"📝 Status: {str(status_msg)}")
                            
                            print(f"🔍 DEBUG: Processed failed operation {i}: {resource_name}")
                            
                        except Exception as e:
                            print(f"⚠️ DEBUG: Error processing failed operation {i}: {e}")
                            error_details.append(f"⚠️ Error processing failed operation {i}: {str(e)}")
                
                # Check for nested deployments
                nested_deployments = [
                    op for op in operations 
                    if op.get("properties", {}).get("targetResource", {}).get("resourceType") == "Microsoft.Resources/deployments"
                ]
                
                if nested_deployments:
                    print(f"🔍 DEBUG: Found {len(nested_deployments)} nested deployments")
                    error_details.append(f"\n🔄 **NESTED DEPLOYMENT ANALYSIS**")
                    error_details.append(f"Found {len(nested_deployments)} nested deployments")
                    
                    for nested in nested_deployments:
                        try:
                            nested_name = nested.get("properties", {}).get("targetResource", {}).get("resourceName", "Unknown")
                            nested_state = nested.get("properties", {}).get("provisioningState", "Unknown")
                            
                            error_details.append(f"\n📋 Nested Deployment: {nested_name}")
                            error_details.append(f"📊 Status: {nested_state}")
                            
                            if nested_state == "Failed":
                                # Get nested deployment errors
                                nested_errors = self.get_nested_deployment_error_details(resource_group, nested_name)
                                if nested_errors:
                                    error_details.append(f"🔴 Nested Errors:")
                                    error_details.extend(nested_errors)
                            
                        except Exception as e:
                            print(f"⚠️ DEBUG: Error processing nested deployment: {e}")
                            error_details.append(f"⚠️ Error processing nested deployment: {str(e)}")
                
                # Add troubleshooting suggestions
                error_details.append(f"\n💡 **TROUBLESHOOTING SUGGESTIONS**")
                error_details.append("1. Check that all required permissions are granted")
                error_details.append("2. Verify resource names don't conflict with existing resources")
                error_details.append("3. Ensure the selected location supports all required services")
                error_details.append("4. Check subscription quotas and limits")
                error_details.append("5. Verify network configuration (VNet, subnets, DNS)")
                
                result_text = "\n".join(error_details)
                print(f"🔍 DEBUG: Generated error details ({len(result_text)} characters)")
                
                # Create structured error details for UI
                failed_operations = []
                for i, op in enumerate(failed_ops, 1):
                    try:
                        props = op.get("properties", {})
                        resource_name = props.get("targetResource", {}).get("resourceName", "Unknown")
                        resource_type = props.get("targetResource", {}).get("resourceType", "Unknown")
                        
                        # Get status message
                        status_msg = props.get("statusMessage", {})
                        error_code = "Unknown"
                        error_message = "No message"
                        
                        if status_msg and isinstance(status_msg, dict):
                            error_code = status_msg.get("error", {}).get("code", "Unknown")
                            error_message = status_msg.get("error", {}).get("message", "No message")
                        
                        failed_operations.append({
                            "resource_name": resource_name,
                            "resource_type": resource_type,
                            "error_code": error_code,
                            "error_message": error_message
                        })
                    except Exception as e:
                        print(f"⚠️ DEBUG: Error processing failed operation {i}: {e}")
                
                structured_errors = {
                    "failed_operations": failed_operations,
                    "error_summary": result_text
                }
                
                return True, result_text, structured_errors
                
            except json.JSONDecodeError as e:
                print(f"❌ DEBUG: JSON decode error for error details: {e}")
                error_msg = f"❌ Failed to parse error details: {str(e)}\n\nRaw output:\n{result.stdout}"
                return False, error_msg, None
            
        except Exception as e:
            print(f"💥 DEBUG: Exception getting error details: {e}")
            error_msg = f"❌ Error retrieving deployment details: {str(e)}"
            return False, error_msg, None
    
    def get_nested_deployment_error_details(self, resource_group: str, nested_deployment_name: str) -> List[str]:
        """Get detailed error information for nested deployments."""
        try:
            print(f"🔍 DEBUG: Getting nested deployment errors for: {nested_deployment_name}")
            
            # Get nested deployment operation details
            cmd = [
                "az", "deployment", "operation", "group", "list",
                "--resource-group", resource_group,
                "--name", nested_deployment_name,
                "--output", "json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                print(f"❌ DEBUG: Failed to get nested deployment errors: {result.stderr}")
                return [f"❌ Failed to get nested deployment errors: {result.stderr}"]
            
            try:
                operations = json.loads(result.stdout)
                print(f"🔍 DEBUG: Found {len(operations)} nested operations")
                
                error_details = []
                
                # Look for failed operations in nested deployment
                failed_ops = [op for op in operations if op.get("properties", {}).get("provisioningState") == "Failed"]
                print(f"🔍 DEBUG: Found {len(failed_ops)} failed nested operations")
                
                if failed_ops:
                    for i, op in enumerate(failed_ops, 1):
                        try:
                            props = op.get("properties", {})
                            resource_name = props.get("targetResource", {}).get("resourceName", "Unknown")
                            resource_type = props.get("targetResource", {}).get("resourceType", "Unknown")
                            
                            error_details.append(f"    🔴 Failed Resource {i}: {resource_name}")
                            error_details.append(f"    🏷️ Type: {resource_type}")
                            
                            # Get detailed error message
                            status_msg = props.get("statusMessage", {})
                            error_code = "Unknown"
                            error_message = "No message"
                            
                            if status_msg and isinstance(status_msg, dict):
                                error_code = status_msg.get("error", {}).get("code", "Unknown")
                                error_message = status_msg.get("error", {}).get("message", "No message")
                            
                            error_details.append(f"    🔴 Error Code: {error_code}")
                            error_details.append(f"    📝 Error Message: {error_message}")
                            
                            # Handle specific error patterns
                            if "VnetIsNotEmpty" in error_code:
                                error_details.append(f"    💡 Suggestion: The VNet contains resources. Use an empty VNet or create a new one.")
                            elif "SubnetIsNotEmpty" in error_code:
                                error_details.append(f"    💡 Suggestion: The subnet contains resources. Use an empty subnet or create a new one.")
                            elif "InvalidAddressSpace" in error_code:
                                error_details.append(f"    💡 Suggestion: Check VNet and subnet address spaces for conflicts.")
                            elif "QuotaExceeded" in error_code:
                                error_details.append(f"    💡 Suggestion: Increase subscription quota for this resource type.")
                            elif "LocationNotAvailable" in error_code:
                                error_details.append(f"    💡 Suggestion: Try a different Azure region that supports this resource.")
                            elif "NameAlreadyExists" in error_code:
                                error_details.append(f"    💡 Suggestion: Use a different name for this resource.")
                            elif "AuthenticationFailed" in error_code:
                                error_details.append(f"    💡 Suggestion: Check RBAC permissions for this resource group and subscription.")
                            elif "NetworkSecurityGroupCannotBeDeleted" in error_code:
                                error_details.append(f"    💡 Suggestion: Remove NSG associations before attempting to delete.")
                            
                            # Check for additional nested details
                            nested_details = error_info.get("details", [])
                            if nested_details:
                                error_details.append(f"    📋 Additional Details:")
                                for detail in nested_details:
                                    if isinstance(detail, dict):
                                        detail_code = detail.get("code", "Unknown")
                                        detail_msg = detail.get("message", "No message")
                                        error_details.append(f"      - {detail_code}: {detail_msg}")
                                    if isinstance(detail, dict):
                                        detail_code = detail.get("code", "Unknown")
                                        detail_msg = detail.get("message", "No message")
                                        error_details.append(f"      - {detail_code}: {detail_msg}")
                        except Exception as e:
                            print(f"⚠️ DEBUG: Error processing nested failed operation {i}: {e}")
                            error_details.append(f"    ⚠️ Error processing failed operation {i}: {str(e)}")
                
                # Check for further nested deployments
                further_nested = [
                    op for op in operations 
                    if op.get("properties", {}).get("targetResource", {}).get("resourceType") == "Microsoft.Resources/deployments"
                ]
                
                if further_nested:
                    print(f"🔍 DEBUG: Found {len(further_nested)} further nested deployments")
                    error_details.append(f"    🔄 Found {len(further_nested)} additional nested deployments")
                    
                    for nested in further_nested:
                        try:
                            nested_name = nested.get("properties", {}).get("targetResource", {}).get("resourceName", "Unknown")
                            nested_state = nested.get("properties", {}).get("provisioningState", "Unknown")
                            
                            error_details.append(f"    📋 Further Nested: {nested_name} ({nested_state})")
                            
                            if nested_state == "Failed":
                                # Recursive call for deeper nesting (limit to prevent infinite loops)
                                deeper_errors = self.get_nested_deployment_error_details(resource_group, nested_name)
                                if deeper_errors:
                                    error_details.extend([f"    {line}" for line in deeper_errors])
                            
                        except Exception as e:
                            print(f"⚠️ DEBUG: Error processing further nested deployment: {e}")
                            error_details.append(f"    ⚠️ Error processing further nested deployment: {str(e)}")
                
                print(f"🔍 DEBUG: Generated {len(error_details)} nested error details")
                return error_details
                
            except json.JSONDecodeError as e:
                print(f"❌ DEBUG: JSON decode error for nested deployment: {e}")
                return [f"❌ Failed to parse nested deployment details: {str(e)}"]
            
        except Exception as e:
            print(f"💥 DEBUG: Exception getting nested deployment errors: {e}")
            return [f"❌ Error retrieving nested deployment details: {str(e)}"]
    
    def get_existing_private_endpoints_for_resource(self, resource_id: str) -> List[Dict[str, Any]]:
        """Get existing private endpoints connected to a specific resource."""
        try:
            # Check if Azure CLI is logged in
            logged_in, error = check_azure_cli_login()
            if not logged_in:
                logger.error(f"Azure CLI not logged in: {error}")
                return []
            
            # Extract resource group from resource ID for scoping the search
            parts = resource_id.split('/')
            if len(parts) < 5:
                logger.error(f"Invalid resource ID format: {resource_id}")
                return []
            
            resource_group = parts[4]
            
            # Get all private endpoints in the resource group
            result = subprocess.run([
                "az", "network", "private-endpoint", "list",
                "--resource-group", resource_group,
                "--query", "[].{name:name, id:id, location:location, subnet:subnet.id, connections:privateLinkServiceConnections[].privateLinkServiceId}",
                "--output", "json"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"Failed to get private endpoints: {result.stderr}")
                return []
            
            try:
                all_endpoints = json.loads(result.stdout)
                
                # Filter endpoints that are connected to our resource
                matching_endpoints = []
                for endpoint in all_endpoints:
                    connections = endpoint.get('connections', [])
                    for connection_id in connections:
                        if connection_id and resource_id.lower() in connection_id.lower():
                            matching_endpoints.append({
                                'name': endpoint['name'],
                                'id': endpoint['id'],
                                'location': endpoint['location'],
                                'subnet': endpoint.get('subnet', 'Unknown'),
                                'connected_resource': connection_id
                            })
                            break
                
                logger.info(f"Found {len(matching_endpoints)} private endpoints for resource {resource_id}")
                return matching_endpoints
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse private endpoints JSON: {e}")
                return []
            
        except Exception as e:
            logger.error(f"Error getting private endpoints for resource {resource_id}: {str(e)}")
            return []

    def get_all_private_endpoints_in_resource_group(self, resource_group: str) -> List[Dict[str, Any]]:
        """Get all private endpoints in a resource group with their connected resources."""
        try:
            # Check if Azure CLI is logged in
            logged_in, error = check_azure_cli_login()
            if not logged_in:
                logger.error(f"Azure CLI not logged in: {error}")
                return []
            
            # Get all private endpoints in the resource group
            result = subprocess.run([
                "az", "network", "private-endpoint", "list",
                "--resource-group", resource_group,
                "--query", "[].{name:name, id:id, location:location, subnet:subnet.id, connections:privateLinkServiceConnections[].privateLinkServiceId, resourceGroup:resourceGroup}",
                "--output", "json"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"Failed to get private endpoints in RG {resource_group}: {result.stderr}")
                return []
            
            try:
                endpoints = json.loads(result.stdout)
                
                # Process each endpoint to make it more user-friendly
                processed_endpoints = []
                for endpoint in endpoints:
                    connections = endpoint.get('connections', [])
                    connected_resource_names = []
                    
                    for connection_id in connections:
                        if connection_id:
                            # Extract resource name from connection ID
                            connection_parts = connection_id.split('/')
                            if len(connection_parts) > 0:
                                resource_name = connection_parts[-1]
                                connected_resource_names.append(resource_name)
                    
                    # Extract subnet name from subnet ID
                    subnet_id = endpoint.get('subnet', '')
                    subnet_name = 'Unknown'
                    if subnet_id:
                        subnet_parts = subnet_id.split('/')
                        if len(subnet_parts) > 0:
                            subnet_name = subnet_parts[-1]
                    
                    processed_endpoints.append({
                        'name': endpoint['name'],
                        'id': endpoint['id'],
                        'location': endpoint['location'],
                        'subnet_name': subnet_name,
                        'subnet_id': subnet_id,
                        'connected_resources': connected_resource_names,
                        'resource_group': resource_group
                    })
                
                logger.info(f"Found {len(processed_endpoints)} private endpoints in resource group {resource_group}")
                return processed_endpoints
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse private endpoints JSON: {e}")
                return []
            
        except Exception as e:
            logger.error(f"Error getting private endpoints in resource group {resource_group}: {str(e)}")
            return []
    
    def suggest_private_endpoints_for_services(self, resource_group: str, ai_search_id: str = "", storage_id: str = "", cosmos_id: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """Suggest existing private endpoints for each service based on naming patterns and connections."""
        try:
            all_endpoints = self.get_all_private_endpoints_in_resource_group(resource_group)
            
            suggestions = {
                'ai_search': [],
                'storage': [],
                'cosmos_db': [],
                'other': []
            }
            
            for endpoint in all_endpoints:
                endpoint_name = endpoint['name'].lower()
                connected_resources = [res.lower() for res in endpoint.get('connected_resources', [])]
                
                # Check if connected to specific resources
                categorized = False
                
                if ai_search_id:
                    ai_search_name = ai_search_id.split('/')[-1].lower()
                    if any(ai_search_name in res for res in connected_resources):
                        suggestions['ai_search'].append(endpoint)
                        categorized = True
                
                if storage_id and not categorized:
                    storage_name = storage_id.split('/')[-1].lower()
                    if any(storage_name in res for res in connected_resources):
                        suggestions['storage'].append(endpoint)
                        categorized = True
                
                if cosmos_id and not categorized:
                    cosmos_name = cosmos_id.split('/')[-1].lower()
                    if any(cosmos_name in res for res in connected_resources):
                        suggestions['cosmos_db'].append(endpoint)
                        categorized = True
                
                # If not connected to specific resources, categorize by naming patterns
                if not categorized:
                    if any(pattern in endpoint_name for pattern in ['search', 'ai-search', 'aisearch', 'cognitive']):
                        suggestions['ai_search'].append(endpoint)
                    elif any(pattern in endpoint_name for pattern in ['storage', 'blob', 'file', 'queue', 'table']):
                        suggestions['storage'].append(endpoint)
                    elif any(pattern in endpoint_name for pattern in ['cosmos', 'cosmosdb', 'documentdb', 'mongodb']):
                        suggestions['cosmos_db'].append(endpoint)
                    else:
                        suggestions['other'].append(endpoint)
            
            logger.info(f"Categorized private endpoints: AI Search={len(suggestions['ai_search'])}, Storage={len(suggestions['storage'])}, Cosmos={len(suggestions['cosmos_db'])}, Other={len(suggestions['other'])}")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting private endpoints: {str(e)}")
            return {'ai_search': [], 'storage': [], 'cosmos_db': [], 'other': []}
    
    def switch_subscription_context(self, subscription_id: str) -> Tuple[bool, str]:
        """
        Switch the Azure CLI context to the specified subscription.
        
        Args:
            subscription_id: The subscription ID to switch to
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            import subprocess
            
            logger.info(f"Switching Azure CLI context to subscription: {subscription_id}")
            
            # Run az account set command
            result = subprocess.run(
                ['az', 'account', 'set', '--subscription', subscription_id],
                capture_output=True, text=True, check=True
            )
            
            # Verify the switch was successful
            verify_result = subprocess.run(
                ['az', 'account', 'show', '--query', 'id', '-o', 'tsv'],
                capture_output=True, text=True, check=True
            )
            
            current_sub = verify_result.stdout.strip()
            if current_sub == subscription_id:
                logger.info(f"✅ Successfully switched to subscription: {subscription_id}")
                return True, f"✅ Successfully switched to subscription: {subscription_id}"
            else:
                error_msg = f"❌ Switch failed: Expected {subscription_id}, but current is {current_sub}"
                logger.error(error_msg)
                return False, error_msg
                
        except subprocess.CalledProcessError as e:
            error_msg = f"❌ Azure CLI command failed: {e.stderr if e.stderr else str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"❌ Failed to switch subscription: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_current_subscription_id(self) -> str:
        """
        Get the current Azure CLI subscription ID.
        
        Returns:
            Current subscription ID
            
        Raises:
            Exception: If unable to get current subscription
        """
        try:
            import subprocess
            
            result = subprocess.run(
                ['az', 'account', 'show', '--query', 'id', '-o', 'tsv'],
                capture_output=True, text=True, check=True
            )
            
            current_sub = result.stdout.strip()
            logger.info(f"Current subscription: {current_sub}")
            return current_sub
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to get current subscription: {e.stderr if e.stderr else str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error getting current subscription: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def get_available_resource_groups(self, subscription_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get available resource groups in the current or specified subscription.
        
        Args:
            subscription_id: Optional subscription ID. If not provided, uses current subscription.
            
        Returns:
            List of resource group dictionaries
        """
        try:
            import subprocess
            
            cmd = ['az', 'group', 'list', '--output', 'json']
            
            # Add subscription parameter if specified
            if subscription_id:
                cmd.extend(['--subscription', subscription_id])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
            
            import json
            resource_groups = json.loads(result.stdout)
            
            # Format for consistency
            formatted_rgs = []
            for rg in resource_groups:
                formatted_rgs.append({
                    'name': rg['name'],
                    'location': rg['location'],
                    'id': rg['id'],
                    'managedBy': rg.get('managedBy'),
                    'tags': rg.get('tags', {}),
                    'properties': rg.get('properties', {})
                })
            
            logger.info(f"Found {len(formatted_rgs)} resource groups")
            return formatted_rgs
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to list resource groups: {e.stderr if e.stderr else str(e)}"
            logger.error(error_msg)
            return []
        except Exception as e:
            error_msg = f"Error listing resource groups: {str(e)}"
            logger.error(error_msg)
            return []
    
    def authenticate_and_switch_subscription(self, subscription_id: str) -> Tuple[bool, str]:
        """
        Authenticate to Azure and switch to the specified subscription.
        
        Args:
            subscription_id: The subscription ID to authenticate and switch to
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            import subprocess
            
            logger.info(f"Authenticating and switching to subscription: {subscription_id}")
            
            # Step 1: Check if already logged in to this subscription
            try:
                current_sub = self.get_current_subscription_id()
                if current_sub == subscription_id:
                    return True, f"✅ Already authenticated and using subscription: {subscription_id}"
            except Exception:
                # Not logged in or different subscription, continue with login
                pass
            
            # Step 2: Try to switch to the subscription first (in case already logged in)
            try:
                result = subprocess.run(
                    ['az', 'account', 'set', '--subscription', subscription_id],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    # Successfully switched - verify
                    verify_result = subprocess.run(
                        ['az', 'account', 'show', '--query', 'id', '-o', 'tsv'],
                        capture_output=True, text=True, timeout=30
                    )
                    
                    if verify_result.returncode == 0:
                        current_sub = verify_result.stdout.strip()
                        if current_sub == subscription_id:
                            logger.info(f"✅ Successfully switched to subscription: {subscription_id}")
                            return True, f"✅ Successfully switched to subscription: {subscription_id}"
                
            except subprocess.TimeoutExpired:
                return False, "❌ Timeout while switching subscription"
            except Exception as e:
                logger.warning(f"Could not switch to subscription directly: {e}")
            
            # Step 3: If switching failed, try login (this will open browser)
            logger.info("Attempting Azure CLI login...")
            
            try:
                # Interactive login
                login_result = subprocess.run(
                    ['az', 'login'],
                    capture_output=True, text=True, timeout=300  # 5 minutes for user interaction
                )
                
                if login_result.returncode != 0:
                    error_msg = f"❌ Login failed: {login_result.stderr}"
                    logger.error(error_msg)
                    return False, error_msg
                
                logger.info("✅ Login successful")
                
            except subprocess.TimeoutExpired:
                return False, "❌ Login timed out (5 minutes). Please try again."
            except Exception as e:
                return False, f"❌ Login error: {str(e)}"
            
            # Step 4: Now try to switch to the target subscription
            try:
                switch_result = subprocess.run(
                    ['az', 'account', 'set', '--subscription', subscription_id],
                    capture_output=True, text=True, timeout=30
                )
                
                if switch_result.returncode != 0:
                    error_msg = f"❌ Failed to switch to subscription {subscription_id}: {switch_result.stderr}"
                    logger.error(error_msg)
                    return False, error_msg
                
                # Step 5: Verify the switch was successful
                verify_result = subprocess.run(
                    ['az', 'account', 'show', '--query', 'id', '-o', 'tsv'],
                    capture_output=True, text=True, timeout=30
                )
                
                if verify_result.returncode == 0:
                    current_sub = verify_result.stdout.strip()
                    if current_sub == subscription_id:
                        success_msg = f"✅ Successfully authenticated and switched to subscription: {subscription_id}"
                        logger.info(success_msg)
                        return True, success_msg
                    else:
                        error_msg = f"❌ Switch verification failed: Expected {subscription_id}, but current is {current_sub}"
                        logger.error(error_msg)
                        return False, error_msg
                else:
                    error_msg = f"❌ Could not verify subscription switch: {verify_result.stderr}"
                    logger.error(error_msg)
                    return False, error_msg
                    
            except subprocess.TimeoutExpired:
                return False, "❌ Timeout while switching subscription after login"
            except Exception as e:
                return False, f"❌ Error switching subscription after login: {str(e)}"
                
        except Exception as e:
            error_msg = f"❌ Authentication and subscription switch failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_subscription_context_info(self) -> Dict[str, str]:
        """
        Get detailed information about the current Azure CLI context.
        
        Returns:
            Dictionary with context information
        """
        try:
            import subprocess
            import json
            
            # Get current account details
            result = subprocess.run(
                ['az', 'account', 'show', '--output', 'json'],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                account_info = json.loads(result.stdout)
                
                return {
                    'subscription_id': account_info.get('id', 'Unknown'),
                    'subscription_name': account_info.get('name', 'Unknown'),
                    'tenant_id': account_info.get('tenantId', 'Unknown'),
                    'user_name': account_info.get('user', {}).get('name', 'Unknown'),
                    'user_type': account_info.get('user', {}).get('type', 'Unknown'),
                    'state': account_info.get('state', 'Unknown'),
                    'is_default': account_info.get('isDefault', False)
                }
            else:
                return {
                    'subscription_id': 'Not logged in',
                    'subscription_name': 'Not logged in',
                    'tenant_id': 'Not logged in',
                    'user_name': 'Not logged in',
                    'user_type': 'Not logged in',
                    'state': 'Not logged in',
                    'is_default': False
                }
                
        except Exception as e:
            logger.error(f"Error getting subscription context: {e}")
            return {
                'subscription_id': 'Error',
                'subscription_name': 'Error',
                'tenant_id': 'Error',
                'user_name': 'Error',
                'user_type': 'Error',
                'state': 'Error',
                'is_default': False
            }
    
    def _get_subscriptions_via_sdk(self) -> List[Dict[str, str]]:
        """Fallback method to get subscriptions using Azure SDK."""
        try:
            from azure.identity import DefaultAzureCredential
            from azure.mgmt.subscription import SubscriptionClient
            
            logger.info("Falling back to Azure SDK for subscription list...")
            
            credential = DefaultAzureCredential()
            subscription_client = SubscriptionClient(credential)
            
            subscriptions = []
            for sub in subscription_client.subscriptions.list():
                subscriptions.append({
                    "subscription_id": sub.subscription_id,
                    "subscription_name": sub.display_name,  # Use subscription_name for consistency
                    "display_name": sub.display_name,  # Keep for backward compatibility
                    "state": sub.state,
                    "tenantId": getattr(sub, 'tenant_id', ''),
                    "isDefault": False,  # SDK doesn't provide default info
                    "user": {}
                })
            
            logger.info(f"Found {len(subscriptions)} subscriptions via Azure SDK")
            return subscriptions
            
        except Exception as e:
            logger.error(f"Azure SDK fallback also failed: {e}")
            return []
