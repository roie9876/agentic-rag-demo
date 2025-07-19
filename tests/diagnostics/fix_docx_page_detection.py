#!/usr/bin/env python3
"""
DOCX Page Detection Fix

This script demonstrates how to properly extract page information from Azure Document Intelligence
for DOCX files, ensuring accurate page tracking in the search index.

The issue: Current code estimates page numbers instead of using actual page boundaries
The fix: Use Document Intelligence's page structure and span information
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def analyze_document_intelligence_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a Document Intelligence response to understand page structure.
    
    Args:
        result: Document Intelligence API response
        
    Returns:
        Analysis of page information
    """
    
    analysis = {
        "pages": [],
        "page_count": 0,
        "content_with_pages": [],
        "issues": []
    }
    
    # Extract pages information
    if "pages" in result:
        pages = result["pages"]
        analysis["page_count"] = len(pages)
        
        print(f"📄 Found {len(pages)} pages in Document Intelligence response")
        
        for i, page in enumerate(pages):
            page_info = {
                "page_number": page.get("pageNumber", i + 1),
                "width": page.get("width", 0),
                "height": page.get("height", 0),
                "unit": page.get("unit", "unknown"),
                "angle": page.get("angle", 0),
                "words_count": len(page.get("words", [])),
                "lines_count": len(page.get("lines", [])),
                "selection_marks_count": len(page.get("selectionMarks", [])),
            }
            analysis["pages"].append(page_info)
            
            # Sample some content from this page
            if "lines" in page:
                sample_lines = [line.get("content", "") for line in page["lines"][:3]]
                page_info["sample_content"] = " ".join(sample_lines)
    
    # Extract paragraphs with page information
    if "paragraphs" in result:
        paragraphs = result["paragraphs"]
        print(f"📝 Found {len(paragraphs)} paragraphs")
        
        for i, paragraph in enumerate(paragraphs):
            content = paragraph.get("content", "")
            spans = paragraph.get("spans", [])
            bounding_regions = paragraph.get("boundingRegions", [])
            
            # Extract page numbers from bounding regions
            page_numbers = []
            for region in bounding_regions:
                if "pageNumber" in region:
                    page_numbers.append(region["pageNumber"])
            
            paragraph_info = {
                "paragraph_index": i,
                "content_preview": content[:100] + "..." if len(content) > 100 else content,
                "content_length": len(content),
                "page_numbers": sorted(list(set(page_numbers))),  # Remove duplicates
                "spans_count": len(spans),
                "bounding_regions_count": len(bounding_regions)
            }
            
            analysis["content_with_pages"].append(paragraph_info)
    
    # Check for issues
    if analysis["page_count"] == 0:
        analysis["issues"].append("No pages found in Document Intelligence response")
    
    if analysis["page_count"] == 1 and len(analysis.get("content_with_pages", [])) > 50:
        analysis["issues"].append("Large document showing as single page - possible processing issue")
    
    # Check if all paragraphs show the same page number
    all_page_numbers = []
    for content in analysis["content_with_pages"]:
        all_page_numbers.extend(content["page_numbers"])
    
    unique_pages = set(all_page_numbers)
    if len(unique_pages) == 1 and len(analysis["content_with_pages"]) > 20:
        analysis["issues"].append(f"All paragraphs assigned to page {list(unique_pages)[0]} - page detection failed")
    
    return analysis

def improved_page_extraction_logic(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Improved logic for extracting page information from Document Intelligence.
    
    This replaces the flawed estimation logic with proper page boundary detection.
    
    Args:
        result: Document Intelligence response
        
    Returns:
        List of text segments with accurate page numbers
    """
    
    text_segments = []
    
    # Method 1: Use paragraphs with bounding regions (most accurate)
    if "paragraphs" in result:
        print("🎯 Using paragraphs with bounding regions for accurate page detection")
        
        for i, paragraph in enumerate(result["paragraphs"]):
            content = paragraph.get("content", "").strip()
            if not content:
                continue
                
            # Extract page numbers from bounding regions
            page_numbers = []
            for region in paragraph.get("boundingRegions", []):
                if "pageNumber" in region:
                    page_numbers.append(region["pageNumber"])
            
            # Use the first page number (or default to 1)
            page_number = page_numbers[0] if page_numbers else 1
            
            text_segments.append({
                "content": content,
                "page_number": page_number,
                "paragraph_index": i,
                "method": "bounding_regions"
            })
    
    # Method 2: Fallback - use pages with lines (if paragraphs don't have bounding regions)
    elif "pages" in result:
        print("📄 Using pages with lines as fallback for page detection")
        
        for page in result["pages"]:
            page_number = page.get("pageNumber", 1)
            
            # Combine all lines from this page
            page_content = []
            for line in page.get("lines", []):
                line_content = line.get("content", "").strip()
                if line_content:
                    page_content.append(line_content)
            
            if page_content:
                # Join lines into paragraphs (split by double newlines or long gaps)
                full_page_text = "\n".join(page_content)
                paragraphs = [p.strip() for p in full_page_text.split("\n\n") if p.strip()]
                
                for i, paragraph in enumerate(paragraphs):
                    text_segments.append({
                        "content": paragraph,
                        "page_number": page_number,
                        "paragraph_index": i,
                        "method": "page_lines"
                    })
    
    # Method 3: Last resort - use content with span information
    elif "content" in result:
        print("⚠️  Using content with spans as last resort - page detection may be inaccurate")
        
        content = result["content"]
        
        # Try to find spans that reference pages
        spans_with_pages = []
        if "spans" in result:
            for span in result["spans"]:
                # Look for page references in span metadata (if available)
                # This is implementation-specific and may vary
                spans_with_pages.append({
                    "offset": span.get("offset", 0),
                    "length": span.get("length", 0),
                    "page_number": 1  # Default since we can't determine page
                })
        
        # Split content into reasonable chunks
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        
        for i, paragraph in enumerate(paragraphs):
            text_segments.append({
                "content": paragraph,
                "page_number": 1,  # Can't determine page without bounding regions
                "paragraph_index": i,
                "method": "content_fallback"
            })
    
    print(f"✅ Extracted {len(text_segments)} text segments using improved logic")
    
    return text_segments

def generate_fixed_multimodal_processor_code() -> str:
    """Generate the improved code for multimodal_processor.py"""
    
    return '''
def _process_extraction_result_improved(self, result, filename):
    """
    IMPROVED: Process Document Intelligence result with accurate page detection.
    
    This replaces the flawed estimation logic in the original _process_extraction_result method.
    """
    processed_content = {
        "text_segments": [],
        "images": []
    }
    
    # IMPROVED PAGE DETECTION LOGIC
    text_segments = []
    
    # Method 1: Use paragraphs with bounding regions (most accurate for DOCX)
    if "paragraphs" in result:
        logging.info(f"[{filename}] Using paragraphs with bounding regions for page detection")
        
        for i, paragraph in enumerate(result["paragraphs"]):
            content = paragraph.get("content", "").strip()
            if not content:
                continue
                
            # Extract ACTUAL page numbers from bounding regions
            page_numbers = []
            for region in paragraph.get("boundingRegions", []):
                if "pageNumber" in region:
                    page_numbers.append(region["pageNumber"])
            
            # Use the first page number (paragraphs can span pages, take the first)
            actual_page_number = page_numbers[0] if page_numbers else 1
            
            text_segments.append({
                "content": content,
                "page_number": actual_page_number
            })
    
    # Method 2: Use pages with lines (fallback)
    elif "pages" in result:
        logging.info(f"[{filename}] Using pages with lines for page detection")
        
        for page in result["pages"]:
            page_number = page.get("pageNumber", 1)
            
            # Combine lines from this specific page
            page_lines = []
            for line in page.get("lines", []):
                line_content = line.get("content", "").strip()
                if line_content:
                    page_lines.append(line_content)
            
            # Group lines into paragraphs
            page_text = "\\n".join(page_lines)
            paragraphs = [p.strip() for p in page_text.split("\\n\\n") if p.strip()]
            
            for paragraph in paragraphs:
                text_segments.append({
                    "content": paragraph,
                    "page_number": page_number  # Accurate page number
                })
    
    # Method 3: Legacy fallback (with warning)
    else:
        logging.warning(f"[{filename}] No paragraphs or pages found - using legacy content splitting")
        content = result.get("content", "")
        if content:
            paragraphs = [p.strip() for p in content.split("\\n\\n") if p.strip()]
            for paragraph in paragraphs:
                text_segments.append({
                    "content": paragraph,
                    "page_number": 1  # Can't determine actual page
                })
    
    # Add text segments to processed content
    processed_content["text_segments"] = text_segments
    
    # Log page statistics
    page_numbers = [seg["page_number"] for seg in text_segments]
    unique_pages = sorted(set(page_numbers))
    logging.info(f"[{filename}] Extracted {len(text_segments)} segments across {len(unique_pages)} pages: {unique_pages}")
    
    # Process images (existing logic)
    if "figures" in result:
        # ... existing image processing logic ...
        pass
    
    return processed_content
'''

def test_page_detection_fix():
    """
    Test the page detection fix with a sample Document Intelligence response.
    """
    
    print("🧪 **TESTING PAGE DETECTION FIX**")
    print("=" * 60)
    
    # Sample Document Intelligence response (similar to what you'd get from an 800-page DOCX)
    sample_response = {
        "pages": [
            {
                "pageNumber": 1,
                "width": 8.5,
                "height": 11,
                "unit": "inch",
                "lines": [
                    {"content": "Chapter 1: Introduction"},
                    {"content": "This is the first chapter of the document."},
                    {"content": "It contains important information."}
                ]
            },
            {
                "pageNumber": 2,
                "width": 8.5,
                "height": 11,
                "unit": "inch",
                "lines": [
                    {"content": "Chapter 2: Methodology"},
                    {"content": "This chapter describes our approach."},
                    {"content": "We used several techniques."}
                ]
            }
        ],
        "paragraphs": [
            {
                "content": "Chapter 1: Introduction\nThis is the first chapter of the document. It contains important information.",
                "boundingRegions": [{"pageNumber": 1}],
                "spans": [{"offset": 0, "length": 89}]
            },
            {
                "content": "Chapter 2: Methodology\nThis chapter describes our approach. We used several techniques.",
                "boundingRegions": [{"pageNumber": 2}],
                "spans": [{"offset": 90, "length": 87}]
            }
        ],
        "content": "Chapter 1: Introduction\nThis is the first chapter...\nChapter 2: Methodology..."
    }
    
    # Analyze the current response
    analysis = analyze_document_intelligence_response(sample_response)
    
    print(f"📊 **ANALYSIS RESULTS:**")
    print(f"   Pages found: {analysis['page_count']}")
    print(f"   Paragraphs with pages: {len(analysis['content_with_pages'])}")
    
    if analysis['issues']:
        print(f"   ⚠️  Issues: {', '.join(analysis['issues'])}")
    else:
        print(f"   ✅ No issues detected")
    
    # Test improved extraction
    print(f"\n🔧 **TESTING IMPROVED EXTRACTION:**")
    segments = improved_page_extraction_logic(sample_response)
    
    for i, segment in enumerate(segments[:5]):  # Show first 5 segments
        print(f"   Segment {i+1}: Page {segment['page_number']} - {segment['content'][:50]}...")
    
    # Show page distribution
    page_counts = {}
    for segment in segments:
        page = segment['page_number']
        page_counts[page] = page_counts.get(page, 0) + 1
    
    print(f"\n📈 **PAGE DISTRIBUTION:**")
    for page, count in sorted(page_counts.items()):
        print(f"   Page {page}: {count} segments")

def main():
    """Main function to demonstrate the fix."""
    
    print("🔍 **DOCX PAGE DETECTION FIX DEMONSTRATION**")
    print("=" * 80)
    
    print("\n🚨 **THE PROBLEM:**")
    print("Current multimodal_processor.py has flawed page detection:")
    print("- Estimates page numbers by dividing paragraphs equally")
    print("- Ignores actual page boundaries from Document Intelligence")
    print("- Results in all chunks showing as 'page 1' for DOCX files")
    
    print("\n💡 **THE SOLUTION:**")
    print("Use Document Intelligence's actual page structure:")
    print("- Extract page numbers from paragraph bounding regions")
    print("- Use page-specific line groupings as fallback")
    print("- Maintain accurate page tracking throughout the pipeline")
    
    # Test the fix
    test_page_detection_fix()
    
    print("\n🛠️  **IMPLEMENTATION:**")
    print("1. Replace _process_extraction_result() in multimodal_processor.py")
    print("2. Update chunking logic to use actual page boundaries") 
    print("3. Ensure page_number field gets accurate values in search index")
    print("4. Re-index your 800-page document to get correct page distribution")
    
    print("\n✅ **EXPECTED RESULT AFTER FIX:**")
    print("- iecdoc.docx should show pages 1-800 (not just page 1)")
    print("- Page coverage analysis will show actual document coverage")
    print("- Completeness score should improve significantly")
    print("- Missing page detection will work properly")

if __name__ == "__main__":
    main()
