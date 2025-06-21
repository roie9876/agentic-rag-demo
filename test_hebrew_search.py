#!/usr/bin/env python3
"""
Test Hebrew search capabilities and fix search analysis
"""

import os
import sys

# Add the project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_various_search_queries():
    """Test different ways to search for the PowerPoint content"""
    
    print("🔍 TESTING VARIOUS SEARCH APPROACHES")
    print("=" * 60)
    
    try:
        from azure.search.documents import SearchClient
        from azure.identity import DefaultAzureCredential
        
        # Initialize search client
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        index_name = "delete1"
        credential = DefaultAzureCredential()
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=credential
        )
        
        # Test queries for creating a comparison table of disk types
        test_queries = [
            # English equivalents
            ("comparison", "English: comparison"),
            ("disk types", "English: disk types"),
            ("vs competition", "English: vs competition"),
            ("Ultra Disk vs AWS", "English: specific comparison"),
            ("pricing", "English: pricing"),
            
            # Hebrew transliterations and related terms
            ("דיסק", "Hebrew: disk"),
            ("השוואה", "Hebrew: comparison"),
            ("מחיר", "Hebrew: price"),
            ("azure disk", "Mixed: azure disk"),
            ("premium", "English: premium"),
            
            # Content-based searches for what the user actually wants
            ("AWS io2", "Specific: AWS io2"),
            ("GCP Extreme", "Specific: GCP Extreme"),
            ("Premium V2", "Specific: Premium V2"),
        ]
        
        print("📊 Testing different search queries to find disk comparison data:")
        print("-" * 60)
        
        best_results = []
        
        for query, description in test_queries:
            try:
                results = search_client.search(search_text=query, top=2)
                result_list = list(results)
                count = len(result_list)
                
                print(f"\n🔍 {description}: '{query}'")
                print(f"   Results: {count}")
                
                if count > 0:
                    best_result = result_list[0]
                    score = best_result.get('@search.score', 0)
                    content = best_result.get('content', '')[:100]
                    print(f"   Best score: {score:.4f}")
                    print(f"   Content preview: {content}...")
                    
                    best_results.append({
                        'query': query,
                        'description': description,
                        'score': score,
                        'count': count,
                        'content': content
                    })
                    
            except Exception as e:
                print(f"   Error: {str(e)}")
        
        # Find the best queries for disk comparison
        print("\n🎯 BEST QUERIES FOR DISK COMPARISON:")
        print("-" * 50)
        
        # Sort by score and relevance
        best_results.sort(key=lambda x: x['score'], reverse=True)
        
        for i, result in enumerate(best_results[:5], 1):
            print(f"{i}. {result['description']}: '{result['query']}'")
            print(f"   Score: {result['score']:.4f}, Results: {result['count']}")
            if "comparison" in result['content'].lower() or "vs" in result['content'].lower():
                print(f"   ⭐ Contains comparison content!")
            print()
            
        # Test the specific comparison content
        print("🔍 SEARCHING FOR SPECIFIC COMPARISON TABLE:")
        print("-" * 50)
        
        comparison_query = "Azure Disks vs Competition Price Comparison"
        results = search_client.search(search_text=comparison_query, top=1)
        
        for result in results:
            print("📊 Found comparison table content:")
            content = result.get('content', '')
            print(f"Source: {result.get('source_file', 'Unknown')}")
            print(f"Content:\n{content}")
            
            # This is exactly what the user wants - let's format it as a table
            if "Ultra Disk" in content and "AWS" in content and "GCP" in content:
                print("\n📋 FORMATTED COMPARISON TABLE:")
                print("-" * 40)
                lines = content.split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        print(f"• {line.strip()}")
                        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_various_search_queries()
    
    print("\n" + "=" * 60)
    print("💡 SOLUTION FOR HEBREW QUERIES:")
    print("1. Use English keywords for technical content")
    print("2. Search for 'comparison', 'vs competition', 'pricing'") 
    print("3. The PowerPoint contains exactly what the user wants!")
    print("4. The issue is the Agent not using the right search terms")
    sys.exit(0 if success else 1)
