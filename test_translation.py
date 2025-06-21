#!/usr/bin/env python3

import os
from dotenv import load_dotenv
load_dotenv()

# Test the translation first
from query_translation import translate_hebrew_to_english, should_translate_query

hebrew_query = "תערוך טבלת השוואה בין סוגי הדיסקים"
print(f"Original: {hebrew_query}")
print(f"Should translate: {should_translate_query(hebrew_query)}")
print(f"Translated: {translate_hebrew_to_english(hebrew_query)}")

# Test the enhanced retrieval
print("\n" + "="*50)
try:
    from direct_api_retrieval import retrieve_with_direct_api
    
    result = retrieve_with_direct_api(
        user_question=hebrew_query,
        agent_name='delete1-agent', 
        index_name='delete1',
        include_sources=True
    )
    
    print(f"Chunks found: {len(result.get('chunks', []))}")
    print(f"Answer length: {len(result.get('answer', ''))}")
    
    debug_info = result.get('debug_info', {})
    if 'translated_query' in debug_info:
        print(f"Translation attempted: {debug_info['translated_query']}")
    if 'translation_success' in debug_info:
        print(f"Translation successful: {debug_info['translation_success']}")
    if 'chunks_found_after_translation' in debug_info:
        print(f"Chunks after translation: {debug_info['chunks_found_after_translation']}")
        
    if result.get('answer'):
        print(f"Answer preview: {result['answer'][:200]}...")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
