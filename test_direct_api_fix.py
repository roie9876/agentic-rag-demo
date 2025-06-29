#!/usr/bin/env python3
"""
Test script to verify the fix for knowledge agent retrieval
"""
import os
import sys
import json
import requests
from azure.identity import DefaultAzureCredential

def get_azure_search_token():
    """Get managed identity token for Azure Search"""
    credential = DefaultAzureCredential()
    token = credential.get_token("https://search.azure.com/.default")
    return token.token

def direct_api_retrieval_test(index_name: str, agent_name: str, query: str):
    """Test direct API retrieval with managed identity"""
    try:
        # Get environment variables
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        api_version = os.getenv("API_VERSION", "2025-05-01-preview")
        top_k = int(os.getenv("TOP_K", "5"))
        
        # Get managed identity token
        token = get_azure_search_token()
        
        # Build URL
        url = f"{search_endpoint}/indexes('{index_name}')/knowledgeAgents('{agent_name}')/search?api-version={api_version}"
        
        # Prepare headers and payload
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query,
            "top": top_k
        }
        
        print(f"🔍 Testing direct API retrieval:")
        print(f"   📊 Index: {index_name}")
        print(f"   🤖 Agent: {agent_name}")
        print(f"   ❓ Query: {query}")
        print(f"   🌐 URL: {url}")
        
        # Make API call
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"   📈 Status: {response.status_code}")
        
        if response.status_code == 200:
            result_data = response.json()
            
            # Extract chunks
            chunks = []
            if isinstance(result_data, dict) and "chunks" in result_data:
                raw_chunks = result_data["chunks"]
                print(f"   📦 Raw chunks found: {len(raw_chunks)}")
                
                for i, chunk in enumerate(raw_chunks):
                    if isinstance(chunk, dict):
                        processed_chunk = {
                            "ref_id": chunk.get("ref_id", i),
                            "content": chunk.get("content", ""),
                            "url": chunk.get("url"),
                            "source_file": chunk.get("source_file"),
                            "page_number": chunk.get("page_number"),
                            "score": chunk.get("score"),
                            "doc_key": chunk.get("doc_key"),
                        }
                        # Remove None values
                        processed_chunk = {k: v for k, v in processed_chunk.items() if v is not None}
                        chunks.append(processed_chunk)
            
            print(f"   ✅ Processed chunks: {len(chunks)}")
            if chunks:
                print(f"   📝 First chunk preview: {chunks[0].get('content', '')[:100]}...")
            
            return json.dumps(chunks, ensure_ascii=False)
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
            return "[]"
            
    except Exception as e:
        print(f"   💥 Exception: {str(e)}")
        return "[]"

if __name__ == "__main__":
    print("🧪 DIRECT API KNOWLEDGE AGENT RETRIEVAL TEST")
    print("=" * 60)
    
    # Test with delete3 index
    result = direct_api_retrieval_test(
        index_name="delete3",
        agent_name="delete3-agent", 
        query="What are Pacinian corpuscles?"
    )
    
    print(f"\n📊 Final Result Length: {len(result)}")
    print(f"📊 Result Preview: {result[:300]}...")
    
    if result != "[]":
        print("✅ SUCCESS: Knowledge agent returned content!")
    else:
        print("❌ FAILED: Knowledge agent returned empty results!")
