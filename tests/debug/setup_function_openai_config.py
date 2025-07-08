#!/usr/bin/env python3
"""
Script to set Azure Function App environment variables for OpenAI integration.
Run this to configure the missing OpenAI settings in your Function App.
"""

import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.web import WebSiteManagementClient

def set_function_app_settings():
    """Set the missing environment variables in Azure Function App."""
    
    # You need to set these values
    subscription_id = "YOUR_SUBSCRIPTION_ID"
    resource_group = "YOUR_RESOURCE_GROUP"
    function_app_name = "YOUR_FUNCTION_APP_NAME"
    
    # OpenAI configuration based on your .env file
    settings_to_add = {
        # Core OpenAI settings
        "OPENAI_ENDPOINT": "https://private-openai-agentic.openai.azure.com/",
        "OPENAI_DEPLOYMENT": "gpt-4.1",
        "AZURE_OPENAI_ENDPOINT": "https://private-openai-agentic.openai.azure.com/",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4.1",
        "AZURE_OPENAI_API_VERSION": "2025-01-01-preview",
        
        # Missing API_VERSION for agent calls
        "API_VERSION": "2025-05-01-preview",
        
        # Optional: Add these if you want API key fallback (for development)
        # "OPENAI_KEY": "your-openai-key-here",
        # "AZURE_OPENAI_KEY": "your-openai-key-here",
    }
    
    print("🔧 Setting Azure Function App environment variables...")
    print(f"Subscription: {subscription_id}")
    print(f"Resource Group: {resource_group}")
    print(f"Function App: {function_app_name}")
    print()
    
    try:
        # Connect to Azure
        credential = DefaultAzureCredential()
        web_client = WebSiteManagementClient(credential, subscription_id)
        
        # Get current settings
        print("📥 Getting current Function App settings...")
        current_settings = web_client.web_apps.list_application_settings(
            resource_group_name=resource_group,
            name=function_app_name
        )
        
        # Merge with new settings
        updated_settings = current_settings.properties.copy()
        updated_settings.update(settings_to_add)
        
        # Update Function App settings
        print("📤 Updating Function App settings...")
        web_client.web_apps.update_application_settings(
            resource_group_name=resource_group,
            name=function_app_name,
            app_settings={"properties": updated_settings}
        )
        
        print("✅ Successfully updated Function App settings!")
        print("\n🔧 Added/Updated variables:")
        for key, value in settings_to_add.items():
            # Don't log full keys
            display_value = f"[SET: {len(value)} chars]" if 'KEY' in key else value
            print(f"  {key}: {display_value}")
        
        print(f"\n🔄 Restart your Function App '{function_app_name}' for changes to take effect.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Function App settings: {e}")
        return False

def show_manual_steps():
    """Show manual steps to add environment variables."""
    print("\n📋 MANUAL STEPS (Alternative to running this script):")
    print("=" * 60)
    print("1. Go to Azure Portal → Function Apps → Your Function App")
    print("2. Navigate to Settings → Environment variables")
    print("3. Add these Application Settings:")
    print()
    
    settings = {
        "OPENAI_ENDPOINT": "https://private-openai-agentic.openai.azure.com/",
        "OPENAI_DEPLOYMENT": "gpt-4.1",
        "AZURE_OPENAI_ENDPOINT": "https://private-openai-agentic.openai.azure.com/",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4.1",
        "AZURE_OPENAI_API_VERSION": "2025-01-01-preview",
        "API_VERSION": "2025-05-01-preview"
    }
    
    for key, value in settings.items():
        print(f"   {key} = {value}")
    
    print("\n4. Click 'Apply' to save the settings")
    print("5. Restart the Function App")
    print("6. Test the function again")

if __name__ == "__main__":
    print("🔧 Azure Function OpenAI Configuration Setup")
    print("=" * 50)
    
    # Show what needs to be done
    show_manual_steps()
    
    print("\n" + "=" * 60)
    print("To run this script automatically:")
    print("1. Update the subscription_id, resource_group, and function_app_name variables above")
    print("2. Ensure you have Azure CLI logged in or managed identity configured")
    print("3. Run: python3 setup_function_openai_config.py")
