#!/usr/bin/env python3
"""
Check agent existence and test proper Hebrew search configuration.
"""

import os
import requests
import json
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

# Load environment variables
load_dotenv()

def check_agent_existence():
    """Check if specific agents exist."""
    print("=== Checking Specific Agent Existence ===")
    
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    agent_names = ["delete3-agent", "sharepoint-index-1-agent"]
    
    try:
        credential = DefaultAzureCredential()
        token = credential.get_token("https://search.azure.com/.default")
        
        for agent_name in agent_names:
            print(f"\nChecking agent: {agent_name}")
            
            # Try to get specific agent
            url = f"{endpoint}/knowledgeagents/{agent_name}?api-version=2025-05-01-preview"
            headers = {
                "Authorization": f"Bearer {token.token}"
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                agent_data = response.json()
                print(f"  ✓ Agent exists")
                print(f"  Description: {agent_data.get('description', 'No description')}")
                print(f"  Data sources: {agent_data.get('associatedDataSourceNames', [])}")
            elif response.status_code == 404:
                print(f"  ✗ Agent not found")
            else:
                print(f"  ? Error {response.status_code}: {response.text}")
                
    except Exception as e:
        print(f"Error checking agents: {e}")

def test_hebrew_search_with_different_analyzers():
    """Test Hebrew search with different approaches."""
    print("\n=== Testing Hebrew Search Approaches ===")
    
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        client = SearchClient(endpoint=endpoint, index_name="delete3", credential=credential)
        
        hebrew_queries = [
            "גוף",           # body
            "רפואה",         # medicine
            "טבלה",          # table
            "רשיון",         # license
            "טלפון"          # telephone
        ]
        
        for query in hebrew_queries:
            print(f"\nTesting Hebrew query: {query}")
            
            # Test normal search
            results = list(client.search(
                search_text=query,
                top=3,
                include_total_count=True
            ))
            
            print(f"  Normal search results: {len(results)}")
            
            # Test with wildcard
            wildcard_query = f"{query}*"
            wildcard_results = list(client.search(
                search_text=wildcard_query,
                top=3,
                include_total_count=True
            ))
            
            print(f"  Wildcard search results: {len(wildcard_results)}")
            
            # Test with different search mode
            results_any = list(client.search(
                search_text=query,
                search_mode="any",
                top=3,
                include_total_count=True
            ))
            
            print(f"  'Any' mode search results: {len(results_any)}")
            
            if results:
                for i, result in enumerate(results[:1]):  # Show first result
                    content = str(result.get('content', ''))
                    if query in content:
                        print(f"    ✓ Found query in content")
                    else:
                        print(f"    ? Query not found in content")
        
    except Exception as e:
        print(f"Error testing Hebrew search: {e}")

def test_working_agent():
    """Test with the sharepoint-index-1-agent which we know works."""
    print("\n=== Testing Known Working Agent ===")
    
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    agent_name = "sharepoint-index-1-agent"
    
    try:
        credential = DefaultAzureCredential()
        token = credential.get_token("https://search.azure.com/.default")
        
        url = f"{endpoint}/knowledgeagents/{agent_name}/retrieval?api-version=2025-05-01-preview"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token.token}"
        }
        
        # Test with English query that should work
        payload = {
            "messages": [
                {"role": "user", "content": "What is Azure UltraDisk?"}
            ],
            "includeReferenceSourceData": True
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("response") and len(result["response"]) > 0:
                message = result["response"][0]
                if message.get("content") and len(message["content"]) > 0:
                    content = message["content"][0]
                    text_content = content.get("text", "")
                    
                    print(f"✓ sharepoint-index-1-agent works")
                    print(f"  Content length: {len(text_content)}")
                    print(f"  Content preview: {text_content[:200]}...")
                else:
                    print("✗ Agent returned empty content")
            else:
                print("✗ Agent returned no response")
        else:
            print(f"✗ Agent call failed: {response.status_code}")
            print(f"  Error: {response.text}")
            
    except Exception as e:
        print(f"Error testing working agent: {e}")

def check_search_service_configuration():
    """Check the search service configuration for language support."""
    print("\n=== Checking Search Service Configuration ===")
    
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        token = credential.get_token("https://search.azure.com/.default")
        
        # Get service statistics
        url = f"{endpoint}/servicestats?api-version=2023-11-01"
        headers = {
            "Authorization": f"Bearer {token.token}"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            stats = response.json()
            print("Service statistics:")
            print(f"  Indexes: {stats.get('counters', {}).get('indexCounter', {})}")
            print(f"  Data sources: {stats.get('counters', {}).get('dataSourceCounter', {})}")
            print(f"  Indexers: {stats.get('counters', {}).get('indexerCounter', {})}")
        else:
            print(f"Failed to get service stats: {response.status_code}")
            
    except Exception as e:
        print(f"Error checking service configuration: {e}")

if __name__ == "__main__":
    print("Starting Comprehensive Agent and Language Debug")
    print("=" * 60)
    
    # Check if agents exist
    check_agent_existence()
    
    # Test Hebrew search
    test_hebrew_search_with_different_analyzers()
    
    # Test working agent
    test_working_agent()
    
    # Check service config
    check_search_service_configuration()
    
    print("\n" + "=" * 60)
    print("Comprehensive debug complete")
