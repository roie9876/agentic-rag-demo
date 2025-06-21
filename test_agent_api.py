#!/usr/bin/env python3
"""
Test agent API directly using the agent.py functions
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root and function folder to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
function_dir = os.path.join(current_dir, "function")
sys.path.insert(0, current_dir)
sys.path.insert(0, function_dir)

def test_agent_api():
    """Test the agent API directly"""
    
    print("🔍 TESTING AGENT API DIRECTLY")
    print("=" * 60)
    
    try:
        # Import the agent functions
        from agent import answer_question, _validate_env
        
        print("✅ Successfully imported agent functions")
        
        # Configure the environment for the test
        # Based on the .env file, we need to extract the search service name
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        if search_endpoint:
            # Extract service name from URL like https://ai-serach-demo-eastus.search.windows.net
            service_name = search_endpoint.replace("https://", "").replace(".search.windows.net", "")
            os.environ["SERVICE_NAME"] = service_name
            print(f"🔧 Set SERVICE_NAME: {service_name}")
        else:
            print("❌ AZURE_SEARCH_ENDPOINT not found in environment")
            return False
            
        # Set other required environment variables
        test_configs = [
            ("delete1", "delete1-agent"),  # The index we've been testing
            ("agentic-vectors", "agentic-vectors-agent")  # The default from .env
        ]
        
        for index_name, agent_name in test_configs:
            print(f"\n🧪 Testing agent: {agent_name} with index: {index_name}")
            print("-" * 50)
            
            # Set environment variables for this test
            os.environ["AGENT_NAME"] = agent_name
            os.environ["INDEX_NAME"] = index_name
            
            try:
                # Validate environment
                _validate_env()
                print(f"✅ Environment validation passed")
                
                # Test queries
                test_queries = [
                    "UltraDisk features",  # English query
                    "מה זה UltraDisk?",     # Hebrew query
                    "Azure storage"         # Another English query
                ]
                
                for query in test_queries:
                    print(f"\n🔍 Query: '{query}'")
                    
                    try:
                        # Test with retrieve mode (returns chunks)
                        print("   Testing /retrieve endpoint...")
                        result = answer_question(
                            user_question=query,
                            index_name=index_name,
                            agent_name=agent_name,
                            use_responses=False,  # Use retrieve mode
                            debug=False,
                            include_sources=True
                        )
                        
                        if isinstance(result, dict):
                            answer = result.get("answer", "")
                            sources = result.get("sources", [])
                            print(f"     Answer length: {len(answer)} chars")
                            print(f"     Sources found: {len(sources)}")
                            if answer:
                                print(f"     Answer preview: {answer[:100]}...")
                            if sources:
                                print(f"     First source: {sources[0].get('source_file', 'N/A')}")
                        else:
                            print(f"     Result: {str(result)[:200]}...")
                            
                        # Also test with responses mode
                        print("   Testing /responses endpoint...")
                        result2 = answer_question(
                            user_question=query,
                            index_name=index_name,
                            agent_name=agent_name,
                            use_responses=True,  # Use responses mode
                            debug=False
                        )
                        
                        print(f"     Response length: {len(str(result2))} chars")
                        if result2 and not result2.startswith("⚠️"):
                            print(f"     Response preview: {str(result2)[:100]}...")
                        else:
                            print(f"     Response: {result2}")
                            
                    except Exception as e:
                        print(f"     ❌ Error with query '{query}': {str(e)}")
                        import traceback
                        traceback.print_exc()
                        
            except Exception as e:
                print(f"❌ Error testing agent {agent_name}: {str(e)}")
                
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        print("   The agent.py file might have missing dependencies")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_agent_api()
    
    print("\n" + "=" * 60)
    print("🎯 SUMMARY:")
    if success:
        print("✅ Agent API test completed")
        print("🔍 Check the results above to see if agents exist and return data")
    else:
        print("❌ Agent API test failed")
        print("🛠️ Need to fix environment or dependencies first")
        
    print("\n💡 INTERPRETATION:")
    print("- If you see HTTP 404 errors → Agent doesn't exist")
    print("- If you see empty results → Agent exists but has issues")
    print("- If you see actual content → Agent is working correctly")
    
    sys.exit(0 if success else 1)
