#!/usr/bin/env python3
"""
Deploy Tab Debug Patch
======================
A simple debug patch to temporarily add to the Deploy tab to see what's happening.
"""

debug_patch = '''
# TEMPORARY DEBUG CODE - Add this around line 1260 in _render_deploy_tab method
# File: app/components/ai_foundry_hub_deployment_ui.py

# Add this right after the line: config = st.session_state.deployment_config

st.error("🐛 TEMPORARY DEBUG - Remove this after debugging!")
st.write("=" * 50)
st.write("🔍 **Session State Debug Info**:")
st.write(f"📋 Session state keys: {list(st.session_state.keys())}")
st.write(f"📋 deployment_config exists: {'deployment_config' in st.session_state}")

if 'deployment_config' in st.session_state:
    config = st.session_state.deployment_config
    st.write(f"📋 Config type: {type(config)}")
    
    # Validate config
    issues = self.service.validate_deployment_config(config)
    st.write(f"📋 Config validation issues: {issues}")
    st.write(f"📋 Config valid: {len(issues) == 0}")
    
    # Check subscriptions
    try:
        subscriptions = self.service.get_prioritized_subscriptions()
        st.write(f"📋 Subscriptions loaded: {len(subscriptions) if subscriptions else 0}")
        if subscriptions:
            enabled = [s for s in subscriptions if s.get('state') == 'Enabled']
            st.write(f"📋 Enabled subscriptions: {len(enabled)}")
            for i, sub in enumerate(enabled[:2]):  # Show first 2
                st.write(f"   {i+1}. {sub.get('display_name', 'Unknown')} ({sub.get('subscription_id', 'Unknown')[:8]}...)")
    except Exception as e:
        st.write(f"📋 Subscription loading error: {str(e)}")

st.write("=" * 50)
st.error("🐛 END DEBUG - This should appear BEFORE subscription selection UI")

# The rest of your _render_deploy_tab code continues here...
'''

print("🔧 Debug Patch for Deploy Tab")
print("=" * 40)
print()
print("**INSTRUCTIONS:**")
print("1. Open: app/components/ai_foundry_hub_deployment_ui.py")
print("2. Find the _render_deploy_tab method (around line 1247)")
print("3. Look for the line: config = st.session_state.deployment_config")
print("4. Add the debug code below RIGHT AFTER that line")
print("5. Save the file and restart Streamlit")
print("6. Go to the Deploy tab and see what debug info appears")
print()
print("**DEBUG CODE TO ADD:**")
print("-" * 40)
print(debug_patch)
print()
print("**WHAT TO LOOK FOR:**")
print("- The red debug boxes should appear at the top of Deploy tab")
print("- Check if 'Config valid: True'")
print("- Check if 'Enabled subscriptions: 1'") 
print("- If both are True, but you still don't see subscription selection,")
print("  the issue is in the UI rendering logic after the debug code")
print()
print("**REMEMBER:** Remove this debug code after troubleshooting!")

# Also save to file for easy copying
debug_file = "/tmp/deploy_debug_patch.py"
with open(debug_file, 'w') as f:
    f.write(debug_patch)

print(f"\n📁 Debug patch also saved to: {debug_file}")
print("   You can copy from this file if needed.")
