#!/usr/bin/env python3
"""
Investigate index content to understand why agent returns empty results
"""

import os
from dotenv import load_dotenv
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# Load environment variables
load_dotenv(Path(__file__).resolve().parent / ".env")

def get_search_client(index_name: str) -> SearchClient:
    """Create a SearchClient for document lookups"""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_api_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("SEARCH_API_KEY")
    
    if search_api_key:
        credential = AzureKeyCredential(search_api_key)
    else:
        credential = DefaultAzureCredential()
        
    return SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)

def investigate_index_content():
    """Investigate what's actually in the delete3 index"""
    print("🔍 Investigating Index Content")
    print("=" * 50)
    
    index_name = "delete3"
    client = get_search_client(index_name)
    
    # Get a sample of documents
    try:
        # First, get all documents with a wildcard search
        all_results = client.search(search_text="*", top=10)
        all_docs = [doc for doc in all_results]
        
        print(f"📊 Total documents found with wildcard search: {len(all_docs)}")
        
        if all_docs:
            print("\n📋 Document Analysis:")
            for i, doc in enumerate(all_docs[:3]):  # Show first 3 docs
                print(f"\n--- Document {i+1} ---")
                print(f"Source: {doc.get('source_file', 'Unknown')}")
                print(f"Filename: {doc.get('filename', 'Unknown')}")
                print(f"Document Type: {doc.get('document_type', 'Unknown')}")
                print(f"Page: {doc.get('page_number', 'Unknown')}")
                print(f"Content length: {len(doc.get('content', ''))}")
                print(f"Content preview: {doc.get('content', '')[:300]}...")
                print(f"URL: {doc.get('url', 'None')}")
                print(f"Has embedding: {'contentVector' in doc}")
                
                # Check if this content actually relates to Azure/disk/storage
                content = doc.get('content', '').lower()
                azure_keywords = ['azure', 'disk', 'storage', 'ultradisk', 'premium', 'standard', 'managed']
                found_keywords = [kw for kw in azure_keywords if kw in content]
                print(f"Azure-related keywords found: {found_keywords}")
        
        # Try some specific searches to see what content is actually there
        test_searches = [
            "disk",
            "storage", 
            "Azure",
            "UltraDisk",
            "anatomy",  # Based on the content preview we saw
            "somatosensory",  # Based on the content preview we saw
            "corpuscles",  # Based on the content preview we saw
        ]
        
        print(f"\n🔍 Testing specific search terms:")
        for term in test_searches:
            results = client.search(search_text=term, top=3)
            hits = [doc for doc in results]
            print(f"  '{term}': {len(hits)} hits")
            if hits:
                first_hit = hits[0]
                content_preview = first_hit.get('content', '')[:100]
                print(f"    First hit: {content_preview}...")
        
        # Try semantic search if available
        print(f"\n🧠 Testing semantic search:")
        semantic_queries = [
            "What are the different types of Azure storage disks?",
            "Compare Azure disk performance options",
            "UltraDisk specifications and features"
        ]
        
        for query in semantic_queries:
            try:
                # Try semantic search
                results = client.search(
                    search_text=query,
                    query_type="semantic",
                    semantic_configuration_name="default",
                    top=3
                )
                hits = [doc for doc in results]
                print(f"  Semantic '{query[:50]}...': {len(hits)} hits")
                if hits:
                    first_hit = hits[0]
                    content_preview = first_hit.get('content', '')[:100]
                    print(f"    First hit: {content_preview}...")
            except Exception as e:
                print(f"  Semantic search failed: {e}")
                # Fall back to regular search
                results = client.search(search_text=query, top=3)
                hits = [doc for doc in results]
                print(f"  Regular '{query[:50]}...': {len(hits)} hits")
                
    except Exception as e:
        print(f"❌ Failed to investigate index: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_index_content()
