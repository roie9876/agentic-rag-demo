#!/usr/bin/env python3
"""
Quick Agent Config Checker
==========================
Check the configuration of delete1-agent using the function's environment settings.
"""

import os
import requests
import json
from pathlib import Path

def load_function_env():
    """Load environment from function/local.settings.json"""
    function_dir = Path(__file__).parent / "function"
    settings_file = function_dir / "local.settings.json"
    
    if settings_file.exists():
        with open(settings_file, 'r') as f:
            settings = json.load(f)
            return settings.get("Values", {})
    return {}

def get_search_headers(search_api_key):
    """Get authentication headers for Azure Search API calls"""
    if search_api_key:
        return {"api-key": search_api_key, "Content-Type": "application/json"}
    else:
        raise RuntimeError("SEARCH_API_KEY not found in configuration")

def check_agent_config():
    """Check the configuration of delete1-agent"""
    
    # Load environment from function settings
    env_vars = load_function_env()
    
    service_name = env_vars.get("SERVICE_NAME")
    search_api_key = env_vars.get("SEARCH_API_KEY") 
    agent_name = env_vars.get("AGENT_NAME", "delete1-agent")
    api_version = env_vars.get("API_VERSION", "2025-05-01-preview")
    
    print("🔍 Knowledge Agent Configuration Checker")
    print("=" * 60)
    print(f"📋 Environment Configuration:")
    print(f"   🏢 SERVICE_NAME: {service_name or '❌ Not set'}")
    print(f"   🔑 SEARCH_API_KEY: {'✅ Set' if search_api_key else '❌ Not set'}")
    print(f"   🎯 AGENT_NAME: {agent_name}")
    print(f"   📏 MAX_OUTPUT_SIZE (env): {env_vars.get('MAX_OUTPUT_SIZE', '❌ Not set')}")
    print(f"   🔧 API_VERSION: {api_version}")
    print()
    
    if not service_name or not search_api_key:
        print("❌ Required configuration missing!")
        return
    
    # Build the API endpoint to get agent details
    endpoint = f"https://{service_name}.search.windows.net/agents/{agent_name}?api-version={api_version}"
    
    print(f"🔍 Checking agent: {agent_name}")
    print(f"📡 API Endpoint: {endpoint}")
    print("-" * 60)
    
    try:
        headers = get_search_headers(search_api_key)
        
        # Make the API call
        response = requests.get(endpoint, headers=headers, timeout=30)
        
        print(f"📡 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            agent_config = response.json()
            
            print("✅ Agent Configuration Found!")
            print("=" * 60)
            
            # Display key configuration
            print(f"📝 Agent Name: {agent_config.get('name', 'N/A')}")
            print(f"📄 Description: {agent_config.get('description', 'N/A')}")
            
            # Look for max_output_size in various locations
            max_output_size = None
            possible_locations = [
                ("maxOutputSize", agent_config.get("maxOutputSize")),
                ("requestLimits.maxOutputSize", agent_config.get("requestLimits", {}).get("maxOutputSize")),
                ("limits.maxOutputSize", agent_config.get("limits", {}).get("maxOutputSize")),
                ("generationSettings.maxOutputSize", agent_config.get("generationSettings", {}).get("maxOutputSize")),
            ]
            
            print("\n🎛️ Output Size Configuration:")
            found_max_output = False
            for location, value in possible_locations:
                if value is not None:
                    print(f"   ✅ {location}: {value}")
                    max_output_size = value
                    found_max_output = True
                else:
                    print(f"   ❌ {location}: Not found")
            
            if not found_max_output:
                print("   ⚠️ Max output size not explicitly configured in agent")
                print("   💡 Agent will use service defaults or inherit from deployment")
            
            # Show index connections
            index_connections = agent_config.get('indexConnections', [])
            if index_connections:
                print("\n🔗 Index Connections:")
                for i, connection in enumerate(index_connections, 1):
                    print(f"   📚 Connection {i}:")
                    print(f"      📖 Index: {connection.get('indexName', 'N/A')}")
                    print(f"      🎯 Reranker Threshold: {connection.get('rerankerThreshold', 'N/A')}")
                    print(f"      🔝 Top K: {connection.get('topK', 'N/A')}")
                    print(f"      📝 Citation Field: {connection.get('citationFieldName', 'N/A')}")
            
            # Show generation settings
            generation_settings = agent_config.get('generationSettings', {})
            if generation_settings:
                print("\n🤖 Generation Settings:")
                for key, value in generation_settings.items():
                    print(f"   🔧 {key}: {value}")
            
            # Show the comparison with environment
            env_max_output = env_vars.get('MAX_OUTPUT_SIZE')
            if env_max_output and max_output_size:
                print(f"\n📊 Configuration Comparison:")
                print(f"   🏢 Agent max_output_size: {max_output_size}")
                print(f"   💻 Function MAX_OUTPUT_SIZE: {env_max_output}")
                if str(max_output_size) == str(env_max_output):
                    print("   ✅ Values match!")
                else:
                    print("   ⚠️ Values differ - Function env var overrides agent setting")
            
            # Show full config for debugging
            print("\n🐞 Full Agent Configuration:")
            print("=" * 60)
            print(json.dumps(agent_config, indent=2, ensure_ascii=False))
            
        elif response.status_code == 404:
            print(f"❌ Agent '{agent_name}' not found")
            print("\n💡 Try listing all agents:")
            list_agents(service_name, search_api_key, api_version)
            
        elif response.status_code == 403:
            print("❌ Access denied - check your API key permissions")
            
        else:
            print(f"❌ API call failed: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error checking agent config: {e}")

def list_agents(service_name, search_api_key, api_version):
    """List all available agents"""
    endpoint = f"https://{service_name}.search.windows.net/agents?api-version={api_version}"
    
    try:
        headers = get_search_headers(search_api_key)
        response = requests.get(endpoint, headers=headers, timeout=30)
        
        if response.status_code == 200:
            agents_data = response.json()
            agents = agents_data.get('value', [])
            
            if agents:
                print(f"\n📋 Found {len(agents)} agents:")
                for agent in agents:
                    name = agent.get('name', 'Unknown')
                    description = agent.get('description', 'No description')
                    print(f"   🤖 {name} - {description}")
            else:
                print("\n📋 No agents found")
        else:
            print(f"❌ Failed to list agents: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error listing agents: {e}")

if __name__ == "__main__":
    check_agent_config()
