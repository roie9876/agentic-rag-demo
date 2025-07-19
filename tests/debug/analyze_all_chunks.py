#!/usr/bin/env python3
"""
Create a comprehensive test that shows what the LLM sees
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

load_dotenv()

from direct_api_retrieval import retrieve_with_direct_api

def analyze_chunks():
    result = retrieve_with_direct_api(
        user_question='תוך כמה ימים מאי תשלום החשבון ניתן לנתק צרכן ?',
        agent_name='iec-agent',
        index_name='iec',
        reranker_threshold=1.0,
        include_sources=True
    )
    
    chunks = result.get('chunks', [])
    print(f"Total chunks: {len(chunks)}")
    print("=" * 60)
    
    for i, chunk in enumerate(chunks, 1):
        content = chunk.get('content', chunk.get('text', 'No content'))
        print(f"\n**CHUNK {i}:**")
        print(f"Content: {content[:300]}...")
        
        # Check for 107 days
        if "107" in content and ("ימים" in content or "יום" in content):
            print("🎯 **THIS CHUNK CONTAINS 107 DAYS!**")
            # Find and show the 107-day context
            import re
            matches = list(re.finditer(r'107.*?ימים|ימים.*?107', content))
            for match in matches:
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end]
                print(f"   107-day context: ...{context}...")
            
        # Check for 5 days + disconnect
        if "5" in content and ("ימים" in content or "יום" in content):
            print("❌ **THIS CHUNK CONTAINS 5 DAYS**")
            
    print("\n" + "=" * 60)
    print(f"LLM Answer: {result.get('answer', '')}")
    
    # If we have a chunk with 107 days, let's see what happens if we manually build a better prompt
    chunks_with_107 = []
    for i, chunk in enumerate(chunks, 1):
        content = chunk.get('content', chunk.get('text', ''))
        if "107" in content and ("ימים" in content or "יום" in content):
            chunks_with_107.append((i, content))
            
    if chunks_with_107:
        print(f"\n🎯 FOUND {len(chunks_with_107)} CHUNK(S) WITH 107 DAYS:")
        for chunk_num, content in chunks_with_107:
            print(f"Chunk {chunk_num}: {content[:500]}...")

if __name__ == "__main__":
    analyze_chunks()
