#!/usr/bin/env python3
"""
Test the file format detector with problematic files and improve detection logic.
"""

import os
import sys
from pathlib import Path

# Add the current directory to the path for imports
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

from utils.file_format_detector import FileFormatDetector

def analyze_problematic_file():
    """Analyze a file that's causing problems to understand what it contains."""
    
    # Create a sample file that mimics your Hebrew Wikipedia file
    # Based on the error, it's likely an HTML file with Hebrew content
    sample_html = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<title>תעשייה אווירית – ויקיפדיה</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<h1>תעשייה אווירית</h1>
<p>תעשייה אווירית היא ענף בתעשייה הביטחונית...</p>
</body>
</html>"""
    
    sample_bytes = sample_html.encode('utf-8')
    
    print("🔍 Analyzing problematic file content...")
    print(f"📊 File size: {len(sample_bytes)} bytes")
    print(f"🔤 First 100 bytes: {repr(sample_bytes[:100])}")
    
    # Test current format detection
    detected_format, reason = FileFormatDetector.detect_format(sample_bytes, "תעשייה אווירית – ויקיפדיה.pdf")
    
    print(f"\n📋 Current Detection Results:")
    print(f"   Format: {detected_format}")
    print(f"   Reason: {reason}")
    
    if detected_format:
        content_type = FileFormatDetector.get_content_type(detected_format)
        print(f"   Content-Type: {content_type}")
        supported = FileFormatDetector.is_format_supported_by_document_intelligence(detected_format)
        print(f"   Supported by DI: {supported}")
    else:
        print("   ❌ No format detected")
    
    # Test improved detection logic
    print(f"\n🔧 Testing enhanced detection...")
    
    # Check if it's HTML content
    first_kb = sample_bytes[:1024].lower()
    html_indicators = [b'<!doctype html', b'<html', b'<head', b'<body', b'<meta', b'<title']
    found_indicators = [indicator for indicator in html_indicators if indicator in first_kb]
    
    print(f"   HTML indicators found: {len(found_indicators)}")
    print(f"   Indicators: {[ind.decode('utf-8', errors='ignore') for ind in found_indicators]}")
    
    # Check if it's likely UTF-8 text
    try:
        decoded = sample_bytes.decode('utf-8')
        print(f"   Can decode as UTF-8: Yes ({len(decoded)} characters)")
        # Check for Hebrew characters
        hebrew_chars = any('\u0590' <= c <= '\u05FF' for c in decoded)
        print(f"   Contains Hebrew: {'Yes' if hebrew_chars else 'No'}")
    except:
        print(f"   Can decode as UTF-8: No")

def test_enhanced_format_detection(file_bytes, filename):
    """Enhanced format detection that handles edge cases better."""
    
    if not file_bytes or len(file_bytes) < 4:
        return None, None, "File too small or empty"
    
    # Try current detection first
    detected_format, reason = FileFormatDetector.detect_format(file_bytes, filename)
    
    if detected_format:
        content_type = FileFormatDetector.get_content_type(detected_format)
        return detected_format, content_type, reason
    
    # Enhanced detection for cases where current logic fails
    print(f"🔍 Current detection failed, trying enhanced logic...")
    
    first_2kb = file_bytes[:2048].lower()
    
    # More comprehensive HTML detection
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
    ]
    
    html_score = sum(1 for pattern in html_patterns if pattern in first_2kb)
    
    if html_score >= 3:  # Multiple HTML indicators
        print(f"   ✅ Enhanced detection: HTML (score: {html_score})")
        return 'html', 'text/html', f"Enhanced HTML detection (score: {html_score})"
    
    # Check for XML-like content
    if b'<?xml' in first_2kb or b'<xml' in first_2kb:
        print(f"   ✅ Enhanced detection: XML")
        return 'xml', 'application/xml', "Enhanced XML detection"
    
    # Check for JSON content
    stripped = file_bytes.strip()
    if stripped.startswith(b'{') and stripped.endswith(b'}'):
        print(f"   ✅ Enhanced detection: JSON")
        return 'json', 'application/json', "Enhanced JSON detection"
    
    # Check if it's likely plain text
    try:
        decoded = file_bytes.decode('utf-8', errors='ignore')
        if len(decoded.strip()) > 0:
            # Count printable characters
            printable_ratio = sum(1 for c in decoded if c.isprintable() or c.isspace()) / len(decoded)
            if printable_ratio > 0.8:
                print(f"   ✅ Enhanced detection: Plain text (printable ratio: {printable_ratio:.2f})")
                return 'txt', 'text/plain', f"Enhanced text detection (printable ratio: {printable_ratio:.2f})"
    except:
        pass
    
    # If we still can't detect anything, make an educated guess based on size and content
    if len(file_bytes) < 1000:
        print(f"   ⚠️ Small file, likely text or HTML")
        # For small files, if they contain any HTML-like tags, assume HTML
        if b'<' in file_bytes and b'>' in file_bytes:
            return 'html', 'text/html', "Small file with HTML-like tags"
        else:
            return 'txt', 'text/plain', "Small file, assuming plain text"
    
    return None, None, "Enhanced detection also failed"

def main():
    """Test enhanced format detection."""
    print("🧪 Testing Enhanced File Format Detection")
    print("=" * 50)
    
    # Test with the problematic content
    analyze_problematic_file()
    
    # Test enhanced detection
    print(f"\n" + "=" * 50)
    print("🔧 Testing Enhanced Detection Logic")
    print("=" * 50)
    
    # Create test cases
    test_cases = [
        ("Hebrew HTML", """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head><title>תעשייה אווירית – ויקיפדיה</title></head>
<body><h1>תעשייה אווירית</h1></body>
</html>"""),
        ("Minimal HTML", "<html><head><title>Test</title></head><body>Hello</body></html>"),
        ("Plain text", "This is just plain text content with some Hebrew: שלום"),
        ("JSON", '{"title": "תעשייה אווירית", "content": "test"}'),
        ("XML", '<?xml version="1.0"?><root><title>Test</title></root>'),
    ]
    
    for test_name, content in test_cases:
        print(f"\n📝 Testing: {test_name}")
        file_bytes = content.encode('utf-8')
        filename = f"{test_name.lower().replace(' ', '_')}.pdf"
        
        detected_format, content_type, reason = test_enhanced_format_detection(file_bytes, filename)
        
        print(f"   Result: {detected_format or 'None'}")
        print(f"   Content-Type: {content_type or 'None'}")
        print(f"   Reason: {reason}")

if __name__ == "__main__":
    main()
