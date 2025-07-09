# Function Config Environment Variable Loading Fix

## Issue Description

When using the Function Config tab in the Agentic RAG Demo, environment variables from the `.env` file were not being properly loaded into the Function App settings. Specifically:

- **SERVICE_NAME** (extracted from AZURE_SEARCH_ENDPOINT) was not appearing
- **OPENAI_ENDPOINT** was not being loaded from AZURE_OPENAI_ENDPOINT
- **OPENAI_DEPLOYMENT** was not being loaded from AZURE_OPENAI_DEPLOYMENT

## Root Cause

The issue was caused by **double processing** of environment variables:

1. **Function Config Tab** (`app/tabs/function_config_tab.py`) was pre-processing environment variables and converting them from `.env` keys to Function App keys
2. **Azure Function Helper** (`azure_function_helper.py`) was expecting raw `.env` keys and trying to do the mapping again

This created a mismatch where:
- Function Config: `AZURE_SEARCH_ENDPOINT` → `SERVICE_NAME` 
- Azure Function Helper: Looking for `AZURE_SEARCH_ENDPOINT` but finding `SERVICE_NAME`

## Solution

### 1. **Fixed Function Config Tab** (`app/tabs/function_config_tab.py`)

**Before:**
```python
# Was pre-processing and mapping env vars
local_to_function_mapping = {
    "AZURE_SEARCH_ENDPOINT": "SERVICE_NAME",
    "AZURE_OPENAI_ENDPOINT": "OPENAI_ENDPOINT",
    # ... etc
}

env_vars = {}
for local_key, function_key in local_to_function_mapping.items():
    # Complex pre-processing logic
```

**After:**
```python
# Now passes raw environment variables
raw_env_keys = [
    "AZURE_SEARCH_ENDPOINT",
    "AZURE_OPENAI_ENDPOINT", 
    "AZURE_OPENAI_ENDPOINT_41",
    # ... etc
]

env_vars = {}
for key in raw_env_keys:
    value = os.getenv(key, "")
    if value:
        env_vars[key] = value
```

### 2. **Enhanced Azure Function Helper** (`azure_function_helper.py`)

**Improved mapping logic:**
```python
# Apply .env values to function settings
for env_key, func_key in env_to_function_mapping.items():
    if env_key in env_vars and env_vars[env_key]:
        current_value = param_vals.get(func_key, "")
        
        if func_key == "SERVICE_NAME" and env_vars[env_key]:
            # Extract service name from AZURE_SEARCH_ENDPOINT
            match = re.search(r'https://([^.]+)\.search\.windows\.net', env_vars[env_key])
            if match:
                param_vals[func_key] = match.group(1)
                print(f"DEBUG: Mapped {env_key} -> {func_key}: {match.group(1)}")
        else:
            # Improved update logic with better debugging
            should_update = (
                func_key not in param_vals or 
                not current_value or 
                current_value.strip() == "" or
                env_key.endswith('_41')
            )
            
            if should_update:
                param_vals[func_key] = env_vars[env_key]
                print(f"DEBUG: Mapped {env_key} -> {func_key}: {env_vars[env_key][:20]}...")
            else:
                print(f"DEBUG: Skipped {env_key} -> {func_key}: Function App has existing value")
```

### 3. **Added UI Overrides** (Previous Fix)

UI selections now always override Function App settings:
```python
# Apply UI overrides - these ALWAYS take precedence
for key, value in ui_overrides.items():
    if value:
        current_value = param_vals.get(key, "")
        param_vals[key] = value
        print(f"DEBUG: UI Override: {key}: {value[:20]}... (was: '{current_value}')")
```

## Files Modified

1. **`app/tabs/function_config_tab.py`**
   - Removed duplicate environment variable processing
   - Now passes raw `.env` keys to azure_function_helper.py
   - Added debug logging

2. **`azure_function_helper.py`**
   - Enhanced mapping logic with better error handling
   - Improved debug output
   - Added support for UI overrides (INDEX_NAME, AGENT_NAME)

## Test Results

Created test script: `tests/debug/test_function_config_env_loading.py`

**Test Results:**
```
✅ Environment variables loaded: 10
✅ Values mapped to function settings: 10
✅ UI overrides applied: 2
✅ Final function settings: 10

🔍 Critical Settings Check:
✅ SERVICE_NAME: private-ai-search
✅ OPENAI_ENDPOINT: https://private-openai-agentic.openai.azure.com/
✅ OPENAI_DEPLOYMENT: gpt-4.1
✅ INDEX_NAME: bicep-23
✅ AGENT_NAME: bicep-23-agent
```

## Expected Behavior After Fix

When you:
1. Select an index in the Function Config UI (e.g., "bicep-23")
2. Click "🔄 Load settings"

The system will now:
1. ✅ Load all environment variables from `.env` file
2. ✅ Map them correctly to Function App setting names
3. ✅ Apply UI selections (INDEX_NAME, AGENT_NAME) as overrides
4. ✅ Show all values in the Function App Settings table
5. ✅ Display debug information showing what was mapped

## Debugging

Enable debug output by checking the Streamlit app logs. You should see:
```
DEBUG Function Config Tab: Loaded 10 environment variables:
DEBUG: Mapped AZURE_SEARCH_ENDPOINT -> SERVICE_NAME: private-ai-search
DEBUG: Mapped AZURE_OPENAI_ENDPOINT -> OPENAI_ENDPOINT: https://private-openai-agentic...
DEBUG: UI Override: INDEX_NAME: bicep-23 (was: '')
```

## Verification

1. **Run the test script:**
   ```bash
   python3 tests/debug/test_function_config_env_loading.py
   ```

2. **Test in Streamlit:**
   - Go to Function Config tab
   - Select an index 
   - Click "Load settings"
   - Verify all critical values appear in the table

## Related Issues Fixed

- ✅ Environment variables not loading from `.env` file
- ✅ SERVICE_NAME not being extracted from AZURE_SEARCH_ENDPOINT
- ✅ OPENAI_ENDPOINT and OPENAI_DEPLOYMENT not appearing
- ✅ UI selections being overridden by Function App existing values
- ✅ INDEX_NAME and AGENT_NAME not taking precedence from UI selection
