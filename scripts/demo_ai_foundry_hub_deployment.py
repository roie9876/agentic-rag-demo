#!/usr/bin/env python3
"""
AI Foundry Hub Deployment - Feature Demonstration
================================================
This script demonstrates the key features of the new AI Foundry Hub deployment capability.
"""

import sys
import os
sys.path.append('/home/azureuser/agentic-rag-demo')

from services.ai_foundry_hub_deployment import (
    AIFoundryHubDeploymentService,
    AIFoundryHubDeploymentConfig,
    DeploymentResource,
    NetworkConfig
)
from app.components.ai_foundry_hub_deployment_ui import AIFoundryHubDeploymentUI


def demonstrate_service_features():
    """Demonstrate the service capabilities."""
    print("🚀 AI Foundry Hub Deployment Service Demo")
    print("=" * 50)
    
    # Initialize service
    service = AIFoundryHubDeploymentService()
    print("✅ Service initialized")
    
    # Template validation
    valid, msg = service.validate_template_path()
    print(f"✅ Template validation: {valid} - {msg}")
    
    # Available locations
    locations = service.get_available_locations()
    print(f"✅ Available locations: {len(locations)}")
    print(f"   Regions: {', '.join(locations[:5])}...")
    
    # Resource groups (requires Azure CLI login)
    try:
        rgs = service.get_subscription_resource_groups()
        print(f"✅ Resource groups: {len(rgs)} found")
        if rgs:
            print(f"   Examples: {', '.join(rgs[:3])}...")
    except Exception as e:
        print(f"⚠️  Resource groups: Login required ({str(e)[:50]}...)")
    
    # Configuration example
    config = AIFoundryHubDeploymentConfig()
    config.location = "eastus2"
    config.ai_services_name = "demo-ai-hub"
    config.project_name = "demo-project"
    
    # Network configuration
    config.network_config.create_new_vnet = True
    config.network_config.vnet_name = "demo-vnet"
    config.network_config.vnet_address_prefix = "10.0.0.0/16"
    config.network_config.agent_subnet_prefix = "10.0.1.0/24"
    config.network_config.pe_subnet_prefix = "10.0.2.0/24"
    
    # Resource configuration - mix of new and existing
    config.cosmos_db.create_new = True
    config.ai_search.create_new = False
    config.ai_search.existing_resource_id = "/subscriptions/xxx/resourceGroups/demo/providers/Microsoft.Search/searchServices/existing-search"
    config.storage_account.create_new = True
    
    print("✅ Configuration created")
    
    # Parameter generation
    params = service.generate_bicep_parameters(config)
    print(f"✅ Parameters generated: {len(params)} parameters")
    
    # Configuration validation
    issues = service.validate_deployment_config(config)
    print(f"✅ Validation: {len(issues)} issues found")
    
    if issues:
        print("   Issues:")
        for issue in issues:
            print(f"   - {issue}")
    
    print("\n📋 Generated Parameters Preview:")
    print("-" * 30)
    key_params = ['location', 'aiServices', 'firstProjectName', 'vnetName', 'vnetAddressPrefix']
    for key in key_params:
        if key in params:
            print(f"  {key}: {params[key]['value']}")
    print(f"  ... and {len(params) - len(key_params)} more parameters")
    
    return service, config


def demonstrate_ui_features():
    """Demonstrate the UI capabilities."""
    print("\n🎨 AI Foundry Hub Deployment UI Demo")
    print("=" * 50)
    
    # Initialize UI
    ui = AIFoundryHubDeploymentUI()
    print("✅ UI component initialized")
    print("✅ Service integration: AIFoundryHubDeploymentService")
    
    # Template validation through UI
    valid, msg = ui.service.validate_template_path()
    print(f"✅ Template validation: {valid} - {msg}")
    
    # Available locations through UI
    locations = ui.service.get_available_locations()
    print(f"✅ Available locations: {len(locations)} locations")
    
    # Configuration validation
    from services.ai_foundry_hub_deployment import AIFoundryHubDeploymentConfig
    test_config = AIFoundryHubDeploymentConfig()
    issues = ui.service.validate_deployment_config(test_config)
    print(f"✅ Configuration validation: {len(issues)} issues found")
    
    print("\n📊 UI Features Available:")
    print("  🔧 Configuration Tab:")
    print("    - Basic settings (location, names, model config)")
    print("    - Network configuration (VNet, subnets)")
    print("    - Resource configuration (new vs existing)")
    print("  👀 Preview Tab:")
    print("    - Parameter validation and preview")
    print("    - Resource summary")
    print("  🚀 Deploy Tab:")
    print("    - Resource group selection")
    print("    - One-click deployment")
    print("  📊 Status Tab:")
    print("    - Real-time progress monitoring")
    print("    - Deployment outputs and results")
    
    return ui


def demonstrate_configuration_scenarios():
    """Demonstrate different configuration scenarios."""
    print("\n🎯 Configuration Scenarios Demo")
    print("=" * 50)
    
    service = AIFoundryHubDeploymentService()
    
    # Scenario 1: All new resources
    print("📋 Scenario 1: All New Resources")
    config1 = AIFoundryHubDeploymentConfig()
    config1.ai_services_name = "newresources-hub"
    config1.location = "eastus2"
    # All resources default to create_new = True
    params1 = service.generate_bicep_parameters(config1)
    new_resources = ['cosmos_db', 'ai_search', 'storage_account']
    creating = [r for r in new_resources if getattr(config1, r).create_new]
    print(f"  - Creating: {len(creating)} new resources")
    print(f"  - Parameters: {len(params1)} total")
    
    # Scenario 2: Mix of new and existing
    print("\n📋 Scenario 2: Mixed Resources")
    config2 = AIFoundryHubDeploymentConfig()
    config2.ai_services_name = "mixed-hub"
    config2.cosmos_db.create_new = False
    config2.cosmos_db.existing_resource_id = "/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.DocumentDB/databaseAccounts/existing-cosmos"
    config2.ai_search.create_new = True  # Create new
    config2.storage_account.create_new = False
    config2.storage_account.existing_resource_id = "/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/existingstorage"
    
    params2 = service.generate_bicep_parameters(config2)
    creating2 = [r for r in new_resources if getattr(config2, r).create_new]
    existing2 = [r for r in new_resources if not getattr(config2, r).create_new]
    print(f"  - Creating: {len(creating2)} new resources")
    print(f"  - Reusing: {len(existing2)} existing resources")
    print(f"  - Parameters: {len(params2)} total")
    
    # Scenario 3: Existing VNet
    print("\n📋 Scenario 3: Existing VNet")
    config3 = AIFoundryHubDeploymentConfig()
    config3.ai_services_name = "existingvnet-hub"
    config3.network_config.create_new_vnet = False
    config3.network_config.existing_vnet_resource_id = "/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/existing-vnet"
    config3.network_config.agent_subnet_name = "existing-agents-subnet"
    config3.network_config.pe_subnet_name = "existing-pe-subnet"
    
    params3 = service.generate_bicep_parameters(config3)
    print(f"  - Using existing VNet: {config3.network_config.existing_vnet_resource_id.split('/')[-1]}")
    print(f"  - Agent subnet: {config3.network_config.agent_subnet_name}")
    print(f"  - PE subnet: {config3.network_config.pe_subnet_name}")
    print(f"  - Parameters: {len(params3)} total")
    
    return [config1, config2, config3]


def main():
    """Main demonstration function."""
    print("🎉 AI Foundry Hub Deployment - Complete Feature Demo")
    print("=" * 60)
    
    try:
        # Demonstrate service features
        service, config = demonstrate_service_features()
        
        # Demonstrate UI features
        ui = demonstrate_ui_features()
        
        # Demonstrate configuration scenarios
        scenarios = demonstrate_configuration_scenarios()
        
        print("\n🎯 Integration Summary")
        print("=" * 30)
        print("✅ Service Layer: AI Foundry Hub deployment logic")
        print("✅ UI Layer: Streamlit components for user interaction")
        print("✅ Integration: Seamless integration with existing AI Foundry tab")
        print("✅ Template: Official Microsoft bicep template support")
        print("✅ Features: Full resource selection and configuration")
        print("✅ Security: Private endpoints and network isolation")
        
        print("\n🚀 Ready to Use!")
        print("Start the Streamlit app and navigate to:")
        print("🏭 AI Foundry Hub → 🚀 Deploy New Hub")
        
        print("\n📋 Key Features:")
        print("- Choose new or existing resources for all dependencies")
        print("- Configure private endpoints and DNS automatically")
        print("- Network isolation with customizable VNet settings")
        print("- Real-time deployment monitoring and status")
        print("- Comprehensive validation and error handling")
        print("- Integration with existing resource discovery")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
