#!/usr/bin/env python3
"""
Check if the delete1-agent exists and what its configuration is
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def check_delete1_agent():
    """Check if delete1-agent exists and test it"""
    
    print("🔍 CHECKING delete1-agent SPECIFICALLY")
    print("=" * 60)
    
    try:
        from azure.search.documents.indexes import SearchIndexClient
        from azure.search.documents import SearchClient
        from azure.identity import DefaultAzureCredential
        
        # Configuration
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        
        print(f"🔧 Configuration:")
        print(f"   Search Endpoint: {search_endpoint}")
        print(f"   Target Index: delete1")
        print(f"   Expected Agent: delete1-agent")
        
        if not search_endpoint:
            print("❌ AZURE_SEARCH_ENDPOINT not configured!")
            return False
            
        # Initialize clients
        credential = DefaultAzureCredential()
        search_index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        print(f"✅ Search index client initialized")
        
        # Check if delete1 index exists
        print(f"\n📋 Checking if index 'delete1' exists...")
        try:
            indexes = list(search_index_client.list_indexes())
            index_names = [idx.name for idx in indexes]
            
            if "delete1" not in index_names:
                print(f"❌ Index 'delete1' DOES NOT EXIST!")
                print(f"   Available indexes: {index_names}")
                return False
            else:
                print(f"✅ Index 'delete1' EXISTS")
                
                # Check document count
                search_client = SearchClient(endpoint=search_endpoint, index_name="delete1", credential=credential)
                result = search_client.search("*", top=1, include_total_count=True)
                total_count = result.get_count()
                print(f"   Documents in index: {total_count}")
                
        except Exception as e:
            print(f"   ❌ Error checking index: {str(e)}")
            return False
        
        # Now try to check if the agent exists using the newer SearchIndexClient methods
        print(f"\n🤖 Checking if agent 'delete1-agent' exists...")
        try:
            # Try to list agents using SearchIndexClient
            try:
                agents = search_index_client.list_agents()
                agent_list = list(agents)
                agent_names = [agent.name for agent in agent_list]
                
                print(f"   Found {len(agent_names)} agents:")
                for name in agent_names:
                    print(f"     - {name}")
                    
                if "delete1-agent" in agent_names:
                    print(f"\n✅ Agent 'delete1-agent' EXISTS!")
                    
                    # Try to get agent details
                    try:
                        agent_details = search_index_client.get_agent("delete1-agent")
                        print(f"   Agent details found")
                        
                        # Check target indexes
                        if hasattr(agent_details, 'target_indexes'):
                            target_indexes = [idx.index_name for idx in agent_details.target_indexes]
                            print(f"   Target indexes: {target_indexes}")
                            
                            if "delete1" in target_indexes:
                                print(f"   ✅ Agent correctly points to 'delete1' index")
                            else:
                                print(f"   ❌ Agent does NOT point to 'delete1' index!")
                                print(f"       This could be the problem!")
                        else:
                            print(f"   ⚠️ Could not determine agent's target indexes")
                            
                    except Exception as e:
                        print(f"   ⚠️ Error getting agent details: {str(e)}")
                        
                else:
                    print(f"\n❌ Agent 'delete1-agent' DOES NOT EXIST!")
                    print(f"   This is likely the root cause of empty results")
                    print(f"   Available agents: {agent_names}")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Error listing agents: {str(e)}")
                print(f"   This could indicate the agent feature isn't available")
                return False
                
        except Exception as e:
            print(f"   ❌ Error checking agents: {str(e)}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_agent_call():
    """Try to make a direct call to the agent if it exists"""
    
    print(f"\n🎯 TESTING DIRECT AGENT CALL")
    print("-" * 40)
    
    try:
        # Get the agent client from the main module
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import from the main file (note: using the actual filename)
        import importlib.util
        spec = importlib.util.spec_from_file_location("agentic_rag_demo", "/Users/robenhai/agentic-rag-demo/agentic-rag-demo.py")
        agentic_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agentic_module)
        
        agent_name = "delete1-agent"
        print(f"   Trying to initialize agent client for: {agent_name}")
        
        agent_client = agentic_module.init_agent_client(agent_name)
        print(f"✅ Agent client initialized successfully")
        
        # Note: Direct agent testing skipped due to SDK import issues
        # The main goal is to confirm if the agent exists, which we checked above
        print(f"   Direct agent call test skipped - SDK import issues")
        print(f"   But agent existence check is the key diagnostic")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error testing direct agent call: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_delete1_agent()
    
    if success:
        test_direct_agent_call()
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSIS SUMMARY:")
    
    if success:
        print("✅ Index exists and agent check completed")
        print("🔍 If agent exists but returns empty results, the issue is likely:")
        print("   1. Agent configuration problem")
        print("   2. Agent not pointing to correct index")  
        print("   3. Agent retrieval parameters")
        print("   4. Query processing issue")
    else:
        print("❌ Basic infrastructure issue found")
        print("🛠️ Need to fix index or agent creation first")
        
    sys.exit(0 if success else 1)
