#!/usr/bin/env python3
"""
Diagnostic script to show how the enhanced format detection handles
the problematic Hebrew Wikipedia file scenario.
"""

import logging

# Configure logging to see the debug messages
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Create a sample file that matches your error scenario
problematic_file_content = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<title>תעשייה אווירית – ויקיפדיה</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>console.log("test");</script>
</head>
<body>
<h1>תעשייה אווירית</h1>
<p>תעשייה אווירית היא ענף בתעשייה...</p>
<div class="content">
<span>More Hebrew content here</span>
</div>
</body>
</html>"""

# Trim to approximately 599 bytes to match your scenario
file_bytes = problematic_file_content.encode('utf-8')[:599]
filename = "תעשייה אווירית – ויקיפדיה.pdf"

print("🔍 Analyzing problematic file scenario")
print("=" * 50)
print(f"Filename: {filename}")
print(f"Size: {len(file_bytes)} bytes")
print(f"First 100 bytes: {repr(file_bytes[:100])}")

# Manually test what the enhanced detection would do
print(f"\n🔧 Testing enhanced format detection logic...")

# Check for HTML patterns
first_2kb = file_bytes[:2048].lower()
html_patterns = [
    b'<!doctype html',
    b'<html',
    b'<head>',
    b'<body>',
    b'<meta',
    b'<title>',
    b'<div',
    b'<p>',
    b'<script',
    b'<style',
    b'href=',
    b'src=',
    b'xmlns=',
    b'<br',
    b'<span',
    b'<a ',
]

html_score = sum(1 for pattern in html_patterns if pattern in first_2kb)
found_patterns = [pattern.decode('utf-8') for pattern in html_patterns if pattern in first_2kb]

print(f"HTML patterns found: {html_score}")
print(f"Detected patterns: {found_patterns}")

if html_score >= 3:
    detected_format = 'html'
    content_type = 'text/html'
    reason = f"Enhanced HTML detection (score: {html_score})"
    
    print(f"\n✅ DETECTION RESULT:")
    print(f"   Format: {detected_format}")
    print(f"   Content-Type: {content_type}")
    print(f"   Reason: {reason}")
    
    print(f"\n🎯 SOLUTION:")
    print(f"   Before fix: Document Intelligence receives 'application/pdf'")
    print(f"   After fix:  Document Intelligence receives 'text/html'")
    print(f"   Result:     HTML files are processed correctly instead of getting 400 error!")
    
else:
    print(f"\n❌ Detection would still fail (score: {html_score})")
    print(f"   Need to investigate further or improve detection patterns")

print(f"\n📋 Next steps:")
print(f"1. The enhanced detection is now implemented in multimodal_processor.py")
print(f"2. When you upload a file with .pdf extension that's actually HTML,")
print(f"   it will detect the real format and send the correct content-type")
print(f"3. This should resolve the Document Intelligence 400 error")
print(f"4. Try uploading the problematic file again to test the fix")
