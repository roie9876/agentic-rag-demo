"""
SharePoint Optimization UI Components - Phase 1
==============================================

UI components for displaying and controlling SharePoint indexing optimizations.
"""

import streamlit as st
from typing import Dict, Any, Optional
import logging


def display_optimization_status(sharepoint_manager) -> None:
    """Display the current optimization status in the Streamlit UI."""
    
    try:
        status = sharepoint_manager.get_optimization_status()
        
        # Create an expander for optimization details
        with st.expander("🚀 Phase 1 Optimization Status", expanded=False):
            
            if not status.get("available", False):
                st.error("❌ Optimization service not available")
                st.write(status.get("message", "Unknown error"))
                return
            
            if not status.get("enabled", False):
                st.warning("⚠️ Optimization disabled")
                st.write(status.get("message", "Optimization is disabled"))
                
                # Add button to enable optimization if possible
                if st.button("🔧 Try to Enable Optimization"):
                    try:
                        sharepoint_manager.optimization_enabled = True
                        sharepoint_manager._init_optimization_service()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to enable optimization: {e}")
                return
            
            # Optimization is available and enabled
            st.success("✅ Phase 1 Optimization Active")
            
            # Display configuration
            config = status.get("configuration", {})
            if config:
                st.subheader("📋 Configuration")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Max Parallel Files", config.get("max_parallel_files", "N/A"))
                    st.metric("Chunk Size", f"{config.get('optimal_chunk_size', 'N/A')} chars")
                    st.metric("Batch Size", config.get("batch_size", "N/A"))
                
                with col2:
                    st.metric("Chunk Overlap", f"{config.get('chunk_overlap', 'N/A')} chars")
                    adaptive = "✅ Enabled" if config.get("adaptive_chunking", False) else "❌ Disabled"
                    st.write(f"**Adaptive Chunking:** {adaptive}")
            
            # Display expected improvements
            improvements = status.get("expected_improvements", {})
            if improvements:
                st.subheader("🎯 Expected Performance Gains")
                
                for improvement, description in improvements.items():
                    if improvement != "overall_estimate":
                        st.write(f"• **{improvement.replace('_', ' ').title()}:** {description}")
                
                overall = improvements.get("overall_estimate", "Unknown")
                st.info(f"🚀 **Overall Expected Improvement:** {overall}")
    
    except Exception as e:
        st.error(f"Error displaying optimization status: {e}")
        logging.error(f"Error displaying optimization status: {e}")


def display_performance_comparison(
    baseline_metrics: Optional[Dict[str, Any]] = None,
    optimized_metrics: Optional[Dict[str, Any]] = None,
    sharepoint_manager=None
) -> None:
    """Display performance comparison between baseline and optimized processing."""
    
    if not baseline_metrics or not optimized_metrics:
        return
    
    try:
        comparison = sharepoint_manager.optimization_service.compare_performance(
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics
        )
        
        if "error" in comparison:
            st.error(f"Performance comparison error: {comparison['error']}")
            return
        
        st.subheader("📊 Performance Comparison")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Baseline Rate",
                f"{comparison.get('baseline_rate', 0):.1f} files/min",
            )
        
        with col2:
            st.metric(
                "Optimized Rate", 
                f"{comparison.get('optimized_rate', 0):.1f} files/min",
                delta=f"+{comparison.get('improvement_percentage', 0):.1f}%"
            )
        
        with col3:
            st.metric(
                "Improvement Factor",
                f"{comparison.get('improvement_factor', 1):.1f}x"
            )
        
        # Time savings
        time_savings = comparison.get("time_savings", {})
        if time_savings:
            st.info(
                f"⏱️ **Time Saved per File:** {time_savings.get('per_file', 0):.1f}s "
                f"({time_savings.get('percentage', 0):.1f}% faster)"
            )
    
    except Exception as e:
        st.error(f"Error displaying performance comparison: {e}")


def optimization_controls_sidebar(sharepoint_manager) -> Dict[str, Any]:
    """Add optimization controls to the sidebar."""
    
    with st.sidebar:
        st.subheader("🚀 Phase 1 Optimizations")
        
        try:
            status = sharepoint_manager.get_optimization_status()
            
            if status.get("available", False) and status.get("enabled", False):
                st.success("✅ Active")
                
                # Add control to disable optimization
                if st.button("🔧 Disable Optimization"):
                    sharepoint_manager.optimization_enabled = False
                    sharepoint_manager.optimization_service = None
                    st.rerun()
                
                # Display quick stats
                config = status.get("configuration", {})
                if config:
                    st.write(f"**Parallel Files:** {config.get('max_parallel_files', 'N/A')}")
                    st.write(f"**Chunk Size:** {config.get('optimal_chunk_size', 'N/A')}")
                
            elif status.get("available", False):
                st.warning("⚠️ Disabled")
                
                if st.button("🚀 Enable Optimization"):
                    sharepoint_manager.optimization_enabled = True
                    sharepoint_manager._init_optimization_service()
                    st.rerun()
            
            else:
                st.error("❌ Not Available")
                st.caption(status.get("message", "Unknown issue"))
        
        except Exception as e:
            st.error(f"Optimization controls error: {e}")
    
    return status if 'status' in locals() else {}


def display_processing_results_with_optimization(results: Dict[str, Any]) -> None:
    """Display processing results with optimization information."""
    
    if not results:
        return
    
    # Check if optimization was used
    optimization_used = results.get("optimization_used", False)
    
    if optimization_used:
        st.success("🚀 Processed with Phase 1 Optimizations")
        
        # Display performance metrics
        performance = results.get("performance_metrics", {})
        if performance:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                success_rate = performance.get("success_rate", 0)
                st.metric("Success Rate", f"{success_rate:.1f}%")
            
            with col2:
                avg_time = performance.get("avg_time_per_file", 0)
                st.metric("Avg Time/File", f"{avg_time:.1f}s")
            
            with col3:
                processing_rate = performance.get("processing_rate_files_per_minute", 0)
                st.metric("Processing Rate", f"{processing_rate:.1f} files/min")
            
            # Show improvement estimate
            improvement = performance.get("estimated_improvement_vs_baseline", 1)
            if improvement > 1:
                st.info(f"🎯 **Estimated {improvement:.1f}x faster** than baseline processing")
    
    else:
        st.info("📝 Processed with standard method")
    
    # Display standard results
    total_files = results.get("total_files", len(results.get("processing_results", [])))
    successful = results.get("files_successful", len([r for r in results.get("processing_results", []) if r.get("status") == "success"]))
    failed = results.get("files_failed", len([r for r in results.get("processing_results", []) if r.get("status") == "failed"]))
    chunks = results.get("total_chunks", 0)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Files", total_files)
    
    with col2:
        st.metric("Successful", successful, delta=None if failed == 0 else f"-{failed}")
    
    with col3:
        st.metric("Failed", failed, delta=None if failed == 0 else "failed", delta_color="inverse")
    
    with col4:
        st.metric("Total Chunks", chunks)
    
    # Show processing time if available
    processing_time = results.get("processing_time", 0)
    if processing_time > 0:
        st.metric("Processing Time", f"{processing_time:.1f}s")


def phase_1_info_box() -> None:
    """Display information about Phase 1 optimizations."""
    
    st.info("""
    **🚀 Phase 1 Optimizations Active**
    
    This system now includes performance optimizations:
    - **Parallel Processing:** Multiple files processed simultaneously
    - **Optimized Chunking:** Adaptive chunk sizes based on file characteristics  
    - **Batch Processing:** Memory-efficient handling of large document sets
    - **Enhanced Monitoring:** Detailed performance tracking and analysis
    
    Expected performance improvement: **2-3x faster** than baseline processing.
    """)
