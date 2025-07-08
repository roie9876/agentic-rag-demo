#!/usr/bin/env python3
"""
List all indexes and their content to find the right one with Azure storage docs
"""

import os
from dotenv import load_dotenv
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

# Load environment variables
load_dotenv(Path(__file__).resolve().parent / ".env")

def get_search_index_client() -> SearchIndexClient:
    """Create a SearchIndexClient"""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_api_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("SEARCH_API_KEY")
    
    if search_api_key:
        credential = AzureKeyCredential(search_api_key)
    else:
        credential = DefaultAzureCredential()
        
    return SearchIndexClient(endpoint=search_endpoint, credential=credential)

def get_search_client(index_name: str) -> SearchClient:
    """Create a SearchClient for document lookups"""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_api_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("SEARCH_API_KEY")
    
    if search_api_key:
        credential = AzureKeyCredential(search_api_key)
    else:
        credential = DefaultAzureCredential()
        
    return SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)

def find_azure_storage_content():
    """Find which index contains Azure storage content"""
    print("🔍 Searching All Indexes for Azure Storage Content")
    print("=" * 60)
    
    try:
        # List all indexes
        index_client = get_search_index_client()
        indexes = [idx.name for idx in index_client.list_indexes()]
        
        print(f"📊 Found {len(indexes)} indexes: {indexes}")
        
        # Search each index for Azure storage content
        azure_keywords = ['azure', 'disk', 'storage', 'ultradisk', 'premium', 'managed', 'ssd', 'hdd']
        
        for index_name in indexes:
            print(f"\n{'='*50}")
            print(f"🔍 Checking index: {index_name}")
            
            try:
                client = get_search_client(index_name)
                
                # Get total document count
                all_results = client.search(search_text="*", top=1)
                total_docs = sum(1 for _ in client.search(search_text="*", top=1000))
                print(f"📊 Total documents: {total_docs}")
                
                if total_docs == 0:
                    print("❌ Empty index")
                    continue
                
                # Sample first few documents
                sample_results = client.search(search_text="*", top=3)
                sample_docs = [doc for doc in sample_results]
                
                print(f"📋 Sample documents:")
                azure_content_found = False
                
                for i, doc in enumerate(sample_docs):
                    print(f"\n  --- Document {i+1} ---")
                    source_file = doc.get('source_file', 'Unknown')
                    content = doc.get('content', '')
                    print(f"  Source: {source_file}")
                    print(f"  Content length: {len(content)}")
                    print(f"  Content preview: {content[:200]}...")
                    
                    # Check for Azure keywords
                    content_lower = content.lower()
                    found_keywords = [kw for kw in azure_keywords if kw in content_lower]
                    if found_keywords:
                        print(f"  ✅ Azure keywords found: {found_keywords}")
                        azure_content_found = True
                    else:
                        print(f"  ❌ No Azure keywords found")
                
                # Test specific Azure queries
                if azure_content_found:
                    print(f"\n🎯 Testing Azure-specific queries on {index_name}:")
                    test_queries = [
                        "disk types",
                        "Azure storage",
                        "UltraDisk",
                        "premium SSD"
                    ]
                    
                    for query in test_queries:
                        results = client.search(search_text=query, top=3)
                        hits = [doc for doc in results]
                        print(f"    '{query}': {len(hits)} hits")
                        if hits:
                            first_content = hits[0].get('content', '')[:100]
                            print(f"      Preview: {first_content}...")
                
            except Exception as e:
                print(f"❌ Error checking index {index_name}: {e}")
        
        # Also check agents to see which indexes they target
        print(f"\n{'='*60}")
        print(f"🤖 Checking Knowledge Agents")
        
        import requests
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        
        # Get auth headers
        search_api_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("SEARCH_API_KEY")
        if search_api_key:
            headers = {"api-key": search_api_key, "Content-Type": "application/json"}
        else:
            token = DefaultAzureCredential().get_token("https://search.azure.com/.default").token
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # List agents
        agent_url = f"{search_endpoint}/agents?api-version=2025-05-01-preview"
        response = requests.get(agent_url, headers=headers)
        
        if response.status_code == 200:
            agents = response.json()
            print(f"📊 Found {len(agents.get('value', []))} agents:")
            
            for agent in agents.get('value', []):
                agent_name = agent.get('name', 'Unknown')
                target_indexes = agent.get('targetIndexes', [])
                print(f"  🤖 {agent_name}")
                for target in target_indexes:
                    index_name = target.get('indexName', 'Unknown')
                    print(f"    → targets index: {index_name}")
        else:
            print(f"❌ Failed to list agents: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Failed to search indexes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_azure_storage_content()
