#!/usr/bin/env python3
"""
Simple test to see what the knowledge agent returns using its default configuration
"""
import os
from dotenv import load_dotenv
from azure.search.documents.agent import KnowledgeAgentRetrievalClient
from azure.search.documents.agent.models import (
    KnowledgeAgentRetrievalRequest,
    KnowledgeAgentMessage,
    KnowledgeAgentMessageTextContent,
)
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

def test_simple_agent_call():
    """Test the delete3-agent with minimal configuration"""
    load_dotenv()
    
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    agent_name = "delete3-agent"
    
    # Get credentials
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
    
    # Simple message
    ka_msgs = [
        KnowledgeAgentMessage(
            role="user",
            content=[KnowledgeAgentMessageTextContent(text="somatosensory")]
        )
    ]
    
    # Minimal request - let the agent use its default configuration
    req = KnowledgeAgentRetrievalRequest(messages=ka_msgs)
    
    print(f"🤖 Testing {agent_name} with minimal configuration...")
    print(f"📋 Query: 'somatosensory'")
    
    try:
        result = ka_client.knowledge_retrieval.retrieve(retrieval_request=req)
        
        print(f"✅ Result type: {type(result)}")
        print(f"📊 Has response: {hasattr(result, 'response')}")
        
        if hasattr(result, 'response') and result.response:
            print(f"📨 Response messages: {len(result.response)}")
            
            for i, msg in enumerate(result.response):
                print(f"\n📬 Message {i+1}:")
                print(f"   Role: {getattr(msg, 'role', 'Unknown')}")
                print(f"   Content items: {len(getattr(msg, 'content', []))}")
                
                for j, content_item in enumerate(getattr(msg, 'content', [])):
                    print(f"\n   📄 Content {j+1}:")
                    print(f"      Type: {type(content_item)}")
                    
                    # Try to get all available attributes
                    for attr in ['text', 'ref_id', 'url', 'source_file', 'page_number', 'score']:
                        if hasattr(content_item, attr):
                            value = getattr(content_item, attr)
                            print(f"      {attr}: {repr(value)}")
                    
                    # Show text content if available
                    text = getattr(content_item, 'text', '')
                    if text and text.strip():
                        preview = text[:200] + "..." if len(text) > 200 else text
                        print(f"      📝 Text preview: {preview}")
                    else:
                        print(f"      ⚠️  No text content found")
        else:
            print("❌ No response from agent")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_agent_call()
