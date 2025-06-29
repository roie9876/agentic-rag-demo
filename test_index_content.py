#!/usr/bin/env python3
"""
Test if the delete3 index has any documents
"""

import os
from azure.search.documents import SearchClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

def test_index_content():
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    if not endpoint:
        print("❌ AZURE_SEARCH_ENDPOINT not set")
        return
    
    print(f"Testing index content:")
    print(f"  Endpoint: {endpoint}")
    print("-" * 50)
    
    # Test both delete3 and sharepoint-index-2
    indexes_to_test = ["delete3", "sharepoint-index-2"]
    
    for index_name in indexes_to_test:
        print(f"\n🔍 Testing index: {index_name}")
        try:
            client = SearchClient(
                endpoint=endpoint,
                index_name=index_name,
                credential=DefaultAzureCredential()
            )
            
            # Get document count
            result = client.search("*", top=1, include_total_count=True)
            docs = list(result)
            total_count = getattr(result, 'get_count', lambda: 'Unknown')()
            
            print(f"  📊 Total documents: {total_count}")
            print(f"  📄 Sample docs retrieved: {len(docs)}")
            
            if docs:
                doc = docs[0]
                print(f"  🔑 Sample doc keys: {list(doc.keys())[:10]}")
                
                # Try to find content field
                content_fields = [k for k in doc.keys() if 'content' in k.lower() or 'text' in k.lower()]
                if content_fields:
                    content_field = content_fields[0]
                    content = doc.get(content_field, "")
                    print(f"  📝 Content field '{content_field}' length: {len(str(content))}")
                    print(f"  📝 Content preview: {str(content)[:100]}...")
                else:
                    print(f"  ⚠️  No content/text fields found")
            else:
                print(f"  ❌ No documents found")
                
        except Exception as e:
            print(f"  ❌ Error accessing {index_name}: {e}")

if __name__ == "__main__":
    test_index_content()
