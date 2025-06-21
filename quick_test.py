#!/usr/bin/env python3
"""
Simple test for the enhanced format detection.
"""

import sys
sys.path.append('.')

try:
    from chunking.multimodal_processor import validate_and_detect_format
    print('✅ Import successful')
    
    # Test with HTML content that mimics the problematic file
    test_html = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<title>תעשייה אווירית – ויקיפדיה</title>
</head>
<body>
<h1>תעשייה אווירית</h1>
</body>
</html>"""
    
    print(f"Testing HTML content ({len(test_html)} bytes)...")
    
    result = validate_and_detect_format(test_html.encode('utf-8'), 'test.pdf')
    is_valid, detected_format, content_type, message = result
    
    print(f"✅ Valid: {is_valid}")
    print(f"🔍 Format: {detected_format}")
    print(f"📋 Content-Type: {content_type}")
    print(f"💬 Message: {message}")
    
    if detected_format == 'html' and content_type == 'text/html':
        print("\n🎉 SUCCESS! Enhanced detection is working!")
        print("   The system now detects HTML files and will send them")
        print("   to Document Intelligence with 'text/html' content-type")
        print("   instead of 'application/pdf'.")
    
except Exception as e:
    import traceback
    print(f'❌ Error: {e}')
    traceback.print_exc()
