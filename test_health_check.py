#!/usr/bin/env python3
"""
Test script for the Health Check module
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Test imports
try:
    from health_check import HealthChecker, HealthCheckUI
    print("✅ Successfully imported HealthChecker and HealthCheckUI")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test basic functionality
def test_health_checker():
    """Test the HealthChecker class"""
    print("\n🧪 Testing HealthChecker...")
    
    health_checker = HealthChecker()
    
    # Test individual service checks
    print("  - Testing OpenAI health check...")
    openai_status, openai_msg = health_checker.check_openai_health()
    print(f"    OpenAI: {'✅' if openai_status else '❌'} {openai_msg}")
    
    print("  - Testing AI Search health check...")
    search_status, search_msg = health_checker.check_ai_search_health()
    print(f"    AI Search: {'✅' if search_status else '❌'} {search_msg}")
    
    print("  - Testing Document Intelligence health check...")
    doc_status, doc_msg = health_checker.check_document_intelligence_health()
    print(f"    Document Intelligence: {'✅' if doc_status else '❌'} {doc_msg}")
    
    # Test the comprehensive check
    print("  - Testing comprehensive health check...")
    results, all_healthy, troubleshooting = health_checker.check_all_services()
    print(f"    Overall health: {'✅ All healthy' if all_healthy else '❌ Some issues detected'}")
    
    if troubleshooting:
        print(f"    Troubleshooting info provided for {len(troubleshooting)} services")
    
    return all_healthy

def test_health_ui():
    """Test the HealthCheckUI class"""
    print("\n🧪 Testing HealthCheckUI...")
    
    try:
        health_ui = HealthCheckUI()
        print("  ✅ HealthCheckUI instantiated successfully")
        
        # Note: We can't test the actual UI rendering without Streamlit context
        print("  ℹ️  UI methods available but require Streamlit context to test")
        return True
    except Exception as e:
        print(f"  ❌ HealthCheckUI test failed: {e}")
        return False

if __name__ == "__main__":
    print("🏥 Health Check Module Test Suite")
    print("=" * 40)
    
    # Run tests
    health_checker_ok = test_health_checker()
    health_ui_ok = test_health_ui()
    
    print("\n" + "=" * 40)
    print("📊 Test Results:")
    print(f"  HealthChecker: {'✅ PASS' if health_checker_ok else '❌ FAIL'}")
    print(f"  HealthCheckUI: {'✅ PASS' if health_ui_ok else '❌ FAIL'}")
    
    if health_checker_ok and health_ui_ok:
        print("\n🎉 All tests passed! Health Check module is working correctly.")
        print("\n💡 To use in your main application:")
        print("   from health_check import HealthChecker, HealthCheckUI")
        print("   health_checker = HealthChecker()")
        print("   health_ui = HealthCheckUI()")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")
        sys.exit(1)
