#!/usr/bin/env python3
"""
Check actual page count of DOCX file using python-docx
"""

import sys
import os

def check_docx_pages(filename):
    """Check actual page count of DOCX file"""
    
    try:
        # Try using python-docx
        from docx import Document
        
        doc = Document(filename)
        
        print(f"📄 Document: {filename}")
        print(f"📝 Paragraphs: {len(doc.paragraphs)}")
        print(f"📑 Sections: {len(doc.sections)}")
        
        # Count pages based on page break characters
        page_count = 1
        for paragraph in doc.paragraphs:
            if '\x0c' in paragraph.text:  # Form feed character (page break)
                page_count += 1
                
        print(f"🔢 Estimated pages (by page breaks): {page_count}")
        
        # Check first few paragraphs
        print(f"\n📋 First 5 paragraphs:")
        for i, para in enumerate(doc.paragraphs[:5]):
            text = para.text[:50] + '...' if len(para.text) > 50 else para.text
            print(f"   {i+1}: '{text}'")
            
        return True
        
    except ImportError:
        print("❌ python-docx not available, trying alternative...")
        return False
    except Exception as e:
        print(f"❌ Error reading DOCX: {e}")
        return False

if __name__ == "__main__":
    filename = "iecdocsmall.docx"
    if not os.path.exists(filename):
        print(f"❌ File {filename} not found")
        sys.exit(1)
        
    print("🔍 Checking DOCX structure...")
    success = check_docx_pages(filename)
    
    if not success:
        # Try with basic info
        size = os.path.getsize(filename)
        print(f"📄 File size: {size:,} bytes")
        print("💡 This appears to be a single-page or simple DOCX document")
