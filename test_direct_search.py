#!/usr/bin/env python3
"""
Diagnostic script to test direct Azure Search retrieval for PowerPoint content
"""

import os
import sys
import json

# Add the project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_direct_search():
    """Test direct Azure Search to see if we can retrieve the PowerPoint content"""
    
    print("🔍 TESTING DIRECT AZURE SEARCH RETRIEVAL")
    print("=" * 60)
    
    try:
        # Import Azure Search
        from azure.search.documents import SearchClient
        from azure.core.credentials import AzureKeyCredential
        from azure.identity import DefaultAzureCredential
        
        # Get search configuration
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        index_name = "delete1"  # From your search results
        
        print(f"🔗 Search Endpoint: {search_endpoint}")
        print(f"📋 Index Name: {index_name}")
        
        # Initialize search client (try with credential first)
        try:
            credential = DefaultAzureCredential()
            search_client = SearchClient(
                endpoint=search_endpoint,
                index_name=index_name,
                credential=credential
            )
        except Exception as cred_err:
            print(f"⚠️ Credential auth failed: {cred_err}")
            # Fallback to key if available
            search_key = os.getenv("AZURE_SEARCH_KEY")
            if search_key:
                search_client = SearchClient(
                    endpoint=search_endpoint,
                    index_name=index_name,
                    credential=AzureKeyCredential(search_key)
                )
                print("🔑 Using API key authentication")
            else:
                print("❌ No search credentials available")
                return False
        
        # Test 1: Search for UltraDisk content
        print("\n🧪 Test 1: Search for UltraDisk content")
        print("-" * 40)
        
        query = "UltraDisk"
        results = search_client.search(search_text=query, top=3)
        
        count = 0
        for result in results:
            count += 1
            print(f"\n📄 Result {count}:")
            print(f"   ID: {result.get('id', 'N/A')}")
            print(f"   Score: {result.get('@search.score', 'N/A')}")
            print(f"   Source: {result.get('source_file', 'N/A')}")
            
            # Check different content fields
            content_fields = ['content', 'page_chunk']
            for field in content_fields:
                content = result.get(field, '')
                if content:
                    preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"   {field}: {preview}")
                else:
                    print(f"   {field}: (empty)")
                    
            # Check multimodal fields
            print(f"   imageCaptions: {result.get('imageCaptions', 'N/A')}")
            print(f"   relatedImages: {result.get('relatedImages', 'N/A')}")
            print(f"   isMultimodal: {result.get('isMultimodal', 'N/A')}")
        
        if count == 0:
            print("❌ No results found for UltraDisk query")
            return False
            
        # Test 2: Hebrew query test
        print("\n🧪 Test 2: Hebrew query test")
        print("-" * 40)
        
        hebrew_query = "דיסק"  # Hebrew word for "disk"
        results = search_client.search(search_text=hebrew_query, top=2)
        
        count = 0
        for result in results:
            count += 1
            print(f"\n📄 Hebrew Result {count}:")
            print(f"   ID: {result.get('id', 'N/A')}")
            print(f"   Source: {result.get('source_file', 'N/A')}")
            content = result.get('content', '') or result.get('page_chunk', '')
            preview = content[:100] + "..." if len(content) > 100 else content
            print(f"   Content preview: {preview}")
            
        if count == 0:
            print("❌ No results found for Hebrew query")
        else:
            print(f"✅ Found {count} results for Hebrew query")
            
        # Test 3: Get specific document by ID
        print("\n🧪 Test 3: Get document by ID")
        print("-" * 40)
        
        # Use the first ID from your index results
        doc_id = "42e8f88d1d628a5bad21e2ba5bc9df5c"
        try:
            doc = search_client.get_document(key=doc_id)
            print(f"✅ Found document with ID: {doc_id}")
            print(f"   Source: {doc.get('source_file', 'N/A')}")
            content = doc.get('content', '') or doc.get('page_chunk', '')
            print(f"   Content length: {len(content) if content else 0} characters")
            if content:
                preview = content[:300] + "..." if len(content) > 300 else content
                print(f"   Content preview: {preview}")
            else:
                print("   Content: (empty)")
        except Exception as doc_err:
            print(f"❌ Error getting document: {doc_err}")
            
        print("\n🎯 DIAGNOSIS:")
        print("✅ If content is showing properly here, the issue is in the Streamlit retrieval UI")
        print("❌ If content is empty here too, the issue is in the indexing process")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct_search()
    sys.exit(0 if success else 1)
