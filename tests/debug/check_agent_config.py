#!/usr/bin/env python3
"""
Check Knowledge Agent Configuration
==================================
Script to inspect the current configuration of a knowledge agent,
including max_output_size and other parameters.
"""

import json
import os
import requests
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

def get_search_headers() -> dict:
    """Get authentication headers for Azure Search API calls"""
    search_api_key = os.getenv("SEARCH_API_KEY") or os.getenv("AZURE_SEARCH_KEY")
    
    if search_api_key:
        return {"api-key": search_api_key, "Content-Type": "application/json"}
    
    # Try to get bearer token
    try:
        token = DefaultAzureCredential().get_token("https://search.azure.com/.default").token
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    except Exception:
        raise RuntimeError("No Search authentication available. Set SEARCH_API_KEY or use managed identity.")

def check_agent_configuration(service_name: str, agent_name: str):
    """
    Check the configuration of a knowledge agent
    """
    api_version = "2025-05-01-preview"
    
    # Build the API endpoint to get agent details
    endpoint = f"https://{service_name}.search.windows.net/agents/{agent_name}?api-version={api_version}"
    
    headers = get_search_headers()
    
    print(f"🔍 Checking agent configuration for: {agent_name}")
    print(f"📡 Endpoint: {endpoint}")
    print("-" * 80)
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=30)
        
        print(f"📊 HTTP Status: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        print("-" * 80)
        
        if response.status_code == 200:
            agent_config = response.json()
            print("✅ Agent Configuration Retrieved Successfully!")
            print(json.dumps(agent_config, indent=2, ensure_ascii=False))
            
            # Extract key parameters
            print("\n" + "="*80)
            print("🔧 KEY CONFIGURATION PARAMETERS:")
            print("="*80)
            
            # Check for max_output_size in various possible locations
            max_output_locations = [
                "maxOutputSize",
                "max_output_size", 
                "requestLimits.maxOutputSize",
                "limits.maxOutputSize",
                "configuration.maxOutputSize"
            ]
            
            max_output_found = False
            for location in max_output_locations:
                value = get_nested_value(agent_config, location)
                if value is not None:
                    print(f"📏 Max Output Size ({location}): {value}")
                    max_output_found = True
            
            if not max_output_found:
                print("⚠️  Max Output Size: Not found in agent configuration")
                print("💡 This parameter might be set at the service level or use default values")
            
            # Other important parameters
            important_params = [
                ("description", "📝 Description"),
                ("indexName", "📚 Index Name"), 
                ("systemMessage", "💬 System Message"),
                ("topK", "🔢 Top K Results"),
                ("rerankerThreshold", "📊 Reranker Threshold"),
                ("temperature", "🌡️  Temperature"),
                ("maxTokens", "🎯 Max Tokens"),
                ("deploymentName", "🚀 Deployment Name"),
                ("apiVersion", "🏷️  API Version")
            ]
            
            for param, label in important_params:
                value = get_nested_value(agent_config, param)
                if value is not None:
                    print(f"{label}: {value}")
            
            return agent_config
            
        elif response.status_code == 404:
            print(f"❌ Agent '{agent_name}' not found!")
            print("💡 Available agents:")
            list_all_agents(service_name)
            return None
            
        elif response.status_code == 403:
            print("❌ Access denied! Check your authentication and permissions.")
            print("💡 Make sure you have 'Search Service Contributor' role or API key access.")
            return None
            
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking agent configuration: {e}")
        return None

def get_nested_value(data, path):
    """Get value from nested dictionary using dot notation"""
    keys = path.split('.')
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current

def list_all_agents(service_name: str):
    """List all available agents in the service"""
    api_version = "2025-05-01-preview"
    endpoint = f"https://{service_name}.search.windows.net/agents?api-version={api_version}"
    
    headers = get_search_headers()
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=30)
        
        if response.status_code == 200:
            agents_data = response.json()
            agents = agents_data.get("value", [])
            
            if agents:
                print(f"📋 Found {len(agents)} agents:")
                for i, agent in enumerate(agents, 1):
                    name = agent.get("name", "Unknown")
                    description = agent.get("description", "No description")
                    print(f"  {i}. {name} - {description}")
            else:
                print("📭 No agents found in this service")
        else:
            print(f"❌ Failed to list agents: HTTP {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error listing agents: {e}")

def check_index_configuration(service_name: str, index_name: str):
    """Check the configuration of the associated index"""
    api_version = "2021-04-30-Preview"  # Use stable API for index details
    endpoint = f"https://{service_name}.search.windows.net/indexes/{index_name}?api-version={api_version}"
    
    headers = get_search_headers()
    
    print(f"\n🔍 Checking index configuration for: {index_name}")
    print("-" * 80)
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=30)
        
        if response.status_code == 200:
            index_config = response.json()
            print("✅ Index Configuration Retrieved!")
            
            # Extract key index information
            print(f"📚 Index Name: {index_config.get('name')}")
            print(f"📊 Fields Count: {len(index_config.get('fields', []))}")
            
            # Check for semantic configuration
            semantic_config = index_config.get("semanticConfiguration")
            if semantic_config:
                print(f"🧠 Semantic Configuration: Available")
            else:
                print(f"🧠 Semantic Configuration: Not configured")
            
            # List key fields
            fields = index_config.get("fields", [])
            key_fields = ["content", "source_file", "url", "page_number", "doc_key"]
            
            print("\n📋 Key Fields Status:")
            for field_name in key_fields:
                field_found = any(f.get("name") == field_name for f in fields)
                status = "✅" if field_found else "❌"
                print(f"  {status} {field_name}")
            
            return index_config
        else:
            print(f"❌ Failed to get index configuration: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking index configuration: {e}")
        return None

def main():
    """Main function to check agent and index configuration"""
    
    # Get configuration from environment
    service_name = os.getenv("SERVICE_NAME")
    agent_name = os.getenv("AGENT_NAME") 
    index_name = os.getenv("INDEX_NAME")
    
    if not service_name:
        print("❌ SERVICE_NAME environment variable not set!")
        return
    
    if not agent_name:
        print("❌ AGENT_NAME environment variable not set!")
        return
    
    print("🔍 KNOWLEDGE AGENT CONFIGURATION CHECKER")
    print("="*80)
    print(f"🏢 Service: {service_name}")
    print(f"🤖 Agent: {agent_name}")
    if index_name:
        print(f"📚 Index: {index_name}")
    print("="*80)
    
    # Check agent configuration
    agent_config = check_agent_configuration(service_name, agent_name)
    
    # Check index configuration if specified
    if index_name:
        index_config = check_index_configuration(service_name, index_name)
    
    # Summary
    print("\n" + "="*80)
    print("📋 CONFIGURATION SUMMARY")
    print("="*80)
    
    if agent_config:
        print("✅ Agent configuration retrieved successfully")
        
        # Check if max_output_size is configured
        max_output_found = False
        for location in ["maxOutputSize", "max_output_size", "requestLimits.maxOutputSize"]:
            if get_nested_value(agent_config, location) is not None:
                max_output_found = True
                break
        
        if max_output_found:
            print("✅ Max output size configuration found")
        else:
            print("⚠️  Max output size not explicitly configured (using defaults)")
    else:
        print("❌ Failed to retrieve agent configuration")
    
    print("\n💡 To modify agent configuration, you can:")
    print("   1. Use Azure Portal > AI Search > Agents")
    print("   2. Use REST API to update agent configuration")
    print("   3. Use Azure AI Studio to modify agent settings")

if __name__ == "__main__":
    main()
