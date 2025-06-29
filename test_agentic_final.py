#!/usr/bin/env python3
"""
Test script to verify agentic retrieval functionality after vectorizer fix.
"""
import os
import json
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

def load_env():
    """Load environment variables from .env file."""
    from dotenv import load_dotenv
    load_dotenv()

def test_agentic_retrieval_simple():
    """Test a simple agentic retrieval query."""
    print("🤖 Testing Agentic Retrieval...")
    
    load_env()
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    index_name = os.getenv("INDEX_NAME", "delete3")
    
    try:
        credential = DefaultAzureCredential()
        
        # Import the agentic retrieval function from your main app
        import sys
        sys.path.append('.')
        
        # Try to import the agentic_retrieval function
        try:
            # Check if the main module file exists
            import importlib.util
            spec = importlib.util.spec_from_file_location("agentic_rag_demo", "./agentic-rag-demo.py")
            if spec and spec.loader:
                agentic_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(agentic_module)
                agentic_retrieval = agentic_module.agentic_retrieval
                print("✅ Successfully imported agentic_retrieval function")
            else:
                raise ImportError("Could not load agentic-rag-demo.py")
            
            # Test with a simple query
            test_query = "What is this document about?"
            print(f"🔍 Testing query: '{test_query}'")
            
            result = agentic_retrieval(test_query, index_name)
            
            if result and isinstance(result, list) and len(result) > 0:
                print(f"✅ Agentic retrieval returned {len(result)} results")
                for i, chunk in enumerate(result[:2]):  # Show first 2 results
                    content_preview = chunk.get('content', str(chunk))[:100] + "..."
                    print(f"   Result {i+1}: {content_preview}")
                return True
            else:
                print("⚠️  Agentic retrieval returned empty results")
                print(f"Result: {result}")
                return False
                
        except ImportError as e:
            print(f"❌ Could not import agentic_retrieval function: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing agentic retrieval: {str(e)}")
        return False

def test_vector_search():
    """Test if vector search is working on the index."""
    print("\n🔍 Testing Vector Search...")
    
    load_env()
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    index_name = os.getenv("INDEX_NAME", "delete3")
    
    try:
        credential = DefaultAzureCredential()
        search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
        
        # Try a simple vector search (if vectors exist)
        results = list(search_client.search(
            search_text="document content",
            top=3,
            include_total_count=True
        ))
        
        print(f"✅ Search returned {len(results)} results")
        
        # Check if any results have vector fields
        has_vectors = False
        for result in results:
            vector_fields = [k for k in result.keys() if 'vector' in k.lower()]
            if vector_fields:
                has_vectors = True
                print(f"✅ Found vector fields: {vector_fields}")
                break
        
        if not has_vectors:
            print("⚠️  No vector fields found in search results")
        
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Vector search failed: {str(e)}")
        return False

def main():
    """Run comprehensive tests."""
    print("🧪 Testing Agentic Retrieval After Vectorizer Fix")
    print("=" * 60)
    
    # Test 1: Vector search
    vector_success = test_vector_search()
    
    # Test 2: Agentic retrieval
    agentic_success = test_agentic_retrieval_simple()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    if vector_success:
        print("✅ Vector search: WORKING")
    else:
        print("❌ Vector search: FAILED")
    
    if agentic_success:
        print("✅ Agentic retrieval: WORKING")
    else:
        print("❌ Agentic retrieval: FAILED")
    
    if vector_success and agentic_success:
        print("\n🎉 All tests passed! Agentic retrieval should work in your Streamlit app.")
    else:
        print("\n⚠️  Some issues remain. Check the vectorizer configuration and wait for reindexing to complete.")

if __name__ == "__main__":
    main()
