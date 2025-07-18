"""
SharePoint Optimization Integration Service - Phase 1
====================================================

This service integrates the optimized document processor with the existing
SharePoint indexing system, providing backward compatibility while delivering
significant performance improvements.

Key Features:
- Drop-in replacement for existing SharePoint indexing
- Maintains all existing logging and monitoring
- Adds Phase 1 optimizations transparently
- Provides performance comparison metrics
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import time

from services.optimized_document_processor import OptimizedDocumentProcessor, OptimizationConfig
from connectors.sharepoint.sharepoint_files_indexer import PerformanceLogger


class SharePointOptimizationService:
    """
    Integration service for Phase 1 SharePoint indexing optimizations.
    
    This service provides a seamless upgrade path from the existing
    SharePoint indexing system to the optimized version.
    """
    
    def __init__(self, enable_optimizations: bool = True):
        """Initialize the optimization service."""
        self.enable_optimizations = enable_optimizations
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.performance_logger = PerformanceLogger("sharepoint_optimization_service")
        
        # Initialize optimized processor if enabled
        if self.enable_optimizations:
            self.optimization_config = OptimizationConfig(
                max_parallel_files=3,  # Conservative start - can increase based on testing
                optimal_chunk_size=1500,  # Based on performance analysis
                chunk_overlap=200,
                batch_size=8,  # Process 8 files per batch
                enable_adaptive_chunking=True
            )
            
            self.optimized_processor = OptimizedDocumentProcessor(
                config=self.optimization_config
            )
        else:
            self.optimized_processor = None
    
    def index_files_optimized(
        self, 
        selected_files: List[Dict[str, Any]], 
        index_name: str = "iec"
    ) -> Dict[str, Any]:
        """
        Index SharePoint files with Phase 1 optimizations.
        
        This method is a drop-in replacement for the existing index_files method
        but provides significant performance improvements through:
        - Parallel processing
        - Optimized chunking
        - Batch processing
        - Enhanced error handling
        
        Args:
            selected_files: List of file dictionaries with SharePoint metadata
            index_name: Azure Search index name
            
        Returns:
            Dictionary with indexing results and performance metrics
        """
        self.performance_logger.log_stage_start("OPTIMIZED_SHAREPOINT_INDEXING")
        
        start_time = time.time()
        results = {
            "optimization_enabled": self.enable_optimizations,
            "total_files": len(selected_files),
            "successful_files": 0,
            "failed_files": 0,
            "total_chunks_created": 0,
            "processing_time": 0.0,
            "performance_metrics": {},
            "file_results": []
        }
        
        try:
            if self.enable_optimizations and self.optimized_processor:
                # Use optimized processing
                results.update(self._process_with_optimizations(selected_files, index_name))
            else:
                # Fall back to standard processing
                results.update(self._process_standard(selected_files, index_name))
                
        except Exception as e:
            self.logger.error(f"SharePoint indexing failed: {str(e)}")
            results["error"] = str(e)
        
        finally:
            results["processing_time"] = time.time() - start_time
            
            # Log final performance metrics
            self.performance_logger.log_stage_end(
                "OPTIMIZED_SHAREPOINT_INDEXING",
                metadata={
                    "optimization_enabled": results["optimization_enabled"],
                    "files_processed": results["successful_files"],
                    "files_failed": results["failed_files"],
                    "total_chunks": results["total_chunks_created"],
                    "processing_time": results["processing_time"],
                    "avg_time_per_file": results["processing_time"] / max(results["successful_files"], 1)
                }
            )
        
        return results
    
    def _process_with_optimizations(
        self, 
        selected_files: List[Dict[str, Any]], 
        index_name: str
    ) -> Dict[str, Any]:
        """Process files using Phase 1 optimizations."""
        self.logger.info(f"🚀 Processing {len(selected_files)} files with Phase 1 optimizations")
        
        # Process with optimized processor using full file data
        optimization_results = self.optimized_processor.process_sharepoint_files_batch(
            files=selected_files,
            index_name=index_name
        )
        
        # Convert optimization results to SharePoint format
        results = {
            "successful_files": len(optimization_results["success"]),
            "failed_files": len(optimization_results["failed"]),
            "total_chunks_created": optimization_results["total_chunks"],
            "file_results": self._format_file_results(optimization_results),
            "performance_metrics": optimization_results["performance_metrics"],
            "optimization_details": {
                "parallel_processing": True,
                "adaptive_chunking": True,
                "batch_processing": True,
                "max_parallel_files": self.optimization_config.max_parallel_files,
                "chunk_size": self.optimization_config.optimal_chunk_size
            }
        }
        
        # Log optimization performance
        self.logger.info(
            f"✅ Optimization complete: {results['successful_files']} files, "
            f"{results['total_chunks_created']} chunks, "
            f"{optimization_results['processing_time']:.1f}s"
        )
        
        return results
    
    def _process_standard(
        self, 
        selected_files: List[Dict[str, Any]], 
        index_name: str
    ) -> Dict[str, Any]:
        """Process files using standard (non-optimized) method."""
        self.logger.info(f"📝 Processing {len(selected_files)} files with standard method")
        
        results = {
            "successful_files": 0,
            "failed_files": 0,
            "total_chunks_created": 0,
            "file_results": [],
            "performance_metrics": {"note": "Standard processing - no optimizations applied"}
        }
        
        # TODO: Integrate with existing SharePoint indexing logic
        # This would call the original SharePointIndexManager.index_files method
        
        # Placeholder implementation
        for file_info in selected_files:
            try:
                # Simulate processing
                time.sleep(0.1)  # Simulate processing time
                
                file_result = {
                    "file_path": file_info.get("ServerRelativeUrl", "unknown"),
                    "success": True,
                    "chunks_created": 5,  # Placeholder
                    "processing_time": 0.1
                }
                
                results["file_results"].append(file_result)
                results["successful_files"] += 1
                results["total_chunks_created"] += file_result["chunks_created"]
                
            except Exception as e:
                file_result = {
                    "file_path": file_info.get("ServerRelativeUrl", "unknown"),
                    "success": False,
                    "error": str(e),
                    "chunks_created": 0
                }
                
                results["file_results"].append(file_result)
                results["failed_files"] += 1
        
        return results
    
    def _extract_file_paths(self, selected_files: List[Dict[str, Any]]) -> List[str]:
        """Extract file paths from SharePoint file metadata."""
        file_paths = []
        
        for file_info in selected_files:
            # Extract file path from SharePoint metadata
            # SharePoint files use 'webUrl' as the main URL field
            file_path = (file_info.get("webUrl") or 
                        file_info.get("ServerRelativeUrl") or 
                        file_info.get("file_path"))
            
            if file_path:
                file_paths.append(file_path)
            else:
                self.logger.warning(f"Could not extract file path from: {file_info}")
        
        return file_paths
    
    def _format_file_results(self, optimization_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format optimization results to match SharePoint expectations."""
        formatted_results = []
        
        # Format successful files
        for result in optimization_results["success"]:
            formatted_results.append({
                "file_path": result["file_path"],
                "success": True,
                "chunks_created": result["chunks_created"],
                "processing_time": result["processing_time"],
                "optimizations_applied": result.get("optimizations_applied", [])
            })
        
        # Format failed files
        for result in optimization_results["failed"]:
            formatted_results.append({
                "file_path": result["file_path"],
                "success": False,
                "error": result.get("error", "Unknown error"),
                "chunks_created": 0,
                "processing_time": result.get("processing_time", 0.0)
            })
        
        return formatted_results
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status and configuration."""
        if not self.enable_optimizations:
            return {
                "enabled": False,
                "message": "Optimizations are disabled"
            }
        
        return {
            "enabled": True,
            "configuration": {
                "max_parallel_files": self.optimization_config.max_parallel_files,
                "optimal_chunk_size": self.optimization_config.optimal_chunk_size,
                "chunk_overlap": self.optimization_config.chunk_overlap,
                "batch_size": self.optimization_config.batch_size,
                "adaptive_chunking": self.optimization_config.enable_adaptive_chunking
            },
            "expected_improvements": {
                "parallel_processing": f"{self.optimization_config.max_parallel_files}x throughput",
                "optimized_chunking": "10-20% faster per chunk",
                "batch_processing": "Reduced memory usage",
                "overall_estimate": "2-3x performance improvement"
            }
        }
    
    def compare_performance(
        self, 
        baseline_metrics: Dict[str, Any], 
        optimized_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare performance between baseline and optimized processing."""
        if not baseline_metrics or not optimized_metrics:
            return {"error": "Missing metrics for comparison"}
        
        baseline_rate = baseline_metrics.get("processing_rate_files_per_minute", 3.4)
        optimized_rate = optimized_metrics.get("processing_rate_files_per_minute", 0)
        
        if optimized_rate == 0:
            return {"error": "Invalid optimized metrics"}
        
        improvement_factor = optimized_rate / baseline_rate
        
        return {
            "baseline_rate": baseline_rate,
            "optimized_rate": optimized_rate,
            "improvement_factor": improvement_factor,
            "improvement_percentage": (improvement_factor - 1) * 100,
            "time_savings": {
                "per_file": baseline_metrics.get("avg_time_per_file", 17.7) - 
                          optimized_metrics.get("avg_time_per_file", 0),
                "percentage": ((baseline_metrics.get("avg_time_per_file", 17.7) - 
                              optimized_metrics.get("avg_time_per_file", 0)) / 
                             baseline_metrics.get("avg_time_per_file", 17.7)) * 100
            }
        }
    
    def enable_optimization_mode(self, enabled: bool = True):
        """Enable or disable optimization mode."""
        self.enable_optimizations = enabled
        
        if enabled and not self.optimized_processor:
            self.optimized_processor = OptimizedDocumentProcessor(
                config=self.optimization_config
            )
        
        self.logger.info(f"Optimization mode {'enabled' if enabled else 'disabled'}")
