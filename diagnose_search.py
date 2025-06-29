#!/usr/bin/env python3
"""
Diagnose search issues in the Test Retrieval tab
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the fixed init_search_client function
try:
    from importlib import import_module
    main_module = import_module("agentic-rag-demo")
    init_search_client = main_module.init_search_client
    env = main_module.env
except Exception as e:
    print(f"Error importing: {e}")
    sys.exit(1)

def diagnose_search_issue():
    print("🔍 Diagnosing Search Issues")
    print("=" * 40)
    
    # 1. Check Azure Search configuration
    print("1️⃣ Azure Search Configuration:")
    endpoint = env("AZURE_SEARCH_ENDPOINT")
    print(f"   - Endpoint: {endpoint}")
    
    # 2. Try to initialize search clients
    print("\n2️⃣ Testing Search Client Initialization:")
    try:
        # Test with the index from the screenshot
        test_index = "deletme1"
        search_client, index_client = init_search_client(test_index)
        
        if search_client is None:
            print(f"   ❌ SearchClient is None for index '{test_index}'")
            
            # Check what indexes are available
            _, index_client = init_search_client()  # Get just the index client
            if index_client:
                try:
                    available_indexes = list(index_client.list_indexes())
                    index_names = [idx.name for idx in available_indexes]
                    print(f"   📋 Available indexes: {index_names}")
                    
                    if test_index not in index_names:
                        print(f"   ⚠️  Index '{test_index}' does NOT exist!")
                        print(f"   💡 Try using one of these existing indexes: {index_names}")
                    else:
                        print(f"   ✅ Index '{test_index}' exists but SearchClient failed to initialize")
                        
                except Exception as e:
                    print(f"   ❌ Failed to list indexes: {e}")
            else:
                print(f"   ❌ IndexClient is also None - authentication issue")
        else:
            print(f"   ✅ SearchClient initialized successfully for '{test_index}'")
            
            # Test a simple search
            print("\n3️⃣ Testing Simple Search:")
            try:
                # Try a simple search
                results = search_client.search(
                    search_text="*",  # Search for everything
                    top=3,
                    include_total_count=True
                )
                
                search_results = list(results)
                print(f"   📊 Total documents in index: {len(search_results)}")
                
                if search_results:
                    print(f"   ✅ Search working - found {len(search_results)} documents")
                    print(f"   📄 Sample document keys: {list(search_results[0].keys())}")
                    
                    # Check if there are any documents with Hebrew content
                    hebrew_docs = 0
                    for doc in search_results:
                        content = doc.get('content', '') or doc.get('page_chunk', '')
                        if any(ord(char) >= 0x0590 and ord(char) <= 0x05FF for char in str(content)):
                            hebrew_docs += 1
                    
                    print(f"   🔤 Documents with Hebrew content: {hebrew_docs}")
                    
                else:
                    print(f"   ⚠️  Index exists but contains NO documents")
                    
            except Exception as e:
                print(f"   ❌ Search test failed: {e}")
                
    except Exception as e:
        print(f"   ❌ Failed to initialize search client: {e}")
    
    # 4. Check authentication
    print("\n4️⃣ Authentication Check:")
    try:
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential()
        token = credential.get_token("https://search.azure.com/.default")
        print(f"   ✅ Managed Identity authentication working")
        print(f"   🔑 Token type: {type(token.token)}")
    except Exception as e:
        print(f"   ❌ Managed Identity authentication failed: {e}")
        print(f"   💡 You might need to:")
        print(f"      - Run 'az login' to authenticate")
        print(f"      - Check RBAC permissions on the Search service")
        print(f"      - Verify the search service endpoint is correct")

if __name__ == "__main__":
    diagnose_search_issue()
