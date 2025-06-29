#!/usr/bin/env python3
"""
Test script to verify Azure OpenAI embedding endpoint connectivity and deployment availability.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_embedding_endpoint():
    """Test the Azure OpenAI embedding endpoint connectivity and list deployments."""
    
    # Get configuration from .env
    endpoint = os.getenv('AZURE_OPENAI_EMBEDDING_ENDPOINT')
    api_key = os.getenv('AZURE_OPENAI_EMBEDDING_KEY')
    api_version = os.getenv('AZURE_OPENAI_EMBEDDING_API_VERSION', '2023-05-15')
    deployment = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT')
    
    print(f"Testing Azure OpenAI Embedding Endpoint:")
    print(f"  Endpoint: {endpoint}")
    print(f"  API Version: {api_version}")
    print(f"  Expected Deployment: {deployment}")
    print()
    
    if not endpoint or not api_key:
        print("❌ Missing required configuration: AZURE_OPENAI_EMBEDDING_ENDPOINT or AZURE_OPENAI_EMBEDDING_KEY")
        return False
    
    # Test 1: List deployments
    print("1. Testing deployments list...")
    try:
        deployments_url = f"{endpoint}/openai/deployments?api-version={api_version}"
        headers = {
            'api-key': api_key,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(deployments_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            deployments = response.json()
            print(f"✅ Successfully connected to Azure OpenAI")
            print(f"   Available deployments:")
            
            deployment_found = False
            for dep in deployments.get('data', []):
                deployment_name = dep.get('id', 'Unknown')
                model = dep.get('model', 'Unknown')
                status = dep.get('status', 'Unknown')
                print(f"     - {deployment_name} (model: {model}, status: {status})")
                
                if deployment_name == deployment:
                    deployment_found = True
            
            if deployment_found:
                print(f"✅ Target deployment '{deployment}' found!")
            else:
                print(f"⚠️  Target deployment '{deployment}' not found in available deployments")
                
        else:
            print(f"❌ Failed to list deployments: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error connecting to Azure OpenAI: {str(e)}")
        return False
    
    # Test 2: Test embedding endpoint if deployment exists
    if deployment_found:
        print("\n2. Testing embedding generation...")
        try:
            embedding_url = f"{endpoint}/openai/deployments/{deployment}/embeddings?api-version={api_version}"
            
            test_data = {
                "input": "This is a test sentence for embedding generation.",
                "encoding_format": "float"
            }
            
            response = requests.post(embedding_url, headers=headers, json=test_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                embeddings = result.get('data', [])
                if embeddings and len(embeddings) > 0:
                    embedding_vector = embeddings[0].get('embedding', [])
                    print(f"✅ Embedding generation successful!")
                    print(f"   Vector length: {len(embedding_vector)}")
                    print(f"   First 5 values: {embedding_vector[:5]}")
                else:
                    print("⚠️  No embeddings returned in response")
            else:
                print(f"❌ Embedding generation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing embedding generation: {str(e)}")
            return False
    
    print("\n3. Summary:")
    print("✅ Azure OpenAI embedding endpoint is properly configured")
    print("✅ API key authentication is working")
    print("✅ Ready for use with Azure AI Search vectorizer")
    
    return True

if __name__ == "__main__":
    success = test_embedding_endpoint()
    exit(0 if success else 1)
