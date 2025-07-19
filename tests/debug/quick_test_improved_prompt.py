#!/usr/bin/env python3
"""
Quick test for the improved prompt
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

load_dotenv()

from direct_api_retrieval import retrieve_with_direct_api

def quick_test():
    result = retrieve_with_direct_api(
        user_question='תוך כמה ימים מאי תשלום החשבון ניתן לנתק צרכן ?',
        agent_name='iec-agent',
        index_name='iec',
        reranker_threshold=1.0,
        include_sources=True
    )
    
    answer = result.get('answer', '')
    print(f"Answer: {answer}")
    print(f"Contains 107? {'107' in answer}")
    print(f"Contains 5? {'5' in answer}")

if __name__ == "__main__":
    quick_test()
