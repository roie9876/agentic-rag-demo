#!/usr/bin/env python3
"""
Test the enhanced format detection with the actual problematic file scenario.
"""

import os
import sys
from pathlib import Path

# Add the current directory to the path for imports
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

from chunking.multimodal_processor import validate_and_detect_format

def create_problematic_file_samples():
    """Create various problematic file samples to test detection."""
    
    samples = {
        "hebrew_html_599_bytes": """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<title>תעשייה אווירית – ויקיפדיה</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>
console.log("This is a Hebrew Wikipedia page about aviation industry");
</script>
</head>
<body>
<h1>תעשייה אווירית</h1>
<p>התעשייה האווירית היא ענף בתעשייה הביטחונית...</p>
<div>More content here</div>
</body>
</html>""",
        
        "minimal_html": "<html><head><title>Test</title></head><body>Hello</body></html>",
        
        "broken_html": "Some text <html incomplete",
        
        "wikipedia_style": """<!DOCTYPE html>
<html class="client-nojs" lang="he" dir="rtl">
<head>
<meta charset="UTF-8"/>
<title>תעשייה אווירית – ויקיפדיה</title>
<script>(window.RLQ=window.RLQ||[]).push(function(){});</script>
<link rel="stylesheet" href="/w/load.php"/>
</head>
<body class="mediawiki">
<div id="content">
<h1>תעשייה אווירית</h1>
</div>
</body>
</html>""",
        
        "plain_text": "This is just plain text content",
        
        "empty_file": "",
        
        "very_small": "Hi",
    }
    
    return samples

def test_sample(name, content, expected_format=None):
    """Test a sample content with the enhanced detection."""
    print(f"\n📝 Testing: {name}")
    print(f"   Size: {len(content)} bytes")
    
    if len(content) <= 100:
        print(f"   Content: {repr(content)}")
    else:
        print(f"   Content (first 100): {repr(content[:100])}...")
    
    # Test with .pdf extension to simulate the problematic scenario
    filename = f"{name}.pdf"
    file_bytes = content.encode('utf-8') if isinstance(content, str) else content
    
    try:
        is_valid, detected_format, content_type, message = validate_and_detect_format(file_bytes, filename)
        
        print(f"   ✅ Valid: {is_valid}")
        print(f"   🔍 Format: {detected_format}")
        print(f"   📋 Content-Type: {content_type}")
        print(f"   💬 Message: {message}")
        
        if expected_format and detected_format != expected_format:
            print(f"   ⚠️  Expected {expected_format}, got {detected_format}")
        
        return is_valid, detected_format, content_type
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False, None, None

def main():
    """Test enhanced format detection with problematic scenarios."""
    print("🧪 Testing Enhanced Format Detection")
    print("=" * 60)
    
    samples = create_problematic_file_samples()
    
    results = []
    
    for name, content in samples.items():
        expected_format = None
        if 'html' in name:
            expected_format = 'html'
        elif 'text' in name:
            expected_format = 'txt'
            
        is_valid, detected_format, content_type = test_sample(name, content, expected_format)
        results.append((name, is_valid, detected_format, content_type))
    
    # Summary
    print(f"\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    valid_count = sum(1 for _, is_valid, _, _ in results if is_valid)
    detected_count = sum(1 for _, _, detected_format, _ in results if detected_format is not None)
    
    print(f"Total samples: {len(results)}")
    print(f"Valid files: {valid_count}")
    print(f"Format detected: {detected_count}")
    
    print(f"\nDetailed results:")
    for name, is_valid, detected_format, content_type in results:
        status = "✅" if is_valid and detected_format else "❌"
        print(f"  {status} {name:<25} -> {detected_format or 'None':<8} ({content_type or 'None'})")
    
    # Test specifically with the 599-byte Hebrew HTML scenario
    print(f"\n" + "=" * 60)
    print("🎯 SPECIFIC TEST: 599-byte Hebrew HTML (your scenario)")
    print("=" * 60)
    
    hebrew_html = samples["hebrew_html_599_bytes"]
    # Trim to exactly 599 bytes like your error
    hebrew_html_599 = hebrew_html.encode('utf-8')[:599].decode('utf-8', errors='ignore')
    
    print(f"Trimmed to {len(hebrew_html_599.encode('utf-8'))} bytes")
    is_valid, detected_format, content_type = test_sample("hebrew_html_599_exact", hebrew_html_599, "html")
    
    if detected_format == 'html' and content_type == 'text/html':
        print(f"\n🎉 SUCCESS! The enhanced detection should now handle your problematic file!")
        print(f"   Instead of sending 'application/pdf', it will send 'text/html'")
        print(f"   This should resolve the Document Intelligence 400 error.")
    else:
        print(f"\n⚠️  Still having issues. The file might need further investigation.")

if __name__ == "__main__":
    main()
