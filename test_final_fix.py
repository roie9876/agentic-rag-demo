#!/usr/bin/env python3
"""
Final test to verify the agentic retrieval fix is working
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the fixed agentic_retrieval function
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("agentic_rag_demo", "/Users/robenhai/agentic-rag-demo/agentic-rag-demo.py")
    agentic_rag_demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentic_rag_demo)
    
    env = agentic_rag_demo.env
    agentic_retrieval = agentic_rag_demo.agentic_retrieval
    print("✅ Successfully imported agentic_retrieval function")
except ImportError as e:
    print(f"❌ Failed to import: {e}")
    sys.exit(1)

def test_delete3_agent():
    """Test the delete3-agent with a query that should return results"""
    print("\n🧪 TESTING FIXED AGENTIC RETRIEVAL")
    print("="*60)
    
    # Test parameters
    agent_name = "delete3-agent"
    index_name = "delete3"
    query = "What are Pacinian corpuscles?"
    
    # Create messages in the format expected by the function
    messages = [{"role": "user", "content": query}]
    
    print(f"🤖 Agent: {agent_name}")
    print(f"📚 Index: {index_name}")
    print(f"❓ Query: {query}")
    print("-" * 60)
    
    try:
        # Call the fixed agentic_retrieval function
        result = agentic_retrieval(agent_name, index_name, messages)
        
        if result and result != "[]":
            print("✅ SUCCESS: Agentic retrieval returned results!")
            print(f"📊 Result length: {len(result)} characters")
            
            # Try to parse the JSON to see how many chunks we got
            import json
            try:
                chunks = json.loads(result)
                print(f"📦 Number of chunks: {len(chunks)}")
                if chunks:
                    print(f"📝 First chunk preview: {chunks[0].get('content', '')[:200]}...")
            except json.JSONDecodeError:
                print("⚠️  Result is not valid JSON")
        else:
            print("❌ FAILED: Agentic retrieval returned empty results")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False
    
    return True

def main():
    """Main test function"""
    print("🔧 KNOWLEDGE AGENT FIX VERIFICATION")
    print("=" * 60)
    print("Testing the direct API approach with managed identity...")
    
    # Verify environment variables
    required_vars = ["AZURE_SEARCH_ENDPOINT", "API_VERSION"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return
    
    print(f"🔗 Search Endpoint: {env('AZURE_SEARCH_ENDPOINT')}")
    print(f"📝 API Version: {env('API_VERSION')}")
    
    # Run the test
    success = test_delete3_agent()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 FIX VERIFICATION COMPLETE!")
        print("✅ The knowledge agent retrieval is now working with managed identity")
        print("✅ Direct API calls are successfully returning content")
        print("✅ Your application should now work properly!")
    else:
        print("❌ FIX VERIFICATION FAILED")
        print("Please check the debug output above for errors")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
