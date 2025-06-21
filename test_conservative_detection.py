#!/usr/bin/env python3
"""
Test the conservative format detection for PDF files.
"""

import sys
sys.path.append('.')

from chunking.multimodal_processor import validate_and_detect_format

def test_pdf_format_detection():
    """Test that PDF files are properly detected and not misidentified as HTML."""
    
    # Test case 1: Small file with .pdf extension that might contain some HTML-like content
    # This simulates your problematic files
    small_pdf_like = b"Some content with <tags> but should be PDF based on extension"
    
    print("🧪 Testing PDF format detection...")
    print("=" * 50)
    
    test_files = [
        ("שומה בן חיים.pdf", small_pdf_like),
        ("תעשייה אווירית – ויקיפדיה.pdf", small_pdf_like),
        ("regular_document.pdf", b"PDF content without HTML tags"),
        ("actual_html.html", b"<!DOCTYPE html><html><head><title>Test</title></head><body>Hello</body></html>"),
        ("clear_html_but_pdf_ext.pdf", b"<!DOCTYPE html><html><head><title>This is clearly HTML</title></head><body>HTML content</body></html>"),
    ]
    
    for filename, content in test_files:
        print(f"\n📝 Testing: {filename}")
        print(f"   Content: {content[:50]}...")
        
        try:
            is_valid, detected_format, content_type, message = validate_and_detect_format(content, filename)
            
            print(f"   ✅ Valid: {is_valid}")
            print(f"   🔍 Format: {detected_format}")
            print(f"   📋 Content-Type: {content_type}")
            print(f"   💬 Message: {message}")
            
            # Check if .pdf files are being detected as PDF (not HTML)
            if filename.endswith('.pdf') and not filename.startswith('clear_html'):
                if detected_format == 'pdf' and content_type == 'application/pdf':
                    print(f"   ✅ CORRECT: PDF file detected as PDF")
                else:
                    print(f"   ❌ INCORRECT: PDF file detected as {detected_format}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n" + "=" * 50)
    print("🎯 Summary:")
    print("- Files with .pdf extension should be detected as PDF (application/pdf)")
    print("- Only override to HTML if there's very strong evidence (like <!DOCTYPE html>)")
    print("- This should fix the Document Intelligence 400 error for your files")

if __name__ == "__main__":
    test_pdf_format_detection()
