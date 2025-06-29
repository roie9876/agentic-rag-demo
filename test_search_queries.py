#!/usr/bin/env python3
"""Test search queries on indexes with content"""

import os
from azure.search.documents import SearchClient
from azure.identity import DefaultAzureCredential

def test_search_query(index_name, query="test"):
    """Test a search query on a specific index"""
    try:
        credential = DefaultAzureCredential()
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        
        search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
        
        print(f"🔍 Testing search on index '{index_name}' with query '{query}'")
        
        # First, try a broad search
        results = search_client.search(query, top=3, include_total_count=True)
        count = results.get_count()
        print(f"   📊 Found {count} results")
        
        # Show results
        for i, doc in enumerate(results):
            print(f"   📄 Result {i+1}:")
            # Show key fields
            for key in ['url', 'source', 'content', 'chunk', 'page_chunk'][:3]:
                if key in doc:
                    value = str(doc[key])[:100] + "..." if len(str(doc[key])) > 100 else str(doc[key])
                    print(f"      {key}: {value}")
            print()
            
        # Try a wildcard search
        print(f"🔍 Testing wildcard search on index '{index_name}'")
        results = search_client.search("*", top=3, include_total_count=True)
        count = results.get_count()
        print(f"   📊 Total documents: {count}")
        
        # Show sample documents
        for i, doc in enumerate(results):
            print(f"   📄 Document {i+1}:")
            # Show all available fields
            for key, value in doc.items():
                if key not in ['@search.score', '@search.highlights']:
                    value_str = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                    print(f"      {key}: {value_str}")
            print()
            
    except Exception as e:
        print(f"❌ Error testing search on {index_name}: {e}")

if __name__ == "__main__":
    # Test the indexes that have content
    test_indexes = [
        ("agentic-demo", "test"),
        ("agentic-index", "test"), 
        ("deleme1", "test"),
        ("sharepoint-index-1", "test")
    ]
    
    for index_name, query in test_indexes:
        test_search_query(index_name, query)
        print("=" * 60)
