#!/usr/bin/env python3
"""
Initialize Basic Deploy Configuration
------------------------------------
Helper script to show what a basic configuration should look like
to make the Deploy tab subscription selection appear.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

def create_basic_config():
    """Create a basic configuration example."""
    print("🔧 Basic Configuration Setup Guide")
    print("=" * 40)
    
    try:
        from services.ai_foundry_hub_deployment import AIFoundryHubDeploymentConfig
        
        # Create a basic config
        config = AIFoundryHubDeploymentConfig()
        
        print("📋 **REQUIRED FIELDS** for Deploy tab to show subscription selection:")
        print()
        
        print("🌍 **Location**: (Already set)")
        print(f"   Current value: {config.location}")
        print(f"   ✅ This is sufficient")
        print()
        
        print("🤖 **AI Services Name**: (Already set)")
        print(f"   Current value: {config.ai_services_name}")
        print(f"   ✅ This is sufficient")
        print()
        
        print("📁 **Project Name**: (Already set)")
        print(f"   Current value: {config.project_name}")
        print(f"   ✅ This is sufficient")
        print()
        
        print("🏷️ **Display Name**: (May need to be set)")
        print(f"   Current value: '{config.display_name}'")
        if config.display_name:
            print(f"   ✅ This is sufficient")
        else:
            print(f"   ⚠️ This may need to be filled in")
        print()
        
        # Test validation
        from services.ai_foundry_hub_deployment import AIFoundryHubDeploymentService
        service = AIFoundryHubDeploymentService()
        
        issues = service.validate_deployment_config(config)
        print("🔍 **VALIDATION RESULTS**:")
        if issues:
            print("❌ Current configuration has issues:")
            for i, issue in enumerate(issues):
                print(f"   {i+1}. {issue}")
            print()
            print("💡 **ACTION NEEDED**: Fix these issues in the Configuration tab")
        else:
            print("✅ Default configuration is valid!")
            print("   The Deploy tab should show subscription selection")
        print()
        
        print("📋 **STEP-BY-STEP SOLUTION**:")
        print("1. Click on the '⚙️ Configuration' tab")
        print("2. In the 'Basic Settings' section:")
        print("   - Verify Location is selected")
        print("   - Verify AI Services Name has a value")
        print("   - Verify Project Name has a value")
        print("   - Fill in Display Name if empty")
        print("3. Click on the '🚀 Deploy' tab")
        print("4. You should now see '🎯 Target Subscription' section")
        print()
        
        print("🔍 **DEBUGGING TIP**:")
        print("If you still don't see subscription selection:")
        print("- Look for a warning message at the top of Deploy tab")
        print("- Check if there are validation errors listed")
        print("- Ensure all required fields in Configuration tab are filled")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating config example: {e}")
        return False

def test_streamlit_session_state():
    """Test what happens without session state."""
    print("\n🧪 Testing Session State Simulation")
    print("=" * 40)
    
    print("📋 **WHY SUBSCRIPTION SELECTION ISN'T SHOWING**:")
    print()
    print("The Deploy tab code does this check first:")
    print("```python")
    print("if 'deployment_config' not in st.session_state:")
    print("    st.warning('Please configure the deployment first in the Configuration tab.')")
    print("    return  # ← This stops here!")
    print("```")
    print()
    print("🎯 **ROOT CAUSE**: You haven't created a configuration yet")
    print("💡 **SOLUTION**: Go to Configuration tab and fill in basic settings")
    print()
    
    print("📋 **WHAT SHOULD HAPPEN**:")
    print("1. You fill in Configuration tab")
    print("2. Streamlit saves config to st.session_state.deployment_config")
    print("3. Deploy tab finds the config")
    print("4. Validation passes")
    print("5. Subscription selection appears")

if __name__ == "__main__":
    success = create_basic_config()
    test_streamlit_session_state()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 **SUMMARY**: Go to Configuration tab first, then return to Deploy!")
    else:
        print("❌ **ERROR**: Please check the configuration setup")
    
    exit(0 if success else 1)
