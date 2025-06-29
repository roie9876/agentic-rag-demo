#!/usr/bin/env python3
"""
Check what knowledge agents actually exist and investigate the Hebrew language issue.
"""

import os
import requests
import json
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential

# Load environment variables
load_dotenv()

def list_knowledge_agents():
    """List all available knowledge agents."""
    print("=== Listing All Knowledge Agents ===")
    
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        token = credential.get_token("https://search.azure.com/.default")
        
        url = f"{endpoint}/knowledgeagents"
        headers = {
            "api-version": "2025-05-01-preview",
            "Authorization": f"Bearer {token.token}"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            agents = result.get("value", [])
            
            print(f"Found {len(agents)} knowledge agents:")
            for agent in agents:
                name = agent.get("name", "Unknown")
                description = agent.get("description", "No description")
                print(f"  - {name}: {description}")
                
                # Show associated data source names
                if "associatedDataSourceNames" in agent:
                    data_sources = agent["associatedDataSourceNames"]
                    print(f"    Data sources: {data_sources}")
            
            return agents
        else:
            print(f"Failed to list agents: {response.status_code}")
            print(response.text)
            return []
            
    except Exception as e:
        print(f"Error listing agents: {e}")
        import traceback
        traceback.print_exc()
        return []

def check_index_analyzer():
    """Check the delete3 index analyzer configuration."""
    print("\n=== Checking delete3 Index Analyzer Configuration ===")
    
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        token = credential.get_token("https://search.azure.com/.default")
        
        # Get index definition with correct API version
        url = f"{endpoint}/indexes/delete3?api-version=2023-11-01"
        headers = {
            "Authorization": f"Bearer {token.token}"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            index_def = response.json()
            
            print("Searchable fields and their analyzers:")
            for field in index_def.get("fields", []):
                if field.get("searchable", False):
                    field_name = field.get("name")
                    analyzer = field.get("analyzer", "standard (default)")
                    print(f"  - {field_name}: {analyzer}")
            
            # Check for custom analyzers
            analyzers = index_def.get("analyzers", [])
            if analyzers:
                print(f"\nCustom analyzers ({len(analyzers)}):")
                for analyzer in analyzers:
                    print(f"  - {analyzer.get('name')}: {analyzer}")
            else:
                print("\nNo custom analyzers found")
                
        else:
            print(f"Failed to get index definition: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error checking index analyzer: {e}")

def test_hebrew_vs_english_content():
    """Check if there's actually Hebrew content in the index."""
    print("\n=== Checking for Hebrew Content in Index ===")
    
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        from azure.search.documents import SearchClient
        from azure.identity import DefaultAzureCredential
        
        credential = DefaultAzureCredential()
        client = SearchClient(endpoint=endpoint, index_name="delete3", credential=credential)
        
        # Get all documents to check their content
        print("Sampling documents to check for Hebrew content:")
        
        results = client.search(
            search_text="*",
            top=10,
            select=["content"]
        )
        
        hebrew_found = 0
        english_found = 0
        
        for i, result in enumerate(results):
            content = str(result.get('content', ''))
            
            # Simple check for Hebrew characters (Unicode range)
            has_hebrew = any('\u0590' <= char <= '\u05FF' for char in content)
            # Simple check for English characters
            has_english = any('a' <= char.lower() <= 'z' for char in content)
            
            if has_hebrew:
                hebrew_found += 1
                print(f"  Document {i+1}: Contains Hebrew")
                print(f"    Preview: {content[:100]}...")
            elif has_english:
                english_found += 1
                if i < 3:  # Show first 3 English docs
                    print(f"  Document {i+1}: English only")
                    print(f"    Preview: {content[:100]}...")
        
        print(f"\nSummary:")
        print(f"  Documents with Hebrew: {hebrew_found}")
        print(f"  Documents with English: {english_found}")
        
    except Exception as e:
        print(f"Error checking content: {e}")

if __name__ == "__main__":
    print("Starting Agent and Language Investigation")
    print("=" * 60)
    
    # List all agents
    agents = list_knowledge_agents()
    
    # Check index analyzer
    check_index_analyzer()
    
    # Check for Hebrew content
    test_hebrew_vs_english_content()
    
    print("\n" + "=" * 60)
    print("Investigation complete")
