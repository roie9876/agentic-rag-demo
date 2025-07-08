#!/usr/bin/env python3
"""
Fix Vectorizer Configuration
===========================
Script to update the vectorizer configuration to use the correct resource type
"""

import json
import os
import requests
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

def fix_vectorizer_config():
    """Fix the vectorizer configuration to use the correct Azure OpenAI resource"""
    
    service_name = "ai-serach-demo-eastus"
    index_name = "delete3"
    api_version = "2021-04-30-Preview"
    
    endpoint = f"https://{service_name}.search.windows.net"
    
    # Get authentication headers
    try:
        token = DefaultAzureCredential().get_token("https://search.azure.com/.default").token
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    except Exception as e:
        print(f"❌ Failed to get authentication token: {e}")
        return
    
    # Get current index configuration
    index_url = f"{endpoint}/indexes/{index_name}?api-version={api_version}"
    
    print(f"🔍 Getting current index configuration for: {index_name}")
    print(f"📡 Endpoint: {index_url}")
    print("-" * 80)
    
    try:
        response = requests.get(index_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Failed to get index config: {response.status_code}")
            print(f"Response: {response.text}")
            return
            
        current_config = response.json()
        print(f"✅ Current index config retrieved")
        
        # Check current vectorizer configuration
        vectorizers = current_config.get("vectorizers", [])
        
        print(f"\n🔧 Current vectorizer configuration:")
        print(f"Found {len(vectorizers)} vectorizers")
        
        for i, vectorizer in enumerate(vectorizers):
            print(f"\nVectorizer {i+1}:")
            print(f"  Name: {vectorizer.get('name', 'Unknown')}")
            print(f"  Kind: {vectorizer.get('kind', 'Unknown')}")
            
            if vectorizer.get('kind') == 'azureOpenAI':
                params = vectorizer.get('azureOpenAIParameters', {})
                print(f"  Resource URI: {params.get('resourceUri', 'Not set')}")
                print(f"  Deployment ID: {params.get('deploymentId', 'Not set')}")
                print(f"  Model Name: {params.get('modelName', 'Not set')}")
                print(f"  Auth Identity: {params.get('authIdentity', 'Not set')}")
                
            elif vectorizer.get('kind') == 'azureAIFoundryHub':
                params = vectorizer.get('azureAIFoundryHubParameters', {})
                print(f"  Hub Resource URI: {params.get('hubResourceUri', 'Not set')}")
                print(f"  Project Name: {params.get('projectName', 'Not set')}")
                print(f"  Model Name: {params.get('modelName', 'Not set')}")
                print(f"  Auth Identity: {params.get('authIdentity', 'Not set')}")
        
        # Show suggested fixes
        print(f"\n💡 SUGGESTED FIXES:")
        print(f"================================================================================")
        
        if any(v.get('kind') == 'azureAIFoundryHub' for v in vectorizers):
            print(f"🔧 Option 1: Update AI Foundry Hub vectorizer")
            print(f"   - Project name should be: admin-m845f4ec-eastus2-project")
            print(f"   - Model name should be: text-embedding-3-large")
            print(f"   - Hub Resource URI should point to your AI Foundry Hub")
            
        print(f"\n🔧 Option 2: Change to Azure OpenAI vectorizer")
        print(f"   - Kind: azureOpenAI")
        print(f"   - Resource URI: https://admin-m845f4ec-eastus2.openai.azure.com")
        print(f"   - Deployment ID: text-embedding-3-large")
        print(f"   - Model Name: text-embedding-3-large")
        print(f"   - Auth Identity: systemAssignedManagedIdentity")
        
        # Ask user which option they prefer
        print(f"\n❓ Would you like to:")
        print(f"   1. Keep AI Foundry Hub and fix the project configuration")
        print(f"   2. Switch to traditional Azure OpenAI configuration")
        print(f"   3. Just show the current config (no changes)")
        
        choice = input("\nEnter your choice (1, 2, or 3): ").strip()
        
        if choice == "1":
            update_foundry_hub_config(current_config, headers, index_url)
        elif choice == "2":
            update_azure_openai_config(current_config, headers, index_url)
        else:
            print(f"📋 No changes made. Current configuration displayed above.")
            
    except Exception as e:
        print(f"❌ Error getting index config: {e}")

def update_foundry_hub_config(config, headers, url):
    """Update the AI Foundry Hub vectorizer configuration"""
    print(f"\n🔧 Updating AI Foundry Hub vectorizer configuration...")
    
    # This would require knowing the exact hub resource URI
    # For now, just show what needs to be updated
    print(f"⚠️  Manual update required in Azure Portal:")
    print(f"   1. Go to Azure AI Search > Indexes > delete3 > Vector profiles")
    print(f"   2. Edit the vectorizer")
    print(f"   3. Select project: admin-m845f4ec-eastus2-project")
    print(f"   4. Select model: text-embedding-3-large")
    print(f"   5. Set authentication to: System assigned identity")

def update_azure_openai_config(config, headers, url):
    """Update to use traditional Azure OpenAI configuration"""
    print(f"\n🔧 Updating to Azure OpenAI vectorizer configuration...")
    
    # Find and update vectorizers
    vectorizers = config.get("vectorizers", [])
    
    for vectorizer in vectorizers:
        if vectorizer.get('kind') in ['azureAIFoundryHub', 'azureOpenAI']:
            # Update to Azure OpenAI configuration
            vectorizer['kind'] = 'azureOpenAI'
            vectorizer['azureOpenAIParameters'] = {
                'resourceUri': 'https://admin-m845f4ec-eastus2.openai.azure.com',
                'deploymentId': 'text-embedding-3-large',
                'modelName': 'text-embedding-3-large',
                'authIdentity': {
                    'kind': 'systemAssignedManagedIdentity'
                }
            }
            # Remove AI Foundry Hub parameters if they exist
            vectorizer.pop('azureAIFoundryHubParameters', None)
            
            print(f"✅ Updated vectorizer: {vectorizer.get('name', 'Unknown')}")
    
    # Update the index
    try:
        response = requests.put(url, headers=headers, json=config, timeout=30)
        
        if response.status_code in [200, 201, 204]:
            print(f"✅ Index vectorizer configuration updated successfully!")
            print(f"🎉 The vectorizer should now use Azure OpenAI with managed identity")
        else:
            print(f"❌ Failed to update index: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error updating index config: {e}")

if __name__ == "__main__":
    print("🔧 VECTORIZER CONFIGURATION FIXER")
    print("=" * 80)
    fix_vectorizer_config()
