#!/usr/bin/env python3
"""
Update Knowledge Agent Configuration
==================================
Script to update the delete3-agent to use proper authentication for Azure OpenAI
"""

import json
import os
import requests
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

def update_agent_config():
    """Update the knowledge agent configuration to use managed identity"""
    
    service_name = "ai-serach-demo-eastus"
    agent_name = "delete3-agent"
    api_version = "2025-05-01-preview"
    
    endpoint = f"https://{service_name}.search.windows.net"
    
    # Get authentication headers
    try:
        token = DefaultAzureCredential().get_token("https://search.azure.com/.default").token
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    except Exception as e:
        print(f"❌ Failed to get authentication token: {e}")
        return
    
    # Get current agent configuration
    agent_url = f"{endpoint}/agents/{agent_name}?api-version={api_version}"
    
    print(f"🔍 Getting current agent configuration...")
    try:
        response = requests.get(agent_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Failed to get agent config: {response.status_code} - {response.text}")
            return
            
        current_config = response.json()
        print(f"✅ Current config retrieved")
        
    except Exception as e:
        print(f"❌ Error getting agent config: {e}")
        return
    
    # Update the configuration to use system-assigned managed identity
    updated_config = current_config.copy()
    
    # Update the Azure OpenAI model configuration
    if "models" in updated_config and len(updated_config["models"]) > 0:
        model = updated_config["models"][0]
        if "azureOpenAIParameters" in model:
            # Try a simpler approach - just remove the apiKey and let it use default auth
            model["azureOpenAIParameters"]["apiKey"] = None
            # Don't set authIdentity for now, let it use default
            
            print("🔧 Updated model configuration:")
            print(f"   Resource URI: {model['azureOpenAIParameters']['resourceUri']}")
            print(f"   Deployment ID: {model['azureOpenAIParameters']['deploymentId']}")
            print(f"   Auth Identity: default (managed identity)")
    
    # Remove read-only fields before updating
    fields_to_remove = ["@odata.context", "@odata.etag"]
    for field in fields_to_remove:
        updated_config.pop(field, None)
    
    # Update the agent
    print(f"🚀 Updating agent configuration...")
    try:
        update_response = requests.put(
            agent_url, 
            headers=headers, 
            json=updated_config,
            timeout=30
        )
        
        if update_response.status_code in [200, 201]:
            print(f"✅ Agent configuration updated successfully!")
            print(f"🎉 The agent should now be able to access Azure OpenAI with managed identity")
        else:
            print(f"❌ Failed to update agent: {update_response.status_code}")
            print(f"Response: {update_response.text}")
            
    except Exception as e:
        print(f"❌ Error updating agent config: {e}")

if __name__ == "__main__":
    print("🔧 KNOWLEDGE AGENT CONFIGURATION UPDATER")
    print("=" * 80)
    update_agent_config()
