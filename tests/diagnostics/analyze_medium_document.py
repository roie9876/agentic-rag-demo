#!/usr/bin/env python3
"""
Enhanced Document Analysis for Medium-Sized Documents

This script provides more appropriate analysis for documents in the 20-100 page range,
like the Hebrew PDF document with 36 pages.
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

def analyze_medium_document(
    index_name: str, 
    source_file: str,
    expected_pages: int = None
) -> Dict[str, Any]:
    """
    Enhanced analysis for medium-sized documents (20-100 pages).
    """
    
    print(f"\n🔍 **ENHANCED DOCUMENT ANALYSIS FOR MEDIUM-SIZED DOCUMENTS**")
    print(f"📄 Document: {source_file}")
    print(f"🗂️  Index: {index_name}")
    print(f"⏰ Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        search_client = get_search_client(index_name)
        
        # Get all chunks for this document
        search_results = search_client.search(
            search_text="*",
            filter=f"source_file eq '{source_file}'",
            select=["id", "content", "source_file", "page_number", "extraction_method", "processing_timestamp"],
            top=1000,
            include_total_count=True
        )
        
        chunks = list(search_results)
        total_count = search_results.get_count()
        
        print(f"✅ Found {len(chunks)} chunks (Total available: {total_count})")
        
        if len(chunks) == 0:
            return {
                "status": "ERROR",
                "message": f"No chunks found for document '{source_file}' in index '{index_name}'"
            }
        
        # Analyze the document structure
        analysis = {
            "total_chunks": len(chunks),
            "document_name": source_file,
            "index_name": index_name,
            "analysis_timestamp": datetime.now().isoformat(),
        }
        
        # Detailed content analysis
        page_numbers = []
        content_lengths = []
        extraction_methods = set()
        processing_timestamps = set()
        
        sample_contents = []
        
        for chunk in chunks:
            page_num = chunk.get("page_number")
            if page_num is not None:
                page_numbers.append(int(page_num))
            
            content = chunk.get("content", "")
            content_lengths.append(len(content))
            
            method = chunk.get("extraction_method")
            if method:
                extraction_methods.add(method)
                
            timestamp = chunk.get("processing_timestamp")
            if timestamp:
                processing_timestamps.add(timestamp)
            
            # Collect samples for quality analysis
            if len(sample_contents) < 3:
                sample_contents.append({
                    "page": page_num,
                    "length": len(content),
                    "preview": content[:200] if content else "",
                    "method": method
                })
        
        # Page analysis
        if page_numbers:
            page_numbers.sort()
            analysis["page_analysis"] = {
                "min_page": min(page_numbers),
                "max_page": max(page_numbers),
                "total_pages": len(set(page_numbers)),
                "page_range": f"{min(page_numbers)}-{max(page_numbers)}",
                "chunks_per_page": len(chunks) / len(set(page_numbers)),
                "page_distribution": dict(Counter(page_numbers))
            }
        
        # Content quality analysis
        analysis["content_analysis"] = {
            "total_content_length": sum(content_lengths),
            "avg_chunk_size": sum(content_lengths) / len(content_lengths) if content_lengths else 0,
            "min_chunk_size": min(content_lengths) if content_lengths else 0,
            "max_chunk_size": max(content_lengths) if content_lengths else 0,
            "content_distribution": {
                "very_small": len([c for c in content_lengths if c < 500]),
                "small": len([c for c in content_lengths if 500 <= c < 1500]),
                "medium": len([c for c in content_lengths if 1500 <= c < 3000]),
                "large": len([c for c in content_lengths if c >= 3000])
            }
        }
        
        # Processing analysis
        analysis["processing_analysis"] = {
            "extraction_methods": list(extraction_methods),
            "processing_timestamps": list(processing_timestamps),
            "sample_contents": sample_contents
        }
        
        # Generate improved completeness assessment for medium documents
        print(f"\n🎯 **ENHANCED COMPLETENESS ASSESSMENT**")
        
        completeness_score = 0
        issues = []
        recommendations = []
        insights = []
        
        # Score based on different factors (out of 100)
        
        # Page coverage (40 points) - Most important for medium documents
        if page_numbers:
            expected_pages_count = expected_pages or max(page_numbers)
            page_coverage_ratio = len(set(page_numbers)) / expected_pages_count
            page_score = 40 * page_coverage_ratio
            completeness_score += page_score
            
            if page_coverage_ratio >= 0.95:
                insights.append(f"✅ Excellent page coverage: {len(set(page_numbers))}/{expected_pages_count} pages")
            elif page_coverage_ratio >= 0.85:
                insights.append(f"✅ Good page coverage: {len(set(page_numbers))}/{expected_pages_count} pages")
                recommendations.append("Check for any missing pages or processing gaps")
            else:
                issues.append(f"Page coverage: {page_coverage_ratio:.2%} - some pages might be missing")
        
        # Content density (30 points)
        avg_size = analysis["content_analysis"]["avg_chunk_size"]
        if avg_size >= 2000:  # Good density for medium documents
            content_score = 30
        elif avg_size >= 1500:
            content_score = 25
        elif avg_size >= 1000:
            content_score = 20
            issues.append(f"Content density could be better (avg: {avg_size:.0f} chars per chunk)")
        else:
            content_score = 10
            issues.append(f"Low content density (avg: {avg_size:.0f} chars per chunk)")
            recommendations.append("Check if document contains mostly images or tables")
        
        completeness_score += content_score
        
        # Chunking appropriateness (20 points)
        chunks_per_page = analysis["page_analysis"].get("chunks_per_page", 0)
        if chunks_per_page >= 2:  # Multiple chunks per page is good
            chunk_score = 20
            insights.append(f"✅ Good chunking granularity: {chunks_per_page:.1f} chunks per page")
        elif chunks_per_page >= 1:  # One chunk per page is acceptable for some documents
            chunk_score = 15
            insights.append(f"📄 Page-level chunking: {chunks_per_page:.1f} chunks per page")
            recommendations.append("Consider enabling more granular chunking if content is dense")
        else:
            chunk_score = 5
            issues.append(f"Unusual chunking pattern: {chunks_per_page:.1f} chunks per page")
        
        completeness_score += chunk_score
        
        # Processing quality (10 points)
        if extraction_methods:
            if any("multimodal" in method.lower() for method in extraction_methods):
                process_score = 10
                insights.append("✅ Advanced multimodal processing detected")
            elif any("document_intelligence" in method.lower() for method in extraction_methods):
                process_score = 8
                insights.append("✅ Document Intelligence processing detected")
            else:
                process_score = 6
        else:
            process_score = 5
            issues.append("No extraction method information available")
        
        completeness_score += process_score
        
        analysis["enhanced_assessment"] = {
            "score": round(completeness_score, 1),
            "grade": "EXCELLENT" if completeness_score >= 90 else 
                    "GOOD" if completeness_score >= 75 else
                    "FAIR" if completeness_score >= 60 else
                    "POOR",
            "issues": issues,
            "recommendations": recommendations,
            "insights": insights
        }
        
        # Display results
        print_enhanced_results(analysis)
        
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

def print_enhanced_results(analysis: Dict[str, Any]):
    """Print enhanced analysis results."""
    
    print(f"\n📊 **ENHANCED ANALYSIS RESULTS**")
    
    # Basic stats
    print(f"Total Chunks: {analysis['total_chunks']}")
    
    # Page analysis
    if "page_analysis" in analysis:
        pa = analysis["page_analysis"]
        print(f"Page Coverage: {pa['page_range']} ({pa['total_pages']} pages)")
        print(f"Chunking Density: {pa['chunks_per_page']:.1f} chunks per page")
    
    # Content analysis
    ca = analysis["content_analysis"]
    print(f"Content Volume: {ca['total_content_length']:,} characters")
    print(f"Average Chunk Size: {ca['avg_chunk_size']:.0f} characters")
    print(f"Size Range: {ca['min_chunk_size']}-{ca['max_chunk_size']} characters")
    
    # Content distribution
    cd = ca["content_distribution"]
    print(f"Size Distribution: {cd['small']} small, {cd['medium']} medium, {cd['large']} large chunks")
    
    # Processing info
    if "processing_analysis" in analysis:
        pa = analysis["processing_analysis"]
        if pa["extraction_methods"]:
            print(f"Processing Methods: {', '.join(pa['extraction_methods'])}")
    
    # Enhanced assessment
    assessment = analysis["enhanced_assessment"]
    score = assessment["score"]
    grade = assessment["grade"]
    
    print(f"\n🎯 **ENHANCED COMPLETENESS SCORE: {score}/100 ({grade})**")
    
    # Show insights first (positive feedback)
    if assessment["insights"]:
        print(f"\n✨ **KEY INSIGHTS:**")
        for i, insight in enumerate(assessment["insights"], 1):
            print(f"   {i}. {insight}")
    
    # Then issues if any
    if assessment["issues"]:
        print(f"\n⚠️  **ISSUES DETECTED:**")
        for i, issue in enumerate(assessment["issues"], 1):
            print(f"   {i}. {issue}")
    
    # Finally recommendations
    if assessment["recommendations"]:
        print(f"\n💡 **RECOMMENDATIONS:**")
        for i, rec in enumerate(assessment["recommendations"], 1):
            print(f"   {i}. {rec}")
    
    # Overall verdict
    print(f"\n📋 **ENHANCED VERDICT:**")
    if score >= 80:
        print("✅ **EXCELLENT** - Document is very well processed with high quality indexing")
        print("   This is appropriate chunking for a medium-sized document")
    elif score >= 65:
        print("✅ **GOOD** - Document is well processed with minor optimization opportunities")
        print("   Consider fine-tuning chunking settings for better retrieval if needed")
    elif score >= 50:
        print("⚠️  **FAIR** - Document is adequately processed but has room for improvement")
        print("   May benefit from reprocessing with adjusted settings")
    else:
        print("❌ **POOR** - Document processing has significant issues that need attention")

def main():
    parser = argparse.ArgumentParser(description="Enhanced analysis for medium-sized documents")
    parser.add_argument("--index", required=True, help="Azure Search index name")
    parser.add_argument("--file", required=True, help="Source document filename")
    parser.add_argument("--pages", type=int, help="Expected number of pages in document")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    try:
        # Perform enhanced analysis
        analysis = analyze_medium_document(args.index, args.file, args.pages)
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, default=str, ensure_ascii=False)
            print(f"\n💾 Results saved to: {args.output}")
        
        # Exit with appropriate code
        score = analysis.get("enhanced_assessment", {}).get("score", 0)
        if score >= 65:
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
