#!/usr/bin/env python3
"""
Check what indexes and agents actually exist in Azure AI Search
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def check_resources():
    """Check available indexes and agents"""
    
    print("🔍 CHECKING AZURE AI SEARCH RESOURCES")
    print("=" * 60)
    
    try:
        from azure.search.documents.indexes import SearchIndexClient
        from azure.search.documents import SearchClient
        from azure.identity import DefaultAzureCredential
        
        # Configuration
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        project_endpoint = os.getenv("PROJECT_ENDPOINT")
        
        print(f"🔧 Configuration:")
        print(f"   Search Endpoint: {search_endpoint}")
        print(f"   Project Endpoint: {project_endpoint}")
        print(f"   INDEX_NAME env var: {os.getenv('INDEX_NAME')}")
        
        if not search_endpoint or not project_endpoint:
            print("❌ Missing required endpoints!")
            return False
            
        # Initialize clients
        credential = DefaultAzureCredential()
        search_index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        print(f"✅ Search index client initialized")
        
        # List indexes
        print(f"\n📋 Checking available indexes...")
        try:
            indexes = list(search_index_client.list_indexes())
            index_names = [idx.name for idx in indexes]
            
            print(f"   Found {len(index_names)} indexes:")
            for name in index_names:
                print(f"     - {name}")
                
            # Check specific indexes
            target_indexes = ["delete1", "agentic-vectors"]
            for target in target_indexes:
                if target in index_names:
                    print(f"\n✅ Index '{target}' EXISTS")                        # Check if it has documents
                        search_client = SearchClient(endpoint=search_endpoint, index_name=target, credential=credential)
                    try:
                        # Count documents
                        result = search_client.search("*", top=1, include_total_count=True)
                        total_count = result.get_count()
                        print(f"   Documents: {total_count}")
                        
                        # Test a simple query
                        test_result = search_client.search("UltraDisk", top=3)
                        test_docs = list(test_result)
                        print(f"   Test query 'UltraDisk': {len(test_docs)} results")
                        
                    except Exception as e:
                        print(f"   ⚠️ Error querying index: {str(e)}")
                        
                else:
                    print(f"\n❌ Index '{target}' DOES NOT EXIST")
                    
        except Exception as e:
            print(f"   ❌ Error listing indexes: {str(e)}")
            return False
        
        # Now check agents using AI project client
        print(f"\n🤖 Checking available agents...")
        try:
            # Try new SDK imports
            try:
                from azure.ai.projects import AIProjectClient
                ai_client = AIProjectClient.from_connection_string(
                    credential=credential,
                    conn_str=project_endpoint
                )
                print(f"✅ AI project client initialized (new SDK)")
                
                # Try to list agents
                agents = ai_client.agents.list_agents()
                agent_list = list(agents)
                agent_names = [agent.id for agent in agent_list]
                
            except Exception as e1:
                print(f"   ⚠️ New SDK failed: {str(e1)}")
                
                # Try alternative approach
                try:
                    from azure.search.documents.agent import AgentClient
                    agent_client = AgentClient(endpoint=project_endpoint, credential=credential)
                    print(f"✅ Agent client initialized (search SDK)")
                    
                    agents = agent_client.agents.list()
                    agent_list = list(agents)
                    agent_names = [agent.name for agent in agent_list]
                    
                except Exception as e2:
                    print(f"   ⚠️ Search SDK also failed: {str(e2)}")
                    print(f"   This might indicate the agent feature isn't available or configured")
                    return True  # Not a fatal error for our diagnosis
                    
            print(f"   Found {len(agent_names)} agents:")
            for name in agent_names:
                print(f"     - {name}")
                
            # Check expected agents
            expected_agents = ["delete1-agent", "agentic-vectors-agent"]
            for expected in expected_agents:
                if expected in agent_names:
                    print(f"\n✅ Agent '{expected}' EXISTS")
                else:
                    print(f"\n❌ Agent '{expected}' DOES NOT EXIST")
                    
        except Exception as e:
            print(f"   ⚠️ Could not check agents: {str(e)}")
            print(f"   This might be expected if agents aren't set up yet")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_resources()
    
    print("\n" + "=" * 60)
    print("🎯 SUMMARY & RECOMMENDATIONS:")
    
    print("\n💡 Based on the environment variable INDEX_NAME=agentic-vectors:")
    print("   1. The Streamlit app should be looking for index 'agentic-vectors'")
    print("   2. The expected agent name would be 'agentic-vectors-agent'")
    print("   3. But you've been testing with index 'delete1'")
    
    print("\n🛠️ TO FIX:")
    print("1. Either:")
    print("   a) Change INDEX_NAME to 'delete1' to match your test index")
    print("   b) OR select 'delete1' in the Streamlit UI")
    print("   c) OR create the 'agentic-vectors' index and populate it")
    print("2. Ensure the corresponding agent exists for whichever index you use")
    print("3. If agents don't exist, you may need to create them manually")
    
    sys.exit(0 if success else 1)
