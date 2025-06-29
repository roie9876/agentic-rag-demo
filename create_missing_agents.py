#!/usr/bin/env python3
"""
Create missing Knowledge Agents for existing indexes
Based on the working logic from agentic-rag-demo.py
"""

import os
import sys
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.agent import SearchServiceClient
from azure.search.documents.agent.models import (
    KnowledgeAgent,
    KnowledgeAgentAzureOpenAIModel,
    KnowledgeAgentTargetIndex,
    KnowledgeAgentRequestLimits,
    AzureOpenAIVectorizerParameters
)
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_search_credential():
    """Get search credential (API key or managed identity)"""
    search_api_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("SEARCH_API_KEY")
    if search_api_key:
        return AzureKeyCredential(search_api_key)
    else:
        return DefaultAzureCredential()

def main():
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_41") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
    
    if not all([search_endpoint, azure_openai_endpoint, deployment_name]):
        print("❌ Missing required environment variables:")
        print(f"   AZURE_SEARCH_ENDPOINT: {'✓' if search_endpoint else '❌'}")
        print(f"   AZURE_OPENAI_ENDPOINT: {'✓' if azure_openai_endpoint else '❌'}")
        print(f"   AZURE_OPENAI_DEPLOYMENT_41: {'✓' if deployment_name else '❌'}")
        return 1
    
    credential = get_search_credential()
    
    print(f"🔗 Connecting to: {search_endpoint}")
    print(f"🤖 OpenAI endpoint: {azure_openai_endpoint}")
    print(f"📋 Deployment: {deployment_name}")
    print()
    
    # Create clients
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
    service_client = SearchServiceClient(endpoint=search_endpoint, credential=credential)
    
    try:
        # List existing indexes
        print("📚 Existing indexes:")
        indexes = list(index_client.list_indexes())
        for idx in indexes:
            print(f"   - {idx.name}")
        
        if not indexes:
            print("❓ No indexes found. Create an index first.")
            return 1
        
        print()
        
        # List existing agents
        print("🤖 Existing agents:")
        try:
            agents = list(service_client.list_agents())
            agent_names = [agent.name for agent in agents]
            if agents:
                for agent in agents:
                    print(f"   - {agent.name}")
            else:
                print("   (none)")
        except Exception as e:
            print(f"   ❌ Could not list agents: {e}")
            agent_names = []
        
        print()
        
        # Create missing agents
        print("🛠️  Creating missing agents:")
        created_count = 0
        
        for index in indexes:
            index_name = index.name
            agent_name = f"{index_name}-agent"
            
            if agent_name in agent_names:
                print(f"   ✓ {agent_name} already exists")
                continue
            
            print(f"   🔨 Creating {agent_name}...")
            
            try:
                # Create agent using the same logic as agentic-rag-demo.py
                agent = KnowledgeAgent(
                    name=agent_name,
                    models=[
                        KnowledgeAgentAzureOpenAIModel(
                            azure_open_ai_parameters=AzureOpenAIVectorizerParameters(
                                resource_url=azure_openai_endpoint,
                                deployment_name=deployment_name,
                                model_name="gpt-4o",  # Fixed model name
                                # api_key removed - uses managed identity authentication
                            )
                        )
                    ],
                    target_indexes=[
                        KnowledgeAgentTargetIndex(
                            index_name=index_name, 
                            default_reranker_threshold=2.5
                        )
                    ],
                    request_limits=KnowledgeAgentRequestLimits(
                        max_output_size=16000  # Match Azure Function's MAX_OUTPUT_SIZE default
                    ),
                )
                
                # Create the agent
                service_client.create_or_update_agent(agent)
                print(f"   ✅ Successfully created {agent_name}")
                created_count += 1
                
            except Exception as e:
                print(f"   ❌ Failed to create {agent_name}: {e}")
                print(f"      Error details: {type(e).__name__}")
                continue
        
        print()
        print(f"🎉 Summary: Created {created_count} new agents")
        
        if created_count > 0:
            print("\n🧪 You can now test agentic retrieval with:")
            for index in indexes:
                agent_name = f"{index.name}-agent" 
                if agent_name not in agent_names:  # This was just created
                    print(f"   - Agent: {agent_name}")
                    print(f"   - Index: {index.name}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
