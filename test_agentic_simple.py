#!/usr/bin/env python3
"""Simple test for agentic retrieval without Streamlit dependencies"""

import os
import json
from dotenv import load_dotenv
from azure.search.documents.agent import KnowledgeAgentRetrievalClient
from azure.search.documents.agent.models import (
    KnowledgeAgentRetrievalRequest,
    KnowledgeAgentMessage,
    KnowledgeAgentMessageTextContent,
    KnowledgeAgentIndexParams
)
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential

load_dotenv()

def _search_credential():
    """Get search credential (same logic as main file)"""
    search_api_key = os.getenv("SEARCH_API_KEY") or os.getenv("AZURE_SEARCH_KEY")
    if search_api_key:
        return AzureKeyCredential(search_api_key)
    return DefaultAzureCredential()

def test_agentic_retrieval():
    """Test agentic retrieval with delete3-agent"""
    
    agent_name = "delete3-agent"
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    print(f"Testing agentic retrieval:")
    print(f"  Agent: {agent_name}")
    print(f"  Endpoint: {search_endpoint}")
    print("-" * 50)
    
    try:
        # Create client
        ka_client = KnowledgeAgentRetrievalClient(
            endpoint=search_endpoint,
            agent_name=agent_name,
            credential=_search_credential(),
        )
        
        # Prepare messages
        messages = [{"role": "user", "content": "test document search"}]
        ka_msgs = [
            KnowledgeAgentMessage(
                role=m["role"],
                content=[KnowledgeAgentMessageTextContent(text=m["content"])]
            )
            for m in messages
        ]
        
        # Create request without forcing specific index (let agent use its default)
        req = KnowledgeAgentRetrievalRequest(messages=ka_msgs)
        
        print("Calling knowledge agent...")
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Request timed out")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)  # 30 second timeout
        
        try:
            result = ka_client.knowledge_retrieval.retrieve(retrieval_request=req)
            signal.alarm(0)  # Cancel the alarm
        except TimeoutError:
            print("❌ Request timed out after 30 seconds")
            return
        
        print(f"✅ API call successful!")
        print(f"Result type: {type(result)}")
        print(f"Has response: {hasattr(result, 'response')}")
        
        if hasattr(result, 'response') and result.response:
            print(f"Number of messages in response: {len(result.response)}")
            
            # Process messages
            chunks = []
            for msg in result.response:
                print(f"Processing message: {type(msg)}")
                for c in getattr(msg, "content", []):
                    text = getattr(c, "text", "")
                    print(f"Content text length: {len(text)}")
                    print(f"Content preview: {text[:100]}...")
                    
                    chunk = {
                        "content": text,
                        "source_file": getattr(c, "source_file", None),
                        "page_number": getattr(c, "page_number", None),
                        "score": getattr(c, "score", None),
                    }
                    chunks.append(chunk)
            
            print(f"\n📊 RESULTS:")
            print(f"Total chunks: {len(chunks)}")
            for i, chunk in enumerate(chunks[:3]):  # Show first 3
                print(f"Chunk {i+1}:")
                print(f"  Content length: {len(chunk['content'])}")
                print(f"  Source: {chunk['source_file']}")
                print(f"  Score: {chunk['score']}")
                print(f"  Preview: {chunk['content'][:200]}...")
                print()
        else:
            print("❌ No response content found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agentic_retrieval()
