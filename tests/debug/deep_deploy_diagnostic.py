#!/usr/bin/env python3
"""
Deploy Tab Real-Time Diagnostic
-------------------------------
Diagnose why subscription selection isn't showing even after configuration.
This simulates the exact flow of the Deploy tab with real data.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

def deep_diagnose_deploy_tab():
    """Deep diagnostic of the Deploy tab flow."""
    print("🔬 Deep Deploy Tab Diagnostic")
    print("=" * 50)
    
    try:
        from app.components.ai_foundry_hub_deployment_ui import AIFoundryHubDeploymentUI
        from services.ai_foundry_hub_deployment import AIFoundryHubDeploymentConfig
        
        # Initialize UI component
        ui = AIFoundryHubDeploymentUI()
        print("✅ UI component initialized")
        
        # Simulate exactly what Deploy tab does
        print("\n🔍 Simulating Deploy Tab Flow...")
        
        # Step 1: Template validation (this runs first in the main deployment tab)
        print("\n1️⃣ Template Validation Check...")
        valid, msg = ui.service.validate_template_path()
        if not valid:
            print(f"❌ Template validation failed: {msg}")
            print("🎯 **ISSUE FOUND**: Template not found - this would prevent Deploy tab from working")
            return False
        else:
            print("✅ Template validation passed")
        
        # Step 2: Configuration existence check
        print("\n2️⃣ Configuration Existence Check...")
        print("   Simulating: if 'deployment_config' not in st.session_state:")
        
        # Create a realistic config (what should be in session state after Configuration tab)
        config = AIFoundryHubDeploymentConfig()
        
        # Test with different configuration states
        print("   📋 Testing with default configuration...")
        print(f"      Location: {config.location}")
        print(f"      AI Services Name: {config.ai_services_name}")
        print(f"      Project Name: {config.project_name}")
        print(f"      Display Name: {config.display_name}")
        print("   ✅ Configuration would exist in session state")
        
        # Step 3: Configuration validation
        print("\n3️⃣ Configuration Validation Check...")
        issues = ui.service.validate_deployment_config(config)
        print(f"   📋 Validation issues: {len(issues)}")
        
        if issues:
            print("   ❌ VALIDATION FAILED - Deploy tab would return early here!")
            print("   🔍 Issues found:")
            for i, issue in enumerate(issues):
                print(f"      {i+1}. {issue}")
            print("   🎯 **ISSUE FOUND**: These validation errors prevent subscription selection")
            return False
        else:
            print("   ✅ Configuration validation passed")
        
        # Step 4: Subscription loading
        print("\n4️⃣ Subscription Loading Check...")
        try:
            subscriptions = ui.service.get_prioritized_subscriptions()
            print(f"   📋 Found {len(subscriptions)} total subscriptions")
            
            if not subscriptions:
                print("   ❌ NO SUBSCRIPTIONS FOUND - Deploy tab would return early here!")
                print("   🎯 **ISSUE FOUND**: No subscriptions available")
                return False
            else:
                print("   ✅ Subscriptions available")
                
                # Show subscription details
                for i, sub in enumerate(subscriptions):
                    status = "✅" if sub['state'] == 'Enabled' else "❌"
                    print(f"      {i+1}. {status} {sub['display_name']} ({sub['subscription_id'][:8]}...)")
        
        except Exception as e:
            print(f"   ❌ SUBSCRIPTION LOADING FAILED: {e}")
            print("   🎯 **ISSUE FOUND**: Cannot load subscriptions")
            return False
        
        # Step 5: Current subscription info
        print("\n5️⃣ Current Subscription Info Check...")
        try:
            current_sub_info = ui.service.get_current_subscription_info()
            if current_sub_info:
                print(f"   ✅ Current subscription: {current_sub_info['display_name']}")
                current_sub_id = current_sub_info['subscription_id']
            else:
                print("   ⚠️ No current subscription detected")
                current_sub_id = None
        except Exception as e:
            print(f"   ❌ CURRENT SUBSCRIPTION FAILED: {e}")
            print("   🎯 **ISSUE FOUND**: Cannot get current subscription")
            return False
        
        # Step 6: Subscription options generation
        print("\n6️⃣ Subscription Options Generation...")
        subscription_options = {}
        enabled_count = 0
        
        for sub in subscriptions:
            if sub['state'] == 'Enabled':
                enabled_count += 1
                label = f"{sub['display_name']} ({sub['subscription_id']})"
                if sub['subscription_id'] == current_sub_id:
                    label = f"🌟 {label} (Current)"
                subscription_options[label] = sub['subscription_id']
        
        print(f"   📋 Generated {len(subscription_options)} subscription options")
        print(f"   📋 {enabled_count} enabled subscriptions found")
        
        if not subscription_options:
            print("   ❌ NO ENABLED SUBSCRIPTIONS - Deploy tab would return early here!")
            print("   🎯 **ISSUE FOUND**: No enabled subscriptions")
            return False
        else:
            print("   ✅ Subscription options generated successfully")
            print("   📋 Available options:")
            for label in list(subscription_options.keys())[:3]:
                print(f"      - {label}")
        
        # Step 7: Check for any other potential issues
        print("\n7️⃣ Additional Checks...")
        
        # Check if there are any import issues
        try:
            import streamlit as st
            print("   ✅ Streamlit import available")
        except ImportError:
            print("   ❌ Streamlit not available (this is normal for CLI)")
        
        # Check if the method exists
        if hasattr(ui, '_render_deploy_tab'):
            print("   ✅ _render_deploy_tab method exists")
        else:
            print("   ❌ _render_deploy_tab method missing")
            return False
        
        print("\n🎉 ALL CHECKS PASSED!")
        print("   The subscription selection should be visible.")
        print("   If it's still not showing, there might be a UI rendering issue.")
        
        return True
        
    except Exception as e:
        print(f"❌ Deep diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def suggest_debugging_steps():
    """Suggest next debugging steps."""
    print("\n🔧 DEBUGGING STEPS")
    print("=" * 30)
    
    print("Since all backend checks pass, try these UI debugging steps:")
    print()
    print("1️⃣ **Check for Warning Messages**:")
    print("   - Look at the very top of the Deploy tab")
    print("   - Any red error messages or yellow warnings?")
    print("   - Screenshot the entire Deploy tab if possible")
    print()
    print("2️⃣ **Browser Developer Tools**:")
    print("   - Press F12 to open developer tools")
    print("   - Go to Console tab")
    print("   - Look for any JavaScript errors (red text)")
    print("   - Refresh the page and check again")
    print()
    print("3️⃣ **Streamlit App Restart**:")
    print("   - Stop the Streamlit app (Ctrl+C)")
    print("   - Restart with: streamlit run agentic-rag-demo.py")
    print("   - Navigate back to AI Foundry → Deploy tab")
    print()
    print("4️⃣ **Clear Browser Cache**:")
    print("   - Press Ctrl+Shift+R to hard refresh")
    print("   - Or clear browser cache completely")
    print()
    print("5️⃣ **Check Streamlit Version**:")
    print("   - Run: streamlit version")
    print("   - Ensure you're using a recent version")
    print()
    print("6️⃣ **Session State Debug**:")
    print("   - In Configuration tab, try changing a value")
    print("   - Save the configuration")
    print("   - Go back to Deploy tab")
    print("   - Check if subscription selection appears")

def check_method_implementation():
    """Check if the Deploy tab method is properly implemented."""
    print("\n🔍 Method Implementation Check")
    print("=" * 40)
    
    try:
        from app.components.ai_foundry_hub_deployment_ui import AIFoundryHubDeploymentUI
        import inspect
        
        ui = AIFoundryHubDeploymentUI()
        
        # Get the method source
        method = ui._render_deploy_tab
        source = inspect.getsource(method)
        
        print("📋 Checking _render_deploy_tab method...")
        
        # Check for key components
        checks = [
            ("Deployment Target section", "Deployment Target" in source),
            ("Target Subscription section", "Target Subscription" in source),
            ("Subscription selection code", "get_prioritized_subscriptions" in source),
            ("Subscription options generation", "subscription_options" in source),
            ("Selectbox widget", "st.selectbox" in source and "subscription" in source.lower()),
        ]
        
        all_good = True
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"   {status} {check_name}")
            if not result:
                all_good = False
        
        if all_good:
            print("   ✅ All required components found in method")
        else:
            print("   ❌ Some components missing from method")
            
        return all_good
        
    except Exception as e:
        print(f"❌ Method implementation check failed: {e}")
        return False

if __name__ == "__main__":
    print("🔬 Deploy Tab Real-Time Diagnostic")
    print("=" * 50)
    
    # Run deep diagnostic
    backend_ok = deep_diagnose_deploy_tab()
    
    # Check method implementation
    method_ok = check_method_implementation()
    
    if backend_ok and method_ok:
        print("\n🤔 CONCLUSION:")
        print("✅ Backend logic is working correctly")
        print("✅ Method implementation is complete")
        print("❓ Issue is likely in UI rendering or session state")
        suggest_debugging_steps()
    else:
        print("\n🎯 CONCLUSION:")
        print("❌ Found issues in backend or method implementation")
        print("💡 Fix the issues above first")
    
    exit(0 if backend_ok and method_ok else 1)
