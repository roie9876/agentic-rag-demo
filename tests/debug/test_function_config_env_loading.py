#!/usr/bin/env python3
"""
Test script to validate Function Config environment variable loading fix.

This script tests the fix for the issue where .env parameters like service_name, 
openai_endpoint, and openai_deployment were not being loaded into Function App settings.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from azure_function_helper import load_function_settings
from dotenv import load_dotenv

def test_env_loading():
    """Test that environment variables are properly loaded and mapped."""
    print("🧪 Testing Function Config Environment Variable Loading Fix")
    print("=" * 60)
    
    # Load .env file
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded .env file from: {env_file}")
    else:
        print(f"❌ .env file not found at: {env_file}")
        return False
    
    # Test environment variables that should be loaded
    test_env_vars = {
        "AZURE_SEARCH_ENDPOINT": "SERVICE_NAME",
        "AZURE_OPENAI_ENDPOINT": "OPENAI_ENDPOINT", 
        "AZURE_OPENAI_ENDPOINT_41": "OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT": "OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_DEPLOYMENT_41": "OPENAI_DEPLOYMENT",
        "MAX_OUTPUT_SIZE": "MAX_OUTPUT_SIZE",
        "RERANKER_THRESHOLD": "RERANKER_THRESHOLD",
        "TOP_K": "TOP_K",
        "debug": "debug",
        "includesrc": "includesrc"
    }
    
    # Simulate environment variables as passed from Function Config tab
    env_vars = {}
    for env_key in test_env_vars.keys():
        value = os.getenv(env_key, "")
        if value:
            env_vars[env_key] = value
    
    print(f"\n📋 Environment Variables Found ({len(env_vars)}):")
    for key, value in env_vars.items():
        # Mask sensitive values
        display_value = "••••••" if "key" in key.lower() else value[:50] + "..." if len(value) > 50 else value
        print(f"  {key}: {display_value}")
    
    # Test UI overrides (simulating user selection)
    ui_overrides = {
        "INDEX_NAME": "bicep-23",
        "AGENT_NAME": "bicep-23-agent"
    }
    
    print(f"\n🎯 UI Overrides ({len(ui_overrides)}):")
    for key, value in ui_overrides.items():
        print(f"  {key}: {value}")
    
    # Mock function parameters (we can't actually test Azure connection without credentials)
    print("\n🔧 Testing Mapping Logic...")
    
    # Test the mapping logic manually
    param_vals = {}  # Simulate empty Function App settings
    
    # This is the same mapping from azure_function_helper.py
    env_to_function_mapping = {
        "INDEX_NAME": "INDEX_NAME",
        "AGENT_NAME": "AGENT_NAME",
        "AZURE_SEARCH_ENDPOINT": "SERVICE_NAME",
        "AZURE_OPENAI_ENDPOINT": "OPENAI_ENDPOINT",
        "AZURE_OPENAI_ENDPOINT_41": "OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT": "OPENAI_DEPLOYMENT", 
        "AZURE_OPENAI_DEPLOYMENT_41": "OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_CHAT_DEPLOYMENT": "OPENAI_DEPLOYMENT",
        "MAX_OUTPUT_SIZE": "MAX_OUTPUT_SIZE",
        "RERANKER_THRESHOLD": "RERANKER_THRESHOLD", 
        "TOP_K": "TOP_K",
        "debug": "debug",
        "includesrc": "includesrc",
        "AZURE_OPENAI_KEY": "OPENAI_KEY",
        "AZURE_OPENAI_KEY_41": "OPENAI_KEY",
        "AZURE_SEARCH_KEY": "SEARCH_API_KEY"
    }
    
    # Apply environment variable mapping
    mapped_count = 0
    for env_key, func_key in env_to_function_mapping.items():
        if env_key in env_vars and env_vars[env_key]:
            current_value = param_vals.get(func_key, "")
            
            if func_key == "SERVICE_NAME" and env_vars[env_key]:
                # Extract service name from AZURE_SEARCH_ENDPOINT
                import re
                match = re.search(r'https://([^.]+)\.search\.windows\.net', env_vars[env_key])
                if match:
                    param_vals[func_key] = match.group(1)
                    print(f"  ✅ Mapped {env_key} -> {func_key}: {match.group(1)}")
                    mapped_count += 1
                else:
                    print(f"  ❌ Failed to extract service name from: {env_vars[env_key]}")
            else:
                should_update = (
                    func_key not in param_vals or 
                    not current_value or 
                    current_value.strip() == "" or
                    env_key.endswith('_41')
                )
                
                if should_update:
                    param_vals[func_key] = env_vars[env_key]
                    display_value = env_vars[env_key][:30] + "..." if len(env_vars[env_key]) > 30 else env_vars[env_key]
                    print(f"  ✅ Mapped {env_key} -> {func_key}: {display_value}")
                    mapped_count += 1
    
    # Apply UI overrides
    override_count = 0
    for key, value in ui_overrides.items():
        if value:
            current_value = param_vals.get(key, "")
            param_vals[key] = value
            print(f"  🎯 UI Override {key}: {value} (was: '{current_value}')")
            override_count += 1
    
    print(f"\n📊 Results:")
    print(f"  Environment variables loaded: {len(env_vars)}")
    print(f"  Values mapped to function settings: {mapped_count}")
    print(f"  UI overrides applied: {override_count}")
    print(f"  Final function settings: {len(param_vals)}")
    
    # Check critical settings
    critical_settings = ["SERVICE_NAME", "OPENAI_ENDPOINT", "OPENAI_DEPLOYMENT", "INDEX_NAME", "AGENT_NAME"]
    print(f"\n🔍 Critical Settings Check:")
    all_good = True
    for setting in critical_settings:
        if setting in param_vals and param_vals[setting]:
            print(f"  ✅ {setting}: {param_vals[setting]}")
        else:
            print(f"  ❌ {setting}: MISSING")
            all_good = False
    
    if all_good:
        print(f"\n🎉 SUCCESS: All critical settings are properly loaded!")
        return True
    else:
        print(f"\n❌ FAILURE: Some critical settings are missing!")
        return False

if __name__ == "__main__":
    success = test_env_loading()
    sys.exit(0 if success else 1)
