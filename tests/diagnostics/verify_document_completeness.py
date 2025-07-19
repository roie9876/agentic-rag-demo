#!/usr/bin/env python3
"""
Document Completeness Verification Tool

This script verifies that large documents (like 800-page Word docs) are fully indexed
by analyzing chunk distribution, content coverage, and potential gaps.

Usage:
    python3 tests/diagnostics/verify_document_completeness.py --index deleteme --file "iecdoc.docx"
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

def analyze_document_completeness(
    index_name: str, 
    source_file: str,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Comprehensive analysis of document indexing completeness.
    
    Args:
        index_name: Azure Search index name
        source_file: Source document filename to analyze
        verbose: Enable detailed output
        
    Returns:
        Dictionary with completeness analysis results
    """
    
    print(f"\n🔍 **DOCUMENT COMPLETENESS VERIFICATION**")
    print(f"📄 Document: {source_file}")
    print(f"🗂️  Index: {index_name}")
    print(f"⏰ Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        search_client = get_search_client(index_name)
        
        # 1. Get ALL chunks for this document
        print(f"\n📊 **STEP 1: RETRIEVING ALL CHUNKS**")
        
        # First, get the index schema to see what fields are available
        try:
            # Try basic search first to see what fields exist
            test_search = search_client.search(
                search_text="*",
                top=1
            )
            sample_doc = next(iter(test_search), {})
            available_fields = list(sample_doc.keys()) if sample_doc else []
            print(f"Available fields: {', '.join(available_fields)}")
        except Exception as e:
            print(f"Could not determine schema: {e}")
            available_fields = ["id", "content"]
        
        # Select only fields that exist
        select_fields = ["id", "content"]
        optional_fields = ["source_file", "page_number", "chunk_index", "doc_key", "url", "title"]
        for field in optional_fields:
            if field in available_fields:
                select_fields.append(field)
        
        print(f"Selecting fields: {', '.join(select_fields)}")
        
        # Search for all chunks from this document
        search_results = search_client.search(
            search_text="*",
            filter=f"source_file eq '{source_file}'",
            select=select_fields,
            top=5000,  # Get up to 5000 chunks
            include_total_count=True
        )
        
        chunks = list(search_results)
        total_count = search_results.get_count()
        
        print(f"✅ Found {len(chunks)} chunks (Total available: {total_count})")
        
        if len(chunks) == 0:
            return {
                "status": "ERROR",
                "message": f"No chunks found for document '{source_file}' in index '{index_name}'",
                "suggestions": [
                    "Verify the document was actually indexed",
                    "Check if the source_file name matches exactly",
                    "Try searching without the file extension"
                ]
            }
        
        # 2. Analyze chunk distribution and gaps
        print(f"\n📈 **STEP 2: ANALYZING CHUNK DISTRIBUTION**")
        
        analysis = {
            "total_chunks": len(chunks),
            "document_name": source_file,
            "index_name": index_name,
            "analysis_timestamp": datetime.now().isoformat(),
        }
        
        # Extract page numbers and chunk indices
        page_numbers = []
        chunk_indices = []
        content_lengths = []
        doc_keys = set()
        
        for chunk in chunks:
            # Page number analysis
            page_num = chunk.get("page_number")
            if page_num is not None:
                page_numbers.append(int(page_num))
            
            # Chunk index analysis
            chunk_idx = chunk.get("chunk_index")
            if chunk_idx is not None:
                chunk_indices.append(int(chunk_idx))
            
            # Content length analysis
            content = chunk.get("content", "")
            content_lengths.append(len(content))
            
            # Document key tracking
            doc_key = chunk.get("doc_key")
            if doc_key:
                doc_keys.add(doc_key)
        
        analysis["unique_doc_keys"] = len(doc_keys)
        analysis["doc_keys_sample"] = list(doc_keys)[:5]
        
        # 3. Page coverage analysis
        if page_numbers:
            page_numbers.sort()
            analysis["page_coverage"] = {
                "min_page": min(page_numbers),
                "max_page": max(page_numbers),
                "total_pages_with_content": len(set(page_numbers)),
                "page_range": f"{min(page_numbers)}-{max(page_numbers)}",
                "pages_distribution": dict(Counter(page_numbers))
            }
            
            # Find potential page gaps
            page_set = set(page_numbers)
            expected_pages = set(range(min(page_numbers), max(page_numbers) + 1))
            missing_pages = sorted(expected_pages - page_set)
            
            analysis["missing_pages"] = missing_pages
            analysis["missing_pages_count"] = len(missing_pages)
            
            if missing_pages:
                analysis["page_gaps"] = []
                gap_start = missing_pages[0]
                gap_end = missing_pages[0]
                
                for i in range(1, len(missing_pages)):
                    if missing_pages[i] == missing_pages[i-1] + 1:
                        gap_end = missing_pages[i]
                    else:
                        analysis["page_gaps"].append(f"{gap_start}-{gap_end}" if gap_start != gap_end else str(gap_start))
                        gap_start = gap_end = missing_pages[i]
                
                analysis["page_gaps"].append(f"{gap_start}-{gap_end}" if gap_start != gap_end else str(gap_start))
        
        # 4. Chunk sequence analysis
        if chunk_indices:
            chunk_indices.sort()
            analysis["chunk_sequence"] = {
                "min_chunk": min(chunk_indices),
                "max_chunk": max(chunk_indices),
                "total_chunk_indices": len(set(chunk_indices)),
                "expected_sequential_chunks": max(chunk_indices) - min(chunk_indices) + 1,
                "actual_chunks": len(chunk_indices)
            }
            
            # Find missing chunk indices
            chunk_set = set(chunk_indices)
            expected_chunks = set(range(min(chunk_indices), max(chunk_indices) + 1))
            missing_chunks = sorted(expected_chunks - chunk_set)
            analysis["missing_chunk_indices"] = missing_chunks
            analysis["missing_chunk_count"] = len(missing_chunks)
        
        # 5. Content analysis
        analysis["content_analysis"] = {
            "avg_chunk_size": sum(content_lengths) / len(content_lengths) if content_lengths else 0,
            "min_chunk_size": min(content_lengths) if content_lengths else 0,
            "max_chunk_size": max(content_lengths) if content_lengths else 0,
            "total_content_length": sum(content_lengths),
            "very_small_chunks": len([c for c in content_lengths if c < 100]),  # Suspiciously small
            "empty_chunks": len([c for c in content_lengths if c == 0])
        }
        
        # 6. Generate completeness assessment
        print(f"\n🎯 **STEP 3: COMPLETENESS ASSESSMENT**")
        
        completeness_score = 0
        issues = []
        recommendations = []
        
        # Score based on different factors (out of 100)
        
        # Chunk count (30 points) - For 800 pages, expect 200-400 chunks typically
        expected_chunks_min = 200
        expected_chunks_max = 500
        if expected_chunks_min <= len(chunks) <= expected_chunks_max:
            completeness_score += 30
        elif len(chunks) < expected_chunks_min:
            completeness_score += max(0, 30 * len(chunks) / expected_chunks_min)
            issues.append(f"Chunk count ({len(chunks)}) lower than expected ({expected_chunks_min}-{expected_chunks_max})")
            recommendations.append("Check if chunking settings are too aggressive or document processing failed partially")
        else:
            completeness_score += 30  # More chunks than expected is usually good
        
        # Page coverage (25 points)
        if page_numbers:
            page_coverage_ratio = len(set(page_numbers)) / (max(page_numbers) - min(page_numbers) + 1)
            completeness_score += 25 * page_coverage_ratio
            
            if page_coverage_ratio < 0.95:
                issues.append(f"Page coverage: {page_coverage_ratio:.2%} - some pages might be missing")
                recommendations.append("Check for pages with only images, tables, or formatting issues")
        else:
            issues.append("No page number information available")
            recommendations.append("Enable page tracking in document processing")
        
        # Chunk sequence continuity (25 points)
        if chunk_indices:
            sequence_ratio = len(set(chunk_indices)) / (max(chunk_indices) - min(chunk_indices) + 1)
            completeness_score += 25 * sequence_ratio
            
            if sequence_ratio < 0.95:
                issues.append(f"Chunk sequence continuity: {sequence_ratio:.2%} - some chunks might be missing")
                recommendations.append("Check for processing errors or timeouts during indexing")
        else:
            issues.append("No chunk index information available")
            recommendations.append("Enable chunk indexing in document processing")
        
        # Content quality (20 points)
        avg_size = analysis["content_analysis"]["avg_chunk_size"]
        if 1000 <= avg_size <= 4000:  # Good chunk size range
            completeness_score += 20
        elif avg_size < 500:
            completeness_score += max(0, 20 * avg_size / 1000)
            issues.append(f"Average chunk size ({avg_size:.0f} chars) is quite small")
            recommendations.append("Check if content extraction is working properly")
        elif avg_size > 6000:
            completeness_score += 15  # Still good but might be too large
            issues.append(f"Average chunk size ({avg_size:.0f} chars) is quite large")
        
        analysis["completeness_assessment"] = {
            "score": round(completeness_score, 1),
            "grade": "EXCELLENT" if completeness_score >= 90 else 
                    "GOOD" if completeness_score >= 75 else
                    "FAIR" if completeness_score >= 60 else
                    "POOR",
            "issues": issues,
            "recommendations": recommendations
        }
        
        # 7. Display results
        print_analysis_results(analysis, verbose)
        
        return analysis
        
    except Exception as e:
        error_analysis = {
            "status": "ERROR",
            "error": str(e),
            "document_name": source_file,
            "index_name": index_name,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"❌ **ERROR**: {e}")
        return error_analysis

def print_analysis_results(analysis: Dict[str, Any], verbose: bool = False):
    """Print formatted analysis results."""
    
    print(f"\n📊 **ANALYSIS RESULTS**")
    print(f"Total Chunks: {analysis['total_chunks']}")
    
    # Page coverage
    if "page_coverage" in analysis:
        pc = analysis["page_coverage"]
        print(f"Page Range: {pc['page_range']} ({pc['total_pages_with_content']} pages with content)")
        
        if analysis.get("missing_pages_count", 0) > 0:
            print(f"⚠️  Missing Pages: {analysis['missing_pages_count']} pages")
            if verbose and "page_gaps" in analysis:
                print(f"   Page Gaps: {', '.join(analysis['page_gaps'])}")
    
    # Chunk sequence
    if "chunk_sequence" in analysis:
        cs = analysis["chunk_sequence"]
        print(f"Chunk Range: {cs['min_chunk']}-{cs['max_chunk']} ({cs['total_chunk_indices']} unique indices)")
        
        if analysis.get("missing_chunk_count", 0) > 0:
            print(f"⚠️  Missing Chunks: {analysis['missing_chunk_count']} chunk indices")
    
    # Content analysis
    ca = analysis["content_analysis"]
    print(f"Content: {ca['total_content_length']:,} chars total, {ca['avg_chunk_size']:.0f} avg per chunk")
    
    if ca["very_small_chunks"] > 0:
        print(f"⚠️  Very Small Chunks: {ca['very_small_chunks']} chunks < 100 chars")
    
    if ca["empty_chunks"] > 0:
        print(f"❌ Empty Chunks: {ca['empty_chunks']} chunks with no content")
    
    # Completeness assessment
    assessment = analysis["completeness_assessment"]
    score = assessment["score"]
    grade = assessment["grade"]
    
    print(f"\n🎯 **COMPLETENESS SCORE: {score}/100 ({grade})**")
    
    if assessment["issues"]:
        print(f"\n⚠️  **ISSUES DETECTED:**")
        for i, issue in enumerate(assessment["issues"], 1):
            print(f"   {i}. {issue}")
    
    if assessment["recommendations"]:
        print(f"\n💡 **RECOMMENDATIONS:**")
        for i, rec in enumerate(assessment["recommendations"], 1):
            print(f"   {i}. {rec}")
    
    # Overall verdict
    print(f"\n📋 **VERDICT:**")
    if score >= 90:
        print("✅ **EXCELLENT** - Document appears to be fully indexed with high confidence")
    elif score >= 75:
        print("✅ **GOOD** - Document is well indexed with minor potential issues")
    elif score >= 60:
        print("⚠️  **FAIR** - Document is partially indexed, some content may be missing")
    else:
        print("❌ **POOR** - Significant portions of the document may be missing")

def compare_with_expected_800_page_doc(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Compare results with expectations for an 800-page document."""
    
    comparison = {
        "document_type": "800-page Word document",
        "expectations": {
            "typical_chunk_count": "200-400 chunks",
            "typical_chunk_size": "1500-3000 characters",
            "expected_pages": "1-800",
            "processing_time": "2-5 minutes"
        },
        "actual_vs_expected": {}
    }
    
    # Chunk count comparison
    actual_chunks = analysis.get("total_chunks", 0)
    if 200 <= actual_chunks <= 400:
        comparison["actual_vs_expected"]["chunk_count"] = "✅ Within expected range"
    elif actual_chunks < 200:
        comparison["actual_vs_expected"]["chunk_count"] = "⚠️  Lower than expected - possible processing issues"
    else:
        comparison["actual_vs_expected"]["chunk_count"] = "📈 Higher than expected - fine granularity chunking"
    
    # Page coverage
    if "page_coverage" in analysis:
        max_page = analysis["page_coverage"]["max_page"]
        if max_page >= 700:  # Allow for some variation in page count
            comparison["actual_vs_expected"]["page_coverage"] = "✅ Full document coverage detected"
        else:
            comparison["actual_vs_expected"]["page_coverage"] = f"⚠️  Only reaches page {max_page} - may be incomplete"
    
    # Content size
    total_content = analysis.get("content_analysis", {}).get("total_content_length", 0)
    if total_content > 500000:  # 500KB+ expected for 800 pages
        comparison["actual_vs_expected"]["content_volume"] = "✅ Substantial content volume"
    else:
        comparison["actual_vs_expected"]["content_volume"] = "⚠️  Content volume lower than expected"
    
    return comparison

def main():
    parser = argparse.ArgumentParser(description="Verify document indexing completeness")
    parser.add_argument("--index", required=True, help="Azure Search index name")
    parser.add_argument("--file", required=True, help="Source document filename")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    try:
        # Perform analysis
        analysis = analyze_document_completeness(args.index, args.file, args.verbose)
        
        # Add 800-page document comparison
        if "800" in args.file or "testdocs" in args.file.lower() or analysis.get("total_chunks", 0) > 100:
            comparison = compare_with_expected_800_page_doc(analysis)
            analysis["800_page_comparison"] = comparison
            
            print(f"\n📖 **800-PAGE DOCUMENT COMPARISON**")
            for key, value in comparison["actual_vs_expected"].items():
                print(f"   {key.replace('_', ' ').title()}: {value}")
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {args.output}")
        
        # Exit with appropriate code
        if analysis.get("completeness_assessment", {}).get("score", 0) >= 75:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Issues detected
            
    except KeyboardInterrupt:
        print("\n❌ Analysis interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        sys.exit(3)

if __name__ == "__main__":
    main()
