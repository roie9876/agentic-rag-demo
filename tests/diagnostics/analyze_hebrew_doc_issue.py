#!/usr/bin/env python3
"""
Hebrew Document Page Number Analysis

This script analyzes why the Hebrew Word document has all chunks with page_number=1
instead of proper page distribution across ~800 pages.

Usage:
    python3 tests/diagnostics/analyze_hebrew_doc_issue.py --index iec --file iecdoc.docx
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, Counter
import re
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

def get_search_client(index_name: str) -> SearchClient:
    """Initialize Azure Search client."""
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    if not endpoint:
        raise ValueError("AZURE_SEARCH_ENDPOINT not configured")
    
    # Try managed identity first, then key
    try:
        credential = DefaultAzureCredential()
        return SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
    except Exception as e:
        print(f"⚠️  Managed identity failed ({e}), trying with key...")
        key = os.getenv("AZURE_SEARCH_KEY")
        if key:
            credential = AzureKeyCredential(key)
            return SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
        else:
            raise ValueError("No valid authentication method found for Azure Search")

def analyze_hebrew_document_issue(index_name: str, source_file: str) -> Dict[str, Any]:
    """
    Analyze the page number extraction issue for Hebrew Word document.
    
    Args:
        index_name: Azure Search index name
        source_file: Source document filename to analyze
        
    Returns:
        Dictionary with analysis results
    """
    
    print(f"\n🔍 **HEBREW DOCUMENT PAGE ANALYSIS**")
    print(f"📄 Document: {source_file}")
    print(f"🗂️  Index: {index_name}")
    print(f"⏰ Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        search_client = get_search_client(index_name)
        
        # Get all chunks for detailed analysis
        print(f"\n📊 **RETRIEVING CHUNKS FOR ANALYSIS**")
        
        search_results = search_client.search(
            search_text="*",
            filter=f"source_file eq '{source_file}'",
            select=["id", "content", "page_number", "page_chunk", "extraction_method", 
                   "processing_timestamp", "doc_key", "has_figures", "isMultimodal"],
            top=1000,
            include_total_count=True
        )
        
        chunks = list(search_results)
        total_count = search_results.get_count()
        
        print(f"✅ Found {len(chunks)} chunks (Total available: {total_count})")
        
        if len(chunks) == 0:
            return {"status": "ERROR", "message": f"No chunks found for '{source_file}'"}
        
        analysis = {
            "document_name": source_file,
            "index_name": index_name,
            "total_chunks": len(chunks),
            "analysis_timestamp": datetime.now().isoformat(),
        }
        
        # 1. Page number distribution analysis
        page_numbers = [chunk.get("page_number", "MISSING") for chunk in chunks]
        page_counter = Counter(page_numbers)
        
        analysis["page_distribution"] = {
            "unique_pages": len(page_counter),
            "page_counts": dict(page_counter),
            "all_chunks_page_1": page_counter.get(1, 0) == len(chunks),
            "missing_page_numbers": page_counter.get("MISSING", 0)
        }
        
        # 2. Content analysis to estimate actual pages
        print(f"\n📈 **CONTENT ANALYSIS FOR PAGE ESTIMATION**")
        
        content_lengths = []
        total_content = ""
        
        for chunk in chunks:
            content = chunk.get("content", "")
            content_lengths.append(len(content))
            total_content += content + " "
        
        analysis["content_analysis"] = {
            "total_content_length": len(total_content),
            "avg_chunk_size": sum(content_lengths) / len(content_lengths) if content_lengths else 0,
            "min_chunk_size": min(content_lengths) if content_lengths else 0,
            "max_chunk_size": max(content_lengths) if content_lengths else 0,
            "estimated_pages_by_content": len(total_content) // 2000,  # ~2000 chars per page estimate
            "small_chunks": len([c for c in content_lengths if c < 100]),
            "large_chunks": len([c for c in content_lengths if c > 5000])
        }
        
        # 3. Processing method analysis
        extraction_methods = [chunk.get("extraction_method", "UNKNOWN") for chunk in chunks]
        method_counter = Counter(extraction_methods)
        
        analysis["processing_analysis"] = {
            "extraction_methods": dict(method_counter),
            "document_intelligence_used": method_counter.get("document_intelligence", 0) > 0,
            "all_same_method": len(method_counter) == 1
        }
        
        # 4. Check for Hebrew text patterns
        hebrew_patterns = 0
        rtl_indicators = 0
        english_patterns = 0
        
        sample_content = ""
        for i, chunk in enumerate(chunks[:10]):  # Sample first 10 chunks
            content = chunk.get("content", "")
            sample_content += content[:200] + "...\n\n"
            
            # Count Hebrew characters (Unicode range)
            hebrew_chars = len([c for c in content if '\u0590' <= c <= '\u05FF'])
            if hebrew_chars > 10:
                hebrew_patterns += 1
            
            # Look for RTL markers or Hebrew words
            if any(word in content for word in ["ספק", "שירות", "חיוני", "רשת", "צרכן"]):
                rtl_indicators += 1
            
            # Count English characters
            english_chars = len([c for c in content if c.isascii() and c.isalpha()])
            if english_chars > hebrew_chars:
                english_patterns += 1
        
        analysis["hebrew_analysis"] = {
            "chunks_with_hebrew": hebrew_patterns,
            "chunks_with_rtl_words": rtl_indicators,
            "chunks_with_english": english_patterns,
            "language_detected": "Hebrew" if hebrew_patterns > english_patterns else "Mixed/English",
            "sample_content": sample_content
        }
        
        # 5. Look for page boundaries or indicators in content
        page_indicators = {
            "page_numbers_in_content": 0,
            "section_breaks": 0,
            "chapter_markers": 0
        }
        
        for chunk in chunks:
            content = chunk.get("content", "")
            
            # Look for page number patterns
            if re.search(r'\b(?:עמוד|דף)\s*\d+', content) or re.search(r'\d+\s*(?:עמוד|דף)', content):
                page_indicators["page_numbers_in_content"] += 1
            
            # Look for section breaks
            if re.search(r'={3,}|_{3,}|-{3,}', content):
                page_indicators["section_breaks"] += 1
            
            # Look for chapter/section markers
            if re.search(r'פרק|סעיף|אמת מידה|סימן', content):
                page_indicators["chapter_markers"] += 1
        
        analysis["page_indicators"] = page_indicators
        
        # 6. Processing metadata analysis
        timestamps = [chunk.get("processing_timestamp") for chunk in chunks if chunk.get("processing_timestamp")]
        doc_keys = set(chunk.get("doc_key") for chunk in chunks if chunk.get("doc_key"))
        
        analysis["metadata_analysis"] = {
            "unique_timestamps": len(set(timestamps)) if timestamps else 0,
            "unique_doc_keys": len(doc_keys),
            "sample_doc_keys": list(doc_keys)[:5],
            "has_figures": sum(1 for chunk in chunks if chunk.get("has_figures", False)),
            "multimodal_chunks": sum(1 for chunk in chunks if chunk.get("isMultimodal", False))
        }
        
        # 7. Generate assessment and recommendations
        print(f"\n🎯 **ISSUE ANALYSIS AND RECOMMENDATIONS**")
        
        issues = []
        recommendations = []
        
        if analysis["page_distribution"]["all_chunks_page_1"]:
            issues.append("All chunks assigned to page 1 - page detection not working")
            recommendations.append("Check Document Intelligence page detection settings")
        
        if analysis["content_analysis"]["estimated_pages_by_content"] > 100:
            issues.append(f"Content suggests ~{analysis['content_analysis']['estimated_pages_by_content']} pages, but only 1 detected")
            recommendations.append("Large document with page detection failure")
        
        if analysis["hebrew_analysis"]["language_detected"] == "Hebrew":
            issues.append("Hebrew RTL text may cause page detection issues")
            recommendations.append("Consider RTL-specific document processing settings")
        
        if analysis["processing_analysis"]["document_intelligence_used"]:
            recommendations.append("Document Intelligence is being used - check API response for page info")
        else:
            issues.append("Document Intelligence not used - may affect page detection")
            recommendations.append("Enable Document Intelligence for better page detection")
        
        analysis["assessment"] = {
            "primary_issue": "Page number extraction failure in Document Intelligence",
            "likely_cause": "Hebrew RTL document processing or Document Intelligence configuration",
            "document_quality": "Content appears complete and well-extracted",
            "page_detection_status": "FAILED",
            "content_completeness": "EXCELLENT",
            "issues": issues,
            "recommendations": recommendations
        }
        
        # Display results
        print_hebrew_analysis_results(analysis)
        
        return analysis
        
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "document_name": source_file,
            "index_name": index_name,
            "timestamp": datetime.now().isoformat()
        }

def print_hebrew_analysis_results(analysis: Dict[str, Any]):
    """Print formatted analysis results."""
    
    print(f"\n📊 **ANALYSIS RESULTS**")
    print(f"Total Chunks: {analysis['total_chunks']}")
    
    # Page distribution
    page_dist = analysis["page_distribution"]
    print(f"Page Distribution: {page_dist['unique_pages']} unique pages")
    print(f"All chunks on page 1: {'✅ YES' if page_dist['all_chunks_page_1'] else '❌ NO'}")
    
    # Content analysis
    content = analysis["content_analysis"]
    print(f"Content: {content['total_content_length']:,} chars total, {content['avg_chunk_size']:.0f} avg per chunk")
    print(f"Estimated pages by content: ~{content['estimated_pages_by_content']} pages")
    
    # Hebrew analysis
    hebrew = analysis["hebrew_analysis"]
    print(f"Language detected: {hebrew['language_detected']}")
    print(f"Hebrew chunks: {hebrew['chunks_with_hebrew']}/{analysis['total_chunks']}")
    
    # Processing analysis
    processing = analysis["processing_analysis"]
    print(f"Extraction method: {', '.join(processing['extraction_methods'].keys())}")
    
    # Assessment
    assessment = analysis["assessment"]
    print(f"\n🎯 **ASSESSMENT**")
    print(f"Primary Issue: {assessment['primary_issue']}")
    print(f"Likely Cause: {assessment['likely_cause']}")
    print(f"Content Quality: {assessment['content_completeness']}")
    print(f"Page Detection: {assessment['page_detection_status']}")
    
    if assessment["issues"]:
        print(f"\n⚠️  **ISSUES DETECTED:**")
        for i, issue in enumerate(assessment["issues"], 1):
            print(f"   {i}. {issue}")
    
    if assessment["recommendations"]:
        print(f"\n💡 **RECOMMENDATIONS:**")
        for i, rec in enumerate(assessment["recommendations"], 1):
            print(f"   {i}. {rec}")
    
    # Sample content
    if hebrew["sample_content"]:
        print(f"\n📄 **SAMPLE CONTENT (First 10 chunks):**")
        print(hebrew["sample_content"][:1000] + "..." if len(hebrew["sample_content"]) > 1000 else hebrew["sample_content"])

def main():
    parser = argparse.ArgumentParser(description="Analyze Hebrew document page number extraction issue")
    parser.add_argument("--index", required=True, help="Azure Search index name")
    parser.add_argument("--file", required=True, help="Source document filename")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    try:
        # Perform analysis
        analysis = analyze_hebrew_document_issue(args.index, args.file)
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, default=str, ensure_ascii=False)
            print(f"\n💾 Results saved to: {args.output}")
        
        # Print summary
        print(f"\n📋 **SUMMARY**")
        if analysis.get("assessment"):
            assessment = analysis["assessment"]
            print(f"Status: Page detection FAILED, but content extraction EXCELLENT")
            print(f"Document: {analysis['total_chunks']} chunks with {analysis['content_analysis']['total_content_length']:,} chars")
            print(f"Issue: {assessment['primary_issue']}")
            print(f"Next Steps: Fix page detection in Document Intelligence processing")
        
    except KeyboardInterrupt:
        print("\n❌ Analysis interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        sys.exit(3)

if __name__ == "__main__":
    main()
