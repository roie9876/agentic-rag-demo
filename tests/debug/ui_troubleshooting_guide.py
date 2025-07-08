#!/usr/bin/env python3
"""
UI State Inspector for Deploy Tab
=================================
This script provides debug commands to inspect and fix UI state issues
that might prevent the subscription selection from appearing.
"""

import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/home/azureuser/agentic-rag-demo')

def print_session_state_debugging_guide():
    """Print a comprehensive debugging guide for UI issues."""
    print("🐛 UI Debugging Guide for Deploy Tab Subscription Selection")
    print("=" * 65)
    print()
    
    print("📋 **STEP 1: Check Configuration Completion**")
    print("-" * 50)
    print("In the Configuration tab, verify ALL sections show green checkmarks:")
    print("   ✅ Basic Settings (location, names)")
    print("   ✅ DNS Zone Configuration (if using private DNS)")
    print("   ✅ Review & Validate (configuration summary)")
    print()
    print("🔧 **Action**: Complete any missing configuration sections.")
    print()
    
    print("📋 **STEP 2: Check for UI Warnings/Errors**")
    print("-" * 50)
    print("Look for these warnings in the Deploy tab:")
    print("   ❌ 'Please configure the deployment first in the Configuration tab'")
    print("   ❌ 'Configuration Issues Found'") 
    print("   ❌ 'Template validation failed'")
    print("   ❌ 'Unable to load subscriptions'")
    print()
    print("🔧 **Action**: If you see any warnings, fix them first.")
    print()
    
    print("📋 **STEP 3: Browser Console Debugging**")
    print("-" * 50)
    print("1. Open browser Developer Tools (F12)")
    print("2. Go to Console tab")
    print("3. Refresh the page")
    print("4. Look for JavaScript errors (red text)")
    print("5. Look for Streamlit connection errors")
    print()
    print("🔧 **Action**: If you see errors, try:")
    print("   - Clear browser cache (Ctrl+Shift+Delete)")
    print("   - Hard refresh (Ctrl+F5)")
    print("   - Try incognito/private mode")
    print("   - Try a different browser")
    print()
    
    print("📋 **STEP 4: Streamlit State Reset**")
    print("-" * 50)
    print("1. In the Streamlit app, look for the menu (≡) in top-right")
    print("2. Click 'Rerun' or 'Clear cache and rerun'")
    print("3. If that doesn't work, restart the Streamlit server:")
    print("   - Press Ctrl+C in the terminal running Streamlit")
    print("   - Run the start command again")
    print()
    
    print("📋 **STEP 5: Check Streamlit Server Logs**")
    print("-" * 50)
    print("In the terminal where Streamlit is running, look for:")
    print("   ❌ Error messages")
    print("   ⚠️  Warning messages") 
    print("   🔄 Session state errors")
    print("   🌐 Connection errors")
    print()
    
    print("📋 **STEP 6: Advanced Debugging**")
    print("-" * 50)
    print("If the issue persists, try these advanced steps:")
    print()
    print("🔧 **Manual State Reset**:")
    print("   1. In Configuration tab, change any setting")
    print("   2. Change it back to original value")
    print("   3. Click 'Validate Configuration' again")
    print("   4. Go back to Deploy tab")
    print()
    print("🔧 **Session State Investigation**:")
    print("   Add this debug code to the app temporarily:")
    print("   ```python")
    print("   st.write('Session state keys:', list(st.session_state.keys()))")
    print("   if 'deployment_config' in st.session_state:")
    print("       st.write('Config exists:', type(st.session_state.deployment_config))")
    print("   ```")
    print()
    
    print("📋 **STEP 7: Expected UI Flow**")
    print("-" * 50)
    print("When working correctly, the Deploy tab should show:")
    print("   ✅ 'Deploy AI Foundry Account' header")
    print("   ✅ 'Deployment Target' section") 
    print("   ✅ 'Target Subscription' section with dropdown")
    print("   ✅ Subscription selection dropdown with your subscription")
    print("   ✅ 'Target Resource Group' section")
    print("   ✅ Resource group dropdown")
    print("   ✅ Deploy button at the bottom")
    print()
    
    print("📋 **STEP 8: What You Should See**")
    print("-" * 50)
    print("The subscription dropdown should contain:")
    print("   🌟 ME-MngEnvMCAP623661-robenhai-1 (7aa77d2e...) (Current)")
    print()
    print("If you see 'No enabled subscriptions found' or similar:")
    print("   1. Check Azure CLI login: `az account show`")
    print("   2. Refresh subscriptions in the app")
    print("   3. Restart Streamlit")
    print()
    
    print("🎯 **QUICK CHECKLIST**")
    print("-" * 50)
    print("□ Configuration tab is complete (all green checkmarks)")
    print("□ No red error messages in Deploy tab")
    print("□ No JavaScript errors in browser console") 
    print("□ Streamlit server is running without errors")
    print("□ Browser cache is cleared")
    print("□ Tried refreshing/rerunning the app")
    print()
    
    print("❓ **Still Not Working?**")
    print("-" * 50)
    print("If you've tried all steps above and still don't see the subscription")
    print("selection, this indicates a deeper UI framework issue.")
    print()
    print("Next steps:")
    print("   1. Take a screenshot of what you DO see in the Deploy tab")
    print("   2. Copy any error messages from browser console")
    print("   3. Copy any error messages from Streamlit logs")
    print("   4. Note which browser and version you're using")
    print()

def create_debug_snippet():
    """Create a debug code snippet to add to the app."""
    snippet = '''
# DEBUG: Add this to the Deploy tab in ai_foundry_hub_deployment_ui.py
# Around line 1250 in _render_deploy_tab method

st.write("🐛 DEBUG INFO:")
st.write(f"session_state keys: {list(st.session_state.keys())}")
st.write(f"deployment_config exists: {'deployment_config' in st.session_state}")

if 'deployment_config' in st.session_state:
    config = st.session_state.deployment_config
    st.write(f"Config type: {type(config)}")
    
    # Validate config
    issues = self.service.validate_deployment_config(config)
    st.write(f"Config issues: {issues}")
    
    # Check subscriptions
    try:
        subscriptions = self.service.get_prioritized_subscriptions()
        st.write(f"Subscriptions loaded: {len(subscriptions) if subscriptions else 0}")
        if subscriptions:
            enabled = [s for s in subscriptions if s.get('state') == 'Enabled']
            st.write(f"Enabled subscriptions: {len(enabled)}")
    except Exception as e:
        st.write(f"Subscription error: {str(e)}")

st.write("🐛 END DEBUG")
'''
    
    debug_file = "/tmp/debug_snippet.py"
    with open(debug_file, 'w') as f:
        f.write(snippet)
    
    print(f"📝 Debug snippet saved to: {debug_file}")
    print()
    print("To use this snippet:")
    print("1. Copy the code from the file above")
    print("2. Add it to the _render_deploy_tab method in ai_foundry_hub_deployment_ui.py") 
    print("3. Restart Streamlit")
    print("4. Check what debug info appears in the Deploy tab")
    print()

def main():
    """Main function."""
    print("🔍 UI State Inspector for Deploy Tab")
    print("=" * 40)
    print()
    
    print_session_state_debugging_guide()
    print()
    create_debug_snippet()
    
    print("✅ Debugging guide complete!")
    print()
    print("💡 **TIP**: Start with Step 1 (check configuration completion)")
    print("    and work through the steps systematically.")

if __name__ == "__main__":
    main()
