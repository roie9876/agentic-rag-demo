#!/usr/bin/env python3
"""
Diagnostic script to identify what type of file this actually is.
"""

import os
import sys
from pathlib import Path

def analyze_file_header(file_bytes, filename):
    """Analyze the file header to determine the actual file type."""
    print(f"\n🔍 Analyzing file: {filename}")
    print(f"📊 File size: {len(file_bytes):,} bytes")
    
    # Show first 100 bytes
    header = file_bytes[:100]
    print(f"🔤 First 100 bytes (raw): {repr(header)}")
    
    # Try to decode as text for the first part
    try:
        text_start = header.decode('utf-8', errors='ignore')[:200]
        print(f"📝 First part as text: {repr(text_start)}")
    except:
        print("📝 Cannot decode as UTF-8 text")
    
    # Check common file signatures
    signatures = {
        b'%PDF-': 'PDF Document',
        b'\x89PNG': 'PNG Image',
        b'\xFF\xD8\xFF': 'JPEG Image',
        b'GIF87a': 'GIF Image (87a)',
        b'GIF89a': 'GIF Image (89a)',
        b'BM': 'Bitmap Image',
        b'PK\x03\x04': 'ZIP Archive (possibly DOCX, XLSX, etc.)',
        b'PK\x05\x06': 'ZIP Archive (empty)',
        b'PK\x07\x08': 'ZIP Archive (spanned)',
        b'\xD0\xCF\x11\xE0': 'Microsoft Office Document (legacy)',
        b'<html': 'HTML Document',
        b'<!DOCTYPE html': 'HTML Document',
        b'<!DOCTYPE HTML': 'HTML Document',
        b'<HTML': 'HTML Document',
        b'<head': 'HTML Document',
        b'<?xml': 'XML Document',
        b'\x7FELF': 'ELF Binary',
        b'\xFE\xFF': 'UTF-16 Big Endian text',
        b'\xFF\xFE': 'UTF-16 Little Endian text',
        b'\xEF\xBB\xBF': 'UTF-8 with BOM text',
    }
    
    print(f"\n🔍 File type detection:")
    detected = False
    for sig, desc in signatures.items():
        if file_bytes.startswith(sig):
            print(f"✅ Detected: {desc}")
            detected = True
            break
    
    if not detected:
        print("❓ Unknown file type")
        
        # Check if it might be text
        try:
            text_content = file_bytes.decode('utf-8', errors='ignore')
            if len(text_content.strip()) > 0 and text_content.isprintable():
                print("📝 Appears to be a text file")
                print(f"📄 First 500 characters:\n{text_content[:500]}")
        except:
            pass
    
    # Additional checks
    if b'<html' in file_bytes[:1000].lower() or b'<!doctype html' in file_bytes[:1000].lower():
        print("🌐 Contains HTML content - likely a web page")
    
    if b'javascript' in file_bytes[:2000].lower():
        print("💻 Contains JavaScript - likely a web page")
        
    if b'<head>' in file_bytes[:2000].lower() or b'<body>' in file_bytes[:2000].lower():
        print("🌐 Contains HTML head/body tags - definitely a web page")

def main():
    """Main diagnostic function."""
    print("🩺 File Type Diagnostic Tool")
    print("=" * 50)
    
    # For testing, create a sample that mimics your issue
    print("\n📂 This tool helps identify what your file actually contains.")
    print("💡 Common issues:")
    print("   • Web pages saved with .pdf extension")
    print("   • Images renamed to .pdf")
    print("   • Corrupted downloads")
    print("   • Non-PDF files with .pdf extension")
    
    # Example with typical "fake PDF" content
    fake_pdf_html = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<title>תעשייה אווירית – ויקיפדיה</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>
console.log("This is actually a web page, not a PDF!");
</script>
</head>
<body>
<h1>תעשייה אווירית</h1>
<p>זהו תוכן HTML ולא PDF...</p>
</body>
</html>"""
    fake_pdf_content = fake_pdf_html.encode('utf-8')
    
    print("\n🧪 Example analysis of what your file might contain:")
    analyze_file_header(fake_pdf_content, "example_fake_pdf.pdf")
    
    print("\n" + "=" * 50)
    print("🔧 How to fix your file:")
    print("1. Open the file in a text editor to see its actual content")
    print("2. If it's HTML, save it as a proper PDF using 'Print to PDF'")
    print("3. If it's an image, convert it properly to PDF")
    print("4. If it's corrupted, re-download from the original source")

if __name__ == "__main__":
    main()
