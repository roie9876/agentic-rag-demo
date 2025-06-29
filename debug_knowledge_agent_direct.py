#!/usr/bin/env python3
"""
Debug Knowledge Agent - Test agent retrieval functionality using direct API calls
(Based on the working logic from backup-agentic-rag-demo.py and direct_api_retrieval.py)
"""

import os
import json
import requests
from typing import Dict, List, Any
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv(Path(__file__).resolve().parent / ".env")

from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

def get_search_headers() -> dict:
    """Get authentication headers for Azure Search API calls"""
    search_api_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("SEARCH_API_KEY")
    
    if search_api_key:
        print("✅ Using API key authentication")
        return {"api-key": search_api_key, "Content-Type": "application/json"}
    
    # Try to get bearer token
    try:
        print("✅ Using Managed Identity authentication")
        token = DefaultAzureCredential().get_token("https://search.azure.com/.default").token
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    except Exception as e:
        raise RuntimeError(f"No Search authentication available. Set AZURE_SEARCH_KEY or use managed identity. Error: {e}")

def search_client_helper(index_name: str) -> SearchClient:
    """Create a SearchClient for document lookups"""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_api_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("SEARCH_API_KEY")
    
    if search_api_key:
        credential = AzureKeyCredential(search_api_key)
    else:
        credential = DefaultAzureCredential()
        
    return SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)

def test_direct_search(query: str, index_name: str) -> List[Dict]:
    """Test direct search to verify index has content"""
    try:
        print(f"🔍 Testing direct search on index '{index_name}'...")
        search_client = search_client_helper(index_name)
        results = search_client.search(search_text=query, top=3)
        hits = [doc for doc in results]
        print(f"📊 Direct search found {len(hits)} documents")
        if hits:
            first_hit = hits[0]
            print(f"📄 First hit keys: {list(first_hit.keys())}")
            print(f"📄 First hit content preview: {str(first_hit.get('content', ''))[:200]}...")
        return hits
    except Exception as e:
        print(f"❌ Direct search failed: {e}")
        return []

def test_knowledge_agent_with_direct_api():
    """Test the delete3-agent using direct API calls (like backup working code)"""
    print("🔍 Testing Knowledge Agent with Direct API Calls")
    print("=" * 50)
    
    # Test configuration
    agent_name = "delete3-agent"
    index_name = "delete3"
    test_queries = [
        "What are the different disk types available in Azure?",
        "Tell me about UltraDisk",
        "Storage comparison"
    ]
    
    # Extract service name from search endpoint
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    if not search_endpoint:
        raise ValueError("AZURE_SEARCH_ENDPOINT not configured")
        
    print(f"🌐 Search Endpoint: {search_endpoint}")
    
    service_name = search_endpoint.replace("https://", "").replace(".search.windows.net", "")
    api_version = "2025-05-01-preview"
    
    # Build the API endpoint for /retrieve
    endpoint = f"https://{service_name}.search.windows.net/agents/{agent_name}/retrieve?api-version={api_version}"
    print(f"🎯 Agent API Endpoint: {endpoint}")
    
    try:
        # Get authentication headers
        headers = get_search_headers()
        print(f"✅ Authentication headers prepared")
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{'=' * 60}")
            print(f"🧪 Test Query {i}: {query}")
            print(f"📋 Agent: {agent_name}")
            print(f"📊 Index: {index_name}")
            
            # First test direct search to verify index has content
            direct_hits = test_direct_search(query, index_name)
            
            # Prepare the request body (using the working structure from direct_api_retrieval.py)
            body = {
                "messages": [
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Answer the question based only on the indexed sources. "
                                    "Cite ref_id in square brackets. If unknown, say \"I don't know\"."
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
                        "includeReferenceSourceData": True  # This is KEY for getting metadata!
                    }
                ]
            }
            
            print(f"📤 Request body prepared")
            print(f"🔑 includeReferenceSourceData: {body['targetIndexParams'][0]['includeReferenceSourceData']}")
            
            # Make the API call
            try:
                print(f"🚀 Making API call...")
                resp = requests.post(endpoint, headers=headers, json=body, timeout=60)
                
                print(f"📊 Response Status: {resp.status_code}")
                
                if resp.status_code != 200:
                    print(f"❌ HTTP Error: {resp.text[:500]}")
                    continue
                    
                # Parse JSON response
                try:
                    response_data = resp.json()
                    print(f"✅ Response JSON parsed successfully")
                    print(f"📊 Response keys: {list(response_data.keys())}")
                except ValueError as e:
                    print(f"❌ Invalid JSON response: {resp.text[:200]}")
                    continue
                    
                # Check for error in response
                if "error" in response_data:
                    error = response_data["error"]
                    error_msg = f"{error.get('code', '')}: {error.get('message', '')}"
                    print(f"❌ Knowledge-Agent error: {error_msg}")
                    continue
                    
                # Extract chunks using the working logic from direct_api_retrieval.py
                chunks = []
                try:
                    if "response" in response_data:
                        print(f"📊 Response contains 'response' field")
                        response_messages = response_data["response"]
                        print(f"📊 Response messages count: {len(response_messages)}")
                        
                        if response_messages:
                            first_message = response_messages[0]
                            print(f"📊 First message keys: {list(first_message.keys())}")
                            
                            if "content" in first_message and first_message["content"]:
                                content_items = first_message["content"]
                                print(f"📊 Content items count: {len(content_items)}")
                                
                                if content_items:
                                    first_content = content_items[0]
                                    print(f"📊 First content keys: {list(first_content.keys())}")
                                    
                                    if "text" in first_content:
                                        json_str = first_content["text"]
                                        print(f"📊 Text content length: {len(json_str)}")
                                        print(f"📄 Text content preview: {json_str[:300]}...")
                                        
                                        try:
                                            # Try to parse as JSON list of chunks
                                            chunks = json.loads(json_str)
                                            print(f"✅ Successfully parsed chunks as JSON")
                                            print(f"📊 Chunks count: {len(chunks)}")
                                            
                                            if chunks and isinstance(chunks, list):
                                                first_chunk = chunks[0]
                                                print(f"📊 First chunk type: {type(first_chunk)}")
                                                if isinstance(first_chunk, dict):
                                                    print(f"📊 First chunk keys: {list(first_chunk.keys())}")
                                                    # Show all chunk data for debugging
                                                    for key, value in first_chunk.items():
                                                        if isinstance(value, str) and len(value) > 100:
                                                            print(f"📋 {key}: {value[:100]}...")
                                                        else:
                                                            print(f"📋 {key}: {value}")
                                        except json.JSONDecodeError as e:
                                            # Not JSON, it's already the final answer
                                            print(f"⚠️  Text content is not JSON, treating as final answer")
                                            print(f"📝 Final answer: {json_str}")
                                            chunks = []
                                    else:
                                        print(f"❌ No 'text' in first content item")
                                else:
                                    print(f"❌ No content items found")
                            else:
                                print(f"❌ No 'content' in first message")
                        else:
                            print(f"❌ No response messages found")
                    elif "chunks" in response_data:
                        print(f"📊 Response contains 'chunks' field")
                        chunks = response_data["chunks"]
                        print(f"📊 Direct chunks count: {len(chunks)}")
                    else:
                        print(f"❌ Response contains neither 'response' nor 'chunks' field")
                        print(f"📊 Available keys: {list(response_data.keys())}")
                        
                except Exception as exc:
                    print(f"❌ Error extracting chunks: {exc}")
                    import traceback
                    traceback.print_exc()
                    chunks = []
                
                print(f"\n📊 FINAL RESULT FOR QUERY {i}:")
                print(f"   Chunks found: {len(chunks)}")
                if chunks:
                    print(f"   First chunk preview: {json.dumps(chunks[0], indent=2) if chunks else 'None'}")
                else:
                    print(f"   ⚠️  No chunks returned - this indicates the agent is not finding content")
                    if direct_hits:
                        print(f"   ⚠️  But direct search found {len(direct_hits)} documents - agent configuration issue!")
                    else:
                        print(f"   ⚠️  Direct search also found no documents - index may be empty")
                    
            except Exception as e:
                print(f"❌ API call failed: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Failed to initialize or run test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_knowledge_agent_with_direct_api()
