#!/usr/bin/env python3
"""
Create a properly configured Azure AI Search index for private mode with working vectorization.
"""

import os
import json
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    VectorSearchAlgorithmConfiguration,
    HnswAlgorithmConfiguration,
    VectorSearchVectorizer,
    AzureOpenAIVectorizer,
    AzureOpenAIParameters,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch
)

def create_private_index():
    """Create a new index with proper vectorization configuration for private mode."""
    
    # Configuration
    SEARCH_ENDPOINT = "https://private-ai-search.search.windows.net"
    INDEX_NAME = "private-test-working"
    OPENAI_ENDPOINT = "https://private-openai-agentic.openai.azure.com/"
    EMBEDDING_DEPLOYMENT = "text-embedding-3-large"
    
    print(f"🔧 Creating private index: {INDEX_NAME}")
    print(f"📍 Search Service: {SEARCH_ENDPOINT}")
    print(f"🤖 OpenAI Endpoint: {OPENAI_ENDPOINT}")
    print(f"📊 Embedding Deployment: {EMBEDDING_DEPLOYMENT}")
    
    # Initialize client with managed identity
    credential = DefaultAzureCredential()
    client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=credential)
    
    # Define fields
    fields = [
        SearchField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            searchable=False,
            filterable=True,
            retrievable=True
        ),
        SearchField(
            name="title",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            retrievable=True,
            analyzer_name="standard.lucene"
        ),
        SearchField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
            retrievable=True,
            analyzer_name="standard.lucene"
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,  # text-embedding-3-large dimensions
            vector_search_profile_name="default-vector-profile"
        ),
        SearchField(
            name="metadata",
            type=SearchFieldDataType.String,
            searchable=False,
            filterable=True,
            retrievable=True
        )
    ]
    
    # Define vectorizer with working API version
    vectorizer = AzureOpenAIVectorizer(
        name="default-vectorizer",
        kind="azureOpenAI",
        azure_open_ai_parameters=AzureOpenAIParameters(
            resource_uri=OPENAI_ENDPOINT,
            deployment_id=EMBEDDING_DEPLOYMENT,
            api_version="2023-05-15"  # Confirmed working version!
        )
    )
    
    # Define vector search configuration
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="default-algorithm")
        ],
        profiles=[
            VectorSearchProfile(
                name="default-vector-profile",
                algorithm_configuration_name="default-algorithm",
                vectorizer="default-vectorizer"
            )
        ],
        vectorizers=[vectorizer]
    )
    
    # Define semantic search (optional but recommended)
    semantic_config = SemanticConfiguration(
        name="default-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[SemanticField(field_name="content")]
        )
    )
    
    semantic_search = SemanticSearch(configurations=[semantic_config])
    
    # Create the index
    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search
    )
    
    try:
        print("🚀 Creating index...")
        result = client.create_index(index)
        print(f"✅ Index '{INDEX_NAME}' created successfully!")
        print(f"📋 Index details:")
        print(f"   - Name: {result.name}")
        print(f"   - Fields: {len(result.fields)}")
        print(f"   - Vectorizer: {result.vector_search.vectorizers[0].name}")
        print(f"   - API Version: {result.vector_search.vectorizers[0].azure_open_ai_parameters.api_version}")
        print(f"   - Authentication: Managed Identity")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating index: {str(e)}")
        return False

if __name__ == "__main__":
    print("🎯 Azure AI Search Private Index Creator")
    print("=" * 50)
    
    success = create_private_index()
    
    if success:
        print("\n🎉 Success! Your new index should work with private mode vectorization.")
        print("\n📋 Next steps:")
        print("1. Go to Azure portal and verify the index was created")
        print("2. Test uploading a document")
        print("3. Verify vectorization works without 403 errors")
    else:
        print("\n❌ Failed to create index. Check the error message above.")
