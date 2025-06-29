#!/usr/bin/env python3
"""
Debug Hebrew query on anatomy content
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv(Path(__file__).resolve().parent / ".env")

from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
import requests
import json

def test_hebrew_anatomy_query():
    """Test Hebrew anatomy query on delete3 index"""
    
    print("🔍 Testing Hebrew Anatomy Query on delete3 Index")
    print("=" * 60)
    
    # Test configuration
    index_name = "delete3"
    agent_name = "delete3-agent"
    hebrew_query = "איך עובדת מערכת החישה של גוף האדם"  # How does the human body's sensory system work
    english_query = "How does the human sensory system work"
    anatomy_query = "What are Pacinian corpuscles"
    
    print(f"📊 Index: {index_name}")
    print(f"🤖 Agent: {agent_name}")
    print(f"❓ Hebrew Query: {hebrew_query}")
    print(f"❓ English Query: {english_query}")
    
    # First test direct search to see if the content is searchable
    try:
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        search_api_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("SEARCH_API_KEY")
        
        if search_api_key:
            credential = AzureKeyCredential(search_api_key)
        else:
            credential = DefaultAzureCredential()
            
        search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
        
        # Test different queries
        test_queries = [
            ("Hebrew Query", hebrew_query),
            ("English Query", english_query), 
            ("Anatomy Query", anatomy_query),
            ("Generic", "somatosensory"),
            ("Generic", "corpuscle"),
            ("Wildcard", "*")
        ]
        
        print(f"\n🔍 Direct Search Results:")
        print("-" * 40)
        
        for query_name, query in test_queries:
            try:
                results = search_client.search(search_text=query, top=3)
                hits = list(results)
                print(f"  {query_name:<15}: {len(hits)} hits")
                if hits:
                    first_hit = hits[0]
                    content_preview = str(first_hit.get('content', ''))[:100]
                    print(f"    Preview: {content_preview}...")
            except Exception as e:
                print(f"  {query_name:<15}: Error - {e}")
        
    except Exception as e:
        print(f"❌ Direct search setup failed: {e}")
        return
    
    # Now test the knowledge agent with different approaches
    print(f"\n🤖 Knowledge Agent Tests:")
    print("-" * 40)
    
    try:
        service_name = search_endpoint.replace("https://", "").replace(".search.windows.net", "")
        api_version = "2025-05-01-preview"
        endpoint = f"https://{service_name}.search.windows.net/agents/{agent_name}/retrieve?api-version={api_version}"
        
        # Get auth headers
        if search_api_key:
            headers = {"api-key": search_api_key, "Content-Type": "application/json"}
        else:
            token = DefaultAzureCredential().get_token("https://search.azure.com/.default").token
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Test different query approaches
        agent_tests = [
            ("Hebrew Original", hebrew_query),
            ("English Translation", english_query),
            ("Simple Anatomy", anatomy_query),
            ("Generic Terms", "somatosensory system anatomy")
        ]
        
        for test_name, query in agent_tests:
            print(f"\n  🧪 {test_name}: {query}")
            
            # Test without specifying target index (let agent use its default)
            body1 = {
                "messages": [
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Answer based on indexed sources. Cite ref_id in brackets."}]
                    },
                    {
                        "role": "user", 
                        "content": [{"type": "text", "text": query}]
                    }
                ],
                # No targetIndexParams - let agent use its configured index
            }
            
            # Test with explicitly specifying the target index
            body2 = {
                "messages": [
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Answer based on indexed sources. Cite ref_id in brackets."}]
                    },
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": query}]
                    }
                ],
                "targetIndexParams": [
                    {
                        "indexName": index_name,
                        "rerankerThreshold": 1.0,  # Lower threshold for better recall
                        "includeReferenceSourceData": True
                    }
                ]
            }
            
            for approach, body in [("Default Config", body1), ("Explicit Index", body2)]:
                try:
                    resp = requests.post(endpoint, headers=headers, json=body, timeout=60)
                    
                    if resp.status_code == 200:
                        response_data = resp.json()
                        if "error" in response_data:
                            print(f"    {approach}: API Error - {response_data['error']}")
                            continue
                            
                        # Extract content
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
                                        chunks = [{"content": text_content}]
                        
                        if chunks and len(chunks) > 0 and any(chunk.get("content", "").strip() and chunk.get("content") != "[]" for chunk in chunks):
                            print(f"    {approach}: ✅ SUCCESS - {len(chunks)} chunks")
                            first_chunk = chunks[0]
                            content_preview = first_chunk.get('content', '')[:100]
                            print(f"      Preview: {content_preview}...")
                        else:
                            print(f"    {approach}: ❌ Empty results")
                    else:
                        print(f"    {approach}: HTTP {resp.status_code}")
                        
                except Exception as e:
                    print(f"    {approach}: Error - {e}")
    
    except Exception as e:
        print(f"❌ Agent test setup failed: {e}")

if __name__ == "__main__":
    test_hebrew_anatomy_query()
