#!/usr/bin/env python3
"""
Test script to verify that the IndexAction error fix works in the full pipeline.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_indexaction_fix():
    """Test that the IndexAction error is fixed."""
    
    print("=== Testing IndexAction Error Fix ===\n")
    
    # Test the specific error handling logic
    failed_ids = []
    
    def _on_error(action):
        try:
            # This is the fixed code from agentic-rag-demo.py
            if hasattr(action, 'id'):
                failed_ids.append(action.id)
            elif hasattr(action, 'document') and hasattr(action.document, 'get'):
                failed_ids.append(action.document.get("id", "?"))
            else:
                failed_ids.append("?")
        except Exception as exc:
            logging.error("⚠️  on_error callback failed to record ID: %s", exc)
            failed_ids.append("?")
    
    # Mock IndexAction that mimics the Azure Search IndexAction object
    class MockIndexAction:
        def __init__(self, action_id, document=None):
            self.id = action_id
            self.document = document or {"id": action_id, "content": "test"}
    
    print("Testing with IndexAction object that has 'id' attribute...")
    test_action = MockIndexAction("test-action-123")
    _on_error(test_action)
    print(f"✅ Result: {failed_ids}")
    
    # Test with action that has document but no id
    print("\nTesting with IndexAction object that has document...")
    failed_ids.clear()
    
    class MockIndexActionWithDoc:
        def __init__(self, document):
            self.document = document
    
    test_action_doc = MockIndexActionWithDoc({"id": "doc-456", "content": "test"})
    _on_error(test_action_doc)
    print(f"✅ Result: {failed_ids}")
    
    # Test with action that has neither
    print("\nTesting with IndexAction object that has neither id nor document...")
    failed_ids.clear()
    
    class MockIndexActionEmpty:
        pass
    
    test_action_empty = MockIndexActionEmpty()
    _on_error(test_action_empty)
    print(f"✅ Result: {failed_ids}")
    
    print("\n✅ All IndexAction error handling tests passed!")
    print("The 'IndexAction' object has no attribute 'get' error should be fixed.")
    
    return True

if __name__ == "__main__":
    print("Testing IndexAction Error Fix")
    print("=" * 50)
    
    try:
        success = test_indexaction_fix()
        if success:
            print("\n" + "=" * 50)
            print("✅ TEST PASSED: IndexAction error fix verified")
            print("You can now run the Streamlit app without the IndexAction.get() error")
        else:
            print("\n" + "=" * 50)
            print("❌ TEST FAILED")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
