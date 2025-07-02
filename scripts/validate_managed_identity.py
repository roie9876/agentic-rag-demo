#!/usr/bin/env python3
"""
Validate Managed Identity Setup for Azure Function
==================================================

This script helps validate that the Azure Function's managed identity
is properly configured with the required RBAC roles for Azure AI Search
and Azure OpenAI.

Usage:
    python scripts/validate_managed_identity.py

Prerequisites:
    1. Azure Function App with system-assigned managed identity enabled
    2. Required RBAC roles assigned:
       - Azure AI Search: Search Index Data Contributor + Search Service Contributor
       - Azure OpenAI: Cognitive Services OpenAI User
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from openai import AzureOpenAI
from azure.identity import get_bearer_token_provider
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_search_access():
    """Test Azure AI Search access with managed identity."""
    print("🔍 Testing Azure AI Search access...")
    
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    if not search_endpoint:
        print("❌ AZURE_SEARCH_ENDPOINT not configured")
        return False
    
    try:
        # Test credentials
        cred = DefaultAzureCredential()
        
        # Test index client access
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=cred)
        indexes = list(index_client.list_indexes())
        print(f"✅ Successfully connected to Azure AI Search")
        print(f"   Found {len(indexes)} indexes")
        
        # Test search client access (if index exists)
        if indexes:
            test_index = indexes[0].name
            search_client = SearchClient(endpoint=search_endpoint, index_name=test_index, credential=cred)
            # Try a simple search
            results = search_client.search("*", top=1)
            doc_count = sum(1 for _ in results)
            print(f"   Successfully queried index '{test_index}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Azure AI Search access failed: {e}")
        print("   Check that managed identity has these roles:")
        print("   - Search Index Data Contributor")
        print("   - Search Service Contributor")
        return False

def test_openai_access():
    """Test Azure OpenAI access with managed identity."""
    print("\n🤖 Testing Azure OpenAI access...")
    
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or os.getenv("OPENAI_DEPLOYMENT")
    
    if not openai_endpoint:
        print("❌ AZURE_OPENAI_ENDPOINT not configured")
        return False
    
    if not openai_deployment:
        print("❌ AZURE_OPENAI_CHAT_DEPLOYMENT or OPENAI_DEPLOYMENT not configured")
        return False
    
    try:
        # Test managed identity token provider
        cred = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(cred, "https://cognitiveservices.azure.com/.default")
        
        client = AzureOpenAI(
            azure_ad_token_provider=token_provider,
            azure_endpoint=openai_endpoint,
            api_version="2024-02-15-preview"
        )
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model=openai_deployment,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        
        print(f"✅ Successfully connected to Azure OpenAI")
        print(f"   Using deployment: {openai_deployment}")
        print(f"   Test response: {response.choices[0].message.content.strip()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Azure OpenAI access failed: {e}")
        print("   Check that managed identity has this role:")
        print("   - Cognitive Services OpenAI User")
        return False

def main():
    """Run all validation tests."""
    print("🔐 Validating Managed Identity Setup for Azure Function")
    print("=" * 60)
    
    # Test each service
    search_ok = test_search_access()
    openai_ok = test_openai_access()
    
    print("\n" + "=" * 60)
    print("📋 Summary:")
    print(f"   Azure AI Search: {'✅ PASS' if search_ok else '❌ FAIL'}")
    print(f"   Azure OpenAI:    {'✅ PASS' if openai_ok else '❌ FAIL'}")
    
    if search_ok and openai_ok:
        print("\n🎉 All tests passed! Managed identity is properly configured.")
        print("\n💡 Next steps:")
        print("   1. Deploy your function code")
        print("   2. Test the function endpoint")
        print("   3. Remove any API keys from environment variables (optional)")
    else:
        print("\n⚠️  Some tests failed. Please check RBAC role assignments.")
        print("\n🔧 Troubleshooting:")
        print("   1. Verify managed identity is enabled on the Function App")
        print("   2. Check RBAC role assignments in Azure Portal")
        print("   3. Wait a few minutes for role assignments to propagate")
        
        if not search_ok:
            print("\n   Azure AI Search roles needed:")
            print("   - Search Index Data Contributor")
            print("   - Search Service Contributor")
            
        if not openai_ok:
            print("\n   Azure OpenAI role needed:")
            print("   - Cognitive Services OpenAI User")

if __name__ == "__main__":
    main()
