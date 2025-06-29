#!/usr/bin/env python3
"""
Fixed debug script for delete3 index and delete3-agent using direct API with managed identity
"""

import os
import json
import requests
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_search_headers() -> dict:
    """Get authentication headers for Azure Search API calls using managed identity"""
    search_api_key = os.getenv("AZURE_SEARCH_KEY")
    
    if search_api_key:
        print("🔑 Using API Key authentication")
        return {"api-key": search_api_key, "Content-Type": "application/json"}
    
    # Use managed identity - get bearer token for Azure Search
    try:
        print("🔐 Using Managed Identity authentication")
        credential = DefaultAzureCredential()
        token = credential.get_token("https://search.azure.com/.default")
        return {"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"}
    except Exception as e:
        print(f"❌ Failed to get authentication token: {e}")
        raise RuntimeError("No Search authentication available. Set AZURE_SEARCH_KEY or use managed identity.")

def test_direct_search(index_name: str, query: str) -> dict:
    """Test direct search on the index to verify it has content"""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_api_key = os.getenv("AZURE_SEARCH_KEY")
    
    print(f"\\n🔍 Testing direct search on index '{index_name}'...")
    
    try:
        if search_api_key:
            credential = AzureKeyCredential(search_api_key)
        else:
            credential = DefaultAzureCredential()
            
        search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
        
        # Search for documents
        results = search_client.search(
            search_text=query,
            top=3,
            include_total_count=True
        )
        
        documents = list(results)
        total_count = getattr(results, 'get_count', lambda: len(documents))()
        
        print(f"✅ Found {total_count} documents in index")
        
        # Show sample documents
        for i, doc in enumerate(documents[:2]):
            print(f"  📄 Document {i+1}:")
            print(f"    ID: {doc.get('id', 'N/A')}")
            print(f"    Content preview: {str(doc.get('content', ''))[:100]}...")
            
        return {"success": True, "count": total_count, "documents": documents}
        
    except Exception as e:
        print(f"❌ Direct search failed: {e}")
        return {"success": False, "error": str(e)}

def test_agent_with_managed_identity(agent_name: str, index_name: str, query: str) -> dict:
    """Test knowledge agent using direct API with managed identity"""
    
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    if not search_endpoint:
        raise ValueError("AZURE_SEARCH_ENDPOINT not configured")
        
    # Extract service name from endpoint
    service_name = search_endpoint.replace("https://", "").replace(".search.windows.net", "")
    api_version = "2025-05-01-preview"
    
    # Build the knowledge agent API endpoint
    endpoint = f"https://{service_name}.search.windows.net/agents/{agent_name}/retrieve?api-version={api_version}"
    
    print(f"\\n🤖 Testing knowledge agent with managed identity...")
    print(f"   Agent: {agent_name}")
    print(f"   Index: {index_name}")
    print(f"   Query: {query}")
    print(f"   Endpoint: {endpoint}")
    
    # Prepare the request body (using the format from direct_api_retrieval.py)
    body = {
        "messages": [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Answer the question based only on the indexed sources. "
                            "Cite ref_id in square brackets. If unknown, say \\\"I don't know\\\"."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": query}],
            },
        ],
        "targetIndexParams": [
            {
                "indexName": index_name,
                "rerankerThreshold": 2.5,
                "includeReferenceSourceData": True
            }
        ]
    }
    
    try:
        # Get authentication headers using managed identity
        headers = get_search_headers()
        print(f"   Headers: {list(headers.keys())}")
        
        # Make the API call
        resp = requests.post(endpoint, headers=headers, json=body, timeout=60)
        
        print(f"   Response Status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"❌ HTTP Error {resp.status_code}: {resp.text}")
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": resp.text
            }
        
        # Parse response
        try:
            response_data = resp.json()
            print(f"   Response Keys: {list(response_data.keys())}")
            
            # Check for errors in response
            if "error" in response_data:
                error = response_data["error"]
                print(f"❌ Agent Error: {error}")
                return {
                    "success": False,
                    "agent_error": error
                }
            
            # Extract content using the same logic as direct_api_retrieval.py
            if "response" in response_data:
                try:
                    content = response_data["response"][0]["content"][0]["text"]
                    print(f"✅ Agent Response: {content}")
                    
                    # Try to parse as JSON chunks
                    try:
                        chunks = json.loads(content)
                        if isinstance(chunks, list):
                            print(f"   📦 Found {len(chunks)} chunks")
                            for i, chunk in enumerate(chunks[:2]):
                                print(f"     Chunk {i+1}: {str(chunk)[:100]}...")
                        else:
                            print(f"   📝 Direct answer: {content}")
                    except json.JSONDecodeError:
                        print(f"   📝 Text response: {content}")
                    
                    return {
                        "success": True,
                        "content": content,
                        "raw_response": response_data
                    }
                    
                except (KeyError, IndexError) as e:
                    print(f"❌ Unexpected response structure: {e}")
                    print(f"   Full response: {json.dumps(response_data, indent=2)}")
                    return {
                        "success": False,
                        "parse_error": str(e),
                        "raw_response": response_data
                    }
            else:
                print(f"❌ No 'response' key in response")
                print(f"   Available keys: {list(response_data.keys())}")
                return {
                    "success": False,
                    "missing_response_key": True,
                    "raw_response": response_data
                }
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response: {e}")
            print(f"   Raw response: {resp.text}")
            return {
                "success": False,
                "json_error": str(e),
                "raw_text": resp.text
            }
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return {
            "success": False,
            "request_error": str(e)
        }

def main():
    print("🔧 DELETE3 INDEX AND AGENT DEBUG - DIRECT API WITH MANAGED IDENTITY")
    print("=" * 80)
    
    # Configuration
    index_name = "delete3"
    agent_name = "delete3-agent"
    
    # Test queries - match the content we found in the index
    test_queries = [
        "What are Pacinian corpuscles?",  # Medical content found in index
        "anatomy",  # General medical term
        "somatosensory system",  # Specific medical term found
        "UltraDisk"  # Azure term that should NOT be found
    ]
    
    print(f"📊 Index: {index_name}")
    print(f"🤖 Agent: {agent_name}")
    print(f"🔍 Search Endpoint: {os.getenv('AZURE_SEARCH_ENDPOINT')}")
    print("=" * 80)
    
    # First, test direct search to confirm index has content
    for query in test_queries[:2]:  # Test first 2 queries
        search_result = test_direct_search(index_name, query)
        if search_result["success"] and search_result["count"] > 0:
            print(f"✅ Index contains relevant documents for '{query}'")
            break
    else:
        print("❌ Index appears to be empty or inaccessible")
        return
    
    print("\\n" + "=" * 80)
    print("🤖 TESTING KNOWLEDGE AGENT WITH DIRECT API + MANAGED IDENTITY")
    print("=" * 80)
    
    # Test agent with each query
    for i, query in enumerate(test_queries, 1):
        print(f"\\n--- Test {i}: {query} ---")
        result = test_agent_with_managed_identity(agent_name, index_name, query)
        
        if result["success"]:
            print(f"✅ Agent responded successfully")
        else:
            print(f"❌ Agent failed: {result}")
            
        print("-" * 40)
    
    print("\\n" + "=" * 80)
    print("🎯 SUMMARY")
    print("=" * 80)
    print("✅ Using direct API calls with managed identity authentication")
    print("✅ Following the same pattern as direct_api_retrieval.py")
    print("✅ Testing with queries that match the actual index content")
    print("=" * 80)

if __name__ == "__main__":
    main()
