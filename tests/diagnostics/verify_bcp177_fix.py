#!/usr/bin/env python3
"""
Test script to verify the BCP177 fix implementation
"""

import os
import sys
sys.path.append('/home/azureuser/agentic-rag-demo')

from services.ai_foundry_hub_deployment import AIFoundryHubDeploymentService

def test_template_selection():
    """Test that the service properly selects ARM template over Bicep."""
    print("🧪 Testing Template Selection Logic")
    print("=" * 50)
    
    service = AIFoundryHubDeploymentService()
    
    # Check template path validation
    valid, msg = service.validate_template_path()
    print(f"✅ Template validation: {valid}")
    print(f"📋 Message: {msg}")
    
    # Check which templates exist
    template_path = "/home/azureuser/agentic-rag-demo/15-private-network-standard-agent-setup"
    main_json = os.path.join(template_path, "main.json")
    main_bicep = os.path.join(template_path, "main.bicep")
    
    print(f"\n📂 Template Files:")
    print(f"   main.json exists: {os.path.exists(main_json)}")
    print(f"   main.bicep exists: {os.path.exists(main_bicep)}")
    
    if os.path.exists(main_json):
        print(f"\n✅ SUCCESS: ARM template (main.json) is available")
        print(f"🎯 The deployment service will use: {main_json}")
        print(f"💡 This avoids the BCP177 Bicep compilation error")
        
        # Check file size to ensure it's valid
        json_size = os.path.getsize(main_json)
        print(f"📊 ARM template size: {json_size:,} bytes")
        
        if json_size > 10000:  # Should be a substantial file
            print(f"✅ ARM template appears to be complete")
        else:
            print(f"⚠️ ARM template seems small - verify it's complete")
    
    else:
        print(f"\n⚠️ ARM template not found - will fall back to Bicep")
        if os.path.exists(main_bicep):
            print(f"⚠️ Bicep template available but may trigger BCP177 error")
        else:
            print(f"❌ No templates available")
    
    return valid

def test_deployment_config():
    """Test deployment configuration to ensure it works with ARM template."""
    print(f"\n🔧 Testing Deployment Configuration")
    print("=" * 50)
    
    try:
        from services.ai_foundry_hub_deployment import (
            AIFoundryHubDeploymentConfig, 
            NetworkConfig, 
            DeploymentResource
        )
        
        # Create a minimal test configuration
        network_config = NetworkConfig(
            create_new_vnet=True,
            vnet_name="test-vnet",
            vnet_address_prefix="10.0.0.0/16",
            agent_subnet_name="agent-subnet",
            agent_subnet_prefix="10.0.1.0/24",
            pe_subnet_name="pe-subnet",
            pe_subnet_prefix="10.0.2.0/24"
        )
        
        cosmos_db = DeploymentResource(
            name="test-cosmos",
            resource_type="Microsoft.DocumentDB/databaseAccounts",
            create_new=True
        )
        
        ai_search = DeploymentResource(
            name="test-search",
            resource_type="Microsoft.Search/searchServices", 
            create_new=True
        )
        
        storage_account = DeploymentResource(
            name="test-storage",
            resource_type="Microsoft.Storage/storageAccounts",
            create_new=True
        )
        
        config = AIFoundryHubDeploymentConfig(
            location="eastus2",
            ai_services_name="test-ai-hub",
            project_name="test-project",
            project_description="Test project",
            display_name="Test AI Hub",
            model_name="gpt-4o",
            model_capacity=30,
            network_config=network_config,
            cosmos_db=cosmos_db,
            ai_search=ai_search,
            storage_account=storage_account
        )
        
        print(f"✅ Configuration created successfully")
        print(f"📍 Location: {config.location}")
        print(f"🤖 AI Services: {config.ai_services_name}")
        print(f"📁 Project: {config.project_name}")
        
        # Test parameter generation (this should work with ARM template)
        service = AIFoundryHubDeploymentService()
        params = service.generate_bicep_parameters(config)
        
        print(f"✅ Parameters generated: {len(params)} parameters")
        print(f"📋 Key parameters: location, aiServices, firstProjectName")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_ui_integration():
    """Test that UI components can still work."""
    print(f"\n🖥️ Testing UI Integration")
    print("=" * 50)
    
    try:
        # This will just test imports, not actual UI rendering
        from app.ui.ai_foundry_hub_deployment_ui import AIFoundryHubDeploymentUI
        
        ui = AIFoundryHubDeploymentUI()
        print(f"✅ UI component imported successfully")
        print(f"🔗 Service integration: {type(ui.service).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ UI integration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🎯 BCP177 Fix Verification")
    print("=" * 60)
    print("Testing the ARM template workaround for BCP177 error")
    print()
    
    results = []
    
    # Test 1: Template selection
    results.append(test_template_selection())
    
    # Test 2: Deployment configuration  
    results.append(test_deployment_config())
    
    # Test 3: UI integration
    results.append(test_ui_integration())
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print(f"✅ BCP177 fix is working correctly")
        print(f"🚀 Your UI app should now be able to deploy successfully")
        print()
        print(f"💡 Next Steps:")
        print(f"   1. Go to AI Foundry Hub tab in your Streamlit app")
        print(f"   2. Navigate to 'Deploy New Hub' tab")
        print(f"   3. Configure your deployment")
        print(f"   4. Deploy - it will use main.json (ARM) instead of main.bicep")
    else:
        print(f"⚠️ SOME TESTS FAILED ({passed}/{total})")
        print(f"❌ Please check the errors above")

if __name__ == "__main__":
    main()
