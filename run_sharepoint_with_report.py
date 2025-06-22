#!/usr/bin/env python3
"""
SharePoint Indexing Report Example
==================================
This script demonstrates how to run SharePoint indexing with detailed reporting.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from connectors.sharepoint.sharepoint_files_indexer import SharepointFilesIndexer

async def run_sharepoint_indexing_with_report():
    """Run SharePoint indexing and generate a detailed report."""
    
    # Check if SharePoint is configured
    if not os.getenv("SHAREPOINT_CONNECTOR_ENABLED", "false").lower() == "true":
        print("⚠️ SharePoint connector is not enabled.")
        print("Set SHAREPOINT_CONNECTOR_ENABLED=true in your .env file to enable it.")
        return
    
    print("🚀 Starting SharePoint indexing with detailed reporting...")
    print("-" * 60)
    
    # Create indexer instance
    indexer = SharepointFilesIndexer()
    
    # Run the indexing process
    try:
        report = await indexer.run()
        
        # The report is automatically printed by the indexer
        # But we can also access the data programmatically
        if report:
            print(f"\n💾 Report Data Available:")
            print(f"   • Processed: {report['summary']['processed_files']} files")
            print(f"   • Total Chunks: {report['summary']['total_chunks']}")
            print(f"   • Processing Time: {report['summary']['duration_seconds']} seconds")
            
            # Save report to file
            import json
            report_file = project_root / "sharepoint_indexing_report.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"   • Full report saved to: {report_file}")
            
    except Exception as e:
        print(f"❌ SharePoint indexing failed: {e}")
        return

if __name__ == "__main__":
    asyncio.run(run_sharepoint_indexing_with_report())
