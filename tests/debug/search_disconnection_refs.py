#!/usr/bin/env python3
"""
Search through the document to find both 5-day and 107-day references
"""

import os
import sys
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.identity import DefaultAzureCredential

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

load_dotenv()  # Load environment variables

def search_disconnection_references():
    """Search for disconnection timeframe references"""
    
    print("🔍 Searching for Disconnection References")
    print("=" * 60)
    
    # Initialize Azure Search client
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    credential = DefaultAzureCredential()
    search_client = SearchClient(
        endpoint=search_endpoint, 
        index_name="iec", 
        credential=credential
    )
    
    # Search for documents containing both Hebrew question terms and time references
    search_queries = [
        "נתק AND ימים",  # disconnect AND days
        "נתק AND יום",   # disconnect AND day
        "107 AND ימים",  # 107 AND days
        "5 AND ימים",    # 5 AND days
        "תשלום AND נתק", # payment AND disconnect
    ]
    
    for query in search_queries:
        print(f"\n🔍 **Search Query:** {query}")
        print("-" * 30)
        
        try:
            results = search_client.search(
                search_text=query,
                top=10,
                include_total_count=True
            )
            
            print(f"📊 **Total Results:** {results.get_count()}")
            
            for i, result in enumerate(results, 1):
                content = result.get("content", "")[:200] + "..." if len(result.get("content", "")) > 200 else result.get("content", "")
                score = result.get("@search.score", "N/A")
                print(f"  Result {i} (Score: {score}): {content}")
                
                # Look for specific time references
                full_content = result.get("content", "")
                if "107" in full_content and ("ימים" in full_content or "יום" in full_content):
                    print(f"    🎯 CONTAINS 107 DAYS REFERENCE!")
                    # Find the context around 107
                    start = max(0, full_content.find("107") - 100)
                    end = min(len(full_content), full_content.find("107") + 200)
                    context = full_content[start:end]
                    print(f"    Context: ...{context}...")
                    
                if "5" in full_content and ("ימים" in full_content or "יום" in full_content) and "נתק" in full_content:
                    print(f"    ❌ CONTAINS 5 DAYS + DISCONNECT REFERENCE")
                    # Find the context around 5 days
                    import re
                    matches = re.finditer(r'5.*?ימים', full_content)
                    for match in matches:
                        start = max(0, match.start() - 50)
                        end = min(len(full_content), match.end() + 50)
                        context = full_content[start:end]
                        print(f"    Context: ...{context}...")
                
                if i >= 3:  # Limit to first 3 results per query
                    break
                    
        except Exception as e:
            print(f"❌ **Error:** {e}")
            
        print()

if __name__ == "__main__":
    search_disconnection_references()
