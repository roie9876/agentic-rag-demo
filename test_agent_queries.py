#!/usr/bin/env python3
"""
Test agentic retrieval with different queries to see what matches
"""

import os
import json
from azure.search.documents.agent import KnowledgeAgentRetrievalClient
from azure.search.documents.agent._generated.models import (
    KnowledgeAgentRetrievalRequest,
    KnowledgeAgentMessage,
    KnowledgeAgentMessageTextContent,
    KnowledgeAgentIndexParams
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

def test_different_queries():
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    agent_name = "delete3-agent"
    
    print(f"Testing different queries with agent: {agent_name}")
    print(f"Endpoint: {endpoint}")
    print("-" * 60)
    
    # Test queries
    test_queries = [
        "סימנים חיוניים",  # Hebrew: "vital signs" - matches the content we saw
        "vital signs",     # English equivalent
        "table",          # Generic search for table content
        "*",              # Wildcard search
        "גובה",           # Hebrew: "height" - specific term from content
        "164",            # Specific number from the content
        "03/01/2024",     # Date from the content
    ]
    
    ka_client = KnowledgeAgentRetrievalClient(
        endpoint=endpoint,
        agent_name=agent_name,
        credential=DefaultAzureCredential(),
    )
    
    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        try:
            messages = [{"role": "user", "content": query}]
            ka_msgs = [
                KnowledgeAgentMessage(
                    role=m["role"],
                    content=[KnowledgeAgentMessageTextContent(text=m["content"])]
                )
                for m in messages
            ]
            
            req = KnowledgeAgentRetrievalRequest(messages=ka_msgs)
            result = ka_client.knowledge_retrieval.retrieve(retrieval_request=req)
            
            # Process results
            chunks = []
            for msg in result.response:
                for c in getattr(msg, "content", []):
                    content_text = getattr(c, "text", "")
                    chunks.append({
                        "content": content_text,
                        "length": len(content_text) if content_text else 0
                    })
            
            print(f"  📊 Found {len(chunks)} chunks")
            for i, chunk in enumerate(chunks[:2]):  # Show first 2 chunks
                print(f"  📄 Chunk {i+1}: length={chunk['length']}, preview='{chunk['content'][:100]}...'")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    test_different_queries()
