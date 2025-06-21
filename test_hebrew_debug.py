#!/usr/bin/env python3
"""
Test the Hebrew query issue with detailed debugging
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_hebrew_query_debug():
    """Test the Hebrew query with detailed debugging"""
    
    print("🔍 TESTING HEBREW QUERY WITH DEBUGGING")
    print("=" * 60)
    
    try:
        from direct_api_retrieval import retrieve_with_direct_api
        
        hebrew_query = "תערוך טבלת השוואה בין סוגי הדיסקים"
        print(f"Query: {hebrew_query}")
        print("(Translation: Create comparison table between disk types)")
        
        result = retrieve_with_direct_api(
            user_question=hebrew_query,
            agent_name='delete1-agent',
            index_name='delete1',
            include_sources=True,
            debug=True
        )
        
        print(f"\n📊 MAIN RESULTS:")
        print(f"   Answer length: {len(result.get('answer', ''))}")
        print(f"   Chunks found: {len(result.get('chunks', []))}")
        print(f"   Sources found: {len(result.get('sources', []))}")
        
        if result.get('error'):
            print(f"   ❌ Error: {result['error']}")
            
        # Show debug info
        debug_info = result.get('debug_info', {})
        if debug_info:
            print(f"\n🐞 API CALL DEBUG:")
            print(f"   Status code: {debug_info.get('status_code', 'N/A')}")
            print(f"   Chunks found: {debug_info.get('chunks_found', 'N/A')}")
            
        # Show alternative search results
        if 'alternative_searches' in debug_info:
            print(f"\n🔍 ALTERNATIVE SEARCH RESULTS:")
            alt_searches = debug_info['alternative_searches']
            
            for search_type, search_result in alt_searches.items():
                hits = search_result.get('hits', 0)
                query = search_result.get('query', search_type)
                
                if hits > 0:
                    print(f"   ✅ {search_type}: {hits} hits for '{query}'")
                    if 'first_hit_source' in search_result:
                        print(f"      First hit: {search_result['first_hit_source']}")
                else:
                    print(f"   ❌ {search_type}: 0 hits for '{query}'")
                    if 'error' in search_result:
                        print(f"      Error: {search_result['error']}")
                        
            # Analysis
            print(f"\n💡 ANALYSIS:")
            english_hits = sum(1 for k, v in alt_searches.items() 
                             if k.startswith('english_') and v.get('hits', 0) > 0)
            hebrew_hits = alt_searches.get('original_hebrew_query', {}).get('hits', 0)
            total_docs = alt_searches.get('wildcard_all_docs', {}).get('hits', 0)
            
            print(f"   Total documents in index: {total_docs}")
            print(f"   Hebrew query hits: {hebrew_hits}")
            print(f"   English queries with hits: {english_hits}")
            
            if total_docs > 0 and hebrew_hits == 0 and english_hits > 0:
                print(f"   🎯 CONCLUSION: Index has content but Hebrew queries don't work")
                print(f"      The index likely doesn't support Hebrew language analysis")
                print(f"      English queries work fine with the same content")
            elif total_docs == 0:
                print(f"   🎯 CONCLUSION: Index appears to be empty")
            elif hebrew_hits > 0:
                print(f"   🎯 CONCLUSION: Hebrew search works, issue might be with agent processing")
            else:
                print(f"   🎯 CONCLUSION: Neither Hebrew nor English queries work")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_hebrew_query_debug()
    
    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS:")
    
    if result and not result.get('error'):
        debug_info = result.get('debug_info', {})
        alt_searches = debug_info.get('alternative_searches', {})
        
        english_hits = sum(1 for k, v in alt_searches.items() 
                         if k.startswith('english_') and v.get('hits', 0) > 0)
        
        if english_hits > 0:
            print("1. ✅ Try English queries instead of Hebrew")
            print("2. 🔧 Configure Hebrew language analyzer in the search index")
            print("3. 🔄 Or translate Hebrew queries to English before sending to agent")
        else:
            print("1. 🔍 Check if the index actually contains the expected content")
            print("2. ⚙️ Verify agent configuration and index mapping")
    else:
        print("1. 🔧 Fix the basic API connection issue first")
        print("2. 🔍 Check authentication and endpoint configuration")
