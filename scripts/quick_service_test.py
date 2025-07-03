#!/usr/bin/env python3
"""
Quick test for AI Foundry service method validation.
"""

import sys
sys.path.append('.')

def quick_test():
    """Quick test of service methods."""
    print("🔍 Quick AI Foundry service test...")
    
    try:
        # Test imports
        from services.ai_foundry_discovery import AIFoundryDiscoveryService
        from services.ai_foundry_service import AIFoundryService
        print("✅ Imports successful")
        
        # Check method names
        discovery_methods = [method for method in dir(AIFoundryDiscoveryService) if 'discover' in method.lower()]
        service_methods = [method for method in dir(AIFoundryService) if 'create' in method.lower()]
        
        print(f"📋 Discovery service methods: {discovery_methods}")
        print(f"📋 AI Foundry service methods: {service_methods}")
        
        # Test creating a mock resource dictionary and calling create_project
        print("\n🧪 Testing create_project with mock data...")
        
        # Mock resource dictionary (like what comes from the UI)
        mock_resource = {
            'name': 'test-account',
            'resource_type': 'Microsoft.CognitiveServices/accounts',
            'location': 'eastus',
            'resource_group': 'test-rg',
            'subscription_id': 'test-sub-id',
            'endpoint': 'https://test-account.cognitiveservices.azure.com/',
            'id': '/subscriptions/test-sub-id/resourceGroups/test-rg/providers/Microsoft.CognitiveServices/accounts/test-account',
            'properties': {}
        }
        
        # Initialize service (this might fail but we'll catch it)
        try:
            service = AIFoundryService()
            print("✅ Service initialized")
            
            # Test the create_project method signature and handling
            print("🔍 Testing create_project method...")
            
            # This should not crash due to attribute access errors
            success, message, project = service.create_project(
                mock_resource,
                "test-project",
                "Test description"
            )
            
            print(f"✅ create_project method completed: success={success}")
            print(f"📋 Message: {message}")
            
        except Exception as e:
            print(f"⚠️  Service test completed with expected error: {str(e)}")
            # This is expected since we don't have real credentials/resources
            if "dictionary" in str(e) or "attribute" in str(e):
                print("❌ The fix didn't work - still getting attribute/dictionary errors")
                return False
            else:
                print("✅ No attribute/dictionary errors - fix appears to be working")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = quick_test()
    print(f"\n🎯 Test result: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
