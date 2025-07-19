#!/usr/bin/env python3
"""
Analyze iectest.docx structure for page detection
"""

from docx import Document
import os

def analyze_iectest_docx(filename):
    """Analyze the iectest.docx file structure"""
    
    print(f"📄 Document: {filename}")
    print(f"📏 File size: {os.path.getsize(filename):,} bytes")
    
    try:
        doc = Document(filename)
        
        print(f"📝 Total paragraphs: {len(doc.paragraphs)}")
        print(f"📑 Sections: {len(doc.sections)}")
        
        # Count page breaks and structure indicators
        page_breaks = 0
        manual_page_refs = 0
        empty_paras = 0
        paragraph_with_content = 0
        
        for i, para in enumerate(doc.paragraphs):
            text = para.text
            if '\x0c' in text:  # Form feed character (page break)
                page_breaks += 1
                print(f"   📄 Page break found at paragraph {i+1}")
            
            if text.strip():
                paragraph_with_content += 1
                # Look for page references in Hebrew/English
                if any(word in text for word in ['עמוד', 'page', 'Page', 'PAGE']):
                    manual_page_refs += 1
                    print(f"   🔢 Page reference at para {i+1}: '{text[:100]}...'")
            else:
                empty_paras += 1
        
        print(f"\n📊 Structure Analysis:")
        print(f"🔀 Page breaks (\\x0c): {page_breaks}")
        print(f"🔢 Manual page references: {manual_page_refs}")
        print(f"⬜ Empty paragraphs: {empty_paras}")
        print(f"📝 Content paragraphs: {paragraph_with_content}")
        
        # Estimate pages based on content distribution
        if page_breaks > 0:
            estimated_pages = page_breaks + 1
        elif paragraph_with_content > 100:  # Large document heuristic
            estimated_pages = max(1, paragraph_with_content // 50)  # ~50 paragraphs per page
        else:
            estimated_pages = 1
            
        print(f"📄 Estimated pages: {estimated_pages}")
        
        # Show sample content from different parts of the document
        print(f"\n📋 Content samples:")
        sample_indices = [0, len(doc.paragraphs)//4, len(doc.paragraphs)//2, 3*len(doc.paragraphs)//4, len(doc.paragraphs)-1]
        
        for idx in sample_indices:
            if idx < len(doc.paragraphs) and doc.paragraphs[idx].text.strip():
                text = doc.paragraphs[idx].text[:100] + '...' if len(doc.paragraphs[idx].text) > 100 else doc.paragraphs[idx].text
                print(f"   Para {idx+1}: '{text}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing document: {e}")
        return False

if __name__ == "__main__":
    analyze_iectest_docx("iectest.docx")
