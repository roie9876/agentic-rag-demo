#!/usr/bin/env python3
"""
Diagnostic Script: Index Consistency Checker
Purpose: Compare two indexes to identify why they have different chunk counts for the same content
Usage: python3 tests/diagnostics/diagnose_index_consistency.py
"""

import os
import sys
import json
from typing import Dict, List, Any, Tuple
from collections import defaultdict, Counter
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.core.exceptions import ResourceNotFoundError

def get_search_client(index_name: str) -> SearchClient:
    """Create a SearchClient for the given index"""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    if not search_endpoint:
        raise ValueError("AZURE_SEARCH_ENDPOINT environment variable not set")
    
    credential = DefaultAzureCredential()
    return SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)

def analyze_index_content(index_name: str, folder_filter: str = "Malan") -> Dict[str, Any]:
    """
    Analyze index content and return comprehensive statistics
    """
    print(f"\n🔍 Analyzing index: {index_name}")
    
    try:
        client = get_search_client(index_name)
        
        # Get all documents with wildcard search
        all_results = client.search(
            search_text="*",
            top=1000,  # Increase limit to catch all chunks
            select=["doc_key", "source_file", "content", "chunk_id", "url", "title", "source"]
        )
        
        documents = list(all_results)
        print(f"📊 Total documents in index: {len(documents)}")
        
        # Filter by folder if specified
        filtered_docs = []
        if folder_filter:
            for doc in documents:
                source_file = doc.get("source_file", "")
                url = doc.get("url", "")
                
                # Check if document is from the specified folder
                if (folder_filter.lower() in source_file.lower() or 
                    folder_filter.lower() in url.lower()):
                    filtered_docs.append(doc)
            
            print(f"📁 Documents from '{folder_filter}' folder: {len(filtered_docs)}")
        else:
            filtered_docs = documents
        
        # Analyze filtered documents
        analysis = {
            "index_name": index_name,
            "total_chunks": len(filtered_docs),
            "folder_filter": folder_filter,
            "files_analysis": {},
            "chunk_size_distribution": Counter(),
            "unique_files": set(),
            "duplicate_chunks": [],
            "missing_metadata": [],
            "content_hashes": {}
        }
        
        # Group by source file
        files_data = defaultdict(list)
        for doc in filtered_docs:
            source_file = doc.get("source_file", "unknown")
            analysis["unique_files"].add(source_file)
            files_data[source_file].append(doc)
            
            # Check for missing metadata
            if not doc.get("doc_key"):
                analysis["missing_metadata"].append({
                    "issue": "missing_doc_key",
                    "source_file": source_file
                })
            
            # Analyze content size
            content = doc.get("content", "")
            content_size = len(content)
            size_bucket = f"{(content_size // 500) * 500}-{(content_size // 500 + 1) * 500}"
            analysis["chunk_size_distribution"][size_bucket] += 1
            
            # Check for duplicate content (simplified hash)
            content_hash = hash(content[:200])  # Hash first 200 chars
            if content_hash in analysis["content_hashes"]:
                analysis["duplicate_chunks"].append({
                    "source_file": source_file,
                    "duplicate_of": analysis["content_hashes"][content_hash],
                    "content_preview": content[:100]
                })
            else:
                analysis["content_hashes"][content_hash] = source_file
        
        # Analyze each file
        for source_file, docs in files_data.items():
            analysis["files_analysis"][source_file] = {
                "chunk_count": len(docs),
                "total_content_size": sum(len(doc.get("content", "")) for doc in docs),
                "has_doc_keys": all(doc.get("doc_key") for doc in docs),
                "has_urls": all(doc.get("url") for doc in docs),
                "chunk_ids": [doc.get("chunk_id", "no_id") for doc in docs[:5]]  # First 5 chunk IDs
            }
        
        return analysis
        
    except ResourceNotFoundError:
        print(f"❌ Index '{index_name}' not found")
        return {"error": f"Index '{index_name}' not found"}
    except Exception as e:
        print(f"❌ Error analyzing index '{index_name}': {str(e)}")
        return {"error": str(e)}

def compare_indexes(index1_analysis: Dict, index2_analysis: Dict) -> Dict[str, Any]:
    """
    Compare two index analyses and identify discrepancies
    """
    comparison = {
        "chunk_count_difference": index2_analysis["total_chunks"] - index1_analysis["total_chunks"],
        "file_differences": {},
        "potential_issues": [],
        "recommendations": []
    }
    
    # Compare file-by-file
    files1 = set(index1_analysis["files_analysis"].keys())
    files2 = set(index2_analysis["files_analysis"].keys())
    
    # Files only in one index
    only_in_index1 = files1 - files2
    only_in_index2 = files2 - files1
    common_files = files1 & files2
    
    if only_in_index1:
        comparison["potential_issues"].append(f"Files only in {index1_analysis['index_name']}: {list(only_in_index1)}")
    
    if only_in_index2:
        comparison["potential_issues"].append(f"Files only in {index2_analysis['index_name']}: {list(only_in_index2)}")
    
    # Compare common files
    for file_name in common_files:
        file1 = index1_analysis["files_analysis"][file_name]
        file2 = index2_analysis["files_analysis"][file_name]
        
        chunk_diff = file2["chunk_count"] - file1["chunk_count"]
        if chunk_diff != 0:
            comparison["file_differences"][file_name] = {
                f"{index1_analysis['index_name']}_chunks": file1["chunk_count"],
                f"{index2_analysis['index_name']}_chunks": file2["chunk_count"],
                "difference": chunk_diff,
                f"{index1_analysis['index_name']}_total_size": file1["total_content_size"],
                f"{index2_analysis['index_name']}_total_size": file2["total_content_size"]
            }
    
    # Generate recommendations based on findings
    if comparison["chunk_count_difference"] > 0:
        comparison["recommendations"].extend([
            f"🔍 {index2_analysis['index_name']} has {comparison['chunk_count_difference']} more chunks",
            "💡 Check if chunking strategies or parameters differ between indexes",
            "💡 Verify if indexing was completed for both indexes",
            "💡 Check for different document processing pipelines"
        ])
    
    if len(comparison["file_differences"]) > 0:
        comparison["recommendations"].append(
            "💡 Some files have different chunk counts - check chunking configuration"
        )
    
    if index1_analysis.get("duplicate_chunks") or index2_analysis.get("duplicate_chunks"):
        comparison["recommendations"].append(
            "⚠️  Duplicate chunks detected - check for re-indexing issues"
        )
    
    if index1_analysis.get("missing_metadata") or index2_analysis.get("missing_metadata"):
        comparison["recommendations"].append(
            "⚠️  Missing metadata detected - check indexing pipeline configuration"
        )
    
    return comparison

def print_analysis_summary(analysis: Dict[str, Any]):
    """Print a formatted summary of the analysis"""
    if "error" in analysis:
        print(f"❌ Error: {analysis['error']}")
        return
    
    print(f"\n📊 Index Analysis Summary: {analysis['index_name']}")
    print("=" * 60)
    print(f"Total chunks in '{analysis['folder_filter']}' folder: {analysis['total_chunks']}")
    print(f"Unique files: {len(analysis['unique_files'])}")
    
    print(f"\n📁 Files breakdown:")
    for file_name, file_data in analysis['files_analysis'].items():
        print(f"  • {file_name}: {file_data['chunk_count']} chunks ({file_data['total_content_size']} chars)")
    
    print(f"\n📏 Chunk size distribution:")
    for size_range, count in analysis['chunk_size_distribution'].most_common(5):
        print(f"  • {size_range} chars: {count} chunks")
    
    if analysis['duplicate_chunks']:
        print(f"\n⚠️  Found {len(analysis['duplicate_chunks'])} potential duplicate chunks")
    
    if analysis['missing_metadata']:
        print(f"\n⚠️  Found {len(analysis['missing_metadata'])} chunks with missing metadata")

def print_comparison_summary(comparison: Dict[str, Any]):
    """Print a formatted comparison summary"""
    print(f"\n🔍 Index Comparison Results")
    print("=" * 60)
    print(f"Chunk count difference: {comparison['chunk_count_difference']}")
    
    if comparison['file_differences']:
        print(f"\n📄 File-by-file differences:")
        for file_name, diff in comparison['file_differences'].items():
            print(f"  • {file_name}:")
            for key, value in diff.items():
                if key != 'difference':
                    print(f"    - {key}: {value}")
    
    if comparison['potential_issues']:
        print(f"\n⚠️  Potential Issues:")
        for issue in comparison['potential_issues']:
            print(f"  • {issue}")
    
    if comparison['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in comparison['recommendations']:
            print(f"  {rec}")

def check_index_schema_differences(index1_name: str, index2_name: str) -> Dict[str, Any]:
    """
    Check if the two indexes have different schemas that could affect chunking
    """
    try:
        from azure.search.documents.indexes import SearchIndexClient
        
        credential = DefaultAzureCredential()
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        
        # Get index definitions
        try:
            index1_def = index_client.get_index(index1_name)
            index2_def = index_client.get_index(index2_name)
            
            schema_comparison = {
                "index1_fields": len(index1_def.fields),
                "index2_fields": len(index2_def.fields),
                "field_differences": [],
                "analyzer_differences": []
            }
            
            # Compare field names
            fields1 = {field.name: field for field in index1_def.fields}
            fields2 = {field.name: field for field in index2_def.fields}
            
            all_fields = set(fields1.keys()) | set(fields2.keys())
            for field_name in all_fields:
                if field_name in fields1 and field_name in fields2:
                    field1 = fields1[field_name]
                    field2 = fields2[field_name]
                    if field1.type != field2.type:
                        schema_comparison["field_differences"].append(
                            f"{field_name}: {field1.type} vs {field2.type}"
                        )
                elif field_name in fields1 and field_name not in fields2:
                    schema_comparison["field_differences"].append(f"{field_name}: only in {index1_name}")
                elif field_name in fields2 and field_name not in fields1:
                    schema_comparison["field_differences"].append(f"{field_name}: only in {index2_name}")
            
            return schema_comparison
            
        except Exception as e:
            return {"error": f"Could not compare schemas: {str(e)}"}
            
    except ImportError:
        return {"error": "azure-search-documents[management] not available for schema comparison"}

def main():
    """Main diagnostic function"""
    print("🔍 Azure Search Index Consistency Diagnostic")
    print("=" * 50)
    
    # Configuration
    index1_name = "deleteme"
    index2_name = "bicep23" 
    folder_name = "Malan"
    
    print(f"Comparing indexes:")
    print(f"  📋 Index 1: {index1_name}")
    print(f"  📋 Index 2: {index2_name}")
    print(f"  📁 Folder filter: {folder_name}")
    
    # Analyze both indexes
    print(f"\n🔄 Starting analysis...")
    
    analysis1 = analyze_index_content(index1_name, folder_name)
    analysis2 = analyze_index_content(index2_name, folder_name)
    
    # Print individual summaries
    print_analysis_summary(analysis1)
    print_analysis_summary(analysis2)
    
    # Compare indexes
    if "error" not in analysis1 and "error" not in analysis2:
        comparison = compare_indexes(analysis1, analysis2)
        print_comparison_summary(comparison)
        
        # Check schema differences
        print(f"\n🔧 Checking schema differences...")
        schema_comparison = check_index_schema_differences(index1_name, index2_name)
        if "error" not in schema_comparison:
            print(f"Schema fields: {schema_comparison['index1_fields']} vs {schema_comparison['index2_fields']}")
            if schema_comparison["field_differences"]:
                print("Schema differences found:")
                for diff in schema_comparison["field_differences"]:
                    print(f"  • {diff}")
        else:
            print(f"Schema comparison failed: {schema_comparison['error']}")
    
    print(f"\n✅ Diagnostic complete!")

if __name__ == "__main__":
    main()
