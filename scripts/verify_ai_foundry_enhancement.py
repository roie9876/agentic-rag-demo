#!/usr/bin/env python3
"""
Verify AI Foundry Enhancement
Test script to verify all AI Foundry components are working properly
"""

import sys
import os
sys.path.append('.')

def test_imports():
    """Test all enhanced AI Foundry imports"""
    print("🧪 Testing AI Foundry Enhancement Imports...")
    
    # Test main tab
    try:
        from app.tabs.enhanced_ai_foundry_tab import render_enhanced_ai_foundry_tab
        print("✅ Enhanced AI Foundry tab imported successfully")
    except ImportError as e:
        print(f"❌ Enhanced AI Foundry tab import error: {e}")
        return False

    # Test services
    try:
        from services.ai_foundry_discovery import AIFoundryDiscoveryService
        print("✅ AI Foundry discovery service imported successfully")
    except ImportError as e:
        print(f"❌ AI Foundry discovery import error: {e}")
        return False

    try:
        from services.ai_foundry_rbac import AIFoundryRBACService
        print("✅ AI Foundry RBAC service imported successfully")
    except ImportError as e:
        print(f"❌ AI Foundry RBAC import error: {e}")
        return False

    try:
        from services.ai_foundry_agent_deployment import AIFoundryAgentDeploymentService
        print("✅ AI Foundry agent deployment service imported successfully")
    except ImportError as e:
        print(f"❌ AI Foundry agent deployment import error: {e}")
        return False

    # Test utilities
    try:
        from utils.ai_foundry_helpers import AIFoundryHelper
        print("✅ AI Foundry helpers imported successfully")
    except ImportError as e:
        print(f"❌ AI Foundry helpers import error: {e}")
        return False
    
    return True

def test_service_initialization():
    """Test service initialization without actual API calls"""
    print("\n🔧 Testing Service Initialization...")
    
    try:
        from services.ai_foundry_discovery import AIFoundryDiscoveryService
        discovery = AIFoundryDiscoveryService()
        print("✅ Discovery service initialized")
    except Exception as e:
        print(f"❌ Discovery service initialization error: {e}")
        return False
    
    try:
        from services.ai_foundry_rbac import AIFoundryRBACService
        rbac = AIFoundryRBACService()
        print("✅ RBAC service initialized")
    except Exception as e:
        print(f"❌ RBAC service initialization error: {e}")
        return False
    
    try:
        from services.ai_foundry_agent_deployment import AIFoundryAgentDeploymentService
        deployment = AIFoundryAgentDeploymentService()
        print("✅ Agent deployment service initialized")
    except Exception as e:
        print(f"❌ Agent deployment service initialization error: {e}")
        return False
    
    return True

def test_main_integration():
    """Test that the main app can import the enhanced tab"""
    print("\n🔗 Testing Main App Integration...")
    
    try:
        # This simulates the import in agentic-rag-demo.py
        from app.tabs.enhanced_ai_foundry_tab import render_enhanced_ai_foundry_tab
        
        # Test that the function exists and is callable
        if callable(render_enhanced_ai_foundry_tab):
            print("✅ Enhanced AI Foundry tab is callable")
        else:
            print("❌ Enhanced AI Foundry tab is not callable")
            return False
            
        print("✅ Main app integration successful")
        return True
        
    except Exception as e:
        print(f"❌ Main app integration error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 AI Foundry Enhancement Verification")
    print("=" * 50)
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    # Test service initialization
    if not test_service_initialization():
        success = False
    
    # Test main integration
    if not test_main_integration():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All AI Foundry Enhancement tests passed!")
        print("\n📋 What's Available:")
        print("✅ Enhanced AI Foundry Agent tab with:")
        print("   • AI Foundry Account & Hub discovery")
        print("   • RBAC permissions checking and management")
        print("   • Project selection and creation")
        print("   • Agent deployment workflow")
        print("   • Private endpoint support")
        print("\n🚀 Ready to run: streamlit run agentic-rag-demo.py")
        return 0
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())
