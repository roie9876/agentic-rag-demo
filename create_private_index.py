#!/usr/bin/env python3
"""
Create a private index with proper vectorizer configuration for managed identity.
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
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters
)

def create_private_index():
    """Create a search index with managed identity vectorization."""
    
    # Load environment variables
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    openai_endpoint = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")
    embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
    
    if not search_endpoint or not openai_endpoint:
        print("❌ Missing required environment variables:")
        print(f"   AZURE_SEARCH_ENDPOINT: {search_endpoint or 'NOT SET'}")
        print(f"   AZURE_OPENAI_ENDPOINT: {openai_endpoint or 'NOT SET'}")
        return False
    
    print(f"🔧 Creating index with configuration:")
    print(f"   Search Endpoint: {search_endpoint}")
    print(f"   OpenAI Endpoint: {openai_endpoint}")
    print(f"   Embedding Deployment: {embedding_deployment}")
    print()
    
    # Initialize the search client with managed identity
    credential = DefaultAzureCredential()
    search_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
    
    # Define the index name
    index_name = "private-test-index"
    
    # Configure the vectorizer for managed identity
    vectorizer = AzureOpenAIVectorizer(
        vectorizer_name="default_vectorizer",
        kind="azureOpenAI",
        azure_open_ai_parameters=AzureOpenAIVectorizerParameters(
            resource_url=openai_endpoint,
            deployment_name=embedding_deployment,
            # Note: No API key - using managed identity
        )
    )
    
    # Configure vector search
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="default_algorithm")
        ],
        profiles=[
            VectorSearchProfile(
                name="default_profile",
                algorithm_configuration_name="default_algorithm",
                vectorizer_name="default_vectorizer"
            )
        ],
        vectorizers=[vectorizer]
    )
    
    # Define the index fields
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
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
            retrievable=True
        ),
        SearchField(
            name="metadata",
            type=SearchFieldDataType.String,
            searchable=False,
            retrievable=True
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            retrievable=False,
            vector_search_dimensions=3072,  # text-embedding-3-large dimensions
            vector_search_profile_name="default_profile"
        )
    ]
    
    # Create the index
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search
    )
    
    try:
        print(f"🚀 Creating index '{index_name}'...")
        result = search_client.create_index(index)
        print(f"✅ Successfully created index: {result.name}")
        print(f"   Fields: {len(result.fields)}")
        print(f"   Vectorizer: {result.vector_search.vectorizers[0].vectorizer_name}")
        print()
        
        # Test the vectorizer configuration
        print("🧪 Testing vectorizer configuration...")
        test_vectorizer(search_client, index_name)
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create index: {str(e)}")
        if "403" in str(e):
            print("\n💡 This might be the same 403 error. Let's check the vectorizer configuration...")
            print("   The issue might be:")
            print("   1. API version compatibility")
            print("   2. Managed identity configuration")
            print("   3. OpenAI resource endpoint format")
        return False

def test_vectorizer(search_client, index_name):
    """Test the vectorizer by checking if it's properly configured."""
    try:
        # Get the index to verify configuration
        index = search_client.get_index(index_name)
        vectorizer = index.vector_search.vectorizers[0]
        
        print(f"✅ Vectorizer configuration verified:")
        print(f"   Name: {vectorizer.vectorizer_name}")
        print(f"   Kind: {vectorizer.kind}")
        if hasattr(vectorizer, 'azure_open_ai_parameters'):
            params = vectorizer.azure_open_ai_parameters
            print(f"   Resource URL: {params.resource_url}")
            print(f"   Deployment: {params.deployment_name}")
            print(f"   Auth Method: Managed Identity (no API key)")
        
    except Exception as e:
        print(f"⚠️ Could not verify vectorizer: {str(e)}")

if __name__ == "__main__":
    # Load environment variables from .env file
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    except FileNotFoundError:
        print("⚠️ .env file not found. Make sure environment variables are set.")
    
    success = create_private_index()
    if success:
        print("🎉 Index creation completed successfully!")
        print("   You can now test document upload and vectorization.")
    else:
        print("❌ Index creation failed. Check the configuration and try again.")
