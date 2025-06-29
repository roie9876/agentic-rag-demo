#!/usr/bin/env python3
"""
Simple test to verify end-to-end functionality
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from dotenv import load_dotenv
load_dotenv()

def test_document_intelligence():
    """Test Document Intelligence client initialization."""
    try:
        from tools.doc_intelligence import DocumentIntelligenceClient
        
        print("Testing Document Intelligence client...")
        client = DocumentIntelligenceClient()
        print("✅ Document Intelligence client initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Document Intelligence client failed: {e}")
        return False

def test_health_check_ui():
    """Test health check UI resource discovery."""
    try:
        from health_check.health_check_ui import HealthCheckUI
        
        print("Testing health check UI resource discovery...")
        ui = HealthCheckUI()
        
        # Test Document Intelligence resource discovery
        doc_intel_endpoint = os.getenv("DOCUMENT_INTEL_ENDPOINT")
        if doc_intel_endpoint:
            resource_name = ui._find_resource_name_by_endpoint(
                doc_intel_endpoint, 
                ["FormRecognizer", "DocumentIntelligence"]
            )
            if resource_name:
                print(f"✅ Resource discovery successful: Found '{resource_name}'")
                return True
            else:
                print("❌ Resource discovery failed: No resource found")
                return False
        else:
            print("⚠️ DOCUMENT_INTEL_ENDPOINT not configured")
            return False
    except Exception as e:
        print(f"❌ Health check UI test failed: {e}")
        return False

def test_multimodal_processor():
    """Test multimodal processor initialization."""
    try:
        from chunking.multimodal_processor import MultimodalProcessor
        
        print("Testing multimodal processor...")
        processor = MultimodalProcessor()
        
        if processor.doc_client:
            print("✅ Multimodal processor with Document Intelligence initialized successfully")
            return True
        else:
            print("⚠️ Multimodal processor initialized but Document Intelligence client is None")
            return False
    except Exception as e:
        print(f"❌ Multimodal processor failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Running End-to-End Tests")
    print("=" * 50)
    
    tests = [
        ("Document Intelligence Client", test_document_intelligence),
        ("Multimodal Processor", test_multimodal_processor),
        ("Health Check UI Resource Discovery", test_health_check_ui),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 Overall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! The system is ready for use.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
