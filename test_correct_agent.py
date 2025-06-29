#!/usr/bin/env python3
"""
Test the correct agent that targets the index with Azure storage content
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

def test_correct_agent():
    """Test the sharepoint-index-1-agent which has the Azure storage content"""
    print("🔍 Testing CORRECT Agent with Azure Storage Content")
    print("=" * 60)
    
    # Test configuration - use the correct agent and index
    agent_name = "sharepoint-index-1-agent"
    index_name = "sharepoint-index-1"
    test_queries = [
        "What are the different disk types available in Azure?",
        "Tell me about UltraDisk features",
        "Compare Azure disk storage options",
        "What is Azure Dedicated Host support for Ultra Disk?"
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
    print(f"📋 Agent: {agent_name}")
    print(f"📊 Index: {index_name} (contains Azure UltraDisk content)")
    
    try:
        # Get authentication headers
        headers = get_search_headers()
        print(f"✅ Authentication headers prepared")
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{'=' * 60}")
            print(f"🧪 Test Query {i}: {query}")
            
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
            
            print(f"📤 Request prepared with includeReferenceSourceData: True")
            
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
                final_answer = ""
                
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
                                            
                                            if chunks and isinstance(chunks, list) and len(chunks) > 0:
                                                first_chunk = chunks[0]
                                                print(f"📊 First chunk type: {type(first_chunk)}")
                                                if isinstance(first_chunk, dict):
                                                    print(f"📊 First chunk keys: {list(first_chunk.keys())}")
                                                    print(f"🎯 SUCCESS! Agent returned {len(chunks)} chunks with content!")
                                                    
                                                    # Show detailed chunk content
                                                    for j, chunk in enumerate(chunks[:2]):  # Show first 2 chunks
                                                        print(f"\n  📋 Chunk {j+1}:")
                                                        for key, value in chunk.items():
                                                            if isinstance(value, str) and len(value) > 100:
                                                                print(f"    {key}: {value[:100]}...")
                                                            else:
                                                                print(f"    {key}: {value}")
                                        except json.JSONDecodeError as e:
                                            # Not JSON, it's already the final answer
                                            print(f"⚠️  Text content is not JSON, treating as final answer")
                                            final_answer = json_str
                                            print(f"📝 Final answer: {final_answer[:500]}...")
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
                
                print(f"\n🎯 FINAL RESULT FOR QUERY {i}:")
                if final_answer:
                    print(f"   ✅ Got final answer: {final_answer[:200]}...")
                elif chunks and len(chunks) > 0:
                    print(f"   ✅ Got {len(chunks)} chunks successfully!")
                    print(f"   📄 Sample content: {chunks[0].get('content', '')[:200] if chunks else 'None'}...")
                else:
                    print(f"   ❌ No chunks or answer returned")
                    
            except Exception as e:
                print(f"❌ API call failed: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Failed to initialize or run test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_correct_agent()
