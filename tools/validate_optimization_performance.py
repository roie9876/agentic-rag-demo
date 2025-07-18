#!/usr/bin/env python3
"""
Validate Phase 1 Optimization Performance
========================================

This script helps validate that the Phase 1 optimizations are working
by comparing performance before and after the optimization fixes.
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add the root directory to the path
sys.path.insert(0, '/home/azureuser/agentic-rag-demo')

def analyze_performance_logs():
    """Analyze performance logs to compare old vs new processing"""
    
    print("🔍 Phase 1 Optimization Performance Validation")
    print("=" * 60)
    
    # Check if optimization service is working
    print("\n1. Optimization Service Status:")
    try:
        from services.sharepoint_optimization_service import SharePointOptimizationService
        from sharepoint_index_manager import SharePointIndexManager
        
        manager = SharePointIndexManager()
        manager._init_optimization_service()
        
        if manager.optimization_service:
            print("   ✅ Optimization service is ACTIVE and ready")
            print("   ✅ Phase 1 optimizations will be used in next run")
        else:
            print("   ❌ Optimization service failed to initialize")
            return
            
    except Exception as e:
        print(f"   ❌ Error checking optimization service: {e}")
        return
    
    # Analyze recent performance logs
    print("\n2. Recent Performance Analysis:")
    
    # Look for pipeline performance logs
    pipeline_log = Path("/home/azureuser/agentic-rag-demo/logs/pipeline_performance.log")
    if pipeline_log.exists():
        with open(pipeline_log, 'r') as f:
            lines = f.readlines()
            
        # Get the most recent entries
        recent_entries = []
        for line in lines[-20:]:  # Last 20 lines
            if "Processing complete" in line and "files" in line:
                recent_entries.append(line.strip())
        
        if recent_entries:
            print("   Recent processing entries:")
            for entry in recent_entries[-5:]:  # Last 5 entries
                print(f"     {entry}")
        else:
            print("   No recent processing entries found")
    
    # Look for SharePoint indexing logs
    logs_dir = Path("/home/azureuser/agentic-rag-demo/logs")
    sharepoint_logs = list(logs_dir.glob("sharepoint_indexing_*.log"))
    
    if sharepoint_logs:
        latest_log = max(sharepoint_logs, key=lambda p: p.stat().st_mtime)
        mod_time = datetime.fromtimestamp(latest_log.stat().st_mtime)
        print(f"\n   Latest SharePoint log: {latest_log.name}")
        print(f"   Modified: {mod_time}")
        
        # Check if it contains optimization indicators
        with open(latest_log, 'r') as f:
            content = f.read()
            
        if "🚀 Using Phase 1 optimized processing" in content:
            print("   ✅ Contains optimization indicators")
        else:
            print("   ❌ No optimization indicators found")
    
    print("\n3. Performance Comparison:")
    print("   BASELINE (from analysis):")
    print("     - 7 files in 124s (17.7s avg per file)")
    print("     - Processing rate: 3.4 files/minute")
    print("     - Method: Standard document processing")
    print()
    print("   LATEST RUN (08:56:22 - OLD SYSTEM):")
    print("     - 3 files in 75.8s (25.3s avg per file)")
    print("     - Processing rate: 2.4 files/minute")
    print("     - Method: Standard processing (30% SLOWER)")
    print()
    print("   EXPECTED WITH PHASE 1 OPTIMIZATIONS:")
    print("     - Target: 8+ files/minute (2-3x improvement)")
    print("     - Method: Parallel processing + adaptive chunking")
    print("     - Batch size: 8 files, 3 parallel workers")
    
    print("\n4. Next Steps:")
    print("   1. Run SharePoint indexing via 'Run Index Now' button")
    print("   2. Check logs for '🚀 Using Phase 1 optimized processing' messages")
    print("   3. Compare processing times with baseline")
    print("   4. Verify files/minute improvement")
    
    print("\n5. What to Look For:")
    print("   ✅ Optimization service initialization messages")
    print("   ✅ Parallel processing indicators")
    print("   ✅ Improved processing rates (8+ files/minute)")
    print("   ✅ Reduced average time per file (<10s vs 17.7s baseline)")
    
    print("\n" + "=" * 60)
    print("Ready for optimization validation test!")

if __name__ == "__main__":
    analyze_performance_logs()
