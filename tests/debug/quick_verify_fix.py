#!/usr/bin/env python3
"""
Quick verification that the reranker threshold fix is working
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def check_fix():
    """Check if direct_api_retrieval.py has the correct default threshold"""
    
    print("🔍 Verifying Reranker Threshold Fix")
    print("=" * 50)
    
    # Read the direct_api_retrieval.py file
    try:
        with open('direct_api_retrieval.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for the fixed line
        if 'reranker_threshold: float = 1.0' in content:
            print("✅ SUCCESS: Found reranker_threshold: float = 1.0")
            print("🎯 The default threshold is now correctly set to 1.0 (matching agent.py)")
            
            # Also check if the old wrong value is gone
            if 'reranker_threshold: float = 2.5' in content:
                print("⚠️  WARNING: Old value 2.5 still found - may need cleanup")
            else:
                print("✅ CONFIRMED: Old incorrect value 2.5 is gone")
                
        elif 'reranker_threshold: float = 2.5' in content:
            print("❌ ISSUE: Still showing old value 2.5")
            print("🔧 Fix needed: Change default from 2.5 to 1.0")
            
        else:
            print("❓ UNKNOWN: Could not find reranker_threshold default value")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        
    # Also check what function/agent.py uses for comparison
    print("\n🔍 Checking function/agent.py for reference:")
    try:
        with open('function/agent.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'RERANKER_THRESHOLD = float(os.getenv("RERANKER_THRESHOLD", "1"))' in content:
            print("✅ REFERENCE: function/agent.py uses default 1.0")
            print("🎯 Our fix should now match the working implementation")
        else:
            print("❓ Could not find RERANKER_THRESHOLD in function/agent.py")
            
    except Exception as e:
        print(f"❌ ERROR reading function/agent.py: {e}")

if __name__ == "__main__":
    check_fix()
