#!/usr/bin/env python3
"""
Deploy Tab Diagnostic Script
----------------------------
Diagnose why the subscription selection isn't showing up in the Deploy tab.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

def diagnose_deploy_tab():
    """Diagnose the Deploy tab rendering issue."""
    print("🔍 Diagnosing Deploy Tab Issue")
    print("=" * 40)
    
    try:
        from app.components.ai_foundry_hub_deployment_ui import AIFoundryHubDeploymentUI
        from services.ai_foundry_hub_deployment import AIFoundryHubDeploymentConfig
        
        # Initialize UI component
        ui = AIFoundryHubDeploymentUI()
        print("✅ UI component initialized")
        
        # Check if service methods work
        print("\n📋 Testing service methods...")
        
        # Test subscription methods
        try:
            subscriptions = ui.service.get_prioritized_subscriptions()
            print(f"✅ Found {len(subscriptions)} subscriptions")
            
            current_sub = ui.service.get_current_subscription_info()
            if current_sub:
                print(f"✅ Current subscription: {current_sub['display_name']}")
            else:
                print("⚠️ No current subscription detected")
        except Exception as e:
            print(f"❌ Subscription methods failed: {e}")
            return False
        
        # Test configuration validation
        print("\n🔍 Testing configuration validation...")
        
        # Create default config (similar to what session state would have)
        config = AIFoundryHubDeploymentConfig()
        print(f"📋 Default config location: {config.location}")
        print(f"📋 Default config AI services name: {config.ai_services_name}")
        print(f"📋 Default config project name: {config.project_name}")
        
        # Test validation
        issues = ui.service.validate_deployment_config(config)
        print(f"📋 Validation issues found: {len(issues)}")
        
        if issues:
            print("❌ Validation Issues (these would prevent Deploy tab from showing subscription selection):")
            for i, issue in enumerate(issues):
                print(f"  {i+1}. {issue}")
            
            print("\n💡 **SOLUTION**: These validation issues need to be fixed in the Configuration tab first.")
            print("   The Deploy tab returns early if there are validation issues.")
        else:
            print("✅ No validation issues - subscription selection should show")
        
        # Test template validation
        print("\n📋 Testing template validation...")
        valid, msg = ui.service.validate_template_path()
        if valid:
            print("✅ Template validation passed")
        else:
            print(f"❌ Template validation failed: {msg}")
            print("💡 This might prevent the Deploy tab from rendering properly")
        
        # Simulate the exact Deploy tab flow
        print("\n🚀 Simulating Deploy Tab Flow...")
        
        print("1. Check if 'deployment_config' exists in session state...")
        # In real Streamlit, this would be st.session_state.deployment_config
        # For simulation, we'll assume it exists
        print("   ✅ deployment_config exists (simulated)")
        
        print("2. Validate configuration...")
        if issues:
            print("   ❌ Validation failed - Deploy tab would return early here")
            print("   🎯 **ROOT CAUSE**: This is why subscription selection isn't showing!")
            return False
        else:
            print("   ✅ Validation passed - would continue to subscription selection")
        
        print("3. Load subscriptions...")
        if subscriptions:
            print(f"   ✅ {len(subscriptions)} subscriptions available")
        else:
            print("   ❌ No subscriptions - Deploy tab would return early here")
            return False
        
        print("4. Generate subscription options...")
        subscription_options = {}
        current_sub_id = current_sub['subscription_id'] if current_sub else None
        
        for sub in subscriptions:
            if sub['state'] == 'Enabled':
                label = f"{sub['display_name']} ({sub['subscription_id']})"
                if sub['subscription_id'] == current_sub_id:
                    label = f"🌟 {label} (Current)"
                subscription_options[label] = sub['subscription_id']
        
        print(f"   ✅ Generated {len(subscription_options)} subscription options")
        
        if subscription_options:
            print("   ✅ Subscription selection would be rendered")
            print("   📋 Available options:")
            for label in list(subscription_options.keys())[:3]:  # Show first 3
                print(f"      - {label}")
        else:
            print("   ❌ No subscription options - Deploy tab would return early here")
            return False
        
        print("\n🎉 All checks passed - subscription selection should be visible!")
        return True
        
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_solution():
    """Show the solution if validation issues are found."""
    print("\n🎯 SOLUTION TO FIX DEPLOY TAB")
    print("=" * 40)
    
    print("The subscription selection isn't showing because:")
    print("1. The Deploy tab validates the configuration first")
    print("2. If validation fails, it shows errors and returns early")
    print("3. The subscription selection never gets rendered")
    
    print("\n📋 TO FIX:")
    print("1. Go to the 'Configuration' tab")
    print("2. Fill in the required fields:")
    print("   - Location (should be selected)")
    print("   - AI Services Name (enter a name)")
    print("   - Project Name (enter a name)")
    print("   - Display Name (enter a name)")
    print("3. Configure other settings as needed")
    print("4. Return to Deploy tab")
    print("5. Subscription selection should now be visible")
    
    print("\n💡 QUICK TIP:")
    print("The 'Configuration' tab should show validation status.")
    print("Make sure all required fields have values before going to Deploy tab.")

if __name__ == "__main__":
    print("🔍 Deploy Tab Subscription Selection Diagnostic")
    print("=" * 50)
    
    success = diagnose_deploy_tab()
    
    if not success:
        show_solution()
        print("\n⚠️ Fix the issues above and the subscription selection should appear.")
    else:
        print("\n✅ Everything looks good - subscription selection should be working!")
    
    exit(0 if success else 1)
