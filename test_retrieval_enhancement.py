#!/usr/bin/env python3
"""
Quick test script to validate the enhanced retrieval functionality.
This script tests the retrieval components separately from the Streamlit UI.
"""

import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

def test_search_client_init():
    """Test search client initialization with managed identity."""
    load_dotenv()
    
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    if not search_endpoint:
        print("❌ AZURE_SEARCH_ENDPOINT not found in environment")
        return None
    
    try:
        # Try with managed identity first
        print("🔐 Testing search client with managed identity...")
        credential = DefaultAzureCredential()
        
        # Get available indexes
        from azure.search.documents.indexes import SearchIndexClient
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        indexes = list(index_client.list_indexes())
        
        if not indexes:
            print("⚠️ No indexes found in search service")
            return None
        
        # Use the first available index for testing
        index_name = indexes[0].name
        print(f"✅ Found index: {index_name}")
        
        # Create search client
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=credential
        )
        
        # Test document count
        doc_count = search_client.get_document_count()
        print(f"📊 Index '{index_name}' contains {doc_count:,} documents")
        
        return search_client, index_name
        
    except Exception as e:
        print(f"❌ Error initializing search client: {str(e)}")
        return None

def test_sample_search(search_client, index_name):
    """Test a sample search query."""
    if not search_client:
        print("❌ Search client not available")
        return
    
    test_queries = [
        "document",
        "report",
        "meeting", 
        "project"
    ]
    
    print(f"\n🔍 Testing search queries on index '{index_name}':")
    print("-" * 50)
    
    for query in test_queries:
        try:
            results = search_client.search(
                search_text=query,
                top=3,
                include_total_count=True
            )
            
            search_results = list(results)
            print(f"Query: '{query}' -> {len(search_results)} results")
            
            if search_results:
                for i, result in enumerate(search_results[:1]):  # Show only first result
                    content = result.get('content', result.get('page_chunk', 'No content'))
                    print(f"  • Result {i+1}: {result.get('source_file', 'Unknown')} "
                          f"(Score: {result['@search.score']:.3f})")
                    print(f"    Content preview: {content[:100]}...")
            else:
                print(f"  • No results for '{query}'")
                
        except Exception as e:
            print(f"  • Error searching '{query}': {str(e)}")
        
        print()

def main():
    """Main test function."""
    print("🧪 Testing Enhanced Retrieval Functionality")
    print("=" * 50)
    
    # Test search client initialization
    result = test_search_client_init()
    if not result:
        print("❌ Could not initialize search client. Check your configuration.")
        return
    
    search_client, index_name = result
    
    # Test sample searches
    test_sample_search(search_client, index_name)
    
    print("✅ Retrieval enhancement test completed!")

if __name__ == "__main__":
    main()
