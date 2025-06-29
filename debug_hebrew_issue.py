#!/usr/bin/env python3
"""
Debug script to investigate Hebrew query issues with the delete3-agent.
This script will test both Hebrew and English queries on the same agent/index.
"""

import os
import requests
import json
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

# Load environment variables
load_dotenv()

def test_direct_search():
    """Test direct search on the delete3 index to see what content exists."""
    print("=== Testing Direct Search on delete3 Index ===")
    
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        # Use managed identity (no API key)
        credential = DefaultAzureCredential()
        client = SearchClient(endpoint=endpoint, index_name="delete3", credential=credential)
        
        # Test Hebrew query
        print("\n1. Testing Hebrew query directly on index:")
        hebrew_query = "איך עובדת מערכת החישה של גוף האדם"
        print(f"Query: {hebrew_query}")
        
        results = client.search(
            search_text=hebrew_query,
            top=5,
            include_total_count=True
        )
        
        result_count = 0
        for result in results:
            result_count += 1
            print(f"  Document {result_count}:")
            print(f"    Score: {result.get('@search.score', 'N/A')}")
            print(f"    Title: {result.get('title', 'N/A')[:100]}...")
            print(f"    Content preview: {str(result.get('content', 'N/A'))[:200]}...")
            print()
        
        print(f"Total Hebrew results: {result_count}")
        
        # Test English query
        print("\n2. Testing English query directly on index:")
        english_query = "how does the human body sensation system work"
        print(f"Query: {english_query}")
        
        results = client.search(
            search_text=english_query,
            top=5,
            include_total_count=True
        )
        
        result_count = 0
        for result in results:
            result_count += 1
            print(f"  Document {result_count}:")
            print(f"    Score: {result.get('@search.score', 'N/A')}")
            print(f"    Title: {result.get('title', 'N/A')[:100]}...")
            print(f"    Content preview: {str(result.get('content', 'N/A'))[:200]}...")
            print()
        
        print(f"Total English results: {result_count}")
        
        # Test simple Hebrew word
        print("\n3. Testing simple Hebrew word:")
        simple_hebrew = "גוף"  # body
        print(f"Query: {simple_hebrew}")
        
        results = client.search(
            search_text=simple_hebrew,
            top=5,
            include_total_count=True
        )
        
        result_count = 0
        for result in results:
            result_count += 1
            print(f"  Document {result_count}:")
            print(f"    Score: {result.get('@search.score', 'N/A')}")
            print(f"    Title: {result.get('title', 'N/A')[:100]}...")
            print(f"    Content preview: {str(result.get('content', 'N/A'))[:200]}...")
            print()
        
        print(f"Total simple Hebrew results: {result_count}")
        
    except Exception as e:
        print(f"Error in direct search: {e}")
        import traceback
        traceback.print_exc()

def test_agent_with_different_queries():
    """Test the delete3-agent with different types of queries."""
    print("\n=== Testing delete3-agent with Different Queries ===")
    
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    agent_name = "delete3-agent"
    
    # Prepare the API call
    url = f"{endpoint}/knowledgeagents/{agent_name}/retrieval"
    headers = {
        "Content-Type": "application/json",
        "api-version": "2025-05-01-preview"
    }
    
    # Use managed identity
    credential = DefaultAzureCredential()
    token = credential.get_token("https://search.azure.com/.default")
    headers["Authorization"] = f"Bearer {token.token}"
    
    queries = [
        ("Hebrew original", "איך עובדת מערכת החישה של גוף האדם"),
        ("English translation", "how does the human body sensation system work"),
        ("Simple Hebrew", "גוף"),
        ("Simple English", "body"),
        ("Hebrew anatomy", "אנטומיה"),
        ("English anatomy", "anatomy"),
        ("Hebrew nervous system", "מערכת עצבים"),
        ("English nervous system", "nervous system")
    ]
    
    for query_name, query_text in queries:
        print(f"\n--- Testing {query_name}: {query_text} ---")
        
        payload = {
            "messages": [
                {"role": "user", "content": query_text}
            ],
            "includeReferenceSourceData": True
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("response") and len(result["response"]) > 0:
                    message = result["response"][0]
                    if message.get("content") and len(message["content"]) > 0:
                        content = message["content"][0]
                        text_content = content.get("text", "")
                        
                        print(f"  Status: SUCCESS")
                        print(f"  Content length: {len(text_content)}")
                        print(f"  Content preview: {text_content[:200]}...")
                        
                        # Check for reference sources
                        if "referenceSourceData" in result:
                            sources = result["referenceSourceData"]
                            print(f"  Reference sources: {len(sources)} found")
                            for i, source in enumerate(sources[:2]):  # Show first 2 sources
                                print(f"    Source {i+1}: {source.get('title', 'No title')[:50]}...")
                        else:
                            print("  Reference sources: None")
                    else:
                        print(f"  Status: EMPTY CONTENT")
                else:
                    print(f"  Status: NO RESPONSE")
            else:
                print(f"  Status: HTTP ERROR {response.status_code}")
                print(f"  Error: {response.text}")
                
        except Exception as e:
            print(f"  Status: EXCEPTION - {e}")

def check_index_schema():
    """Check the delete3 index schema to understand its structure."""
    print("\n=== Checking delete3 Index Schema ===")
    
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        token = credential.get_token("https://search.azure.com/.default")
        
        # Get index definition
        url = f"{endpoint}/indexes/delete3"
        headers = {
            "api-version": "2023-11-01",
            "Authorization": f"Bearer {token.token}"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            index_def = response.json()
            
            print("Index fields:")
            for field in index_def.get("fields", []):
                field_name = field.get("name")
                field_type = field.get("type")
                searchable = field.get("searchable", False)
                analyzer = field.get("analyzer", "N/A")
                print(f"  - {field_name} ({field_type}): searchable={searchable}, analyzer={analyzer}")
            
            # Check vectorizers
            vectorizers = index_def.get("vectorizers", [])
            if vectorizers:
                print(f"\nVectorizers ({len(vectorizers)}):")
                for vectorizer in vectorizers:
                    print(f"  - {vectorizer.get('name')}: {vectorizer.get('kind')}")
            
            # Check semantic configuration
            semantic_config = index_def.get("semantic", {})
            if semantic_config:
                print(f"\nSemantic configuration: {semantic_config}")
                
        else:
            print(f"Failed to get index schema: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error checking index schema: {e}")

if __name__ == "__main__":
    print("Starting Hebrew Query Debug Investigation")
    print("=" * 60)
    
    # Check index schema first
    check_index_schema()
    
    # Test direct search
    test_direct_search()
    
    # Test agent with different queries
    test_agent_with_different_queries()
    
    print("\n" + "=" * 60)
    print("Debug investigation complete")
