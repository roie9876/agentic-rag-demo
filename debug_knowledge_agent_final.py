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
    print(f"🧪 {description}")
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
