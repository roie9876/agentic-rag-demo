# AI Foundry Streamlit App Restart Guide

## Issue Identified ✅

The AI Foundry service has been successfully updated with MSI-compatible project creation, but the Streamlit app is still showing the old error because it's using cached service instances.

## Backend Status ✅

- ✅ **AIFoundryService**: Updated with MSI-compatible `create_project` method
- ✅ **Account Projects**: Uses Azure Management API with `SystemAssigned` identity
- ✅ **Hub Projects**: Uses Azure Management API 
- ✅ **Test Scripts**: All passing with expected behavior

## Solution: Restart Streamlit App

### Method 1: Restart from Terminal
```bash
# Stop the current Streamlit app (Ctrl+C in the terminal where it's running)
# Then restart it:
cd /home/azureuser/agentic-rag-demo
streamlit run agentic-rag-demo.py
```

### Method 2: Use the Refresh Button in UI
1. Go to the AI Foundry Agent tab
2. Click the **🔄 Refresh Services** button (added to the enhanced tab)
3. This will clear all cached service instances and reload them

### Method 3: Clear Session State Manually
```python
# In the Streamlit app, you can run this in the Python console:
import streamlit as st
keys_to_clear = [
    'ai_foundry_discovery_service',
    'ai_foundry_rbac_service', 
    'ai_foundry_service',
    'ai_foundry_deployment_service'
]
for key in keys_to_clear:
    if key in st.session_state:
        del st.session_state[key]
```

## Expected Behavior After Restart

When you restart the Streamlit app and try to create a project, you should see:

✅ **Success**: Project creation works without MSI validation errors
✅ **Better Errors**: If there are permission issues, you'll get proper Azure ARM errors (like `SubscriptionNotFound`) instead of the MSI validation error

## Debug Information

The enhanced AI Foundry tab now includes a debug section that shows:
- Service status and types
- Whether the updated MSI-compatible code is loaded
- Method signatures and availability

## Files Updated

- ✅ `services/ai_foundry_service.py` - MSI-compatible project creation
- ✅ `app/tabs/enhanced_ai_foundry_tab.py` - Added refresh button and debug info
- ✅ `scripts/test_service_import.py` - Validates the updated code is working

## Next Steps

1. **Restart your Streamlit app** using Method 1 above
2. **Test project creation** in the AI Foundry Agent tab
3. **Use the debug section** to verify the services are using updated code
4. **Report any new errors** - they should be proper Azure ARM errors, not MSI validation errors

The MSI validation error you saw was from the old cached code. The new code properly handles MSI authentication and should work correctly.
