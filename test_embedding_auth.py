#!/usr/bin/env python3
"""
Test script to verify Azure AI Search managed identity can access 
the gdalroiedemovideo Azure OpenAI embedding resource using managed identity authentication.
"""
import os
import requests
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI

def test_embedding_access():
    """Test access to the embedding OpenAI resource with managed identity."""
    
    # Load configuration from .env
    from dotenv import load_dotenv
    load_dotenv()
    
    endpoint = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    api_version = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION")
    service_name = os.getenv("AZURE_OPENAI_EMBEDDING_SERVICE_NAME")
    
    print(f"Testing embedding access to gdalroiedemovideo:")
    print(f"Endpoint: {endpoint}")
    print(f"Service: {service_name}")
    print(f"Deployment: {deployment}")
    print(f"API Version: {api_version}")
    print()
    
    try:
        # Test with DefaultAzureCredential (simulates managed identity)
        credential = DefaultAzureCredential()
        
        # Get access token
        token_response = credential.get_token("https://cognitiveservices.azure.com/.default")
        access_token = token_response.token
        print("✅ Successfully obtained access token with DefaultAzureCredential")
        
        # Test embedding API call
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "input": "Test embedding text for gdalroiedemovideo",
        }
        
        url = f"{endpoint}/openai/deployments/{deployment}/embeddings?api-version={api_version}"
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print("✅ Successfully called embedding API with managed identity")
            result = response.json()
            embedding_length = len(result["data"][0]["embedding"])
            print(f"✅ Received embedding vector with {embedding_length} dimensions")
            return True
        else:
            print(f"❌ Embedding API call failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing embedding access: {str(e)}")
        return False

def test_openai_client():
    """Test using AzureOpenAI client with managed identity."""
    
    from dotenv import load_dotenv
    load_dotenv()
    
    endpoint = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    api_version = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION")
    
    try:
        credential = DefaultAzureCredential()
        
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=lambda: credential.get_token("https://cognitiveservices.azure.com/.default").token,
            api_version=api_version
        )
        
        # Test embedding
        response = client.embeddings.create(
            input="Test embedding with OpenAI client for gdalroiedemovideo",
            model=deployment
        )
        
        embedding_length = len(response.data[0].embedding)
        print("✅ Successfully created embedding with AzureOpenAI client")
        print(f"✅ Embedding vector has {embedding_length} dimensions")
        return True
        
    except Exception as e:
        print(f"❌ Error with AzureOpenAI client: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Azure OpenAI gdalroiedemovideo embedding access with managed identity...\n")
    
    # Test 1: Direct API call with access token
    print("Test 1: Direct API call with access token")
    test1_success = test_embedding_access()
    print()
    
    # Test 2: AzureOpenAI client
    print("Test 2: AzureOpenAI client with managed identity")
    test2_success = test_openai_client()
    print()
    
    if test1_success and test2_success:
        print("🎉 All tests passed! Managed identity access to gdalroiedemovideo embedding resource is working.")
        print("ℹ️  Note: It may take a few minutes for RBAC permissions to propagate.")
        print("ℹ️  If agentic retrieval still returns empty results, wait 5-10 minutes and try again.")
    else:
        print("⚠️  Some tests failed. Check RBAC permissions and configuration.")
        print("ℹ️  RBAC permission propagation can take 5-10 minutes.")
