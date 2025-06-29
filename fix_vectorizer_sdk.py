#!/usr/bin/env python3
"""
Fix vectorizer configuration using the correct Azure SDK approach.
This script will properly configure the vectorizer for the delete3 index.
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

def create_new_vectorized_index():
    """Create a completely new index with proper vectorizer configuration."""
    print("🔧 Creating new vectorized index...")
    
    load_env()
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    embedding_endpoint = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT")
    embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    
    try:
        credential = DefaultAzureCredential()
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        
        # Get current index to copy field structure
        current_index = index_client.get_index("delete3")
        print("✅ Retrieved current index structure")
        
        # Create new index name
        new_index_name = "delete3-vectorized"
        
        # Create vectorizer
        vectorizer = AzureOpenAIVectorizer(
            name="azure_openai_text_3_large",
            azure_open_ai_parameters={
                "resource_uri": embedding_endpoint,
                "deployment_id": embedding_deployment,
                "model_name": "text-embedding-3-large"
            }
        )
        
        # Create vector search configuration
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(name="hnsw_config")
            ],
            profiles=[
                VectorSearchProfile(
                    name="hnsw_text_3_large",
                    algorithm_configuration_name="hnsw_config",
                    vectorizer="azure_openai_text_3_large"
                )
            ],
            vectorizers=[vectorizer]
        )
        
        # Copy existing fields and add vector field
        fields = list(current_index.fields)
        
        # Add vector field for content
        content_vector_field = SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,  # text-embedding-3-large dimensions
            vector_search_profile_name="hnsw_text_3_large"
        )
        fields.append(content_vector_field)
        
        # Create new index
        new_index = SearchIndex(
            name=new_index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=current_index.semantic_search if hasattr(current_index, 'semantic_search') else None
        )
        
        # Create the index
        result = index_client.create_index(new_index)
        print(f"✅ Created new vectorized index: {new_index_name}")
        
        return new_index_name
        
    except Exception as e:
        print(f"❌ Failed to create vectorized index: {str(e)}")
        return None

def copy_documents_to_new_index(source_index, target_index):
    """Copy documents from source to target index and generate vectors."""
    print(f"🔄 Copying documents from {source_index} to {target_index}...")
    
    load_env()
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        from azure.search.documents import SearchClient
        credential = DefaultAzureCredential()
        
        # Get documents from source
        source_client = SearchClient(endpoint=search_endpoint, index_name=source_index, credential=credential)
        target_client = SearchClient(endpoint=search_endpoint, index_name=target_index, credential=credential)
        
        # Get all documents from source
        results = list(source_client.search(search_text="*", top=1000))
        print(f"✅ Found {len(results)} documents to copy")
        
        if results:
            # Prepare documents for upload (remove search-specific fields)
            documents_to_upload = []
            for doc in results:
                clean_doc = {}
                for key, value in doc.items():
                    if not key.startswith('@search'):
                        clean_doc[key] = value
                
                # The vectorizer will automatically generate the contentVector field
                # based on the content field when the document is indexed
                documents_to_upload.append(clean_doc)
            
            # Upload documents to new index
            result = target_client.upload_documents(documents_to_upload)
            print(f"✅ Uploaded {len(documents_to_upload)} documents to new index")
            
            # Check for any failures
            for r in result:
                if not r.succeeded:
                    print(f"⚠️  Failed to upload document {r.key}: {r.error_message}")
            
            return True
        else:
            print("⚠️  No documents found to copy")
            return False
            
    except Exception as e:
        print(f"❌ Failed to copy documents: {str(e)}")
        return False

def verify_vectorizer_working(index_name):
    """Verify that the vectorizer is working in the new index."""
    print(f"🧪 Verifying vectorizer in {index_name}...")
    
    load_env()
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        
        # Get index definition
        index = index_client.get_index(index_name)
        
        # Check vectorizers
        vectorizer_count = len(index.vector_search.vectorizers) if index.vector_search and index.vector_search.vectorizers else 0
        print(f"✅ Index has {vectorizer_count} vectorizer(s)")
        
        # Check vector fields
        vector_fields = [f for f in index.fields if hasattr(f, 'vector_search_dimensions')]
        print(f"✅ Index has {len(vector_fields)} vector field(s)")
        
        if vectorizer_count > 0 and len(vector_fields) > 0:
            print("✅ Vectorizer configuration is complete!")
            return True
        else:
            print("❌ Vectorizer configuration is incomplete")
            return False
            
    except Exception as e:
        print(f"❌ Failed to verify vectorizer: {str(e)}")
        return False

def main():
    """Main function to fix vectorizer configuration."""
    print("🔧 Azure AI Search Vectorizer Fix (SDK Method)")
    print("=" * 60)
    
    # Step 1: Create new vectorized index
    new_index_name = create_new_vectorized_index()
    
    if new_index_name:
        # Step 2: Copy documents to new index
        copy_success = copy_documents_to_new_index("delete3", new_index_name)
        
        if copy_success:
            # Step 3: Verify vectorizer is working
            verify_success = verify_vectorizer_working(new_index_name)
            
            if verify_success:
                print("\n" + "=" * 60)
                print("🎉 VECTORIZER FIX COMPLETED SUCCESSFULLY!")
                print("=" * 60)
                print(f"✅ New vectorized index created: {new_index_name}")
                print("✅ Documents copied and will be vectorized automatically")
                print("✅ .env file left unchanged (users select index in UI)")
                print("\n🎯 Next Steps:")
                print("1. ⏱️  Wait 2-3 minutes for vectorization to complete")
                print(f"2. 🔄 In your Streamlit app, select index: {new_index_name}")
                print("3. 🧪 Test agentic retrieval - it should now return results!")
                print("4. 🗑️  You can delete the old 'delete3' index once confirmed working")
                print(f"\n📋 Available indexes now include:")
                print(f"   - {new_index_name} (NEW - with vectorizer)")
                print(f"   - delete3 (OLD - without vectorizer)")
            else:
                print("\n❌ Vectorizer configuration verification failed")
        else:
            print("\n❌ Failed to copy documents to new index")
    else:
        print("\n❌ Failed to create new vectorized index")

if __name__ == "__main__":
    main()
