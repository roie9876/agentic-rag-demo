#!/usr/bin/env python3
"""
Test improved PDF format detection
"""

import os
import sys

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chunking.multimodal_processor import validate_and_detect_format

def test_fake_pdf_scenarios():
    """Test various fake PDF scenarios"""
    
    # Test 1: HTML content with .pdf extension
    html_content = b"""<!DOCTYPE html>
<html>
<head>
    <title>Error Page</title>
</head>
<body>
    <h1>File Not Found</h1>
    <p>The requested file could not be found.</p>
</body>
</html>"""
    
    print("=== Test 1: HTML content with .pdf extension ===")
    is_valid, detected_format, content_type, message = validate_and_detect_format(html_content, "error.pdf")
    print(f"Valid: {is_valid}")
    print(f"Detected format: {detected_format}")
    print(f"Content type: {content_type}")
    print(f"Message: {message}")
    print()
    
    # Test 2: Plain text with .pdf extension
    text_content = b"""Error: File not found
The requested document is not available.
Please contact support for assistance."""
    
    print("=== Test 2: Plain text with .pdf extension ===")
    is_valid, detected_format, content_type, message = validate_and_detect_format(text_content, "error.pdf")
    print(f"Valid: {is_valid}")
    print(f"Detected format: {detected_format}")
    print(f"Content type: {content_type}")
    print(f"Message: {message}")
    print()
    
    # Test 3: JSON content with .pdf extension
    json_content = b"""{"error": "file_not_found", "message": "The requested file could not be found", "code": 404}"""
    
    print("=== Test 3: JSON content with .pdf extension ===")
    is_valid, detected_format, content_type, message = validate_and_detect_format(json_content, "error.pdf")
    print(f"Valid: {is_valid}")
    print(f"Detected format: {detected_format}")
    print(f"Content type: {content_type}")
    print(f"Message: {message}")
    print()
    
    # Test 4: Valid PDF (should still work)
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj"""
    
    print("=== Test 4: Valid PDF content ===")
    is_valid, detected_format, content_type, message = validate_and_detect_format(pdf_content, "valid.pdf")
    print(f"Valid: {is_valid}")
    print(f"Detected format: {detected_format}")
    print(f"Content type: {content_type}")
    print(f"Message: {message}")
    print()
    
    # Test 5: Very small corrupted PDF (similar to your case)
    small_content = b"""<html><head><title>Error</title></head><body>File not found</body></html>"""[:644]  # Truncate to 644 bytes like your file
    
    print("=== Test 5: Small HTML content (644 bytes like your file) ===")
    print(f"Content preview: {small_content[:100]}...")
    is_valid, detected_format, content_type, message = validate_and_detect_format(small_content, "שומה בן חיים.pdf")
    print(f"Valid: {is_valid}")
    print(f"Detected format: {detected_format}")
    print(f"Content type: {content_type}")
    print(f"Message: {message}")

if __name__ == "__main__":
    print("Testing improved PDF format detection...")
    test_fake_pdf_scenarios()
    print("\nThe improved detection should now correctly identify non-PDF content")
    print("and send it to Document Intelligence with the proper content-type!")
