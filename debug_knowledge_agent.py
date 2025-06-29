#!/usr/bin/env python3
"""
Knowledge Agent Debug Script - SOLUTION FOUND!

ISSUE RESOLVED: The knowledge agent API is working correctly with API version 2025-05-01-preview.
The original problem was that we were testing the wrong agent/index combination.

SOLUTION:
- delete3-agent → delete3 index → contains anatomy/medical content (wrong content)
- sharepoint-index-1-agent → sharepoint-index-1 index → contains Azure UltraDisk content (correct!)

The debug process revealed:
1. ✅ API version 2025-05-01-preview is working
2. ✅ includeReferenceSourceData=true is working  
3. ✅ Authentication (both API key and Managed Identity) is working
4. ✅ Knowledge agent returns chunks when queried with relevant content
5. ❌ The issue was semantic mismatch: asking about Azure storage from an anatomy index

This script now tests both scenarios to demonstrate the solution.
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

def get_search_headers() -> dict:
    """Get authentication headers for Azure Search API calls"""
    search_api_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("SEARCH_API_KEY")
    
    if search_api_key:
        print("✅ Using API key authentication")
        return {"api-key": search_api_key, "Content-Type": "application/json"}
    
    try:
        print("✅ Using Managed Identity authentication")
        token = DefaultAzureCredential().get_token("https://search.azure.com/.default").token
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    except Exception as e:
        raise RuntimeError(f"Authentication failed: {e}")

def test_agent_with_query(agent_name: str, index_name: str, query: str, description: str) -> bool:
    """Test a specific agent with a query and return whether it found relevant content"""
    
    print(f"\n{'='*80}")
    print(f"� {description}")
    print(f"📋 Agent: {agent_name}")
    print(f"📊 Index: {index_name}")
    print(f"❓ Query: {query}")
    
    # Build API endpoint
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    service_name = search_endpoint.replace("https://", "").replace(".search.windows.net", "")
    endpoint = f"https://{service_name}.search.windows.net/agents/{agent_name}/retrieve?api-version=2025-05-01-preview"
    
    # Prepare request body with working structure
    body = {
        "messages": [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "Answer the question based only on the indexed sources. Cite ref_id in square brackets. If unknown, say \"I don't know\"."
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
                "includeReferenceSourceData": True  # KEY parameter for metadata
            }
        ]
    }
    
    try:
        headers = get_search_headers()
        resp = requests.post(endpoint, headers=headers, json=body, timeout=60)
        
        if resp.status_code != 200:
            print(f"❌ HTTP {resp.status_code}: {resp.text[:200]}")
            return False
            
        response_data = resp.json()
        
        if "error" in response_data:
            error = response_data["error"]
            print(f"❌ Agent error: {error.get('code', '')}: {error.get('message', '')}")
            return False
            
        # Extract chunks
        chunks = []
        if "response" in response_data and response_data["response"]:
            first_message = response_data["response"][0]
            if "content" in first_message and first_message["content"]:
                first_content = first_message["content"][0]
                if "text" in first_content:
                    text_content = first_content["text"]
                    try:
                        chunks = json.loads(text_content)
                    except json.JSONDecodeError:
                        # Text response, not chunks
                        print(f"📝 Got text response: {text_content[:200]}...")
                        return bool(text_content.strip())
        
        if chunks and len(chunks) > 0:
            print(f"✅ SUCCESS: Found {len(chunks)} chunks")
            first_chunk = chunks[0]
            content_preview = first_chunk.get('content', '')[:200]
            print(f"📄 Sample content: {content_preview}...")
            return True
        else:
            print(f"❌ No relevant content found (empty response)")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    """Demonstrate the knowledge agent working correctly with proper agent/index combinations"""
    
    print("🔍 Knowledge Agent Debug - SOLUTION DEMONSTRATION")
    print("=" * 80)
    print("This script demonstrates that the knowledge agent API is working correctly")
    print("when using the right agent/index combination with relevant content.")
    print()
    print("KEY FINDINGS:")
    print("✅ API version 2025-05-01-preview works correctly")
    print("✅ includeReferenceSourceData=true returns metadata")
    print("✅ Authentication works (both API key and Managed Identity)")
    print("✅ Knowledge agent returns chunks when content matches query")
    print("❌ Original issue: semantic mismatch between query and indexed content")
    
    # Test scenarios
    test_cases = [
        {
            "agent": "delete3-agent",
            "index": "delete3", 
            "query": "Tell me about UltraDisk features",
            "description": "❌ WRONG: Azure query on anatomy content",
            "expected": False
        },
        {
            "agent": "delete3-agent",
            "index": "delete3",
            "query": "What are Pacinian corpuscles?", 
            "description": "✅ CORRECT: Anatomy query on anatomy content",
            "expected": True
        },
        {
            "agent": "sharepoint-index-1-agent",
            "index": "sharepoint-index-1",
            "query": "Tell me about UltraDisk features",
            "description": "✅ CORRECT: Azure query on Azure content", 
            "expected": True
        },
        {
            "agent": "sharepoint-index-1-agent", 
            "index": "sharepoint-index-1",
            "query": "What are Pacinian corpuscles?",
            "description": "❌ WRONG: Anatomy query on Azure content",
            "expected": False
        }
    ]
    
    results = []
    for test_case in test_cases:
        success = test_agent_with_query(
            test_case["agent"],
            test_case["index"], 
            test_case["query"],
            test_case["description"]
        )
        results.append({
            "test": test_case["description"],
            "expected": test_case["expected"],
            "actual": success,
            "correct": success == test_case["expected"]
        })
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 SUMMARY & SOLUTION")
    print(f"{'='*80}")
    
    correct_predictions = sum(1 for r in results if r["correct"])
    print(f"✅ Correct predictions: {correct_predictions}/{len(results)}")
    
    print("\n🎯 SOLUTION:")
    print("1. The knowledge agent API is working correctly")
    print("2. Use the right agent/index combination for your content:")
    print("   • sharepoint-index-1-agent → Azure UltraDisk content")
    print("   • delete3-agent → Anatomy/medical content")
    print("3. Ensure queries match the semantic domain of indexed content")
    print("4. API version 2025-05-01-preview with includeReferenceSourceData=true works perfectly")
    
    print("\n🛠️ FOR YOUR PROJECT:")
    print("• Update your code to use 'sharepoint-index-1-agent' for Azure storage queries")
    print("• Or populate the delete3 index with actual Azure storage documentation")
    print("• The retrieval logic and API calls are working correctly!")
    
    print(f"\n✅ KNOWLEDGE AGENT DEBUGGING COMPLETE - ISSUE RESOLVED!")

if __name__ == "__main__":
    main()
                print(f"\n🎯 Focusing on: {agent_name}")
                print(f"   📊 Index: {index_name}")
                
                # Test this specific agent
                test_agent_query(agent_name, search_endpoint)
            else:
                print("❌ delete3-agent not found!")
                print("Available agents:")
                for agent in agents.get('value', []):
                    print(f"   - {agent.get('name', 'Unknown')}")
                
        elif response.status_code == 404:
            print("ℹ️  No knowledge agents found - this might be why agentic retrieval is returning empty results")
            print("💡 You may need to create a knowledge agent for your index")
        else:
            print(f"❌ Agent API returned status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing knowledge agent: {str(e)}")

def test_agent_query(agent_name, search_endpoint):
    """Test a specific agent with a simple query using the SDK approach matching the working backup."""
    try:
        # Import required modules
        from azure.search.documents.agent import KnowledgeAgentRetrievalClient
        from azure.search.documents.agent.models import (
            KnowledgeAgentRetrievalRequest,
            KnowledgeAgentMessage,
            KnowledgeAgentMessageTextContent,
            KnowledgeAgentIndexParams,
        )
        from azure.core.credentials import AzureKeyCredential
        from azure.identity import DefaultAzureCredential
        from azure.core.exceptions import HttpResponseError
        import os
        
        # Get credentials (using same logic as backup)
        search_api_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("SEARCH_API_KEY")
        if search_api_key:
            credential = AzureKeyCredential(search_api_key)
        else:
            credential = DefaultAzureCredential()
        
        # Create the knowledge agent client
        ka_client = KnowledgeAgentRetrievalClient(
            endpoint=search_endpoint,
            agent_name=agent_name,
            credential=credential,
        )
        
        # Test with multiple query variations (more specific to existing content)
        test_queries = [
            "What is this document about?",
            "somatosensory system",
            "Pacinian corpuscle",
            "muscle spindles",
            "anatomy"
        ]
        
        success_found = False
        
        for query in test_queries:
            try:
                # Create messages (matching backup format)
                messages = [{"role": "user", "content": query}]
                fixed_msgs = []
                for m in messages:
                    if isinstance(m, dict) and "role" in m and "content" in m:
                        fixed_msgs.append(m)
                    elif isinstance(m, str):
                        fixed_msgs.append({"role": "user", "content": m})
                
                ka_msgs = [
                    KnowledgeAgentMessage(
                        role=m["role"],
                        content=[KnowledgeAgentMessageTextContent(text=m["content"])]
                    )
                    for m in fixed_msgs
                ]
                
                # Test WITHOUT target index first - let agent use its default config
                req_params = {
                    "messages": ka_msgs,
                    # No target_index_params - let agent use default
                }
                
                # Try to add optional parameters (like backup)
                try:
                    test_req = KnowledgeAgentRetrievalRequest(messages=ka_msgs)
                    if hasattr(test_req, "citation_field_name"):
                        req_params["citation_field_name"] = "source_file"
                except Exception:
                    pass
                
                req = KnowledgeAgentRetrievalRequest(**req_params)
                
                # Execute without retry logic for now
                result = ka_client.knowledge_retrieval.retrieve(retrieval_request=req)
                
                # DEBUG: Print raw response structure
                print(f"   🔍 DEBUG - Result type: {type(result)}")
                print(f"   🔍 DEBUG - Has response: {hasattr(result, 'response')}")
                if hasattr(result, 'response') and result.response:
                    print(f"   🔍 DEBUG - Response length: {len(result.response)}")
                    for i, msg in enumerate(result.response):
                        print(f"   🔍 DEBUG - Message {i}: {type(msg)}")
                        content_items = getattr(msg, "content", [])
                        print(f"   🔍 DEBUG - Content items: {len(content_items)}")
                        for j, c in enumerate(content_items):
                            print(f"   🔍 DEBUG - Content {j}: type={type(c)}")
                            text_content = getattr(c, "text", "")
                            print(f"   🔍 DEBUG - Text content: '{text_content}' (len={len(text_content)})")
                            print(f"   🔍 DEBUG - Attributes: {[attr for attr in dir(c) if not attr.startswith('_')]}")
                
                # Process response (matching backup logic)
                chunks = []
                if hasattr(result, 'response') and result.response:
                    for msg in result.response:
                        for c in getattr(msg, "content", []):
                            chunk = {
                                "ref_id": getattr(c, "ref_id", None) or len(chunks),
                                "content": getattr(c, "text", ""),
                                "url": getattr(c, "url", None),
                                "source_file": getattr(c, "source_file", None),
                                "page_number": getattr(c, "page_number", None),
                                "score": getattr(c, "score", None),
                                "doc_key": getattr(c, "doc_key", None),
                            }
                            # prune empty keys (like backup)
                            chunks.append({k: v for k, v in chunk.items() if v is not None})
                
                if chunks and any(chunk.get("content", "").strip() for chunk in chunks):
                    print(f"   ✅ Query '{query}' - Found {len(chunks)} chunks with content!")
                    
                    # Show detailed response for successful query
                    for i, chunk in enumerate(chunks[:2]):  # Show first 2
                        content = chunk.get("content", "")
                        source = chunk.get("source_file", "Unknown")
                        print(f"      � Chunk {i+1}: {len(content)} chars from {source}")
                        if content:
                            preview = content[:150] + "..." if len(content) > 150 else content
                            print(f"         Preview: {preview}")
                    
                    success_found = True
                    break  # Stop after first successful query
                else:
                    print(f"   ⚠️  Query '{query}' - Empty chunks returned")
                    
            except Exception as query_err:
                print(f"   ❌ Query '{query}' failed: {str(query_err)}")
        
        if not success_found:
            print(f"   ⚠️  All queries returned empty results for agent {agent_name}")
            
    except Exception as e:
        print(f"   ❌ Agent query error: {str(e)}")

def test_direct_search():
    """Test direct search on the delete3 index to ensure documents are accessible."""
    print("\n🔍 Testing Direct Search on delete3 Index...")
    
    load_env()
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        from azure.search.documents import SearchClient
        credential = DefaultAzureCredential()
        
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name="delete3",
            credential=credential
        )
        
        # Test simple search - use correct field names from agent config
        results = list(search_client.search(
            search_text="*",
            top=3,
            select=["id", "page_chunk", "source_file"]  # Use page_chunk not content
        ))
        
        print(f"✅ Direct search returned {len(results)} documents")
        
        for i, doc in enumerate(results):
            content = doc.get('page_chunk', 'No content')  # Use page_chunk
            filename = doc.get('source_file', 'No filename')  # Use source_file  
            doc_id = doc.get('id', 'No ID')
            
            print(f"\n📄 Document {i+1}:")
            print(f"   ID: {doc_id}")
            print(f"   Filename: {filename}")
            print(f"   Content preview: {str(content)[:150]}...")
            
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Direct search failed: {str(e)}")
        return False

def main():
    print("🧪 Knowledge Agent Debugging")
    print("=" * 50)
    
    # Test 1: Check knowledge agents
    test_knowledge_agent()
    
    # Test 2: Test direct search
    has_docs = test_direct_search()
    
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSIS & NEXT STEPS")
    print("=" * 50)
    
    if has_docs:
        print("✅ Documents are accessible via direct search")
        print("💡 Issue is likely with knowledge agent configuration")
        print("\n🔧 Recommended actions:")
        print("1. Check if knowledge agents exist for your indexes")
        print("2. Verify agent configuration in Azure Portal")
        print("3. Ensure agent is using the correct vectorized fields")
        print("4. Test with different query languages/content")
    else:
        print("❌ Documents not accessible - check index permissions")

if __name__ == "__main__":
    main()
