#!/usr/bin/env python3
"""
Focused diagnostic script to identify why the Agent returns empty results
even though the search index contains the data.
"""

import os
import sys
import json

# Add the project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def diagnose_agent_retrieval():
    """Diagnose Agent retrieval issues step by step"""
    
    print("🔍 DIAGNOSING AGENT RETRIEVAL ISSUES")
    print("=" * 60)
    
    try:
        # Import required modules
        from azure.search.documents.agent.models import (
            KnowledgeAgentRetrievalRequest,
            KnowledgeAgentMessage,
            KnowledgeAgentMessageTextContent,
            KnowledgeAgentIndexParams,
            KnowledgeAgentRequestLimits
        )
        from azure.search.documents.agent import AgentClient
        from azure.identity import DefaultAzureCredential
        
        # Get configuration
        project_endpoint = os.getenv("PROJECT_ENDPOINT")
        index_name = "delete1"  # The index from your search results
        agent_name = f"{index_name}-agent"  # Expected agent name
        
        print(f"🔧 Configuration:")
        print(f"   Project Endpoint: {project_endpoint}")
        print(f"   Index Name: {index_name}")
        print(f"   Agent Name: {agent_name}")
        
        # Initialize agent client
        credential = DefaultAzureCredential()
        agent_client = AgentClient(
            endpoint=project_endpoint,
            credential=credential
        )
        
        print(f"\n✅ Agent client initialized")
        
        # Step 1: Check if agent exists
        print(f"\n📋 Step 1: Checking if agent '{agent_name}' exists...")
        try:
            # Try to get agent information
            agents = agent_client.agents.list()
            agent_list = list(agents)
            agent_names = [agent.name for agent in agent_list]
            
            print(f"   Available agents: {agent_names}")
            
            if agent_name in agent_names:
                print(f"   ✅ Agent '{agent_name}' exists")
                
                # Get agent details
                agent_details = agent_client.agents.get(agent_name)
                print(f"   Agent details: {agent_details}")
            else:
                print(f"   ❌ Agent '{agent_name}' does not exist!")
                print(f"   💡 This could be the main issue.")
                print(f"   Available agents: {agent_names}")
                return False
                
        except Exception as e:
            print(f"   ⚠️ Error checking agent: {str(e)}")
            print(f"   Continuing with retrieval test...")
        
        # Step 2: Test simple English query
        print(f"\n📋 Step 2: Testing simple English query...")
        
        test_queries = [
            "UltraDisk",
            "comparison", 
            "vs competition",
            "disk types"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")
            
            try:
                # Create messages
                messages = [
                    KnowledgeAgentMessage(
                        role="user",
                        content=[KnowledgeAgentMessageTextContent(text=query)]
                    )
                ]
                
                # Create request with minimal parameters
                ka_req = KnowledgeAgentRetrievalRequest(
                    messages=messages,
                    target_index_params=[
                        KnowledgeAgentIndexParams(
                            index_name=index_name,
                            reranker_threshold=1.0
                        )
                    ],
                    request_limits=KnowledgeAgentRequestLimits(
                        max_output_size=16000
                    )
                )
                
                print(f"   📤 Request created")
                print(f"   📋 Request details: messages={len(messages)}, index={index_name}")
                
                # Make the request
                result = agent_client.knowledge_retrieval.retrieve(
                    retrieval_request=ka_req
                )
                
                print(f"   📥 Response received")
                print(f"   📊 Response type: {type(result).__name__}")
                
                # Analyze the response
                response_info = {
                    "has_response": hasattr(result, "response"),
                    "has_chunks": hasattr(result, "chunks"),
                    "attributes": [attr for attr in dir(result) if not attr.startswith('_')]
                }
                
                if hasattr(result, "response") and result.response:
                    response_info["response_count"] = len(result.response)
                    if result.response:
                        first_response = result.response[0]
                        response_info["first_response_type"] = type(first_response).__name__
                        response_info["first_response_attrs"] = [attr for attr in dir(first_response) if not attr.startswith('_')]
                        
                        if hasattr(first_response, "content") and first_response.content:
                            response_info["content_count"] = len(first_response.content)
                            if first_response.content:
                                first_content = first_response.content[0]
                                response_info["first_content_type"] = type(first_content).__name__
                                response_info["first_content_attrs"] = [attr for attr in dir(first_content) if not attr.startswith('_')]
                                
                                # Check if content has text
                                if hasattr(first_content, "text"):
                                    content_text = first_content.text
                                    response_info["content_text_length"] = len(content_text) if content_text else 0
                                    if content_text:
                                        response_info["content_preview"] = content_text[:200]
                                    else:
                                        response_info["content_text"] = "EMPTY"
                                        
                print(f"   📊 Response analysis: {json.dumps(response_info, indent=2)}")
                
                # Check chunks specifically
                if hasattr(result, "chunks"):
                    chunks = result.chunks
                    print(f"   📦 Chunks: {len(chunks) if chunks else 0}")
                    if chunks:
                        for i, chunk in enumerate(chunks[:2]):  # First 2 chunks
                            print(f"     Chunk {i}: {type(chunk).__name__}")
                            if hasattr(chunk, "__dict__"):
                                chunk_dict = {k: v for k, v in chunk.__dict__.items() if not k.startswith('_')}
                                print(f"     Content: {json.dumps(chunk_dict, indent=6)}")
                else:
                    print(f"   📦 No chunks attribute found")
                
                # If we got empty results, that's the issue we're investigating
                if (not hasattr(result, "response") or not result.response or 
                    not result.response[0].content or not result.response[0].content[0].text):
                    print(f"   ❌ EMPTY RESULTS for query '{query}'")
                    print(f"   🔍 This confirms the issue - Agent returns empty results")
                else:
                    print(f"   ✅ NON-EMPTY RESULTS for query '{query}'")
                    
            except Exception as e:
                print(f"   ❌ Error with query '{query}': {str(e)}")
                import traceback
                traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = diagnose_agent_retrieval()
    
    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS:")
    print("1. If agent doesn't exist → Create the agent first")
    print("2. If agent exists but returns empty → Check agent configuration")
    print("3. If agent works with English but not Hebrew → Language processing issue")
    print("4. Check agent's index configuration matches actual index name")
    sys.exit(0 if success else 1)
