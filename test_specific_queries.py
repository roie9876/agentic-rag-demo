#!/usr/bin/env python3
"""Test specific search terms that should match the content"""

import os
from azure.search.documents import SearchClient
from azure.identity import DefaultAzureCredential

def test_specific_queries():
    """Test specific search queries that should match content"""
    
    # Test queries that should work based on the content we saw
    test_cases = [
        ("agentic-demo", "משרד הביטחון"),  # Hebrew content from the docs
        ("agentic-demo", "מכרז"),  # Another Hebrew term
        ("agentic-index", "תמיכות"),  # Hebrew content
        ("deleme1", "muscle"),  # English content from somatosensory.pdf
        ("deleme1", "proprioceptive"),  # Technical term from the PDF
        ("sharepoint-index-1", "enterprise"),  # From Enterprise Chat.docx
        ("sharepoint-index-1", "chat"),  # From Enterprise Chat.docx
        ("sharepoint-index-1", "Azure"),  # From UltraDisk presentation
        ("sharepoint-index-1", "UltraDisk"),  # From presentation title
    ]
    
    credential = DefaultAzureCredential()
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    for index_name, query in test_cases:
        try:
            search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
            
            print(f"🔍 Searching '{index_name}' for '{query}'")
            results = search_client.search(query, top=3, include_total_count=True)
            count = results.get_count()
            
            if count > 0:
                print(f"   ✅ Found {count} results!")
                for i, doc in enumerate(results):
                    print(f"   📄 Result {i+1}: {doc.get('source', 'No source')} - Score: {doc.get('@search.score', 'N/A')}")
                    # Show relevant content snippet
                    content = doc.get('content') or doc.get('page_chunk', '')
                    if content:
                        snippet = content[:200] + "..." if len(content) > 200 else content
                        print(f"      Content: {snippet}")
            else:
                print(f"   ❌ No results found")
                
            print()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()

if __name__ == "__main__":
    test_specific_queries()
