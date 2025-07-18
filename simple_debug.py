#!/usr/bin/env python3
"""
Simple debug test for SharePoint optimization
"""

import sys
import os
import logging

# Add the root directory to the path
sys.path.insert(0, '/home/azureuser/agentic-rag-demo')

def test_optimization():
    """Test optimization availability"""
    
    print("🔍 Simple Optimization Test")
    print("=" * 30)
    
    # Test 1: Environment variable
    env_var = os.getenv('SHAREPOINT_OPTIMIZATION_ENABLED', 'Not set')
    print(f"Environment variable: {env_var}")
    
    # Test 2: Can we import the optimization service?
    try:
        from services.sharepoint_optimization_service import SharePointOptimizationService
        print("✅ Optimization service import successful")
    except ImportError as e:
        print(f"❌ Optimization service import failed: {e}")
        return
    
    # Test 3: Can we create a SharePointIndexManager?
    try:
        from sharepoint_index_manager import SharePointIndexManager
        
        # Just check if we can import it first
        print("✅ SharePointIndexManager import successful")
        
        # Now try to create it
        manager = SharePointIndexManager()
        print(f"✅ SharePointIndexManager created")
        print(f"Optimization enabled: {manager.optimization_enabled}")
        
    except Exception as e:
        print(f"❌ SharePointIndexManager creation failed: {e}")
        return
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_optimization()
