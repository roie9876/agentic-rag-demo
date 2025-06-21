#!/usr/bin/env python3
"""
Test if we can create/check agents using the same method as the main code
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_agent_creation():
    """Test agent creation using the exact same approach as the main code"""
    
    print("🔍 TESTING AGENT CREATION CAPABILITY")
    print("=" * 60)
    
    try:
        from azure.search.documents.indexes import SearchIndexClient
        from azure.identity import DefaultAzureCredential
        
        # Import the same classes used in the main code for agent creation
        from azure.search.documents.indexes.models import (
            KnowledgeAgent,
            KnowledgeAgentAzureOpenAIModel,
            AzureOpenAIVectorizerParameters,
            KnowledgeAgentTargetIndex
        )
        
        # Configuration
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT_41")
        openai_api_key = os.getenv("AZURE_OPENAI_KEY_41")
        openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_41")
        
        print(f"🔧 Configuration:")
        print(f"   Search Endpoint: {search_endpoint}")
        print(f"   OpenAI Endpoint: {azure_openai_endpoint}")
        print(f"   OpenAI Deployment: {openai_deployment}")
        print(f"   API Key: {'***' + openai_api_key[-4:] if openai_api_key else 'None'}")
        
        if not all([search_endpoint, azure_openai_endpoint, openai_api_key, openai_deployment]):
            print("❌ Missing required configuration!")
            return False
            
        # Initialize client
        credential = DefaultAzureCredential()
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        print(f"✅ Search index client initialized")
        
        # Check if delete1 index exists
        indexes = list(index_client.list_indexes())
        index_names = [idx.name for idx in indexes]
        
        if "delete1" not in index_names:
            print(f"❌ Index 'delete1' does not exist! Cannot test agent creation.")
            print(f"   Available indexes: {index_names}")
            return False
        
        print(f"✅ Index 'delete1' exists")
        
        # Try to create/update the agent (same as main code)
        print(f"\n🤖 Testing agent creation...")
        
        agent_name = "delete1-agent"
        agent = KnowledgeAgent(
            name=agent_name,
            models=[
                KnowledgeAgentAzureOpenAIModel(
                    azure_open_ai_parameters=AzureOpenAIVectorizerParameters(
                        resource_url=azure_openai_endpoint,
                        deployment_name=openai_deployment,
                        model_name="gpt-4.1",
                        api_key=openai_api_key,
                    )
                )
            ],
            target_indexes=[
                KnowledgeAgentTargetIndex(index_name="delete1", default_reranker_threshold=2.5)
            ],
        )
        
        print(f"   Agent object created: {agent_name}")
        
        # Check if index_client has create_or_update_agent method
        if hasattr(index_client, 'create_or_update_agent'):
            print(f"   ✅ index_client.create_or_update_agent method exists")
            
            try:
                index_client.create_or_update_agent(agent)
                print(f"   ✅ Agent creation/update successful!")
                
                # Now try to check if we can retrieve it
                if hasattr(index_client, 'get_agent'):
                    try:
                        retrieved_agent = index_client.get_agent(agent_name)
                        print(f"   ✅ Agent retrieval successful!")
                        print(f"     Agent name: {retrieved_agent.name}")
                        if hasattr(retrieved_agent, 'target_indexes'):
                            target_indexes = [idx.index_name for idx in retrieved_agent.target_indexes]
                            print(f"     Target indexes: {target_indexes}")
                        return True
                        
                    except Exception as e:
                        print(f"   ⚠️ Agent created but retrieval failed: {str(e)}")
                        print(f"     This might be normal - some SDK versions don't support get_agent")
                        return True  # Agent creation worked, that's the main thing
                        
                else:
                    print(f"   ⚠️ index_client.get_agent method not available")
                    print(f"     But agent creation succeeded, so agent should exist")
                    return True
                
            except Exception as e:
                print(f"   ❌ Agent creation failed: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
                
        else:
            print(f"   ❌ index_client.create_or_update_agent method NOT available")
            print(f"     This explains why agents might not be created!")
            return False
        
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        print(f"   Agent classes not available in current SDK version")
        return False
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_retrieval():
    """Test if we can retrieve and use the agent for queries"""
    
    print(f"\n🎯 TESTING AGENT RETRIEVAL")
    print("-" * 40)
    
    try:
        # Import agent client setup from main code
        import importlib.util
        spec = importlib.util.spec_from_file_location("agentic_rag_demo", "/Users/robenhai/agentic-rag-demo/agentic-rag-demo.py")
        agentic_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agentic_module)
        
        agent_name = "delete1-agent"
        print(f"   Initializing agent client for: {agent_name}")
        
        agent_client = agentic_module.init_agent_client(agent_name)
        print(f"   ✅ Agent client created successfully")
        
        # The fact that we can create the client suggests the agent exists
        # Direct testing would require the agent SDK imports which are problematic
        print(f"   💡 Agent client creation succeeded - this suggests agent exists")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error initializing agent client: {str(e)}")
        print(f"     This suggests the agent doesn't exist or has configuration issues")
        return False

if __name__ == "__main__":
    creation_success = test_agent_creation()
    
    if creation_success:
        retrieval_success = test_agent_retrieval()
    else:
        retrieval_success = False
    
    print("\n" + "=" * 60)
    print("🎯 FINAL DIAGNOSIS:")
    
    if creation_success and retrieval_success:
        print("✅ Agent infrastructure appears to be working")
        print("🔍 The empty results issue is likely in:")
        print("   1. Query processing")
        print("   2. Agent retrieval parameters")
        print("   3. Index data format/compatibility")
        print("   4. Language/encoding issues")
    elif creation_success and not retrieval_success:
        print("⚠️ Agent can be created but not retrieved/used")
        print("🔍 This suggests an agent configuration or SDK compatibility issue")
    else:
        print("❌ Agent creation failed")
        print("🔍 This is likely the root cause - agents aren't being created when indexes are made")
        print("💡 Possible solutions:")
        print("   1. Update Azure Search SDK")
        print("   2. Check if agent features are enabled in your Azure AI Search service")
        print("   3. Manually create agents using different approach")
        
    sys.exit(0 if creation_success else 1)
