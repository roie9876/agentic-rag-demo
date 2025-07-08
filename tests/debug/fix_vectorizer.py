#!/usr/bin/env python3
"""
Script to fix the delete3 index by adding the vectorizer configuration
and ensuring documents get properly vectorized.
"""
import os
import json
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import *

def load_env():
    """Load environment variables from .env file."""
    from dotenv import load_dotenv
    load_dotenv()

def fix_vectorizer_configuration():
    """Add vectorizer configuration to the delete3 index."""
    print("🔧 Fixing vectorizer configuration for delete3 index...")
    
    load_env()
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    embedding_endpoint = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT")
    embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    
    try:
        credential = DefaultAzureCredential()
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        
        # Get current index
        index = index_client.get_index("delete3")
        print("✅ Retrieved current index definition")
        
        # Create Azure OpenAI vectorizer
        vectorizer = AzureOpenAIVectorizer(
            name="azure_openai_text_3_large",
            kind="azureOpenAI",
            azure_open_ai_parameters=AzureOpenAIParameters(
                resource_uri=embedding_endpoint,
                deployment_id=embedding_deployment,
                model_name="text-embedding-3-large",
                api_key=None  # Use managed identity
            )
        )
        
        # Add vectorizer to index
        if not index.vectorizers:
            index.vectorizers = []
        
        # Remove any existing vectorizer with the same name
        index.vectorizers = [v for v in index.vectorizers if v.name != "azure_openai_text_3_large"]
        index.vectorizers.append(vectorizer)
        
        # Update vector profile to use the new vectorizer
        if index.vector_search and index.vector_search.profiles:
            for profile in index.vector_search.profiles:
                if profile.name == "hnsw_text_3_large":
                    profile.vectorizer = "azure_openai_text_3_large"
                    print(f"✅ Updated vector profile '{profile.name}' to use new vectorizer")
        
        # Add a vector field to the index if it doesn't exist
        content_vector_field = SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,  # text-embedding-3-large dimensions
            vector_search_profile_name="hnsw_text_3_large"
        )
        
        # Check if contentVector field already exists
        has_vector_field = any(field.name == "contentVector" for field in index.fields)
        if not has_vector_field:
            index.fields.append(content_vector_field)
            print("✅ Added contentVector field to index")
        else:
            print("✅ contentVector field already exists")
        
        # Update the index
        index_client.create_or_update_index(index)
        print("✅ Successfully updated index with vectorizer configuration")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update vectorizer configuration: {str(e)}")
        return False

def trigger_reindexing():
    """Trigger reindexing to generate vectors for existing documents."""
    print("\n🔄 Triggering reindexing to generate vectors...")
    
    load_env()
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        
        # Get indexers that might be associated with this index
        indexers = list(index_client.list_indexers())
        
        print(f"✅ Found {len(indexers)} indexer(s)")
        
        delete3_indexers = [idx for idx in indexers if "delete3" in idx.target_index_name.lower()]
        
        if delete3_indexers:
            for indexer in delete3_indexers:
                print(f"🔄 Running indexer: {indexer.name}")
                index_client.run_indexer(indexer.name)
                print(f"✅ Started indexer: {indexer.name}")
        else:
            print("⚠️  No indexers found for delete3 index")
            print("ℹ️  You may need to manually re-upload documents or trigger indexing in Azure Portal")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to trigger reindexing: {str(e)}")
        return False

def test_vectorizer():
    """Test if the vectorizer is working."""
    print("\n🧪 Testing vectorizer functionality...")
    
    load_env()
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        
        # Get updated index
        index = index_client.get_index("delete3")
        
        # Check vectorizers
        if index.vectorizers:
            print(f"✅ Index now has {len(index.vectorizers)} vectorizer(s):")
            for vectorizer in index.vectorizers:
                print(f"   - {vectorizer.name} ({vectorizer.kind})")
        else:
            print("❌ No vectorizers found")
        
        # Check vector fields
        vector_fields = [f for f in index.fields if hasattr(f, 'vector_search_dimensions')]
        if vector_fields:
            print(f"✅ Index has {len(vector_fields)} vector field(s):")
            for field in vector_fields:
                print(f"   - {field.name} ({field.vector_search_dimensions} dimensions)")
        else:
            print("❌ No vector fields found")
        
        return len(index.vectorizers) > 0 and len(vector_fields) > 0
        
    except Exception as e:
        print(f"❌ Failed to test vectorizer: {str(e)}")
        return False

def main():
    """Fix the vectorizer configuration and trigger reindexing."""
    print("🔧 Azure AI Search Vectorizer Fix")
    print("=" * 50)
    
    # Step 1: Fix vectorizer configuration
    vectorizer_success = fix_vectorizer_configuration()
    
    if vectorizer_success:
        # Step 2: Test the configuration
        test_success = test_vectorizer()
        
        if test_success:
            # Step 3: Trigger reindexing
            trigger_reindexing()
            
            print("\n" + "=" * 50)
            print("✅ VECTORIZER FIX COMPLETED!")
            print("=" * 50)
            print("🎯 Next Steps:")
            print("1. ⏱️  Wait 5-10 minutes for reindexing to complete")
            print("2. 🔄 Go to Azure Portal and verify vectorizer is working")
            print("3. 🧪 Test agentic retrieval again in your Streamlit app")
            print("4. 📊 Check Azure Portal for indexing progress")
        else:
            print("\n❌ Vectorizer configuration test failed")
    else:
        print("\n❌ Failed to fix vectorizer configuration")

if __name__ == "__main__":
    main()
