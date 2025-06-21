#!/usr/bin/env python3
"""
Simple diagnostic to check Agent existence and basic configuration
"""

import os
import sys

# Add the project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def simple_agent_check():
    """Simple check of Agent availability and basic retrieval"""
    
    print("🔍 SIMPLE AGENT DIAGNOSTIC")
    print("=" * 60)
    
    try:
        from azure.search.documents.agent import AgentClient
        from azure.identity import DefaultAzureCredential
        
        # Configuration
        project_endpoint = os.getenv("PROJECT_ENDPOINT")
        index_name = "delete1"
        agent_name = f"{index_name}-agent"
        
        print(f"🔧 Configuration:")
        print(f"   Project Endpoint: {project_endpoint}")
        print(f"   Expected Agent: {agent_name}")
        
        if not project_endpoint:
            print("❌ PROJECT_ENDPOINT not configured!")
            return False
            
        # Initialize agent client
        credential = DefaultAzureCredential()
        agent_client = AgentClient(endpoint=project_endpoint, credential=credential)
        print(f"✅ Agent client initialized")
        
        # Check what agents exist
        print(f"\n📋 Checking available agents...")
        try:
            agents = agent_client.agents.list()
            agent_list = list(agents)
            agent_names = [agent.name for agent in agent_list]
            
            print(f"   Found {len(agent_names)} agents:")
            for name in agent_names:
                print(f"     - {name}")
                
            if agent_name in agent_names:
                print(f"\n✅ Target agent '{agent_name}' EXISTS")
                
                # Get agent details
                try:
                    agent_details = agent_client.agents.get(agent_name)
                    print(f"   Agent type: {type(agent_details).__name__}")
                    
                    # Check if agent has index configuration
                    if hasattr(agent_details, '__dict__'):
                        agent_dict = {k: v for k, v in agent_details.__dict__.items() if not k.startswith('_')}
                        print(f"   Agent details: {agent_dict}")
                    else:
                        print(f"   Agent details: {agent_details}")
                        
                except Exception as e:
                    print(f"   ⚠️ Error getting agent details: {str(e)}")
                    
            else:
                print(f"\n❌ Target agent '{agent_name}' DOES NOT EXIST!")
                print(f"   This is likely the main issue.")
                print(f"   Available agents: {agent_names}")
                
                if len(agent_names) > 0:
                    print(f"\n💡 Try using one of the existing agents:")
                    for name in agent_names:
                        print(f"     - {name}")
                    print(f"\n   Or create the missing agent '{agent_name}'")
                else:
                    print(f"\n💡 No agents found - you need to create the agent first")
                
                return False
                
        except Exception as e:
            print(f"   ❌ Error listing agents: {str(e)}")
            print(f"   This could indicate authentication or endpoint issues")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_streamlit_session_state():
    """Check what index is actually selected in the Streamlit session"""
    
    print(f"\n🎯 STREAMLIT SESSION STATE CHECK:")
    print("-" * 40)
    
    # Check environment variables that might indicate the selected index
    possible_index_vars = [
        "INDEX_NAME",
        "AZURE_SEARCH_SHAREPOINT_INDEX_NAME", 
        "AZURE_SEARCH_INDEX_NAME"
    ]
    
    for var in possible_index_vars:
        value = os.getenv(var)
        if value:
            print(f"   {var}: {value}")
        else:
            print(f"   {var}: (not set)")
            
    print(f"\n💡 The issue might be:")
    print(f"   1. Streamlit is using a different index name than 'delete1'")
    print(f"   2. The agent 'delete1-agent' doesn't exist") 
    print(f"   3. The agent exists but points to wrong index")

if __name__ == "__main__":
    success = simple_agent_check()
    check_streamlit_session_state()
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSIS SUMMARY:")
    if success:
        print("✅ Agent exists - issue is likely in retrieval parameters or query processing")
        print("🔍 Next: Check agent's index configuration and query handling")
    else:
        print("❌ Agent doesn't exist - this is the root cause")
        print("🛠️ Next: Create the missing agent or use existing agent")
        
    print("\n💡 TO FIX:")
    print("1. Ensure agent exists with correct name")
    print("2. Verify agent points to correct index") 
    print("3. Check agent supports the query language (Hebrew vs English)")
    sys.exit(0 if success else 1)
