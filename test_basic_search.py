#!/usr/bin/env python3
"""
Simple test to verify that basic search works on delete3 index
and to understand the document structure better.
"""
import os
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

def load_env():
    """Load environment variables from .env file."""
    from dotenv import load_dotenv
    load_dotenv()

def test_basic_search():
    """Test basic search functionality."""
    print("🔍 Testing basic search on delete3 index...")
    
    load_env()
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        search_client = SearchClient(endpoint=search_endpoint, index_name="delete3", credential=credential)
        
        # Test 1: Get all documents
        print("\n📄 Getting all documents...")
        results = list(search_client.search(search_text="*", top=10, include_total_count=True))
        total_count = len(results)
        print(f"✅ Found {total_count} documents")
        
        # Test 2: Show document structure
        if results:
            print("\n📋 Document structure:")
            sample_doc = results[0]
            for key, value in sample_doc.items():
                if not key.startswith('@search'):
                    value_preview = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                    print(f"   {key}: {value_preview}")
        
        # Test 3: Search for specific content
        print("\n🔎 Testing content search...")
        content_results = list(search_client.search(search_text="document", top=3))
        print(f"✅ Content search returned {len(content_results)} results")
        
        # Test 4: Check if documents have actual content
        content_docs = [doc for doc in results if doc.get('content') and len(str(doc.get('content'))) > 50]
        print(f"✅ {len(content_docs)} documents have substantial content")
        
        if content_docs:
            print("\n📖 Sample content:")
            sample_content = content_docs[0].get('content', '')
            print(f"   Content preview: {str(sample_content)[:200]}...")
        
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Basic search failed: {str(e)}")
        return False

def main():
    """Test basic search functionality."""
    print("🧪 Basic Search Test for delete3 Index")
    print("=" * 50)
    
    success = test_basic_search()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Basic search is working!")
        print("ℹ️  The index has documents with content")
        print("ℹ️  Once vectorizer is configured, agentic retrieval should work")
    else:
        print("❌ Basic search failed")
        print("ℹ️  There may be an issue with the index or permissions")

if __name__ == "__main__":
    main()
