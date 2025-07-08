#!/usr/bin/env python3
"""
Comprehensive diagnostic script to identify why agentic retrieval is returning empty results.
This will check all components: Search index, vectorizer, agent, and permissions.
"""
import os
import sys
import json
import requests
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import *

def load_env():
    """Load environment variables from .env file."""
    from dotenv import load_dotenv
    load_dotenv()

def test_search_access():
    """Test basic Azure Search access with managed identity."""
    print("🔍 Testing Azure Search Access...")
    
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    if not search_endpoint:
        print("❌ AZURE_SEARCH_ENDPOINT not found in .env")
        return False
    
    try:
        credential = DefaultAzureCredential()
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        
        # List indexes
        indexes = list(index_client.list_indexes())
        print(f"✅ Successfully connected to Azure Search")
        print(f"✅ Found {len(indexes)} indexes:")
        for idx in indexes:
            print(f"   - {idx.name}")
        
        return True, indexes
    except Exception as e:
        print(f"❌ Failed to connect to Azure Search: {str(e)}")
        return False, []

def check_index_content(index_name):
    """Check if the index has documents and vectors."""
    print(f"\n📊 Checking index content: {index_name}")
    
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
        
        # Get document count
        results = search_client.search(search_text="*", top=1, include_total_count=True)
        total_count = results.get_count()
        
        print(f"✅ Index '{index_name}' contains {total_count} documents")
        
        if total_count > 0:
            # Get a sample document to check structure
            sample_docs = list(search_client.search(search_text="*", top=3))
            if sample_docs:
                sample_doc = sample_docs[0]
                print(f"✅ Sample document keys: {list(sample_doc.keys())}")
                
                # Check if document has vector fields
                vector_fields = [k for k in sample_doc.keys() if 'vector' in k.lower() or 'embedding' in k.lower()]
                if vector_fields:
                    print(f"✅ Found vector fields: {vector_fields}")
                else:
                    print("⚠️  No vector fields found in documents")
            
        return total_count > 0
        
    except Exception as e:
        print(f"❌ Failed to check index content: {str(e)}")
        return False

def check_vectorizer_config(index_name):
    """Check the vectorizer configuration for the index."""
    print(f"\n🔧 Checking vectorizer configuration for: {index_name}")
    
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        
        # Get index definition
        index = index_client.get_index(index_name)
        
        print(f"✅ Retrieved index definition for '{index_name}'")
        
        # Check vectorizers
        if hasattr(index, 'vectorizers') and index.vectorizers:
            print(f"✅ Found {len(index.vectorizers)} vectorizer(s):")
            for vectorizer in index.vectorizers:
                print(f"   - Name: {vectorizer.name}")
                print(f"   - Kind: {vectorizer.kind}")
                if hasattr(vectorizer, 'azure_open_ai_parameters'):
                    params = vectorizer.azure_open_ai_parameters
                    print(f"   - Resource URI: {getattr(params, 'resource_uri', 'N/A')}")
                    print(f"   - Deployment: {getattr(params, 'deployment_id', 'N/A')}")
                    print(f"   - Model: {getattr(params, 'model_name', 'N/A')}")
        else:
            print("⚠️  No vectorizers found in index definition")
        
        # Check vector profiles
        if hasattr(index, 'vector_search') and index.vector_search:
            vs = index.vector_search
            if hasattr(vs, 'profiles') and vs.profiles:
                print(f"✅ Found {len(vs.profiles)} vector profile(s):")
                for profile in vs.profiles:
                    print(f"   - Profile: {profile.name}")
                    print(f"   - Vectorizer: {getattr(profile, 'vectorizer', 'N/A')}")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to check vectorizer config: {str(e)}")
        return False

def test_agent_access():
    """Test knowledge agent access."""
    print(f"\n🤖 Testing Knowledge Agent Access...")
    
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        
        # Get access token for agent API
        token_response = credential.get_token("https://search.azure.com/.default")
        access_token = token_response.token
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Try to list agents
        agent_url = f"{search_endpoint}/agents?api-version=2025-05-01-preview"
        response = requests.get(agent_url, headers=headers)
        
        if response.status_code == 200:
            agents = response.json()
            print(f"✅ Successfully accessed agent API")
            print(f"✅ Found {len(agents.get('value', []))} agent(s)")
            
            for agent in agents.get('value', []):
                print(f"   - Agent: {agent.get('name', 'Unknown')}")
                print(f"   - Index: {agent.get('indexName', 'Unknown')}")
                
            return True, agents.get('value', [])
        else:
            print(f"❌ Agent API returned status: {response.status_code}")
            print(f"Response: {response.text}")
            return False, []
            
    except Exception as e:
        print(f"❌ Failed to access knowledge agent: {str(e)}")
        return False, []

def test_simple_search(index_name):
    """Test simple text search to verify basic functionality."""
    print(f"\n🔎 Testing simple search on: {index_name}")
    
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
        
        # Try simple search
        results = list(search_client.search(search_text="*", top=3))
        
        if results:
            print(f"✅ Simple search returned {len(results)} results")
            for i, result in enumerate(results):
                content_preview = str(result).get('content', str(result))[:100] + "..."
                print(f"   Result {i+1}: {content_preview}")
            return True
        else:
            print("⚠️  Simple search returned no results")
            return False
            
    except Exception as e:
        print(f"❌ Simple search failed: {str(e)}")
        return False

def main():
    """Run comprehensive diagnostics."""
    print("🔬 Azure AI Search Agentic Retrieval Diagnostics")
    print("=" * 60)
    
    load_env()
    
    # Test 1: Basic Search Access
    search_success, indexes = test_search_access()
    if not search_success:
        print("\n❌ Cannot proceed - Azure Search access failed")
        sys.exit(1)
    
    # Test 2: Check index content
    index_name = os.getenv("INDEX_NAME", "sharepoint-index-2")
    print(f"\nUsing index: {index_name}")
    
    if index_name not in [idx.name for idx in indexes]:
        print(f"⚠️  Index '{index_name}' not found. Available indexes:")
        for idx in indexes:
            print(f"   - {idx.name}")
        
        # Try the delete3 index mentioned in logs
        if "delete3" in [idx.name for idx in indexes]:
            print("🔄 Switching to 'delete3' index (found in logs)")
            index_name = "delete3"
        else:
            print("❌ Cannot find a suitable index to test")
            sys.exit(1)
    
    has_content = check_index_content(index_name)
    
    # Test 3: Check vectorizer configuration
    check_vectorizer_config(index_name)
    
    # Test 4: Test agent access
    agent_success, agents = test_agent_access()
    
    # Test 5: Simple search test
    if has_content:
        test_simple_search(index_name)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    if search_success:
        print("✅ Azure Search access: WORKING")
    else:
        print("❌ Azure Search access: FAILED")
    
    if has_content:
        print(f"✅ Index '{index_name}' content: HAS DOCUMENTS")
    else:
        print(f"⚠️  Index '{index_name}' content: EMPTY OR NO ACCESS")
    
    if agent_success:
        print("✅ Knowledge Agent API: ACCESSIBLE")
    else:
        print("❌ Knowledge Agent API: FAILED")
    
    print("\n🎯 RECOMMENDATIONS:")
    
    if not has_content:
        print("1. ⚠️  Index appears empty - check document ingestion")
        print("2. 🔄 Try re-running the indexing process")
    
    if not agent_success:
        print("3. ⏱️  RBAC permissions may still be propagating (wait 5-10 minutes)")
        print("4. 🔄 Try refreshing the vectorizer configuration in Azure Portal")
    
    print("5. 🔄 Consider restarting your Streamlit app to pick up new configurations")
    print("6. 📊 Check Azure Portal for any indexing errors or warnings")

if __name__ == "__main__":
    main()
