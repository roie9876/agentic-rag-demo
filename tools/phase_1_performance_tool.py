#!/usr/bin/env python3
"""
Phase 1 Performance Comparison Tool
==================================

This tool helps you compare the performance of optimized vs standard SharePoint indexing.
It provides easy commands to test and analyze your improvements.
"""

import sys
import os
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

def show_baseline_metrics():
    """Display your established baseline metrics."""
    print("📊 Your Established Baseline Performance")
    print("=" * 45)
    
    baseline = {
        "files_processed": 7,
        "total_size_mb": 8.08,
        "total_time_seconds": 124.0,
        "total_chunks": 199,
        "avg_time_per_file": 17.7,
        "processing_rate_files_per_minute": 3.4,
        "avg_chunks_per_file": 28.4,
        "time_per_chunk": 0.62
    }
    
    print(f"Files Processed: {baseline['files_processed']}")
    print(f"Total Size: {baseline['total_size_mb']} MB")
    print(f"Total Time: {baseline['total_time_seconds']}s ({baseline['total_time_seconds']/60:.1f} minutes)")
    print(f"Total Chunks: {baseline['total_chunks']}")
    print(f"Average Time per File: {baseline['avg_time_per_file']}s")
    print(f"Processing Rate: {baseline['processing_rate_files_per_minute']} files/minute")
    print(f"Time per Chunk: {baseline['time_per_chunk']}s")
    
    print("\n🎯 Phase 1 Optimization Targets:")
    print(f"• Target Rate: {baseline['processing_rate_files_per_minute'] * 2.5:.1f} files/minute (2.5x improvement)")
    print(f"• Target Time per File: {baseline['avg_time_per_file'] / 2.5:.1f}s (2.5x faster)")
    print(f"• Target for Large Documents: <5 minutes for 800+ page docs")
    
    return baseline

def show_optimization_status():
    """Show current optimization configuration."""
    print("\n🚀 Phase 1 Optimization Status")
    print("=" * 35)
    
    # Check environment
    enabled = os.getenv("SHAREPOINT_OPTIMIZATION_ENABLED", "false").lower() == "true"
    print(f"Environment Variable: {'✅ Enabled' if enabled else '❌ Disabled'}")
    
    # Check files
    required_files = [
        "services/optimized_document_processor.py",
        "services/sharepoint_optimization_service.py"
    ]
    
    all_present = True
    for file_path in required_files:
        if (project_root / file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing!")
            all_present = False
    
    if enabled and all_present:
        print("\n🎉 Phase 1 Optimization is READY!")
        print("\nOptimization Features:")
        print("• Parallel processing (3 concurrent files)")
        print("• Adaptive chunking (1200-2000 chars)")
        print("• Batch processing (8 files per batch)")
        print("• Enhanced error handling")
        print("• Detailed performance monitoring")
    else:
        print("\n⚠️ Optimization not fully configured")

def simulate_performance_improvement():
    """Simulate expected performance improvements."""
    print("\n📈 Expected Performance Improvements")
    print("=" * 40)
    
    baseline_rate = 3.4  # files/minute
    baseline_time_per_file = 17.7  # seconds
    
    # Conservative estimate: 2.5x improvement
    optimized_rate = baseline_rate * 2.5
    optimized_time_per_file = baseline_time_per_file / 2.5
    
    print(f"Baseline Performance:")
    print(f"  • {baseline_rate} files/minute")
    print(f"  • {baseline_time_per_file}s per file")
    print(f"  • {baseline_time_per_file * 7:.0f}s for 7 files")
    
    print(f"\nExpected Optimized Performance:")
    print(f"  • {optimized_rate:.1f} files/minute ({optimized_rate/baseline_rate:.1f}x faster)")
    print(f"  • {optimized_time_per_file:.1f}s per file ({baseline_time_per_file/optimized_time_per_file:.1f}x faster)")
    print(f"  • {optimized_time_per_file * 7:.0f}s for 7 files (saves {(baseline_time_per_file - optimized_time_per_file) * 7:.0f}s)")
    
    print(f"\nLarge Document Projections:")
    print(f"  • 20MB file: ~{optimized_time_per_file * 2:.0f}s (was ~{baseline_time_per_file * 2:.0f}s)")
    print(f"  • 800+ page doc: ~3-4 minutes (was ~8-10 minutes)")

def test_readiness():
    """Test if system is ready for optimized processing."""
    print("\n🔧 System Readiness Check")
    print("=" * 30)
    
    checks = []
    
    # Environment variable
    enabled = os.getenv("SHAREPOINT_OPTIMIZATION_ENABLED", "false").lower() == "true"
    checks.append(("Environment Variable", enabled))
    
    # Required files
    files_exist = all((project_root / f).exists() for f in [
        "services/optimized_document_processor.py",
        "services/sharepoint_optimization_service.py",
        "sharepoint_index_manager.py"
    ])
    checks.append(("Required Files", files_exist))
    
    # Services directory
    services_dir = (project_root / "services").exists()
    checks.append(("Services Directory", services_dir))
    
    # Display results
    all_ready = True
    for check_name, status in checks:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {check_name}")
        if not status:
            all_ready = False
    
    if all_ready:
        print("\n🎉 System is READY for Phase 1 optimization!")
        print("\nTo test:")
        print("1. Use the SharePoint UI 'Run Index Now' button")
        print("2. Check the logs for optimization indicators")
        print("3. Compare processing times with baseline")
    else:
        print("\n⚠️ System not ready. Please fix the issues above.")
    
    return all_ready

def provide_testing_instructions():
    """Provide instructions for testing the optimizations."""
    print("\n📋 Testing Instructions")
    print("=" * 25)
    
    print("To test Phase 1 optimizations:")
    print()
    print("1. 🚀 **Start the Streamlit App:**")
    print("   streamlit run agentic-rag-demo.py")
    print()
    print("2. 📁 **Go to SharePoint Integration Tab**")
    print()
    print("3. 🗂️ **Select the Same Folder You Tested Before:**")
    print("   - Use the same 7-file folder for comparison")
    print("   - Or try a different folder with similar files")
    print()
    print("4. ▶️ **Click 'Run Index Now'**")
    print("   - The system will automatically use optimizations")
    print("   - Look for optimization indicators in the UI")
    print()
    print("5. 📊 **Check Performance Logs:**")
    print("   python3 tests/debug/debug_sharepoint_performance_analyzer.py")
    print()
    print("6. 🔍 **Compare Results:**")
    print("   - Baseline: 3.4 files/minute, 17.7s per file")
    print("   - Target: 8+ files/minute, <7s per file")
    print()
    print("7. 📈 **Monitor Improvements:**")
    print("   - Check for '🚀 Phase 1 Optimized' messages")
    print("   - Verify parallel processing is working")
    print("   - Compare total processing time")

def main():
    """Main menu for the performance comparison tool."""
    print("🚀 Phase 1 Performance Comparison Tool")
    print("=" * 42)
    
    while True:
        print("\nSelect an option:")
        print("1. 📊 Show Baseline Metrics")
        print("2. 🚀 Show Optimization Status") 
        print("3. 📈 Show Expected Improvements")
        print("4. 🔧 Test System Readiness")
        print("5. 📋 Testing Instructions")
        print("6. 🏃 Quick Performance Analysis")
        print("7. ❌ Exit")
        
        try:
            choice = input("\nEnter choice (1-7): ").strip()
            
            if choice == "1":
                show_baseline_metrics()
            elif choice == "2":
                show_optimization_status()
            elif choice == "3":
                simulate_performance_improvement()
            elif choice == "4":
                test_readiness()
            elif choice == "5":
                provide_testing_instructions()
            elif choice == "6":
                # Quick analysis
                os.system("python3 tests/debug/debug_sharepoint_performance_analyzer.py")
            elif choice == "7":
                print("\n👋 Happy optimizing!")
                break
            else:
                print("❌ Invalid choice. Please enter 1-7.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
