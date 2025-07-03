#!/usr/bin/env python3
"""
Check AI Foundry Project Details
This script connects to the AI Foundry endpoint and retrieves project information
to verify the correct project name and configuration.
"""

import os
import requests
import json
from typing import Dict, Any, Optional
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

def load_environment():
    """Load environment variables from .env file."""
    load_dotenv()
    return {
        'project_endpoint': os.getenv('PROJECT_ENDPOINT'),
        'api_version': os.getenv('API_VERSION', '2025-05-01-preview'),
        'azure_openai_endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
        'azure_openai_deployment': os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4.1'),
    }

def get_azure_token() -> str:
    """Get Azure access token using DefaultAzureCredential for AI Foundry Account."""
    try:
        credential = DefaultAzureCredential()
        # Try multiple scopes for AI Foundry Account
        scopes_to_try = [
            "https://cognitiveservices.azure.com/.default",
            "https://ml.azure.com/.default",
            "https://management.azure.com/.default"
        ]
        
        for scope in scopes_to_try:
            try:
                print(f"🔑 Trying token scope: {scope}")
                token = credential.get_token(scope)
                print(f"✅ Successfully got token with scope: {scope}")
                return token.token
            except Exception as scope_error:
                print(f"❌ Failed with scope {scope}: {scope_error}")
                continue
        
        raise Exception("All token scopes failed")
        
    except Exception as e:
        print(f"❌ Failed to get Azure token: {e}")
        return None

def parse_project_endpoint(endpoint: str) -> Dict[str, str]:
    """Parse the project endpoint to extract components."""
    try:
        # Example: https://aiagenticservicesfgtt.services.ai.azure.com/api/projects/agentic-rag
        parts = endpoint.split('/')
        
        # Extract the foundry hostname
        foundry_hostname = parts[2]  # aiagenticservicesfgtt.services.ai.azure.com
        
        # Extract project name from the last part
        project_name = parts[-1]  # agentic-rag
        
        # Extract foundry name (first part of hostname)
        foundry_name = foundry_hostname.split('.')[0]  # aiagenticservicesfgtt
        
        return {
            'foundry_hostname': foundry_hostname,
            'foundry_name': foundry_name,
            'project_name': project_name,
            'base_url': f"https://{foundry_hostname}",
            'projects_api': f"https://{foundry_hostname}/api/projects"
        }
    except Exception as e:
        print(f"❌ Error parsing endpoint: {e}")
        return {}

def check_project_details(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Check project details using the AI Foundry API."""
    if not config['project_endpoint']:
        print("❌ PROJECT_ENDPOINT not found in environment variables")
        return None
    
    # Parse the endpoint
    parsed = parse_project_endpoint(config['project_endpoint'])
    if not parsed:
        return None
    
    print(f"🔍 Checking project at: {config['project_endpoint']}")
    print(f"📍 Foundry: {parsed['foundry_name']}")
    print(f"📋 Project Name (from URL): {parsed['project_name']}")
    print()
    
    # Get access token
    token = get_azure_token()
    if not token:
        return None
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        # Method 1: Try to get specific project details
        print("🔸 Method 1: Getting specific project details...")
        response = requests.get(
            config['project_endpoint'],
            headers=headers,
            params={'api-version': config['api_version']},
            timeout=30
        )
        
        if response.status_code == 200:
            project_data = response.json()
            print("✅ Project found!")
            print(f"   Real Project Name: {project_data.get('name', 'Unknown')}")
            print(f"   Display Name: {project_data.get('displayName', 'Unknown')}")
            print(f"   Description: {project_data.get('description', 'None')}")
            print(f"   Location: {project_data.get('location', 'Unknown')}")
            print(f"   Resource Group: {project_data.get('resourceGroup', 'Unknown')}")
            return project_data
        else:
            print(f"❌ Failed to get project details: {response.status_code}")
            print(f"   Response: {response.text}")
    
    except Exception as e:
        print(f"❌ Error getting project details: {e}")
    
    try:
        # Method 2: List all projects in the foundry
        print("\n🔸 Method 2: Listing all projects in foundry...")
        list_url = parsed['projects_api']
        response = requests.get(
            list_url,
            headers=headers,
            params={'api-version': config['api_version']},
            timeout=30
        )
        
        if response.status_code == 200:
            projects_data = response.json()
            projects = projects_data.get('value', [])
            
            print(f"✅ Found {len(projects)} projects in foundry:")
            for i, project in enumerate(projects, 1):
                name = project.get('name', 'Unknown')
                display_name = project.get('displayName', 'Unknown')
                description = project.get('description', 'No description')
                print(f"   {i}. Name: {name}")
                print(f"      Display Name: {display_name}")
                print(f"      Description: {description}")
                print()
                
                # Check if this matches our target project
                if name == parsed['project_name']:
                    print(f"🎯 Found matching project: {name}")
                    return project
        else:
            print(f"❌ Failed to list projects: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error listing projects: {e}")
    
    return None

def check_agents_in_project(config: Dict[str, Any], project_data: Dict[str, Any]) -> None:
    """Check what agents exist in the project."""
    if not project_data:
        return
    
    token = get_azure_token()
    if not token:
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        # Try to list agents
        agents_url = f"{config['project_endpoint']}/agents"
        print(f"\n🔸 Checking agents in project...")
        print(f"   URL: {agents_url}")
        
        response = requests.get(
            agents_url,
            headers=headers,
            params={'api-version': config['api_version']},
            timeout=30
        )
        
        if response.status_code == 200:
            agents_data = response.json()
            agents = agents_data.get('value', [])
            
            print(f"✅ Found {len(agents)} agents:")
            for i, agent in enumerate(agents, 1):
                name = agent.get('name', 'Unknown')
                display_name = agent.get('displayName', 'Unknown')
                description = agent.get('description', 'No description')
                model = agent.get('model', {}).get('deploymentName', 'Unknown')
                print(f"   {i}. Name: {name}")
                print(f"      Display Name: {display_name}")
                print(f"      Model: {model}")
                print(f"      Description: {description}")
                print()
        else:
            print(f"❌ Failed to list agents: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error checking agents: {e}")

def main():
    """Main function to check AI Foundry project details."""
    print("🚀 AI Foundry Project Checker")
    print("=" * 50)
    
    # Load configuration
    config = load_environment()
    
    print("📋 Current Configuration:")
    print(f"   PROJECT_ENDPOINT: {config['project_endpoint']}")
    print(f"   API_VERSION: {config['api_version']}")
    print(f"   AZURE_OPENAI_ENDPOINT: {config['azure_openai_endpoint']}")
    print(f"   AZURE_OPENAI_DEPLOYMENT: {config['azure_openai_deployment']}")
    print()
    
    # Check project details
    project_data = check_project_details(config)
    
    if project_data:
        # Check agents if project exists
        check_agents_in_project(config, project_data)
        
        print("\n🎯 Summary:")
        print(f"   ✅ Project exists and is accessible")
        print(f"   📋 Real project name: {project_data.get('name', 'Unknown')}")
        print(f"   🏷️  Display name: {project_data.get('displayName', 'Unknown')}")
        
        # Check if names match
        parsed = parse_project_endpoint(config['project_endpoint'])
        url_project_name = parsed.get('project_name', '')
        real_project_name = project_data.get('name', '')
        
        if url_project_name != real_project_name:
            print(f"\n⚠️  WARNING: Project name mismatch!")
            print(f"   URL says: {url_project_name}")
            print(f"   API says: {real_project_name}")
            print(f"\n💡 You might need to update your PROJECT_ENDPOINT to:")
            print(f"   PROJECT_ENDPOINT={config['project_endpoint'].replace(url_project_name, real_project_name)}")
        else:
            print(f"   ✅ Project names match correctly")
    else:
        print("\n❌ Could not access project or project does not exist")
        print("\n🔧 Troubleshooting tips:")
        print("   1. Verify the PROJECT_ENDPOINT URL is correct")
        print("   2. Check that your Azure credentials have access to the AI Foundry")
        print("   3. Ensure the project exists in the specified foundry")
        print("   4. Verify the API version is supported")

if __name__ == "__main__":
    main()
