#!/usr/bin/env python3
"""
Focused debug script for delete3 index and delete3-agent empty results issue.
This script will test both direct search and agent-based retrieval.
"""

import os
import json
import asyncio
from dotenv import load_dotenv
import aiohttp
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

load_dotenv()

def get_azure_credentials():
    """Get Azure credentials (Managed Identity or API Key)"""
    api_key = os.getenv("AZURE_SEARCH_KEY", "").strip()
    if api_key:
        print("🔑 Using API Key authentication")
        return AzureKeyCredential(api_key)
    else:
        print("🔐 Using Managed Identity (RBAC) authentication")
        return DefaultAzureCredential()

async def test_direct_search(index_name: str, query: str):
    """Test direct search on the index"""
    print(f"\n🔍 DIRECT SEARCH TEST - Index: {index_name}")
    print("=" * 80)
    
    try:
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        credential = get_azure_credentials()
        
        search_client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=credential
        )
        
        # Test basic search
        print(f"Query: '{query}'")
        results = search_client.search(
            search_text=query,
            top=5,
            include_total_count=True
        )
        
        print(f"Total results: {results.get_count()}")
        
        count = 0
        for result in results:
            count += 1
            print(f"\n📄 Document {count}:")
            print(f"   Score: {result.get('@search.score', 'N/A')}")
            
            # Show key fields
            for key in ['content', 'title', 'chunk_id', 'metadata_storage_name']:
                if key in result:
                    value = result[key]
                    if isinstance(value, str) and len(value) > 200:
                        value = value[:200] + "..."
                    print(f"   {key}: {value}")
        
        if count == 0:
            print("❌ No documents found in direct search")
            return False
        else:
            print(f"✅ Found {count} documents in direct search")
            return True
            
    except Exception as e:
        print(f"❌ Direct search failed: {str(e)}")
        return False

async def test_agent_retrieval(agent_name: str, index_name: str, query: str):
    """Test knowledge agent retrieval"""
    print(f"\n🤖 AGENT RETRIEVAL TEST - Agent: {agent_name}")
    print("=" * 80)
    
    try:
        project_endpoint = os.getenv("PROJECT_ENDPOINT")
        function_key = os.getenv("AGENT_FUNC_KEY")
        api_version = os.getenv("API_VERSION", "2025-05-01-preview")
        
        if not all([project_endpoint, function_key]):
            print("❌ Missing PROJECT_ENDPOINT or AGENT_FUNC_KEY")
            return False
        
        url = f"{project_endpoint}/query"
        
        headers = {
            "Authorization": f"Bearer {function_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "agentName": agent_name,
            "sessionState": {},
            "context": {
                "indexName": index_name,
            },
            "messages": [
                {
                    "role": "user",
                    "content": query
                }
            ],
            "stream": False
        }
        
        print(f"Request URL: {url}")
        print(f"Agent Name: {agent_name}")
        print(f"Index Name: {index_name}")
        print(f"Query: '{query}'")
        print(f"API Version: {api_version}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                print(f"Response Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract the actual response content
                    if 'result' in data and 'message' in data['result']:
                        content = data['result']['message'].get('content', '')
                        print(f"✅ Agent Response Length: {len(content)} characters")
                        
                        if content.strip():
                            print(f"📄 Agent Response Preview:")
                            preview = content[:500] + "..." if len(content) > 500 else content
                            print(f"   {preview}")
                            return True
                        else:
                            print("❌ Agent returned empty content")
                            print(f"Full response structure: {json.dumps(data, indent=2)}")
                            return False
                    else:
                        print("❌ Unexpected response structure")
                        print(f"Full response: {json.dumps(data, indent=2)}")
                        return False
                        
                elif response.status == 404:
                    print(f"❌ Agent '{agent_name}' not found (404)")
                    return False
                else:
                    error_text = await response.text()
                    print(f"❌ Request failed with status {response.status}")
                    print(f"Error: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Agent retrieval failed: {str(e)}")
        return False

async def test_agent_configuration(agent_name: str):
    """Test if agent is properly configured"""
    print(f"\n⚙️ AGENT CONFIGURATION TEST - Agent: {agent_name}")
    print("=" * 80)
    
    try:
        project_endpoint = os.getenv("PROJECT_ENDPOINT")
        function_key = os.getenv("AGENT_FUNC_KEY")
        
        # Try to get agent info (if there's an endpoint for it)
        # This is a hypothetical endpoint - adjust based on actual API
        url = f"{project_endpoint}/agents/{agent_name}"
        
        headers = {
            "Authorization": f"Bearer {function_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Agent configuration retrieved:")
                    print(json.dumps(data, indent=2))
                    return True
                elif response.status == 404:
                    print(f"❌ Agent '{agent_name}' not found")
                    return False
                else:
                    print(f"⚠️ Could not retrieve agent config (status: {response.status})")
                    return None
                
    except Exception as e:
        print(f"⚠️ Could not test agent configuration: {str(e)}")
        return None

async def main():
    """Main debug function"""
    print("🐛 FOCUSED DEBUG: delete3 Index & delete3-agent Empty Results")
    print("=" * 80)
    
    index_name = "delete3"
    agent_name = "delete3-agent"
    
    # Test with different types of queries
    test_queries = [
        "What is Azure?",  # Generic query
        "UltraDisk",       # Specific term from the index
        "storage",         # Common term
        "performance"      # Another common term
    ]
    
    print(f"Testing index: {index_name}")
    print(f"Testing agent: {agent_name}")
    print(f"Test queries: {test_queries}")
    
    # Test agent configuration first
    await test_agent_configuration(agent_name)
    
    # Test each query
    for i, query in enumerate(test_queries, 1):
        print(f"\n" + "=" * 80)
        print(f"TEST {i}/{len(test_queries)}: Query = '{query}'")
        print("=" * 80)
        
        # Test direct search
        direct_success = await test_direct_search(index_name, query)
        
        # Test agent retrieval
        agent_success = await test_agent_retrieval(agent_name, index_name, query)
        
        # Summary for this query
        print(f"\n📊 QUERY '{query}' SUMMARY:")
        print(f"   Direct Search: {'✅ SUCCESS' if direct_success else '❌ FAILED'}")
        print(f"   Agent Retrieval: {'✅ SUCCESS' if agent_success else '❌ FAILED'}")
        
        if direct_success and not agent_success:
            print("⚠️ ISSUE: Direct search works but agent fails - this is the core problem!")
    
    print(f"\n" + "=" * 80)
    print("🏁 DEBUG COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
