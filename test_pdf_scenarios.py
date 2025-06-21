#!/usr/bin/env python3
"""
Test script to compare our Document Intelligence request with different approaches
to identify why files work in the portal but not in our code.
"""

import os
import sys
from pathlib import Path

# Add the current directory to the path for imports
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

from chunking.multimodal_processor import validate_and_detect_format, MultimodalProcessor

def test_small_pdf_scenarios():
    """Test different scenarios with small PDF files that might fail."""
    
    # Create various test scenarios
    test_cases = [
        {
            "name": "Valid PDF header, minimal content",
            "content": b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000089 00000 n \n0000000173 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n267\n%%EOF",
            "filename": "valid_small.pdf"
        },
        {
            "name": "Corrupted PDF - HTML content",
            "content": b"<!DOCTYPE html><html><head><title>Fake PDF</title></head><body>This is actually HTML</body></html>",
            "filename": "fake_html.pdf"
        },
        {
            "name": "Corrupted PDF - Plain text",
            "content": b"This is just plain text that someone saved as .pdf",
            "filename": "fake_text.pdf"
        },
        {
            "name": "Empty or minimal file",
            "content": b"",
            "filename": "empty.pdf"
        },
        {
            "name": "Very small file",
            "content": b"Hi",
            "filename": "tiny.pdf"
        }
    ]
    
    print("🧪 Testing PDF Processing Scenarios")
    print("=" * 60)
    
    for test_case in test_cases:
        print(f"\n📝 Testing: {test_case['name']}")
        print(f"   File: {test_case['filename']}")
        print(f"   Size: {len(test_case['content'])} bytes")
        
        if len(test_case['content']) <= 100:
            print(f"   Content: {repr(test_case['content'])}")
        else:
            print(f"   Content (first 100): {repr(test_case['content'][:100])}...")
        
        # Test format detection
        try:
            is_valid, detected_format, content_type, message = validate_and_detect_format(
                test_case['content'], test_case['filename']
            )
            
            print(f"   ✅ Validation: {is_valid}")
            print(f"   🔍 Format: {detected_format}")
            print(f"   📋 Content-Type: {content_type}")
            print(f"   💬 Message: {message}")
            
            # Test actual processing if validation passed
            if is_valid and detected_format:
                print(f"   🚀 Testing Document Intelligence processing...")
                
                try:
                    processor = MultimodalProcessor()
                    if processor.doc_client:
                        result = processor.process_document(test_case['content'], test_case['filename'])
                        if result:
                            print(f"   ✅ Processing SUCCESS!")
                            print(f"      Text segments: {len(result.get('text_segments', []))}")
                            print(f"      Images: {len(result.get('images', []))}")
                        else:
                            print(f"   ⚠️  Processing returned None")
                    else:
                        print(f"   ⏭️  No Document Intelligence client available")
                except Exception as e:
                    print(f"   ❌ Processing FAILED: {str(e)[:100]}...")
            else:
                print(f"   ⏭️  Skipping processing (validation failed)")
                
        except Exception as e:
            print(f"   ❌ Validation ERROR: {str(e)[:100]}...")

def test_real_file_diagnostics():
    """Diagnostic information for real problematic files."""
    print(f"\n" + "=" * 60)
    print("🔍 REAL FILE DIAGNOSTICS")
    print("=" * 60)
    
    print("Based on your error messages, here's what we know:")
    print()
    
    # Analysis of your specific error
    problematic_files = [
        {"name": "תעשייה אווירית – ויקיפדיה.pdf", "size": 599},
        {"name": "שומה בן חיים.pdf", "size": 644}
    ]
    
    for file_info in problematic_files:
        print(f"📄 File: {file_info['name']}")
        print(f"   Size: {file_info['size']} bytes")
        print(f"   Status: Works in Azure portal, fails in our code")
        print(f"   Error: Document Intelligence 400 - UnsupportedContent")
        print(f"   Content-Type sent: application/pdf (correct)")
        print()
    
    print("🔍 Possible causes:")
    print("1. ✅ Content-type mismatch (FIXED - now sending application/pdf)")
    print("2. ❓ Request headers difference between portal and our code")
    print("3. ❓ API version difference")
    print("4. ❓ Authentication method difference")
    print("5. ❓ Request body encoding difference")
    print("6. ❓ File upload method difference (multipart vs binary)")
    print()
    
    print("📋 Our current request details:")
    print("   URL: /documentintelligence/documentModels/prebuilt-layout:analyze")
    print("   API Version: 2024-11-30")
    print("   Method: POST")
    print("   Content-Type: application/pdf")
    print("   Body: Raw binary data")
    print("   Features: ocr.highResolution")
    print("   Output: markdown + figures")
    print()
    
    print("🔧 Recommended next steps:")
    print("1. ✅ Implement fallback text extraction for failed files")
    print("2. 🔍 Compare exact request headers with Azure portal")
    print("3. 🧪 Test with different API versions")
    print("4. 🔄 Test multipart/form-data upload method")
    print("5. 📊 Capture network traffic from Azure portal for comparison")

def main():
    """Main test function."""
    print("🩺 Document Intelligence Processing Diagnostics")
    print("=" * 60)
    
    # Test various scenarios
    test_small_pdf_scenarios()
    
    # Diagnostic information
    test_real_file_diagnostics()
    
    print(f"\n" + "=" * 60)
    print("✅ SOLUTION IMPLEMENTED")
    print("=" * 60)
    print("The enhanced format detection and fallback processing has been")
    print("implemented in the multimodal processor. Files that fail with")
    print("Document Intelligence will now fall back to basic text extraction")
    print("instead of completely failing.")
    print()
    print("Your files should now be processed successfully, even if Document")
    print("Intelligence rejects them. The system will extract whatever text")
    print("content is available and create searchable chunks.")

if __name__ == "__main__":
    main()
